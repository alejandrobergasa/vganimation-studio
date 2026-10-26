"""Utilidad de exploración: dibuja datos crudos como hojas de tiles en gris."""
import numpy as np
from PIL import Image, ImageDraw
import ndsgfx as G

def tiles_img(data, bpp=4, cols=16, scale=2, maxrows=None):
    a = np.frombuffer(data, np.uint8)
    if bpp == 4:
        px = np.empty(a.size * 2, np.uint8); px[0::2] = a & 15; px[1::2] = a >> 4; px = px * 17
    else:
        px = a
    n = px.size // 64
    if n == 0: return None
    px = px[:n * 64].reshape(n, 8, 8)
    rows = (n + cols - 1) // cols
    if maxrows: rows = min(rows, maxrows)
    im = np.zeros((rows * 8, cols * 8), np.uint8)
    for i in range(min(n, rows * cols)):
        im[(i // cols) * 8:(i // cols) * 8 + 8, (i % cols) * 8:(i % cols) * 8 + 8] = px[i]
    return Image.fromarray(im).resize((cols * 8 * scale, rows * 8 * scale), Image.NEAREST)
