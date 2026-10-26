"""Rutas del repositorio: ROMs, biblioteca de assets, bandejas de entrada y salida.

Solo usa la librería estándar para que lo importe cualquier script de cualquier juego, también con
`python -I`. Un script de juego no calcula nunca rutas relativas a sí mismo hacia ROMs o assets:
las pide aquí.

    from valedores import rutas
    rutas.rom('animal-crossing')        # ROM localizada por su código de juego
    rutas.extraidos('animal-crossing')  # biblioteca/animal-crossing/extraidos
    rutas.salida('animal-crossing')     # carpeta donde dejar los vídeos

Con `VALEDORES_PROYECTO=<slug>` (lo fijan el estudio y `valedores.py ejecutar`) la salida pasa a
`salida/<slug>/` y el trabajo a `proyectos/<slug>/trabajo/`, sea cual sea el juego.
"""
import json
import os

_AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(_AQUI, '..', '..'))

ROMS = os.path.join(REPO, 'roms')
ENTRADA = os.path.join(REPO, 'entrada')
SALIDA = os.path.join(REPO, 'salida')
BIBLIOTECA = os.path.join(REPO, 'biblioteca')
JUEGOS = os.path.join(REPO, 'juegos')
PROYECTOS = os.path.join(REPO, 'proyectos')
CACHE = os.path.join(REPO, '.cache')
LIB = os.path.join(REPO, 'lib')


def juego_dir(juego):
    return os.path.join(JUEGOS, juego)


def biblioteca(juego):
    return os.path.join(BIBLIOTECA, juego)


def extraidos(juego):
    """Assets sacados de la ROM por el extractor. Regenerable, no se versiona."""
    return os.path.join(BIBLIOTECA, juego, 'extraidos')


def personalizados(juego):
    """Assets propios (personajes, fotos, sprites hechos a mano). Sí se versionan."""
    return os.path.join(BIBLIOTECA, juego, 'personalizados')


def cache(juego):
    """Audio renderizado y temporales regenerables."""
    d = os.path.join(CACHE, juego)
    os.makedirs(d, exist_ok=True)
    return d


def proyecto_activo():
    """Slug del proyecto en curso (variable `VALEDORES_PROYECTO`), o None."""
    return os.environ.get('VALEDORES_PROYECTO') or None


def proyecto_dir(slug):
    return os.path.join(PROYECTOS, slug)


def salida(juego=None):
    """Carpeta de vídeos resultado: la del proyecto activo, o `salida/<juego>/` si no hay."""
    p = proyecto_activo()
    if p:
        d = os.path.join(SALIDA, p)
    elif juego:
        d = os.path.join(SALIDA, juego)
    else:
        d = SALIDA
    os.makedirs(d, exist_ok=True)
    return d


def trabajo(juego=None):
    """Carpeta para fotogramas de revisión, audio intermedio y basura de trabajo (no se versiona)."""
    p = proyecto_activo()
    if p:
        d = os.path.join(PROYECTOS, p, 'trabajo')
    else:
        d = os.path.join(CACHE, juego or '_general', 'trabajo')
    os.makedirs(d, exist_ok=True)
    return d


def motor_dir(juego):
    """Carpeta del motor del juego (la que un script de proyecto añade a `sys.path`)."""
    return os.path.join(juego_dir(juego), manifiesto(juego).get('motor', 'video/'))


def manifiesto(juego):
    with open(os.path.join(juego_dir(juego), 'juego.json'), encoding='utf-8') as f:
        return json.load(f)


def juegos():
    """Ids de los juegos instalados (carpetas de `juegos/` con `juego.json`)."""
    if not os.path.isdir(JUEGOS):
        return []
    return sorted(d for d in os.listdir(JUEGOS) if os.path.isfile(os.path.join(JUEGOS, d, 'juego.json')))


def codigo_rom(path):
    """Código de juego de 4 letras de una ROM de DS (cabecera, offset 0xC), o None."""
    try:
        with open(path, 'rb') as f:
            h = f.read(0x10)
    except OSError:
        return None
    if len(h) < 0x10:
        return None
    c = h[0xC:0x10]
    if not all(32 <= b < 127 for b in c):
        return None
    return c.decode('ascii')


def roms_disponibles():
    """{ruta: codigo} de todas las .nds de `roms/` (recursivo)."""
    out = {}
    for raiz, _, fs in os.walk(ROMS):
        for n in sorted(fs):
            if n.lower().endswith('.nds'):
                p = os.path.join(raiz, n)
                c = codigo_rom(p)
                if c:
                    out[p] = c
    return out


def rom_opt(juego):
    """Ruta de la ROM del juego, o None si no está en `roms/`."""
    codigos = set(manifiesto(juego)['rom']['codigos'])
    for p, c in roms_disponibles().items():
        if c in codigos:
            return p
    return None


def rom(juego):
    p = rom_opt(juego)
    if p is None:
        m = manifiesto(juego)
        raise FileNotFoundError(
            'Falta la ROM de «%s» (código %s). Copia tu .nds a %s; se reconoce por su cabecera, '
            'el nombre del fichero da igual.' % (m['nombre'], '/'.join(m['rom']['codigos']), ROMS))
    return p
