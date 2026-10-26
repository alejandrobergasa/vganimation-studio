"""Fuentes NFTR (RTFN): glifos, anchos y mapa de caracteres."""
import struct
import numpy as np
from PIL import Image


class Font:
    def __init__(self, d, off=0):
        d = bytes(d[off:])
        assert d[:4] == b'RTFN'
        hsize, nblocks = struct.unpack_from('<HH', d, 0xC)
        p = hsize
        blocks = {}
        for _ in range(nblocks):
            m = d[p:p+4]; sz = struct.unpack_from('<I', d, p+4)[0]
            blocks[m] = p
            p += sz
        f = blocks[b'FNIF']
        (_, self.height, self.err, self.dleft, self.dwidth, self.dadv, self.enc,
         ocglp, ocwdh, ocmap) = struct.unpack_from('<BBHBBBBIII', d, f + 8)
        g = ocglp - 8
        self.tw, self.th, self.tbytes = struct.unpack_from('<BBH', d, g + 8)
        self.depth = d[g + 14]
        self.rot = d[g + 15]
        gsz = struct.unpack_from('<I', d, g + 4)[0]
        self.glyph_data = d[g + 16:g + gsz]
        self.nglyphs = len(self.glyph_data) // self.tbytes
        # anchos
        self.widths = [None] * self.nglyphs
        q = ocwdh - 8
        while q:
            first, last, nxt = struct.unpack_from('<HHI', d, q + 8)
            for i in range(first, last + 1):
                l, w, a = struct.unpack_from('<bBB', d, q + 16 + (i - first) * 3)
                if i < self.nglyphs: self.widths[i] = (l, w, a)
            q = nxt - 8 if nxt else 0
        # mapa char -> glifo
        self.cmap = {}
        q = ocmap - 8
        while q:
            first, last, typ, _, nxt = struct.unpack_from('<HHHHI', d, q + 8)
            base = q + 20
            if typ == 0:
                idx0 = struct.unpack_from('<H', d, base)[0]
                for c in range(first, last + 1): self.cmap[c] = idx0 + c - first
            elif typ == 1:
                for c in range(first, last + 1):
                    v = struct.unpack_from('<H', d, base + (c - first) * 2)[0]
                    if v != 0xFFFF: self.cmap[c] = v
            elif typ == 2:
                n = struct.unpack_from('<H', d, base)[0]
                for k in range(n):
                    c, v = struct.unpack_from('<HH', d, base + 2 + k * 4)
                    if v != 0xFFFF: self.cmap[c] = v
            q = nxt - 8 if nxt else 0
        self._cache = {}

    def glyph(self, idx):
        """Bitmap (th, tw) con valores 0..(2^depth-1)."""
        if idx in self._cache: return self._cache[idx]
        raw = np.frombuffer(self.glyph_data[idx * self.tbytes:(idx + 1) * self.tbytes], np.uint8)
        bits = np.unpackbits(raw).reshape(-1, 8)
        px = bits.reshape(-1)
        if self.depth == 2:
            px = (px[0::2] << 1) | px[1::2]
        elif self.depth != 1:
            px = px  # no usado
        a = px[:self.tw * self.th].reshape(self.th, self.tw)
        self._cache[idx] = a
        return a

    def char_index(self, ch):
        return self.cmap.get(ord(ch), self.err)
