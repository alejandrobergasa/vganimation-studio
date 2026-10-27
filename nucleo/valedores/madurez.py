"""Indicadores de madurez de cada juego: cuánto del trabajo de producir un vídeo está ya resuelto (motor, ejemplos, lecciones) y cuánto
cuesta de verdad (correcciones y coste por vídeo). Son orientativos: sirven para ver hacia dónde mejora cada juego, no para puntuarlo."""
import glob
import json
import os
import re

from . import lecciones, rutas

PREFIJO_PRUEBA = 'prueba_motor_'
NIVELES = ((5, 'alta'), (3, 'media'), (0, 'baja'))


def _lineas(ruta):
    try:
        with open(ruta, encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _coste(slug):
    """Coste total del proyecto según el historial del chat del estudio (0 si no hay)."""
    total = 0.0
    for f in glob.glob(os.path.join(rutas.REPO, '.estudio', 'chats', slug + '*.jsonl')):
        if os.path.basename(f)[len(slug):][:1] not in ('.', '@'):
            continue
        with open(f, encoding='utf-8') as fh:
            for linea in fh:
                try:
                    e = json.loads(linea)
                except ValueError:
                    continue
                if e.get('t') == 'fin' and e.get('coste'):
                    total += e['coste']
    return total


def de_juego(juego):
    d = rutas.juego_dir(juego)
    loc = 0
    for raiz, _, fs in os.walk(d):
        if '__pycache__' in raiz:
            continue
        loc += sum(_lineas(os.path.join(raiz, f)) for f in fs if f.endswith('.py'))
    motor = os.path.join(d, 'video', 'motor.py')
    compartido = os.path.isfile(motor) and 'video_nds' in open(motor, encoding='utf-8', errors='ignore').read()
    ejemplos = 0
    for sub in ('video', 'ejemplos', 'cinematicas'):
        for raiz, _, fs in os.walk(os.path.join(d, sub)):
            if '__pycache__' in raiz or (sub == 'video' and raiz != os.path.join(d, sub)):
                continue                 # los paquetes dentro de video/ son el motor, no ejemplos
            ejemplos += sum(1 for f in fs if f.endswith(('.py', '.md')) and not f.startswith(('motor', 'demo', '__')))
    try:
        with open(os.path.join(d, 'CONOCIMIENTO.md'), encoding='utf-8') as f:
            pendientes = len(re.findall(r'pendiente', f.read(), re.I))
    except OSError:
        pendientes = 0
    reales, cambios, coste = 0, 0, 0.0
    for pj in glob.glob(os.path.join(rutas.PROYECTOS, '*', 'proyecto.json')):
        slug = os.path.basename(os.path.dirname(pj))
        try:
            with open(pj, encoding='utf-8') as f:
                p = json.load(f)
        except (OSError, ValueError):
            continue
        if p.get('juego') != juego or slug.startswith(PREFIJO_PRUEBA):
            continue
        reales += 1
        cambios += len(p.get('cambios', []))
        coste += _coste(slug)
    ls = lecciones.leer(juego)['lecciones']
    m = {
        'juego': juego, 'loc': loc, 'motor_compartido': compartido, 'ejemplos': ejemplos, 'pendientes': pendientes,
        'videos_reales': reales, 'cambios': cambios, 'coste': coste,
        'lecciones_activas': sum(l['estado'] == 'activa' for l in ls), 'lecciones_promovidas': sum(l['estado'] == 'promovida' for l in ls),
        'reabiertas': sum(l.get('reabierta', 0) for l in ls),
    }
    m['cambios_por_video'] = cambios / reales if reales else None
    m['coste_por_video'] = coste / reales if reales and coste else None
    puntos = (2 if loc >= 2500 else 1 if loc >= 300 else 0) + (1 if ejemplos >= 5 else 0) + (2 if reales >= 3 else 1 if reales >= 1 else 0)
    puntos += (1 if pendientes <= 3 else 0) + (1 if m['lecciones_promovidas'] >= 3 else 0)
    if ejemplos >= 10:
        puntos += 1                      # muchos vídeos previos con sus guiones: el agente tiene de dónde copiar
    m['puntos'] = puntos
    m['nivel'] = next(n for minimo, n in NIVELES if puntos >= minimo)
    return m


def todos():
    return [de_juego(j) for j in sorted(rutas.juegos())]
