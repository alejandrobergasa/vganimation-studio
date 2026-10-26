"""Formatos 2D de NSMB (sin cabeceras Nitro): tiles 4bpp/8bpp, paletas BGR555, mapas de pantalla."""
import numpy as np
from PIL import Image
import rom

def palette(name):
    """Paleta cruda -> array (n,4) RGBA, color 0 de cada banco transparente se decide al dibujar."""
    d = rom.getu(name)
    v = np.frombuffer(d[:len(d)//2*2], '<u2').astype(np.uint32)
    r = (v & 31) * 255 // 31; g = ((v >> 5) & 31) * 255 // 31; b = ((v >> 10) & 31) * 255 // 31
    return np.stack([r, g, b, np.full_like(r, 255)], -1).astype(np.uint8)

def tiles(name, bpp=4):
    d = np.frombuffer(rom.getu(name), np.uint8)
    if bpp == 4:
        px = np.empty(d.size * 2, np.uint8); px[0::2] = d & 15; px[1::2] = d >> 4
    else:
        px = d
    n = px.size // 64
    return px[:n*64].reshape(n, 8, 8)

def screen(name):
    d = np.frombuffer(rom.getu(name), '<u2')
    return d

def draw_screen(entries, w, h, tl, pal, bpp=4, transparent0=True, tile_base=0):
    out = np.zeros((h*8, w*8, 4), np.uint8)
    for i in range(min(w*h, entries.size)):
        e = int(entries[i]); ti = (e & 0x3FF) + tile_base; hf = (e >> 10) & 1; vf = (e >> 11) & 1; pb = e >> 12
        if ti >= len(tl): continue
        t = tl[ti]
        if hf: t = t[:, ::-1]
        if vf: t = t[::-1]
        base = pb * 16 if bpp == 4 else 0
        rgba = pal[base:base + (16 if bpp == 4 else 256)]
        if len(rgba) < (16 if bpp == 4 else 256): continue
        rgba = rgba.copy()
        if transparent0: rgba[0, 3] = 0
        y, x = (i // w) * 8, (i % w) * 8
        out[y:y+8, x:x+8] = rgba[t]
    return Image.fromarray(out, 'RGBA')

def map16(name):
    return np.frombuffer(rom.getu(name), '<u2').reshape(-1, 4)

def render_map16(entry, tl, pals, bpp8=True):
    """entry: 4 u16 (TL,TR,BL,BR). tl: array de tiles combinados. pals: función (slot)->tabla 256 RGBA."""
    out = np.zeros((16, 16, 4), np.uint8)
    for q in range(4):
        v = int(entry[q]); ti = v & 0x3ff; hf = (v >> 10) & 1; vf = (v >> 11) & 1; pb = v >> 12
        if ti >= len(tl): continue
        t = tl[ti]
        if hf: t = t[:, ::-1]
        if vf: t = t[::-1]
        pl = pals(pb)
        px = pl[t].copy(); px[t == 0, 3] = 0
        yy = (q // 2) * 8; xx = (q % 2) * 8
        out[yy:yy+8, xx:xx+8] = px
    return out
