"""Tareas largas de un proyecto (renders, síntesis de audio…) con tiempo estimado.

`python valedores.py ejecutar <slug> -- <comando>` registra aquí cada ejecución. El estudio las enseña con una barra de
progreso basada en el tiempo: la estimación es la que dé el agente (`--eta`) o, si no, la mediana de las últimas veces que
se ejecutó lo mismo en este proyecto.

    proyectos/<slug>/trabajo/tareas.json   {"activas": {id: {...}}, "historial": {clave: [segundos, ...]}}   (no se versiona)
"""
import json
import os
import statistics
import time
import uuid

from . import bloqueo, rutas

RECIENTES = 5


def _ruta(slug):
    return os.path.join(rutas.proyecto_dir(slug), 'trabajo', 'tareas.json')


def _leer(slug):
    try:
        with open(_ruta(slug), encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    d.setdefault('activas', {})
    d.setdefault('historial', {})
    return d


def _modificar(slug, fn):
    with bloqueo.bloqueo(_ruta(slug) + '.lock'):
        d = _leer(slug)
        r = fn(d)
        tmp = _ruta(slug) + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False)
        bloqueo.reemplazar(tmp, _ruta(slug))
        return r


def clave_de(cmd):
    """Identifica «lo mismo» entre ejecuciones: el script y sus argumentos, sin rutas."""
    partes = [os.path.basename(a) if (os.sep in a or '/' in a) else a for a in cmd]
    return ' '.join(partes)[:200]


def etiqueta_de(cmd):
    for a in cmd:
        if a.lower().endswith('.py'):
            return 'Ejecutando ' + os.path.basename(a)
    return 'Ejecutando ' + os.path.basename(cmd[0]) if cmd else 'Tarea'


def estimar(historial, clave):
    """Segundos previstos para `clave` según las últimas ejecuciones; si nunca se ejecutó igual, se mira el mismo script con otros argumentos."""
    h = historial.get(clave)
    if not h:
        script = clave.split(' ')[0:2]
        base = [v for k, v in historial.items() if k.split(' ')[0:2] == script]
        h = [d for v in base for d in v]
    return round(statistics.median(h[-RECIENTES:])) if h else None


def iniciar(slug, etiqueta, clave, eta=None, fase=None, elemento=None, pid=None):
    tid = uuid.uuid4().hex[:8]

    def f(d):
        d['activas'] = {k: t for k, t in d['activas'].items() if bloqueo.vivo(t.get('pid'))}
        d['activas'][tid] = {
            'id': tid, 'etiqueta': etiqueta, 'clave': clave, 'inicio': time.time(), 'pid': pid or os.getpid(),
            'eta': eta if eta else estimar(d['historial'], clave), 'eta_origen': 'agente' if eta else 'historial',
            'fase': fase, 'elemento': elemento,
        }
    _modificar(slug, f)
    return tid


def terminar(slug, tid, ok=True):
    def f(d):
        t = d['activas'].pop(tid, None)
        if t and ok:
            h = d['historial'].setdefault(t['clave'], [])
            h.append(round(time.time() - t['inicio']))
            del h[:-RECIENTES * 2]
    _modificar(slug, f)


def activas(slug):
    """Tareas en marcha (se descartan las de procesos que ya no existen: el agente se paró a medias)."""
    if not os.path.isfile(_ruta(slug)):
        return []
    d = _leer(slug)
    vivas = [t for t in d['activas'].values() if bloqueo.vivo(t.get('pid'))]
    return sorted(vivas, key=lambda t: t['inicio'])
