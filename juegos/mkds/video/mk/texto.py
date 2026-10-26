"""Texto con la fuente del juego (marioFont.NFTR / LC_Font_m.NFTR de Main2D.carc) para títulos y subtítulos.
Devuelve RGBA float32 listo para componer; se escala suavizando los bordes del píxel-art."""
import math
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation

import mkrom, nftr

_F = {}


def fuente(nombre='marioFont.NFTR'):
    if nombre not in _F:
        _F[nombre] = nftr.Font(mkrom.narc('data/Main2D.carc')[nombre])
    return _F[nombre]


def _niveles(s, nombre):
    """Mapa de niveles (alto, ancho) de la línea completa; 0 = vacío."""
    f = fuente(nombre)
    gl = [f.char_index(c) for c in s]
    adv = [(f.widths[g] if g < len(f.widths) and f.widths[g] else (0, f.tw, f.tw)) for g in gl]
    W = sum(a[2] for a in adv) + f.tw + 4; H = f.th + 4
    img = np.zeros((H, W), np.uint8); x = 2
    for g, (l, w, ad) in zip(gl, adv):
        bm = f.glyph(g); xs = max(0, x + l)
        sub = img[2:2 + f.th, xs:xs + f.tw]
        sub[:, :] = np.maximum(sub, bm[:, :sub.shape[1]])
        x += ad
    cols = np.nonzero(img.any(0))[0]
    return img[:, max(0, cols[0] - 1):cols[-1] + 2] if len(cols) else img


def render(s, alto_px=96, relleno=((1.0, 1.0, 0.75), (1.0, 0.85, 0.15)), borde=(0.10, 0.05, 0.25), grosor=0.12,
           sombra=(0.0, 0.0, 0.0), nombre='marioFont.NFTR', interletra=0):
    """-> RGBA float32 (h, w, 4), con `alto_px` de altura de línea. relleno = (color arriba, color abajo)."""
    lv = _niveles(s, nombre)
    f = fuente(nombre)
    k = 8
    grande = np.kron(lv, np.ones((k, k), np.uint8))
    cuerpo = (lv == lv.max()) if f.depth == 2 else (lv > 0)
    cu = np.kron(cuerpo.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
    tinta = grande > 0
    pad = int(grosor * f.th * k)
    ext = binary_dilation(tinta, iterations=max(1, pad)) if pad else tinta
    H, W = grande.shape
    out = np.zeros((H, W, 4), np.float32)
    # sombra
    sh = np.roll(np.roll(ext, int(f.th * k * 0.10), 0), int(f.th * k * 0.06), 1)
    out[sh] = (*sombra, 0.45)
    out[ext] = (*borde, 1.0)
    # contorno interno del juego en tono intermedio, cuerpo con degradado vertical
    ys = np.linspace(0, 1, H)[:, None, None]
    arriba, abajo = np.array(relleno[0], np.float32), np.array(relleno[1], np.float32)
    grad = arriba * (1 - ys) + abajo * ys
    out[cu, :3] = np.broadcast_to(grad, (H, W, 3))[cu]
    out[cu, 3] = 1.0
    medio = tinta & ~cu
    out[medio, :3] = (np.array(borde) * 0.6 + np.array(abajo) * 0.4)
    esc = alto_px / (f.th + 4) / k
    im = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), 'RGBA')
    # premultiplicado para no ensuciar bordes al reducir
    a = np.asarray(im, np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    nw, nh = max(1, int(W * esc)), max(1, int(H * esc))
    ch = [np.asarray(Image.fromarray(a[..., c]).resize((nw, nh), Image.LANCZOS)) for c in range(4)]
    r = np.stack(ch, -1)
    r[..., :3] = np.where(r[..., 3:4] > 1e-4, r[..., :3] / np.maximum(r[..., 3:4], 1e-4), 0)
    return np.clip(r, 0, 1)


def componer(img, rgba, cx, cy, alfa=1.0, escala=1.0, giro=0.0, anclaje=(0.5, 0.5), ajustar=0.92):
    """Compone rgba sobre img (float32 h,w,3) centrado (según anclaje) en (cx, cy) píxeles, con escala y giro."""
    if alfa <= 0 or escala <= 0.01: return img
    t = rgba
    if ajustar and rgba.shape[1] * escala > ajustar * img.shape[1]:       # nunca se sale de la pantalla
        escala = ajustar * img.shape[1] / rgba.shape[1]
    if abs(escala - 1) > 1e-3 or abs(giro) > 1e-3:
        im = Image.fromarray((np.concatenate([t[..., :3] * t[..., 3:4], t[..., 3:4]], -1) * 255).astype(np.uint8), 'RGBA')
        nw, nh = max(1, int(t.shape[1] * escala)), max(1, int(t.shape[0] * escala))
        im = im.resize((nw, nh), Image.BILINEAR)
        if abs(giro) > 1e-3: im = im.rotate(giro, Image.BILINEAR, expand=True)
        a = np.asarray(im, np.float32) / 255.0
        t = np.concatenate([np.where(a[..., 3:4] > 1e-4, a[..., :3] / np.maximum(a[..., 3:4], 1e-4), 0), a[..., 3:4]], -1)
    h, w = t.shape[:2]
    x0 = int(round(cx - w * anclaje[0])); y0 = int(round(cy - h * anclaje[1]))
    H, W = img.shape[:2]
    xa, ya, xb, yb = max(0, x0), max(0, y0), min(W, x0 + w), min(H, y0 + h)
    if xa >= xb or ya >= yb: return img
    s = t[ya - y0:yb - y0, xa - x0:xb - x0]
    al = s[..., 3:4] * alfa
    img[ya:yb, xa:xb] = img[ya:yb, xa:xb] * (1 - al) + s[..., :3] * al
    return img


def rebote(t, dur=0.5):
    """Escala 0 -> 1 con rebote elástico (para títulos que entran de golpe)."""
    if t <= 0: return 0.0
    if t >= dur: return 1.0
    x = t / dur
    return 1 - math.exp(-6.5 * x) * math.cos(2 * math.pi * 1.4 * x)
