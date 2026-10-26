"""Proyectos de vídeo: una carpeta por vídeo con su estado por fases.

    proyectos/<slug>/
        proyecto.json   estado: juego, formato, ritmo, agente, fases y sus archivos
        brief.md        la idea / el guion del usuario, tal cual
        guion.md, musica.md, storyboard.md, ...   lo que va produciendo el agente
        musica/, previsualizacion/                 audio y fotogramas para validar
        trabajo/                                   temporales (no se versiona)
    entrada/<slug>/     ficheros del usuario para este vídeo (también vale `entrada/` suelta)
    salida/<slug>/      vídeos resultado (no se versionan)

El agente y el estudio comparten el estado a través de `proyecto.json`: el agente lo actualiza con
`python valedores.py fase|elemento|cambio ...` y el estudio lo muestra y recoge la validación.

    fases       las 7 etapas con su estado, nota, archivos, hora de inicio y tiempo estimado
    elementos   cada concepto del vídeo (guion, música, un personaje, una escena…) colgado de una fase
    cambios     peticiones de cambio del usuario (sobre cualquier fase o elemento, en cualquier momento)

Varios procesos escriben este fichero a la vez (el estudio, el agente principal y los agentes en paralelo): toda
modificación pasa por `modificar()`, que usa un cerrojo.
"""
import json
import os
import re
import time
import unicodedata

from . import bloqueo, juegos, rutas

FASES = [
    {'id': 'idea', 'nombre': 'Idea y alcance',
     'resumen': 'Concreta formato, duración, tono, reparto y qué assets hacen falta.', 'archivo': 'brief.md'},
    {'id': 'guion', 'nombre': 'Guion',
     'resumen': 'Texto completo: quién dice qué y cuándo.', 'archivo': 'guion.md'},
    {'id': 'musica', 'nombre': 'Música',
     'resumen': 'Composición con los instrumentos del juego, con un audio de muestra.', 'archivo': 'musica.md'},
    {'id': 'storyboard', 'nombre': 'Storyboard',
     'resumen': 'Escenas, planos, tiempos y assets elegidos.', 'archivo': 'storyboard.md'},
    {'id': 'escenas', 'nombre': 'Previsualización',
     'resumen': 'Fotogramas clave y hoja de contactos antes del render completo.', 'archivo': 'previsualizacion'},
    {'id': 'render', 'nombre': 'Render',
     'resumen': 'El vídeo final en la bandeja de salida.', 'archivo': None},
    {'id': 'revision', 'nombre': 'Revisión final',
     'resumen': 'Comprobación de imagen, texto y audio del archivo entregado.', 'archivo': 'revision.md'},
]
IDS_FASE = [f['id'] for f in FASES]
# De qué fases depende cada una. Música y storyboard solo necesitan el guion: pueden hacerse a la vez (en paralelo).
DEPENDE = {
    'idea': [], 'guion': ['idea'], 'musica': ['guion'], 'storyboard': ['guion'],
    'escenas': ['musica', 'storyboard'], 'render': ['escenas'], 'revision': ['render'],
}
TIPOS_ELEMENTO = ('guion', 'musica', 'personaje', 'escenario', 'escena', 'voz', 'efecto', 'texto', 'imagen', 'video', 'otro')
ESTADOS_CAMBIO = ('pendiente', 'en_curso', 'hecho', 'descartado')
ESTADOS = ('pendiente', 'en_curso', 'validar', 'aprobada', 'cambios', 'omitida')
RITMOS = {
    'paso_a_paso': 'Paso a paso: el agente se detiene al terminar cada fase y espera tu validación.',
    'de_una': 'De una: el agente hace todo seguido y solo te enseña el resultado final.',
}


def slugify(texto):
    t = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    t = re.sub(r'[^a-zA-Z0-9]+', '_', t).strip('_').lower()
    return t or 'video'


def _ruta(slug):
    return os.path.join(rutas.proyecto_dir(slug), 'proyecto.json')


def existe(slug):
    return os.path.isfile(_ruta(slug))


def leer(slug):
    with open(_ruta(slug), encoding='utf-8') as f:
        return json.load(f)


def guardar(slug, p):
    p['actualizado'] = time.strftime('%Y-%m-%d %H:%M:%S')
    d = rutas.proyecto_dir(slug)
    os.makedirs(d, exist_ok=True)
    tmp = _ruta(slug) + '.%d.tmp' % os.getpid()
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    bloqueo.reemplazar(tmp, _ruta(slug))


def modificar(slug, fn):
    """Lee, aplica `fn(p)` y guarda con el cerrojo del proyecto. Devuelve el proyecto guardado."""
    with bloqueo.bloqueo(os.path.join(rutas.proyecto_dir(slug), '.proyecto.lock')):
        p = leer(slug)
        fn(p)
        guardar(slug, p)
        return p


def listar():
    if not os.path.isdir(rutas.PROYECTOS):
        return []
    out = []
    for s in sorted(os.listdir(rutas.PROYECTOS)):
        if existe(s):
            out.append(leer(s))
    out.sort(key=lambda p: p.get('actualizado', ''), reverse=True)
    return out


def crear(titulo, juego, formato=None, ritmo='paso_a_paso', agente='claude', modelo=None, esfuerzo=None,
          brief='', slug=None):
    if juego not in rutas.juegos():
        raise ValueError('Juego desconocido: %s' % juego)
    if not juegos.formatos(juego):
        raise ValueError('%s admite extracción de recursos; todavía no tiene motor de vídeo.' %
                         juegos.cargar(juego)['nombre'])
    if ritmo not in RITMOS:
        raise ValueError('Ritmo desconocido: %s' % ritmo)
    base = slug or slugify(titulo)
    s, n = base, 2
    while existe(s):
        s = '%s_%d' % (base, n)
        n += 1
    fmts = [f['id'] for f in juegos.formatos(juego)]
    if formato is None and fmts:
        formato = fmts[0]
    p = {
        'slug': s, 'titulo': titulo, 'juego': juego, 'formato': formato, 'ritmo': ritmo,
        'agente': agente, 'modelo': modelo, 'esfuerzo': esfuerzo, 'permisos': 'normal',
        'creado': time.strftime('%Y-%m-%d %H:%M:%S'),
        'fase_actual': 'idea',
        'fases': {f['id']: {'estado': 'pendiente', 'archivos': [], 'nota': ''} for f in FASES},
    }
    d = rutas.proyecto_dir(s)
    for sub in ('', 'trabajo'):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    os.makedirs(os.path.join(rutas.ENTRADA, s), exist_ok=True)
    with open(os.path.join(d, 'brief.md'), 'w', encoding='utf-8') as f:
        f.write('# %s\n\n%s\n' % (titulo, brief.strip() or '(Aún sin idea escrita.)'))
    guardar(s, p)
    return p


def _cronometro(nodo, estado, ahora):
    """Apunta cuándo empieza a trabajarse un nodo (fase o elemento) y, al dejar de estar en curso, cuánto tardó."""
    antes = nodo.get('estado')
    nodo['estado'] = estado
    if estado == 'en_curso':
        if antes != 'en_curso' or not nodo.get('inicio'):
            nodo['inicio'] = ahora
    elif antes == 'en_curso' and nodo.get('inicio'):
        d = nodo.setdefault('duraciones', [])
        d.append(round(ahora - nodo['inicio']))
        del d[:-5]
        for k in ('inicio', 'eta', 'progreso'):
            nodo.pop(k, None)


def _ajustes_nodo(nodo, eta, progreso):
    if eta is not None:
        nodo['eta'] = max(1, int(eta))
    if progreso is not None:
        nodo['progreso'] = max(0, min(100, int(progreso)))


def fase(slug, fase_id, estado, archivos=None, nota=None, eta=None, progreso=None):
    """Marca el estado de una fase (lo usa el agente). Avanza `fase_actual` al aprobar.
    `eta`: segundos que se prevé que tarde (barra de progreso del estudio); `progreso`: 0-100 si se conoce de verdad."""
    if fase_id not in IDS_FASE:
        raise ValueError('Fase desconocida «%s». Fases: %s' % (fase_id, ', '.join(IDS_FASE)))
    if estado not in ESTADOS:
        raise ValueError('Estado desconocido «%s». Estados: %s' % (estado, ', '.join(ESTADOS)))

    def aplicar(p):
        f = p['fases'][fase_id]
        _cronometro(f, estado, time.time())
        _ajustes_nodo(f, eta, progreso)
        for a in archivos or []:
            if a not in f['archivos']:
                f['archivos'].append(a)
        if nota is not None:
            f['nota'] = nota
        if estado in ('en_curso', 'validar', 'cambios'):
            p['fase_actual'] = fase_id
        if estado == 'aprobada':
            for e in p.get('elementos', {}).values():
                if e['fase'] == fase_id and e['estado'] == 'validar':
                    _cronometro(e, 'aprobada', time.time())
        if estado in ('aprobada', 'omitida'):
            i = IDS_FASE.index(fase_id)
            sig = next((x for x in IDS_FASE[i + 1:] if p['fases'][x]['estado'] not in ('aprobada', 'omitida')), None)
            if sig:
                p['fase_actual'] = sig
    return modificar(slug, aplicar)


# ------------------------------------------------------------------ elementos: los conceptos que intervienen en el vídeo

def elemento(slug, eid, tipo=None, nombre=None, fase_id=None, estado=None, nota=None, archivos=None, depende=None,
             eta=None, progreso=None, borrar=False):
    """Crea o actualiza un elemento (un personaje, una escena, la música, una voz…) del mapa del vídeo."""
    if not re.fullmatch(r'[\w-]{1,40}', eid or ''):
        raise ValueError('Identificador de elemento no válido «%s» (letras, números, _ y -; máximo 40).' % eid)
    if fase_id is not None and fase_id not in IDS_FASE:
        raise ValueError('Fase desconocida «%s». Fases: %s' % (fase_id, ', '.join(IDS_FASE)))
    if estado is not None and estado not in ESTADOS:
        raise ValueError('Estado desconocido «%s». Estados: %s' % (estado, ', '.join(ESTADOS)))
    if tipo is not None and tipo not in TIPOS_ELEMENTO:
        tipo = 'otro'

    def aplicar(p):
        els = p.setdefault('elementos', {})
        if borrar:
            els.pop(eid, None)
            return
        e = els.get(eid)
        if e is None:
            if not fase_id:
                raise ValueError('Elemento nuevo «%s»: indica la fase a la que pertenece (--fase).' % eid)
            e = els[eid] = {'id': eid, 'tipo': tipo or 'otro', 'nombre': nombre or eid, 'fase': fase_id, 'estado': 'pendiente',
                            'nota': '', 'archivos': [], 'depende': []}
        if tipo:
            e['tipo'] = tipo
        if nombre:
            e['nombre'] = nombre
        if fase_id:
            e['fase'] = fase_id
        if estado:
            _cronometro(e, estado, time.time())
        _ajustes_nodo(e, eta, progreso)
        if nota is not None:
            e['nota'] = nota
        for a in archivos or []:
            if a not in e['archivos']:
                e['archivos'].append(a)
        if depende is not None:
            e['depende'] = [d for d in depende if d != eid]
    p = modificar(slug, aplicar)
    return p.get('elementos', {}).get(eid)


# ------------------------------------------------------------------ cambios pedidos por el usuario

def posteriores(fase_id):
    """Todas las fases que dependen (directa o indirectamente) de `fase_id`, en el orden del flujo."""
    out, pend = set(), [fase_id]
    while pend:
        x = pend.pop()
        for f, deps in DEPENDE.items():
            if x in deps and f not in out:
                out.add(f)
                pend.append(f)
    return [f for f in IDS_FASE if f in out]


def pedir_cambio(slug, texto, objetivos, afectadas=None):
    """Registra un cambio. `objetivos`: [{'tipo': 'fase'|'elemento', 'id'}] (vacío = «todo el vídeo / no lo sé»).
    Las fases con trabajo hecho que toca el cambio pasan a `cambios`, con una nota; lo que aún no se ha hecho se deja como está."""
    texto = (texto or '').strip()
    if not texto:
        raise ValueError('Describe el cambio.')
    afectadas = [a for a in (afectadas or []) if a in IDS_FASE]
    hecho = {}

    def aplicar(p):
        cambios = p.setdefault('cambios', [])
        cid = max([c['id'] for c in cambios] + [0]) + 1
        nota = 'Cambio #%d: %s' % (cid, texto if len(texto) <= 140 else texto[:139] + '…')
        fases_obj = []
        objs = []
        for o in objetivos or []:
            if o.get('tipo') == 'fase' and o.get('id') in IDS_FASE:
                fases_obj.append(o['id'])
                objs.append({'tipo': 'fase', 'id': o['id']})
            elif o.get('tipo') == 'elemento' and o.get('id') in p.get('elementos', {}):
                e = p['elementos'][o['id']]
                fases_obj.append(e['fase'])
                objs.append({'tipo': 'elemento', 'id': e['id']})
                if e['estado'] in ('aprobada', 'validar', 'omitida'):
                    _cronometro(e, 'cambios', time.time())
                    e['nota'] = nota
        marcadas = []
        for fid in dict.fromkeys(fases_obj + afectadas):
            f = p['fases'][fid]
            if f['estado'] in ('aprobada', 'validar'):
                _cronometro(f, 'cambios', time.time())
                f['nota'] = nota
                marcadas.append(fid)
        if marcadas:
            p['fase_actual'] = min(marcadas, key=IDS_FASE.index)
        c = {'id': cid, 'texto': texto, 'objetivos': objs, 'afectadas': [a for a in afectadas if a not in fases_obj],
             'fases_marcadas': marcadas, 'estado': 'pendiente', 'creado': time.strftime('%Y-%m-%d %H:%M:%S')}
        cambios.append(c)
        hecho.update(c)
    modificar(slug, aplicar)
    return hecho


def cambio_estado(slug, cid, estado, nota=None):
    if estado not in ESTADOS_CAMBIO:
        raise ValueError('Estado de cambio desconocido «%s». Estados: %s' % (estado, ', '.join(ESTADOS_CAMBIO)))

    def aplicar(p):
        c = next((c for c in p.get('cambios', []) if c['id'] == int(cid)), None)
        if c is None:
            raise ValueError('No existe el cambio #%s.' % cid)
        c['estado'] = estado
        if nota is not None:
            c['nota'] = nota
        if estado in ('hecho', 'descartado'):
            c['cerrado'] = time.strftime('%Y-%m-%d %H:%M:%S')
    return modificar(slug, aplicar)


# ------------------------------------------------------------------ trabajo en paralelo

def puede_paralelo(p, fase_id):
    """(sí/no, motivo). Una fase puede abrir su propio carril si lo que necesita ya está aprobado (o ya tiene trabajo suyo)."""
    f = p['fases'][fase_id]
    if f['estado'] in ('en_curso', 'validar', 'cambios'):
        return True, 'ya tiene trabajo'
    if f['estado'] in ('aprobada', 'omitida'):
        return False, 'ya está terminada (pide un cambio si quieres rehacerla)'
    faltan = [d for d in DEPENDE[fase_id] if p['fases'][d]['estado'] not in ('aprobada', 'omitida')]
    if faltan:
        return False, 'primero hay que aprobar: ' + ', '.join(faltan)
    return True, ''


def archivos_proyecto(slug):
    """Árbol plano de lo que hay en la carpeta del proyecto (sin `trabajo/`)."""
    base = rutas.proyecto_dir(slug)
    out = []
    for raiz, dirs, fs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ('trabajo', '__pycache__'))
        for n in sorted(fs):
            if n == 'proyecto.json' or n.endswith('.tmp') or n.startswith('.'):
                continue
            out.append(os.path.relpath(os.path.join(raiz, n), base).replace('\\', '/'))
    return out


def videos_salida(slug):
    d = os.path.join(rutas.SALIDA, slug)
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.lower().endswith(('.mp4', '.gif', '.webm', '.mov')))


def entradas(slug=None):
    """Ficheros de la bandeja de entrada: sueltos y, si hay slug, los de su subcarpeta."""
    out = []
    base = rutas.ENTRADA
    if not os.path.isdir(base):
        return out
    for raiz, dirs, fs in os.walk(base):
        rel = os.path.relpath(raiz, base).replace('\\', '/')
        top = rel.split('/')[0]
        if rel != '.' and slug is not None and top != slug and top in listar_slugs():
            dirs[:] = []
            continue
        for n in sorted(fs):
            if n in ('LEEME.md', '.gitkeep'):
                continue
            out.append(n if rel == '.' else rel + '/' + n)
    return out


def listar_slugs():
    if not os.path.isdir(rutas.PROYECTOS):
        return []
    return [s for s in os.listdir(rutas.PROYECTOS) if existe(s)]


def contexto(slug, carril=None):
    """Texto de arranque para el agente: qué proyecto es y cómo trabajar. Lo antepone el estudio al primer mensaje.
    `carril`: id de fase si es un agente en paralelo que solo se ocupa de esa fase."""
    p = leer(slug)
    m = juegos.cargar(p['juego'])
    fmt = next((f for f in m.get('formatos', []) if f['id'] == p.get('formato')), None)
    skill = fmt['skill'] if fmt else None
    lineas = [
        'Estás trabajando en el proyecto de vídeo «%s» (slug `%s`).' % (p['titulo'], slug),
        '- Juego: %s (`%s`). Formato: %s.' % (m['nombre'], m['id'], fmt['nombre'] if fmt else p.get('formato')),
        '- Ritmo: %s' % RITMOS[p['ritmo']],
        '- Carpeta del proyecto: `proyectos/%s/` (estado en `proyecto.json`). Ficheros del usuario: `entrada/%s/` y `entrada/`.' % (slug, slug),
        '- Variable de entorno `VALEDORES_PROYECTO=%s` activa: los motores ya dejan el vídeo en `salida/%s/` y los temporales en `proyectos/%s/trabajo/`.' % (slug, slug, slug),
        '- Sigue la skill `crear-video`' + (' y la del juego `%s`.' % skill if skill else '.'),
        '- Los assets extraídos están en `biblioteca/%s/extraidos/` (si faltan: `python valedores.py extraer %s`).' % (m['id'], m['id']),
        '- El estudio dibuja el mapa del vídeo con `proyecto.json`: registra cada concepto con `python valedores.py elemento` y cada fase con `fase`'
        ' (con `--eta` en segundos cuando algo vaya a tardar); los comandos largos, con `python valedores.py ejecutar`.',
    ]
    if carril:
        otras = [f for f in IDS_FASE if f != carril and p['fases'][f]['estado'] == 'en_curso']
        lineas += [
            '',
            'ERES EL AGENTE EN PARALELO DE LA FASE «%s». Trabaja SOLO en esa fase y en sus elementos. Otros agentes trabajan a la vez en el mismo'
            ' proyecto (fases en curso: %s): no edites los ficheros de otras fases ni toques su estado.' % (carril, ', '.join(otras) or 'ninguna'),
            'Al terminar marca la fase `validar` con una nota y para: la valida el usuario.',
        ]
    return '\n'.join(lineas)
