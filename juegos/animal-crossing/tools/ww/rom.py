"""Acceso a la ROM de Animal Crossing: Wild World (NitroFS) con descompresión automática.

Los ficheros comprimidos empiezan por 'LZ77' seguido de un flujo LZ10 estándar de la BIOS.
"""
import os
import struct
import sys
import ndspy.rom

def _repo():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(d, 'valedores.toml')):
        d = os.path.dirname(d)
    return d


sys.path.insert(0, os.path.join(_repo(), 'nucleo'))
from valedores import rutas  # noqa: E402,F401

JUEGO = 'animal-crossing'


def lz10(data, off=0):
    """Descomprime un flujo LZ10 (tipo 0x10) que empieza en data[off]."""
    return _lz10(data, off)[0]


def _lz10(data, off):
    """Como lz10, pero devuelve también la posición donde acaba el flujo."""
    if data[off] != 0x10:
        raise ValueError('no es LZ10')
    size = data[off + 1] | data[off + 2] << 8 | data[off + 3] << 16
    out = bytearray()
    p = off + 4
    n = len(data)
    while len(out) < size and p < n:
        flags = data[p]; p += 1
        for bit in range(8):
            if len(out) >= size or p >= n:
                break
            if flags & (0x80 >> bit):
                b0, b1 = data[p], data[p + 1]; p += 2
                ln = (b0 >> 4) + 3
                disp = ((b0 & 15) << 8 | b1) + 1
                for _ in range(ln):
                    out.append(out[-disp])
            else:
                out.append(data[p]); p += 1
    return bytes(out[:size]), p


def lz10_trozos(data, off, total):
    """Tipo 0xF7 (textos y scripts): 'LZ77', 0xF7+tamaño u24, tabla de u16 (uno por bloque) y bloques LZ10 de <= 4096 bytes."""
    out = bytearray()
    p = off
    while len(out) < total and p + 4 <= len(data):
        size = data[p + 1] | data[p + 2] << 8 | data[p + 3] << 16
        chunk, p = _lz10(data, p)
        out += chunk
    return bytes(out[:total])


def unwrap(data):
    """Quita la envoltura LZ77 si la hay."""
    data = bytes(data)
    if data[:4] == b'LZ77':
        if data[4] == 0xF7:
            total = data[5] | data[6] << 8 | data[7] << 16
            return lz10_trozos(data, 8 + 2 * -(-total // 4096), total)
        return lz10(data, 4)
    return data


class Rom:
    def __init__(self, path=None):
        path = path or rutas.rom(JUEGO)
        self.rom = ndspy.rom.NintendoDSRom.fromFile(path)
        self.header = open(path, 'rb').read(0x200)
        self.index = {}
        self._walk(self.rom.filenames, '')

    def _walk(self, folder, prefix):
        for name, sub in folder.folders:
            self._walk(sub, prefix + name + '/')
        for i, name in enumerate(folder.files):
            self.index[prefix + name] = folder.firstID + i

    @property
    def title(self):
        return self.header[:12].decode('ascii', 'replace').strip('\0')

    @property
    def game_code(self):
        return self.header[12:16].decode('ascii')

    def raw(self, path):
        return bytes(self.rom.files[self.index[path]])

    def get(self, path):
        return unwrap(self.raw(path))

    def list(self, prefix=''):
        return sorted(p for p in self.index if p.startswith(prefix))
