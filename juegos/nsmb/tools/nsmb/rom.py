"""Acceso a la ROM de NSMB: ficheros por nombre, descompresión automática."""
import os, glob, struct, sys
import ndspy.rom
import ndsgfx as G

def _repo():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(d, 'valedores.toml')):
        d = os.path.dirname(d)
    return d


sys.path.insert(0, os.path.join(_repo(), 'nucleo'))
from valedores import rutas  # noqa: E402,F401

JUEGO = 'nsmb'

_ROM = None
_PATH = None

def find_rom():
    return rutas.rom(JUEGO)

def rom():
    global _ROM
    if _ROM is None:
        _ROM = ndspy.rom.NintendoDSRom.fromFile(find_rom())
    return _ROM

def get(name):
    """Bytes de un fichero NitroFS tal cual."""
    return bytes(rom().getFileByName(name))

def getu(name):
    """Bytes del fichero, descomprimiendo LZ10/LZ11 si procede."""
    d = get(name)
    if d[:1] in (b'\x10', b'\x11'):
        u = G.lz_decompress(d)
        if u is not None:
            return u
    return d

def listdir(prefix):
    out = []
    def walk(f, p):
        for n, sub in f.folders: walk(sub, p + n + '/')
        for n in f.files: out.append(p + n)
    walk(rom().filenames, '')
    return [f for f in out if f.startswith(prefix)]
