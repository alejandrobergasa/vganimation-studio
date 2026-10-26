"""Fondos de parallax de NSMB (capas back_* y free_*): pantalla 64x64 tiles de 8x8, 8 bpp.

Los índices de tile de la pantalla llevan una base fija según la capa (free = 256, back = 576: comparten VRAM,
320 tiles cada una) y el bloque de 256 colores de la paleta es banco % 2. Validado con las hojas de contactos.
"""
import numpy as np
from PIL import Image
import rom
import raw2d as R

P = 'd_2d_I_M_'
BASE = {'free': 256, 'back': 576}


def _nsc(kind, theme):
    names = set(rom.listdir('BG_nsc/'))
    for suf in ('_UR', ''):
        n = f'BG_nsc/{P}{kind}_{theme}{suf}_nsc.bin'
        if n in names: return n
    raise FileNotFoundError(theme)


def layer(kind, theme='nohara_W1_1', alpha2=None):
    """kind: 'back' o 'free'. Devuelve PIL RGBA 512x512 (fondo transparente donde el tile es vacío).
    alpha2: si se da, los píxeles del segundo bloque de paleta se mezclan con esa opacidad (aspecto de las capas lejanas)."""
    ncg = f'BG_ncg/{P}{kind}_{theme}_ncg.bin'
    ncl = f'BG_ncl/{P}{kind}_{theme}_ncl.bin'
    tl = R.tiles(ncg, 8); pal = R.palette(ncl); sc = R.screen(_nsc(kind, theme)).copy()
    base = BASE[kind]
    tile = sc & 0x3ff
    out = (sc & 0xc00) | ((tile.astype(np.int32) - base).clip(0, 0x3ff).astype(np.uint16))
    out[tile < base] = 0x3ff                                   # sin tile
    blank = out & 0x3ff
    out[blank >= len(tl)] = 0x3ff
    sel = ((sc >> 12) % 2) == 1
    return _draw(out, sel, tl, pal, 1.0 if alpha2 is None else alpha2)


def _draw(out, sel, tl, pal, alpha2):
    """Dibuja por separado los tiles de cada bloque de paleta (256 colores)."""
    res = None
    for blk in (0, 1):
        m = sel if blk else ~sel
        e = out.copy(); e[~m] = 0x3ff
        im = R.draw_screen(e, 64, 64, tl, pal[blk * 256:(blk + 1) * 256], 8, True)
        if blk == 1 and alpha2 != 1.0:
            a = np.asarray(im).copy(); a[..., 3] = (a[..., 3] * alpha2).astype(np.uint8); im = Image.fromarray(a, 'RGBA')
        if res is None: res = im
        else: res.alpha_composite(im)
    return res
