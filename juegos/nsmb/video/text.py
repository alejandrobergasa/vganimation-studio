"""Texto con la fuente del juego (font_a.NFTR, dentro del ARM9, LZ10)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'nsmb'))
import numpy as np
import ndspy.lz10, ndspy.codeCompression as cc
from PIL import Image
import rom, nftr

_fonts = {}


def font(which=0):
    """which 0 = font_a (completa), 1 = font_b."""
    if not _fonts:
        a9 = cc.decompress(rom.rom().arm9) if rom.rom().arm9[-8:-4] else rom.rom().arm9
        res = []; i = 0
        while True:
            i = a9.find(b'LZ77\x10', i)
            if i < 0: break
            try:
                d = ndspy.lz10.decompress(a9[i + 4:i + 4 + 0x20000])
                if d[:4] == b'RTFN': res.append(nftr.Font(d))
            except Exception: pass
            i += 4
        _fonts['all'] = res
    return _fonts['all'][which]


def render(s, color=(255, 255, 255), outline=(24, 24, 48), which=0, spacing=0):
    """Devuelve PIL RGBA con el texto (1 línea) y contorno de 1 px."""
    f = font(which)
    gl = [(f.char_index(c)) for c in s]
    adv = []
    for g in gl:
        w = f.widths[g] if g < len(f.widths) and f.widths[g] else (0, f.tw, f.tw)
        adv.append(w)
    W = sum(a[2] for a in adv) + spacing * len(s) + 4; H = f.th + 4
    img = np.zeros((H, W, 4), np.uint8); x = 0
    for g, (l, w, a) in zip(gl, adv):
        bm = f.glyph(g)
        sub = img[2:2 + f.th, 1 + max(0, x + l):1 + max(0, x + l) + f.tw]
        n = min(sub.shape[1], f.tw)
        m = bm[:, :n] > 0
        sub[m[:, :sub.shape[1]]] = (*color, 255)
        x += a + spacing
    if outline:
        a = img[..., 3] > 0; d = np.zeros_like(a)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                d |= np.roll(np.roll(a, dy, 0), dx, 1)
        img[d & ~a] = (*outline, 255)
    return Image.fromarray(img, 'RGBA')


def size(s, which=0):
    return render(s, which=which).size
