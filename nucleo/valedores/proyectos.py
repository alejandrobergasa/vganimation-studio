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
`python valedores.py fase <slug> <fase> <estado>` y el estudio lo muestra y recoge la validación.
"""
import json
import os
import re
import time
import unicodedata

from . import juegos, rutas

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
    tmp = _ruta(slug) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(p, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _ruta(slug))


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


def fase(slug, fase_id, estado, archivos=None, nota=None):
    """Marca el estado de una fase (lo usa el agente). Avanza `fase_actual` al aprobar."""
    if fase_id not in IDS_FASE:
        raise ValueError('Fase desconocida «%s». Fases: %s' % (fase_id, ', '.join(IDS_FASE)))
    if estado not in ESTADOS:
        raise ValueError('Estado desconocido «%s». Estados: %s' % (estado, ', '.join(ESTADOS)))
    p = leer(slug)
    f = p['fases'][fase_id]
    f['estado'] = estado
    if archivos:
        for a in archivos:
            if a not in f['archivos']:
                f['archivos'].append(a)
    if nota is not None:
        f['nota'] = nota
    if estado in ('en_curso', 'validar', 'cambios'):
        p['fase_actual'] = fase_id
    if estado in ('aprobada', 'omitida'):
        i = IDS_FASE.index(fase_id)
        sig = next((x for x in IDS_FASE[i + 1:] if p['fases'][x]['estado'] not in ('aprobada', 'omitida')), None)
        if sig:
            p['fase_actual'] = sig
    guardar(slug, p)
    return p


def archivos_proyecto(slug):
    """Árbol plano de lo que hay en la carpeta del proyecto (sin `trabajo/`)."""
    base = rutas.proyecto_dir(slug)
    out = []
    for raiz, dirs, fs in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in ('trabajo', '__pycache__'))
        for n in sorted(fs):
            if n == 'proyecto.json' or n.endswith('.tmp'):
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


def contexto(slug):
    """Texto de arranque para el agente: qué proyecto es y cómo trabajar. Lo antepone el estudio al primer mensaje."""
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
    ]
    return '\n'.join(lineas)
