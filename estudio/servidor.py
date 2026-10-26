"""Servidor local del estudio (solo biblioteca estándar): API JSON + eventos SSE + ficheros estáticos.

Escucha únicamente en 127.0.0.1. Como puede lanzar agentes con acceso al repo, rechaza peticiones que no vengan de la propia
página: comprueba la cabecera `Host` (contra DNS rebinding) y exige `X-Estudio: 1` en todo lo que no sea GET.
"""
import json
import mimetypes
import os
import queue
import re
import shutil
import sys
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlparse

from valedores import doctor, extraer, juegos, proyectos, rutas, tareas

from . import agentes, chat

WEB = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'web')
MAX_SUBIDA = 4 * 1024 ** 3
EXT_IMG = ('.png', '.jpg', '.jpeg', '.webp', '.gif')
EXT_AUDIO = ('.wav', '.mp3', '.ogg', '.m4a', '.flac')
EXT_VIDEO = ('.mp4', '.webm', '.mov', '.m4v')
JOBS = {}                       # extracciones en curso: juego -> {'lineas', 'estado'}
JOBS_L = threading.Lock()

mimetypes.add_type('text/markdown; charset=utf-8', '.md')
mimetypes.add_type('video/mp4', '.mp4')
mimetypes.add_type('audio/wav', '.wav')


def tipo(nombre):
    n = nombre.lower()
    if n.endswith(EXT_IMG):
        return 'imagen'
    if n.endswith(EXT_AUDIO):
        return 'audio'
    if n.endswith(EXT_VIDEO):
        return 'video'
    if n.endswith(('.md', '.txt')):
        return 'texto'
    if n.endswith(('.json', '.py', '.csv', '.srt')):
        return 'codigo'
    return 'otro'


def url_archivo(rel):
    return '/api/archivo?ruta=' + quote(rel.replace('\\', '/'))


def ruta_permitida(rel):
    """Ruta absoluta dentro de las carpetas que el navegador puede leer, o None."""
    abs_ = os.path.realpath(os.path.join(rutas.REPO, rel))
    for base in (rutas.PROYECTOS, rutas.SALIDA, rutas.ENTRADA, rutas.BIBLIOTECA):
        b = os.path.realpath(base)
        if abs_ == b or abs_.startswith(b + os.sep):
            return abs_
    for j in rutas.juegos():
        b = os.path.realpath(os.path.join(rutas.juego_dir(j), 'vistas'))
        if abs_.startswith(b + os.sep):
            return abs_
    return None


def ficheros(base, rel_base=''):
    """Lista recursiva [{ruta, nombre, tipo, tam, mtime}] de una carpeta (sin `trabajo/` ni ocultos)."""
    out = []
    if not os.path.isdir(base):
        return out
    for raiz, dirs, fs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ('trabajo', '__pycache__') and not d.startswith('.'))
        for n in sorted(fs):
            if n in ('proyecto.json', 'LEEME.md', '.gitkeep') or n.endswith('.tmp') or n.startswith('.'):
                continue
            p = os.path.join(raiz, n)
            rel = os.path.relpath(p, rutas.REPO).replace('\\', '/')
            st = os.stat(p)
            out.append({'ruta': rel, 'nombre': os.path.relpath(p, base).replace('\\', '/'), 'tipo': tipo(n),
                        'tam': st.st_size, 'mtime': st.st_mtime, 'url': url_archivo(rel)})
    return out


def info_juego(m):
    st = juegos.estado(m['id'])
    return {
        'id': m['id'], 'nombre': m['nombre'], 'corto': m.get('corto', m['nombre']), 'plataforma': m.get('plataforma', ''),
        'descripcion': m.get('descripcion', ''), 'formatos': m.get('formatos', []),
        'vistas': ['/vistas/%s/%s' % (m['id'], v) for v in juegos.vistas(m['id'])],
        'rom': bool(st['rom']), 'estado': st['estado'], 'etiqueta': juegos.ETIQUETAS[st['estado']],
        'extraido': st['sello']['fecha'] if st['sello'] else None,
        'rom_codigos': m['rom']['codigos'], 'rom_ejemplo': m['rom'].get('ejemplo'),
    }


def _artefactos(slug, nombres, por_ruta):
    """Ficheros (ya existentes) de un proyecto a partir de rutas relativas a `proyectos/<slug>/` o a la raíz del repo."""
    out, vistos = [], set()
    for a in nombres:
        a = a.replace('\\', '/')
        for r in ('proyectos/%s/%s' % (slug, a), a):
            if r in por_ruta and r not in vistos:
                vistos.add(r)
                out.append(por_ruta[r])
                break
    return out


def _nodo(n):
    """Campos de seguimiento de tiempo de una fase o un elemento."""
    return {'inicio': n.get('inicio'), 'eta': n.get('eta'), 'progreso': n.get('progreso'), 'duraciones': n.get('duraciones', [])}


def _redondear(d):
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def vista_proyecto(slug):
    p = proyectos.leer(slug)
    base = rutas.proyecto_dir(slug)
    archivos = ficheros(base)
    por_ruta = {a['ruta']: a for a in archivos}
    salida = ficheros(os.path.join(rutas.SALIDA, slug))
    por_ruta.update({a['ruta']: a for a in salida})
    videos = [f for f in salida if f['tipo'] in ('video', 'imagen')]
    fases = []
    for d in proyectos.FASES:
        f = p['fases'][d['id']]
        rels = []
        for a in f.get('archivos', []):
            rels.append('proyectos/%s/%s' % (slug, a.replace('\\', '/')))
        if d.get('archivo'):
            pref = 'proyectos/%s/%s' % (slug, d['archivo'])
            for r in por_ruta:
                if r == pref or r.startswith(pref + '/'):
                    rels.append(r)
        if d['id'] == 'musica':
            rels += [r for r in por_ruta if r.startswith('proyectos/%s/musica/' % slug)]
        if d['id'] == 'idea':
            rels += ['proyectos/%s/brief.md' % slug]
        vistos, arts = set(), []
        for r in rels:
            if r in vistos:
                continue
            vistos.add(r)
            if r in por_ruta:
                arts.append(por_ruta[r])
        if d['id'] == 'render':
            arts = list(videos)
        fases.append(dict(d, estado=f['estado'], nota=f.get('nota', ''), artefactos=arts, **_nodo(f)))
    elementos = []
    for e in p.get('elementos', {}).values():
        elementos.append(dict(e, artefactos=_artefactos(slug, e.get('archivos', []), por_ruta), **_nodo(e)))
    orden = {f: i for i, f in enumerate(proyectos.IDS_FASE)}
    elementos.sort(key=lambda e: (orden.get(e['fase'], 99), e['nombre'].lower()))
    carriles = chat.carriles_de(slug)
    uso = chat.resumen_uso(slug)
    paralelo = {}
    for f in proyectos.IDS_FASE:
        ok, motivo = proyectos.puede_paralelo(p, f)
        paralelo[f] = {'puede': ok, 'motivo': motivo}
    return {'proyecto': p, 'fases': fases, 'elementos': elementos, 'cambios': p.get('cambios', []),
            'archivos': archivos, 'videos': videos,
            'entradas': [{'ruta': 'entrada/' + e, 'nombre': e, 'tipo': tipo(e), 'url': url_archivo('entrada/' + e)}
                         for e in proyectos.entradas(slug)],
            'tareas': tareas.activas(slug), 'ahora': time.time(),
            'uso': {'total': _redondear(uso['total']), 'por_fase': {f: _redondear(d) for f, d in uso['por_fase'].items()}},
            'carriles': [{'id': c.carril, 'ocupado': c.ocupado, 'cola': len(c.cola), 'eventos': len(c.eventos)} for c in carriles],
            'paralelo': paralelo,
            'ocupado': any(c.ocupado for c in carriles), 'eventos': len(carriles[0].eventos)}


def firma(slug):
    """Cambia cuando cambia algo visible del proyecto (para avisar al navegador por SSE)."""
    m, n = 0.0, 0
    for base in (rutas.proyecto_dir(slug), os.path.join(rutas.SALIDA, slug), os.path.join(rutas.ENTRADA, slug)):
        for raiz, dirs, fs in os.walk(base):
            dirs[:] = [d for d in dirs if d != 'trabajo']
            for f in fs:
                if f.startswith('.') or f.endswith('.tmp'):
                    continue
                try:
                    m = max(m, os.path.getmtime(os.path.join(raiz, f)))
                    n += 1
                except OSError:
                    pass
    try:                                   # las tareas en marcha cambian en trabajo/tareas.json
        m = max(m, os.path.getmtime(os.path.join(rutas.proyecto_dir(slug), 'trabajo', 'tareas.json')))
    except OSError:
        pass
    return (m, n)


def mensaje_carril(p, fase_id):
    """Primer mensaje de un agente en paralelo."""
    nombre = next(f['nombre'] for f in proyectos.FASES if f['id'] == fase_id)
    return ('Haz ahora la fase «%s» (`%s`) en paralelo. Las fases de las que depende ya están aprobadas: lee sus ficheros en `proyectos/%s/`. '
            'Márcala `en_curso` al empezar (con `--eta` en segundos), regístrale sus elementos, y al terminar márcala `validar` con una nota y para.'
            % (nombre, fase_id, p['slug']))


def instrucciones_cambio(slug, c):
    """Lo que recibe el agente además del texto del usuario cuando éste pide un cambio."""
    p = proyectos.leer(slug)
    objs = []
    for o in c['objetivos']:
        if o['tipo'] == 'fase':
            objs.append('la fase `%s`' % o['id'])
        else:
            e = p.get('elementos', {}).get(o['id'])
            objs.append('el elemento `%s` (%s, fase `%s`)' % (o['id'], e['nombre'], e['fase']) if e else 'el elemento `%s`' % o['id'])
    lineas = [
        'Petición de cambio #%d del usuario. Puede pedirse sobre cualquier parte del vídeo y en cualquier momento, también sobre fases anteriores a la que se está viendo.' % c['id'],
        'Afecta a: %s.' % (', '.join(objs) if objs else 'no lo ha concretado (decide tú el alcance)'),
    ]
    if c['fases_marcadas']:
        lineas.append('Ya he puesto en `cambios` estas fases: %s.' % ', '.join('`%s`' % f for f in c['fases_marcadas']))
    lineas += [
        'Procede así:',
        '1. `python valedores.py cambio %s %d en_curso`.' % (slug, c['id']),
        '2. Calcula el alcance real. Si toca fases o elementos que no están marcados, márcalos (`fase … cambios --nota …`, `elemento … --estado cambios`) y díselo al usuario.',
        '3. Rehaz solo lo necesario, en orden de dependencias (guion → música y storyboard → previsualización → render → revisión). Cada fase o elemento que rehagas: `en_curso` (con `--eta`) y, al acabar, `validar`.',
        '4. Termina con `python valedores.py cambio %s %d hecho`. En paso a paso, para al terminar la fase objetivo y pide validación; en «de una», sigue con las posteriores.' % (slug, c['id']),
    ]
    return '\n'.join(lineas)


class Handler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    server_version = 'valedores-estudio'

    def log_message(self, *a):
        pass

    # ---------------------------------------------------------- utilidades
    def _host_ok(self):
        h = (self.headers.get('Host') or '').split(':')[0].lower()
        return h in ('127.0.0.1', 'localhost', '[::1]')

    def _json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(cuerpo)

    def _error(self, codigo, msg):
        self._json({'error': msg}, codigo)

    def _leer_json(self):
        n = int(self.headers.get('Content-Length') or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode('utf-8'))
        except ValueError:
            return {}

    def _rechazar(self, codigo, msg):
        """Responde un error sin haber leído el cuerpo: lo descarta (o cierra la conexión si es enorme) para no provocar un reset."""
        n = int(self.headers.get('Content-Length') or 0)
        if n > (1 << 20):
            self.close_connection = True
        else:
            self.rfile.read(n)
        self._error(codigo, msg)

    def _entrar(self, escritura):
        if not self._host_ok():
            self._rechazar(403, 'Host no permitido')
            return None
        if escritura and self.headers.get('X-Estudio') != '1':
            self._rechazar(403, 'Falta X-Estudio')
            return None
        u = urlparse(self.path)
        return u.path, {k: v[0] for k, v in parse_qs(u.query).items()}

    def _fichero(self, abs_, descargar=False):
        if not os.path.isfile(abs_):
            return self._error(404, 'No existe')
        tam = os.path.getsize(abs_)
        ct = mimetypes.guess_type(abs_)[0] or 'application/octet-stream'
        ini, fin = 0, tam - 1
        rango = self.headers.get('Range')
        codigo = 200
        if rango:
            m = re.match(r'bytes=(\d*)-(\d*)', rango)
            if m:
                if m.group(1):
                    ini = int(m.group(1))
                    if m.group(2):
                        fin = min(int(m.group(2)), tam - 1)
                elif m.group(2):
                    ini = max(0, tam - int(m.group(2)))
                if ini > fin or ini >= tam:
                    self.send_response(416)
                    self.send_header('Content-Range', 'bytes */%d' % tam)
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                codigo = 206
        self.send_response(codigo)
        self.send_header('Content-Type', ct)
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Length', str(fin - ini + 1))
        self.send_header('Cache-Control', 'no-cache')
        if codigo == 206:
            self.send_header('Content-Range', 'bytes %d-%d/%d' % (ini, fin, tam))
        self.end_headers()
        try:
            with open(abs_, 'rb') as f:
                f.seek(ini)
                resto = fin - ini + 1
                while resto > 0:
                    b = f.read(min(1 << 20, resto))
                    if not b:
                        break
                    self.wfile.write(b)
                    resto -= len(b)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def _index(self, p):
        """index.html con la versión de app.js/app.css en la URL: tras editar la interfaz el navegador nunca usa una copia vieja."""
        with open(p, encoding='utf-8') as f:
            html = f.read()
        v = int(max(os.path.getmtime(os.path.join(WEB, n)) for n in os.listdir(WEB) if n.endswith(('.js', '.css', '.html'))))
        html = re.sub(r'(src|href)="([\w.-]+\.(?:js|css))"', lambda m: '%s="%s?v=%d"' % (m.group(1), m.group(2), v), html)
        cuerpo = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(cuerpo)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(cuerpo)

    # ---------------------------------------------------------- GET
    def do_GET(self):
        r = self._entrar(False)
        if r is None:
            return
        ruta, q = r
        try:
            if ruta.startswith('/api/'):
                return self._api_get(ruta, q)
            if ruta.startswith('/vistas/'):
                _, _, juego, nombre = ruta.split('/', 3)
                base = os.path.realpath(os.path.join(rutas.juego_dir(juego), 'vistas'))
                p = os.path.realpath(os.path.join(base, unquote(nombre)))
                if not p.startswith(base + os.sep):
                    return self._error(404, 'No existe')
                return self._fichero(p)
            nombre = 'index.html' if ruta in ('/', '') else ruta.lstrip('/')
            p = os.path.realpath(os.path.join(WEB, nombre))
            if not p.startswith(os.path.realpath(WEB) + os.sep):
                return self._error(404, 'No existe')
            if nombre == 'index.html' and os.path.isfile(p):
                return self._index(p)
            return self._fichero(p)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:  # noqa: BLE001
            self._error(500, '%s: %s' % (type(e).__name__, e))

    def _api_get(self, ruta, q):
        if ruta == '/api/estado':
            return self._json({
                'juegos': [info_juego(m) for m in juegos.todos()],
                'agentes': agentes.catalogo(), 'permisos': agentes.PERMISOS, 'ritmos': proyectos.RITMOS,
                'fases': proyectos.FASES, 'dependencias': proyectos.DEPENDE, 'tipos_elemento': proyectos.TIPOS_ELEMENTO,
                'proyectos': proyectos.listar(),
            })
        if ruta == '/api/proyectos':
            return self._json(proyectos.listar())
        m = re.fullmatch(r'/api/proyectos/([\w-]+)', ruta)
        if m:
            if not proyectos.existe(m.group(1)):
                return self._error(404, 'No existe el proyecto')
            return self._json(vista_proyecto(m.group(1)))
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/eventos', ruta)
        if m:
            return self._sse(m.group(1), int(q.get('desde', 0) or 0), q.get('carril') or chat.PRINCIPAL)
        if ruta == '/api/archivo':
            rel = q.get('ruta', '')
            p = ruta_permitida(rel)
            if not p:
                return self._error(403, 'Ruta no permitida')
            return self._fichero(p)
        if ruta == '/api/entrada':
            return self._json(ficheros(rutas.ENTRADA))
        if ruta == '/api/salida':
            return self._json(ficheros(rutas.SALIDA))
        m = re.fullmatch(r'/api/extraer/([\w-]+)', ruta)
        if m:
            with JOBS_L:
                j = JOBS.get(m.group(1)) or {'lineas': [], 'estado': 'libre'}
                d = int(q.get('desde', 0) or 0)
                return self._json({'estado': j['estado'], 'lineas': j['lineas'][d:], 'total': len(j['lineas'])})
        if ruta == '/api/doctor':
            return self._json([{'nivel': n, 'texto': t} for n, t in doctor.comprobar()])
        return self._error(404, 'No existe')

    def _sse(self, slug, desde, carril=chat.PRINCIPAL):
        if not proyectos.existe(slug):
            return self._error(404, 'No existe el proyecto')
        if carril != chat.PRINCIPAL and carril not in proyectos.IDS_FASE:
            return self._error(404, 'No existe el carril')
        c = chat.obtener(slug, carril)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Connection', 'close')
        self.end_headers()
        self.close_connection = True
        q = c.suscribir()

        def enviar(ev):
            self.wfile.write(('data: %s\n\n' % json.dumps(ev, ensure_ascii=False)).encode('utf-8'))
            self.wfile.flush()

        try:
            with c.lock:
                previos = c.eventos[desde:]
            for ev in previos:
                enviar(ev)
            enviar({'t': 'estado', 'estado': 'trabajando' if c.ocupado else 'libre'})
            enviar({'t': 'cola', 'textos': c.textos_en_cola()})
            ultimo, ticks, sig = len(previos) + desde, 0, firma(slug)
            while True:
                try:
                    ev = q.get(timeout=1)
                    if 'n' in ev and ev['n'] < ultimo:
                        continue
                    if 'n' in ev:
                        ultimo = ev['n'] + 1
                    enviar(ev)
                except queue.Empty:
                    ticks += 1
                    s2 = firma(slug)
                    if s2 != sig:
                        sig = s2
                        enviar({'t': 'proyecto'})
                    elif ticks % 15 == 0:
                        self.wfile.write(b': latido\n\n')
                        self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            c.baja(q)

    # ---------------------------------------------------------- escritura
    def do_POST(self):
        self._escritura('POST')

    def do_PATCH(self):
        self._escritura('PATCH')

    def do_DELETE(self):
        self._escritura('DELETE')

    def _escritura(self, metodo):
        r = self._entrar(True)
        if r is None:
            return
        ruta, q = r
        try:
            self._api_escritura(metodo, ruta, q)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except (ValueError, KeyError, FileNotFoundError) as e:
            self._error(400, str(e))
        except Exception as e:  # noqa: BLE001
            self._error(500, '%s: %s' % (type(e).__name__, e))

    def _api_escritura(self, metodo, ruta, q):
        if metodo == 'POST' and ruta == '/api/proyectos':
            d = self._leer_json()
            ag = agentes.catalogo()
            agente = d.get('agente') or 'claude'
            if agente not in ag:
                raise ValueError('Agente desconocido')
            p = proyectos.crear(
                (d.get('titulo') or '').strip() or 'Vídeo sin título', d['juego'], d.get('formato'), d.get('ritmo') or 'paso_a_paso',
                agente, d.get('modelo') or ag[agente]['modelo_defecto'], d.get('esfuerzo') or ag[agente]['esfuerzo_defecto'],
                brief=d.get('brief') or '')
            if d.get('permisos') in agentes.PERMISOS:
                p['permisos'] = d['permisos']
                proyectos.guardar(p['slug'], p)
            return self._json(p, 201)
        m = re.fullmatch(r'/api/proyectos/([\w-]+)', ruta)
        if m and metodo == 'PATCH':
            slug = m.group(1)
            d = self._leer_json()

            def aplicar(p):
                for k in ('titulo', 'agente', 'modelo', 'esfuerzo', 'permisos', 'ritmo', 'formato'):
                    if k in d:
                        p[k] = d[k]
            return self._json(proyectos.modificar(slug, aplicar))
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/chat', ruta)
        if m and metodo == 'POST':
            slug = m.group(1)
            d = self._leer_json()
            texto = (d.get('texto') or '').strip()
            adjuntos = []
            for rel in d.get('adjuntos') or []:
                p = ruta_permitida(rel)
                if not p or not p.startswith(os.path.realpath(rutas.ENTRADA) + os.sep) or not os.path.isfile(p):
                    raise ValueError('Adjunto no válido: %s' % rel)
                rel = os.path.relpath(p, rutas.REPO).replace('\\', '/')
                adjuntos.append({'nombre': os.path.basename(p), 'ruta': rel, 'tipo': tipo(p), 'url': url_archivo(rel)})
            if not proyectos.existe(slug):
                return self._error(404, 'No existe el proyecto')
            carril = d.get('carril') or chat.PRINCIPAL
            if carril != chat.PRINCIPAL:
                if carril not in proyectos.IDS_FASE:
                    raise ValueError('Carril desconocido')
                p = proyectos.leer(slug)
                puede, motivo = proyectos.puede_paralelo(p, carril)
                if not puede:
                    raise ValueError('No se puede trabajar «%s» en paralelo: %s.' % (carril, motivo))
                if not texto and not adjuntos:
                    texto = mensaje_carril(p, carril)
            if not texto and not adjuntos:
                raise ValueError('Mensaje vacío')
            if not texto:
                texto = 'Te adjunto estos ficheros.'
            r = chat.obtener(slug, carril).enviar(texto, adjuntos)
            return self._json({'ok': True, 'cola': r == 'cola'}, 202)
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/cambio', ruta)
        if m and metodo == 'POST':
            slug = m.group(1)
            if not proyectos.existe(slug):
                return self._error(404, 'No existe el proyecto')
            d = self._leer_json()
            c = proyectos.pedir_cambio(slug, d.get('texto'), d.get('objetivos') or [], d.get('afectadas') or [])
            texto = '✎ Cambio #%d: %s' % (c['id'], c['texto'])
            r = chat.obtener(slug).enviar(texto, None, instrucciones_cambio(slug, c))
            return self._json(dict(c, en_cola=r == 'cola'), 201)
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/cambio/(\d+)', ruta)
        if m and metodo == 'PATCH':
            d = self._leer_json()
            proyectos.cambio_estado(m.group(1), int(m.group(2)), d.get('estado'), d.get('nota'))
            return self._json({'ok': True})
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/parar', ruta)
        if m and metodo == 'POST':
            carril = q.get('carril') or chat.PRINCIPAL
            chat.obtener(m.group(1), carril).parar()
            return self._json({'ok': True})
        m = re.fullmatch(r'/api/proyectos/([\w-]+)/fase', ruta)
        if m and metodo == 'POST':
            slug = m.group(1)
            d = self._leer_json()
            accion = d.get('accion')
            estado = {'aprobar': 'aprobada', 'cambios': 'cambios', 'reabrir': 'pendiente', 'omitir': 'omitida'}.get(accion)
            if not estado:
                raise ValueError('Acción desconocida')
            p = proyectos.fase(slug, d['fase'], estado, nota=(d.get('nota') if accion == 'cambios' else None))
            return self._json(p)
        if ruta == '/api/entrada' and metodo == 'POST':
            return self._subida(q)
        if ruta == '/api/entrada' and metodo == 'DELETE':
            rel = q.get('ruta', '')
            p = ruta_permitida(rel)
            if not p or not (p + os.sep).startswith(os.path.realpath(rutas.ENTRADA) + os.sep) or not os.path.isfile(p):
                raise ValueError('Ruta no permitida')
            os.remove(p)
            return self._json({'ok': True})
        m = re.fullmatch(r'/api/extraer/([\w-]+)', ruta)
        if m and metodo == 'POST':
            return self._extraer(m.group(1), q.get('rapido') == '1')
        return self._error(404, 'No existe')

    def _subida(self, q):
        nombre = os.path.basename((q.get('nombre') or '').replace('\\', '/'))
        nombre = re.sub(r'[<>:"|?*\x00-\x1f]', '_', nombre).strip(' .')
        if not nombre or nombre in ('LEEME.md', '.gitkeep'):
            raise ValueError('Nombre de fichero no válido')
        slug = q.get('proyecto') or ''
        destino = rutas.ENTRADA
        if slug:
            if not proyectos.existe(slug):
                raise ValueError('No existe el proyecto')
            destino = os.path.join(rutas.ENTRADA, slug)
        os.makedirs(destino, exist_ok=True)
        n = int(self.headers.get('Content-Length') or 0)
        if n > MAX_SUBIDA:
            return self._rechazar(413, 'Fichero demasiado grande')
        base, ext = os.path.splitext(nombre)
        p, i = os.path.join(destino, nombre), 2
        while os.path.exists(p):
            p = os.path.join(destino, '%s_%d%s' % (base, i, ext))
            i += 1
        with open(p, 'wb') as f:
            resto = n
            while resto > 0:
                b = self.rfile.read(min(1 << 20, resto))
                if not b:
                    break
                f.write(b)
                resto -= len(b)
        rel = os.path.relpath(p, rutas.REPO).replace('\\', '/')
        return self._json({'ruta': rel, 'nombre': os.path.basename(p), 'tipo': tipo(p), 'url': url_archivo(rel), 'tam': os.path.getsize(p)}, 201)

    def _extraer(self, juego, rapido):
        if juego not in rutas.juegos():
            raise ValueError('Juego desconocido')
        with JOBS_L:
            j = JOBS.get(juego)
            if j and j['estado'] == 'corriendo':
                return self._error(409, 'Ya se está extrayendo')
            j = JOBS[juego] = {'lineas': [], 'estado': 'corriendo'}

        def trabajo():
            try:
                ok = extraer.ejecutar(juego, rapido=rapido, salida=lambda s: j['lineas'].append(s))
                j['estado'] = 'ok' if ok else 'error'
            except Exception as e:  # noqa: BLE001
                j['lineas'].append('✗ %s' % e)
                j['estado'] = 'error'

        threading.Thread(target=trabajo, daemon=True).start()
        return self._json({'ok': True}, 202)


class Servidor(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = False


def principal(puerto=8765, abrir=True):
    srv = None
    for p in range(puerto, puerto + 20):
        try:
            srv = Servidor(('127.0.0.1', p), Handler)
            break
        except OSError:
            continue
    if srv is None:
        print('No hay ningún puerto libre entre %d y %d.' % (puerto, puerto + 19))
        return 1
    url = 'http://127.0.0.1:%d/' % srv.server_address[1]
    print('Estudio en %s  (Ctrl+C para cerrar)' % url)
    if abrir:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print('\nCerrando…')
    finally:
        srv.server_close()
    return 0


if __name__ == '__main__':
    sys.exit(principal())
