"""Conversación de un proyecto con su agente: historial en disco, difusión de eventos y turnos en segundo plano.

Un proyecto tiene un carril `principal` y, opcionalmente, un carril por fase (`musica`, `storyboard`…) para trabajar en
paralelo: cada carril es un agente distinto, con su propia sesión e historial, que solo se ocupa de su fase.
"""
import glob
import json
import os
import queue
import threading
import time

from valedores import proyectos, rutas
from . import agentes

ESTADO = os.path.join(rutas.REPO, '.estudio', 'chats')
PRINCIPAL = 'principal'


PISTAS = {
    'imagen': 'ábrela con la herramienta de lectura de imágenes',
    'video': 'mira sus fotogramas con `python valedores.py revisar hoja <ruta>` (y `revisar audio` para el sonido)',
    'audio': 'analízalo con `python valedores.py revisar audio <ruta>`',
}


def con_adjuntos(texto, adjuntos):
    """Texto que recibe el agente: el mensaje más la lista de ficheros que el usuario ha adjuntado."""
    if not adjuntos:
        return texto
    lineas = ['', '', 'Ficheros adjuntos por el usuario (están en `entrada/`, no los modifiques):']
    for a in adjuntos:
        pista = PISTAS.get(a['tipo'])
        lineas.append('- `%s`%s' % (a['ruta'], ' (%s: %s)' % (a['tipo'], pista) if pista else ''))
    return texto + '\n'.join(lineas)


class Chat:
    def __init__(self, slug, carril=PRINCIPAL):
        self.slug = slug
        self.carril = carril
        self.dir = ESTADO
        os.makedirs(self.dir, exist_ok=True)
        base = slug if carril == PRINCIPAL else '%s@%s' % (slug, carril)
        self.f_log = os.path.join(self.dir, base + '.jsonl')
        self.f_ses = os.path.join(self.dir, base + '.sesion.json')
        self.lock = threading.Lock()
        self.eventos = []
        self.suscriptores = []
        self.proc = None
        self.ocupado = False
        self.parado = False
        self.cola = []                 # mensajes escritos mientras el agente trabaja: se envían uno a uno al terminar
        self.sesiones = {}
        if os.path.isfile(self.f_log):
            with open(self.f_log, encoding='utf-8') as f:
                for linea in f:
                    try:
                        self.eventos.append(json.loads(linea))
                    except ValueError:
                        pass
        if os.path.isfile(self.f_ses):
            try:
                with open(self.f_ses, encoding='utf-8') as f:
                    self.sesiones = json.load(f)
            except ValueError:
                self.sesiones = {}

    # ---- eventos
    def emitir(self, ev, persistir=True):
        with self.lock:
            ev = dict(ev, ts=time.strftime('%H:%M:%S'))
            if persistir:
                ev['n'] = len(self.eventos)
                self.eventos.append(ev)
                with open(self.f_log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + '\n')
            subs = list(self.suscriptores)
        for q in subs:
            q.put(ev)

    def suscribir(self):
        q = queue.Queue()
        with self.lock:
            self.suscriptores.append(q)
        return q

    def baja(self, q):
        with self.lock:
            if q in self.suscriptores:
                self.suscriptores.remove(q)

    def _guardar_sesiones(self):
        with open(self.f_ses, 'w', encoding='utf-8') as f:
            json.dump(self.sesiones, f)

    def textos_en_cola(self):
        with self.lock:
            return [c['texto'] for c in self.cola]

    def _avisar_cola(self):
        self.emitir({'t': 'cola', 'textos': self.textos_en_cola()}, persistir=False)

    # ---- turnos
    def enviar(self, texto, adjuntos=None, instrucciones=None):
        """Lanza un turno, o lo deja en cola si el agente sigue ocupado. `adjuntos`: [{nombre, ruta, tipo, url}] ya subidos a `entrada/`.
        `instrucciones`: texto extra solo para el agente (el chat enseña únicamente `texto`). Devuelve 'iniciado' o 'cola'."""
        with self.lock:
            if self.ocupado:
                self.cola.append({'texto': texto, 'adjuntos': adjuntos, 'instrucciones': instrucciones})
                encolado = True
            else:
                self.ocupado = True
                self.parado = False
                encolado = False
        if encolado:
            self._avisar_cola()
            return 'cola'
        ev = {'t': 'usuario', 'texto': texto}
        if adjuntos:
            ev['adjuntos'] = adjuntos
        self.emitir(ev)
        self.emitir({'t': 'estado', 'estado': 'trabajando'}, persistir=False)
        extra = '\n\n' + instrucciones if instrucciones else ''
        para_agente = con_adjuntos(texto + extra, adjuntos) + self._aviso_carriles()
        threading.Thread(target=self._turno, args=(para_agente,), daemon=True).start()
        return 'iniciado'

    def _aviso_carriles(self):
        """Al agente principal se le dice qué fases están llevando ahora otros agentes en paralelo."""
        if self.carril != PRINCIPAL:
            return ''
        otros = carriles_ocupados(self.slug)
        if not otros:
            return ''
        return '\n\n(Aviso del estudio: ahora mismo trabajan agentes en paralelo en las fases %s. No toques esas fases ni sus ficheros.)' % ', '.join(otros)

    def _fase_ahora(self, inicial):
        """Fase a la que se atribuye la actividad del agente en este momento (para repartir el consumo por fases)."""
        if self.carril != PRINCIPAL:
            return self.carril
        try:
            fa = proyectos.leer(self.slug)['fase_actual']
        except (OSError, ValueError, KeyError):
            return inicial
        return inicial if fa in carriles_ocupados(self.slug) else fa

    def _turno(self, texto, reintento=False):
        try:
            p = proyectos.leer(self.slug)
            agente = p.get('agente', 'claude')
            sesion = self.sesiones.get(agente)
            sistema = proyectos.contexto(self.slug, None if self.carril == PRINCIPAL else self.carril)
            hubo_error = []
            inicial = self.carril if self.carril != PRINCIPAL else p.get('fase_actual', 'idea')
            actividad = {}

            def emitir(e):
                if self.parado and e['t'] == 'error':
                    return
                if e['t'] == 'error':
                    hubo_error.append(e['texto'])
                if e['t'] in ('asistente', 'herramienta'):
                    f = self._fase_ahora(inicial)
                    actividad[f] = actividad.get(f, 0) + 1
                if e['t'] == 'fin':
                    total = sum(actividad.values())
                    e['reparto'] = {f: n / total for f, n in actividad.items()} if total else {inicial: 1.0}
                    e['carril'] = self.carril
                    e['modelo'] = e.get('modelo') or p.get('modelo')
                    e['agente'] = agente
                    if e.get('coste') is None and e.get('uso'):
                        e['coste'] = agentes.coste_estimado(p.get('modelo'), e['uso'])
                        e['coste_estimado'] = e['coste'] is not None
                self.emitir(e, persistir=e['t'] not in ('delta', 'uso_vivo'))

            nueva = agentes.ejecutar_turno(
                agente, texto, p.get('modelo'), p.get('esfuerzo'), p.get('permisos', 'normal'), sesion, rutas.REPO,
                {'VALEDORES_PROYECTO': self.slug}, emitir, sistema=sistema,
                registrar_proc=lambda pr: setattr(self, 'proc', pr))
            if sesion and hubo_error and 'No conversation found' in ' '.join(hubo_error) and not reintento:
                self.sesiones.pop(agente, None)
                self._guardar_sesiones()
                return self._turno(texto, reintento=True)
            if nueva:
                self.sesiones[agente] = nueva
                self._guardar_sesiones()
        except Exception as e:  # noqa: BLE001  (se muestra en el chat)
            self.emitir({'t': 'error', 'texto': str(e)})
        finally:
            siguiente = None
            with self.lock:
                self.ocupado = False
                self.proc = None
                if self.parado:
                    self.cola.clear()
                elif self.cola:
                    siguiente = self.cola.pop(0)
            if self.parado:
                self.emitir({'t': 'sistema', 'texto': 'Agente detenido.'})
            self.emitir({'t': 'estado', 'estado': 'libre'}, persistir=False)
            self._avisar_cola()
            self.emitir({'t': 'proyecto'}, persistir=False)
            if siguiente:
                self.enviar(siguiente['texto'], siguiente['adjuntos'], siguiente.get('instrucciones'))

    def parar(self):
        self.parado = True
        agentes.matar(self.proc)


_CHATS = {}
_L = threading.Lock()


def obtener(slug, carril=PRINCIPAL):
    with _L:
        if (slug, carril) not in _CHATS:
            _CHATS[(slug, carril)] = Chat(slug, carril)
        return _CHATS[(slug, carril)]


def carriles_ocupados(slug):
    """Ids de los carriles en paralelo (no el principal) con un agente trabajando ahora mismo."""
    with _L:
        return [c for (s, c), ch in _CHATS.items() if s == slug and c != PRINCIPAL and ch.ocupado]


def carriles_de(slug):
    """Los carriles del proyecto: el principal y los que alguna vez se han abierto (hay historial en disco o en memoria)."""
    ids = {PRINCIPAL}
    for f in glob.glob(os.path.join(ESTADO, slug + '@*.jsonl')):
        ids.add(os.path.basename(f)[len(slug) + 1:-len('.jsonl')])
    with _L:
        ids |= {c for (s, c) in _CHATS if s == slug}
    orden = [PRINCIPAL] + [f for f in proyectos.IDS_FASE if f in ids]
    return [obtener(slug, c) for c in orden]


def _sumar_uso(dest, uso, w=1.0):
    for k in agentes.CAMPOS_USO:
        dest[k] = dest.get(k, 0) + (uso.get(k) or 0) * w


def resumen_uso(slug):
    """Tokens y precio del proyecto, en total y por fase, sumando los turnos de todos los carriles.
    El consumo de un turno que cruza varias fases se reparte según la actividad del agente en cada una."""
    total = {k: 0 for k in agentes.CAMPOS_USO}
    total.update(coste=0.0, turnos=0, coste_completo=True, sin_desglose=0)
    por_fase = {}
    for c in carriles_de(slug):
        with c.lock:
            fines = [e for e in c.eventos if e.get('t') == 'fin']
        for e in fines:
            uso = e.get('uso')
            coste = e.get('coste')
            total['turnos'] += 1
            if not uso:                                    # historial anterior al desglose
                total['sin_desglose'] += e.get('tokens') or 0
            else:
                _sumar_uso(total, uso)
            if coste is None:
                total['coste_completo'] = False
            else:
                total['coste'] += coste
            for f, w in (e.get('reparto') or {'sin_fase': 1.0}).items():
                d = por_fase.setdefault(f, dict.fromkeys(agentes.CAMPOS_USO, 0))
                d.setdefault('coste', 0.0)
                if uso:
                    _sumar_uso(d, uso, w)
                if coste is not None:
                    d['coste'] += coste * w
    return {'total': total, 'por_fase': por_fase}
