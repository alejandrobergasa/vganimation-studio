"""Acceso a la ROM de Mario Kart DS (Europa): ficheros NitroFS y archivos .carc (NARC con LZ10)."""
import os, sys
import ndspy.rom, ndspy.narc, ndspy.lz10


def _repo():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(d, 'valedores.toml')):
        d = os.path.dirname(d)
    return d


sys.path.insert(0, os.path.join(_repo(), 'nucleo'))
from valedores import rutas  # noqa: E402

JUEGO = 'mkds'

_ROM = None
_NARCS = {}

def find_rom():
    return rutas.rom(JUEGO)


def rom():
    global _ROM
    if _ROM is None:
        _ROM = ndspy.rom.NintendoDSRom.fromFile(find_rom())
    return _ROM


def descomprimir(d):
    d = bytes(d)
    if d[:4] == b'LZ77':
        return ndspy.lz10.decompress(d[4:])
    if d[:1] == b'\x10':
        return ndspy.lz10.decompress(d)
    return d


def get(name):
    """Fichero NitroFS descomprimido (LZ10 / envoltorio LZ77 si lo tiene)."""
    return descomprimir(rom().getFileByName(name))


def listdir(prefix=''):
    out = []
    def walk(f, p):
        for n, sub in f.folders: walk(sub, p + n + '/')
        for n in f.files: out.append(p + n)
    walk(rom().filenames, '')
    return [f for f in out if f.startswith(prefix)]


def narc(name):
    """{ruta interna: bytes} de un .carc (ruta completa NitroFS, p. ej. 'data/KartModelSub.carc')."""
    if name not in _NARCS:
        ar = ndspy.narc.NARC(get(name))
        res = {}
        def w(f, p):
            for a, s in f.folders: w(s, p + a + '/')
            for a in f.files: res[p + a] = bytes(ar.files[f.idOf(a)])
        w(ar.filenames, '')
        _NARCS[name] = res
    return _NARCS[name]
