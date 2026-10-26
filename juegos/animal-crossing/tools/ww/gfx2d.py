"""Gráficos 2D de la DS: tiles 4/8 bpp, paletas BGR555 y mapas de tiles (pantallas)."""
import numpy as np
from PIL import Image


def palette(data, n=None):
    a = np.frombuffer(data[:len(data) // 2 * 2], '<u2').astype(np.uint32)
    if n:
        a = a[:n]
    r = (a & 31) * 255 // 31
    g = ((a >> 5) & 31) * 255 // 31
    b = ((a >> 10) & 31) * 255 // 31
    return np.stack([r, g, b, np.full_like(r, 255)], -1).astype(np.uint8)


def tiles(data, bpp):
    """Devuelve array (n, 8, 8) de índices."""
    a = np.frombuffer(data, np.uint8)
    if bpp == 4:
        px = np.empty(a.size * 2, np.uint8)
        px[0::2] = a & 15
        px[1::2] = a >> 4
    else:
        px = a
    return px[:px.size // 64 * 64].reshape(-1, 8, 8)


def render_map(tile_idx, pal, nsc, bpp, width=32, height=None, transparent0=True, tile_base=0):
    """nsc: u16 por celda: tile 0-9, flipx 10, flipy 11, paleta 12-15."""
    cells = np.frombuffer(nsc[:len(nsc) // 2 * 2], '<u2')
    h = height or len(cells) // width
    out = np.zeros((h * 8, width * 8, 4), np.uint8)
    for i, c in enumerate(cells[:width * h]):
        t = (int(c) & 0x3FF) - tile_base
        if t < 0 or t >= len(tile_idx):
            continue
        px = tile_idx[t]
        if c & 0x400:
            px = px[:, ::-1]
        if c & 0x800:
            px = px[::-1, :]
        pb = ((int(c) >> 12) & 15) * 16 if bpp == 4 else 0
        rgba = pal[np.minimum(px.astype(np.int32) + pb, len(pal) - 1)].copy()
        if transparent0:
            rgba[px == 0, 3] = 0
        y, x = divmod(i, width)
        out[y * 8:(y + 1) * 8, x * 8:(x + 1) * 8] = rgba
    return out


def tile_sheet(tile_idx, pal, cols=16, pal_sel=0, bpp=4):
    n = len(tile_idx)
    rows = (n + cols - 1) // cols
    out = np.zeros((rows * 8, cols * 8, 4), np.uint8)
    for i in range(n):
        y, x = divmod(i, cols)
        px = tile_idx[i]
        out[y * 8:(y + 1) * 8, x * 8:(x + 1) * 8] = pal[np.minimum(px.astype(np.int32) + pal_sel * 16, len(pal) - 1)]
    return out
