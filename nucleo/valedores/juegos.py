"""Catálogo de juegos: manifiestos, estado de la ROM y de los assets extraídos."""
import hashlib
import json
import os
import time

from . import rutas

SELLO = '.extraccion.json'
EXT_IMAGEN = ('.png', '.jpg', '.jpeg', '.webp', '.gif')


def cargar(juego):
    m = rutas.manifiesto(juego)
    m['id'] = juego
    m['dir'] = rutas.juego_dir(juego)
    return m


def todos():
    return [cargar(j) for j in rutas.juegos()]


def _archivos_extractor(juego):
    """Código que decide qué sale de la ROM: `tools/` del juego y de los juegos de los que depende."""
    m = rutas.manifiesto(juego)
    for j in [juego] + list(m.get('depende', [])):
        base = os.path.join(rutas.juego_dir(j), 'tools')
        for raiz, dirs, fs in os.walk(base):
            dirs[:] = sorted(d for d in dirs if d != '__pycache__')
            for n in sorted(fs):
                if n.endswith('.py'):
                    yield os.path.join(raiz, n)


def hash_extractor(juego):
    h = hashlib.sha1()
    for p in _archivos_extractor(juego):
        h.update(os.path.relpath(p, rutas.JUEGOS).replace('\\', '/').encode())
        with open(p, 'rb') as f:
            h.update(f.read().replace(b'\r\n', b'\n'))
    return h.hexdigest()[:12]


def leer_sello(juego):
    p = os.path.join(rutas.extraidos(juego), SELLO)
    try:
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def escribir_sello(juego, rom, rapido=False):
    d = rutas.extraidos(juego)
    os.makedirs(d, exist_ok=True)
    s = {'fecha': time.strftime('%Y-%m-%d %H:%M:%S'), 'rom': os.path.basename(rom),
         'codigo': rutas.codigo_rom(rom), 'extractor': hash_extractor(juego), 'rapido': bool(rapido)}
    with open(os.path.join(d, SELLO), 'w', encoding='utf-8') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return s


def estado(juego):
    """{'rom', 'estado', 'sello'}; estado: sin_rom | sin_extraer | parcial | desactualizado | al_dia."""
    rom = rutas.rom_opt(juego)
    sello = leer_sello(juego)
    if sello is None:
        e = 'sin_extraer'
        if rom is None:
            e = 'sin_rom'
    elif sello.get('rapido'):
        e = 'parcial'
    elif sello.get('extractor') != hash_extractor(juego):
        e = 'desactualizado'
    else:
        e = 'al_dia'
    if rom is None and sello is None:
        e = 'sin_rom'
    return {'rom': rom, 'estado': e, 'sello': sello}


ETIQUETAS = {
    'sin_rom': 'falta la ROM',
    'sin_extraer': 'sin extraer',
    'parcial': 'extracción parcial (--rapido)',
    'desactualizado': 'el extractor ha cambiado',
    'al_dia': 'al día',
}


def vistas(juego):
    """Imágenes de ejemplo versionadas (`juegos/<id>/vistas/`) para las tarjetas del estudio."""
    d = os.path.join(rutas.juego_dir(juego), 'vistas')
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if n.lower().endswith(EXT_IMAGEN))


def formatos(juego):
    return cargar(juego).get('formatos', [])


def skills_del_juego(juego):
    d = os.path.join(rutas.juego_dir(juego), 'skills')
    if not os.path.isdir(d):
        return []
    return sorted(n for n in os.listdir(d) if os.path.isfile(os.path.join(d, n, 'SKILL.md')))
