"""Postproceso sobre imágenes float32 (h,w,3): bloom, viñeta, aberración cromática, desenfoque radial,
líneas de velocidad, gradación de color, grano, destellos y transiciones. Todo funciones puras."""
import math
import numpy as np
from scipy.ndimage import gaussian_filter, zoom

_CACHE = {}


def _polar(h, w):
    k = (h, w)
    if k not in _CACHE:
        y, x = np.mgrid[0:h, 0:w].astype(np.float32)
        cx, cy = (w - 1) / 2, (h - 1) / 2
        dx, dy = (x - cx) / (h / 2), (y - cy) / (h / 2)
        _CACHE[k] = (dx, dy, np.hypot(dx, dy), np.arctan2(dy, dx))
    return _CACHE[k]


def _reducir(img, f):
    h, w = img.shape[:2]
    hh, ww = h // f, w // f
    return img[:hh * f, :ww * f].reshape(hh, f, ww, f, 3).mean((1, 3))


def _ampliar(img, h, w):
    f = h / img.shape[0], w / img.shape[1]
    return zoom(img, (f[0], f[1], 1), order=1)[:h, :w]


def bloom(img, umbral=0.78, fuerza=0.35, radio=14, pasadas=2):
    h, w = img.shape[:2]
    f = 4
    p = _reducir(img, f)
    br = np.maximum(p - umbral, 0) / max(1e-3, 1 - umbral + 0.5)
    acc = np.zeros_like(br)
    for k in range(pasadas):
        acc += gaussian_filter(br, (radio / f * (1 + k * 1.6),) * 2 + (0,))
    return img + _ampliar(acc / pasadas, h, w) * fuerza * 2.2


def vineta(img, fuerza=0.38, dureza=1.8):
    h, w = img.shape[:2]
    _, _, r, _ = _polar(h, w)
    v = 1 - fuerza * np.clip(r / 1.15, 0, 1.4) ** dureza
    return img * v[..., None]


def _escala_idx(n, centro, s):
    """Índices de muestreo de una escala s alrededor de `centro` (separable en x e y)."""
    return np.clip(np.rint(centro + (np.arange(n) - centro) * s).astype(np.int32), 0, n - 1)


def aberracion(img, px=3.0):
    """Separa rojo y azul radialmente (px píxeles en el borde) con escalas distintas por canal (separable, rápido)."""
    if px < 0.05: return img
    h, w = img.shape[:2]
    out = img.copy()
    k = px / (w / 2.0)
    for c, s in ((0, 1 + k), (2, 1 - k)):
        iy = _escala_idx(h, (h - 1) / 2, s); ix = _escala_idx(w, (w - 1) / 2, s)
        out[..., c] = img[..., c][np.ix_(iy, ix)]
    return out


def desenfoque_radial(img, fuerza=0.04, muestras=8, centro=(0.5, 0.5), zona_limpia=0.25):
    """Zoom-blur: promedia copias ampliadas desde el centro; la zona central permanece nítida."""
    if fuerza < 1e-4: return img
    h, w = img.shape[:2]
    _, _, r, _ = _polar(h, w)
    peso = np.clip((r - zona_limpia) / 0.8, 0, 1)[..., None]
    acc = np.zeros_like(img)
    for k in range(muestras):
        s = 1 - fuerza * k / max(1, muestras - 1)
        iy = _escala_idx(h, centro[1] * h, s); ix = _escala_idx(w, centro[0] * w, s)
        acc += img[np.ix_(iy, ix)]
    acc /= muestras
    return img * (1 - peso) + acc * peso


def lineas_velocidad(img, t, fuerza=1.0, n=46, color=(1, 1, 1), semilla=5, hueco=0.38):
    """Líneas radiales de manga/anime que parten del centro; parpadean con t."""
    if fuerza < 0.01: return img
    h, w = img.shape[:2]
    dx, dy, r, ang = _polar(h, w)
    rng = np.random.default_rng(semilla + int(t * 24))
    ang_c = rng.uniform(-math.pi, math.pi, n)
    anch = rng.uniform(0.006, 0.03, n)
    ini = rng.uniform(hueco, hueco + 0.5, n)
    m = np.zeros(r.shape, np.float32)
    for a, wd, i0 in zip(ang_c, anch, ini):
        d = np.abs(((ang - a + math.pi) % (2 * math.pi)) - math.pi)
        m = np.maximum(m, np.clip(1 - d / (wd / np.maximum(r, 0.2)), 0, 1) * np.clip((r - i0) / 0.25, 0, 1))
    m = (m * fuerza * 0.85)[..., None]
    return img * (1 - m) + np.array(color, np.float32) * m


def gradacion(img, contraste=1.08, saturacion=1.12, tinte=(1.0, 1.0, 1.0), gamma=1.0, exposicion=1.0):
    x = img * exposicion
    lum = (x * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    x = lum + (x - lum) * saturacion
    x = (x - 0.5) * contraste + 0.5
    x = x * np.asarray(tinte, np.float32)
    return np.clip(x, 0, None) ** (1.0 / gamma)


def grano(img, fuerza=0.025, semilla=0):
    rng = np.random.default_rng(semilla)
    g = rng.normal(0, fuerza, img.shape[:2]).astype(np.float32)[..., None]
    return img + g


def destello(img, a, color=(1, 1, 1)):
    if a <= 0: return img
    return img * (1 - min(a, 1)) + np.array(color, np.float32) * min(a, 1)


def barras(img, alto):
    """Bandas negras superior e inferior (alto en fracción de la altura)."""
    h = img.shape[0]; n = int(h * alto)
    if n <= 0: return img
    img = img.copy(); img[:n] = 0; img[-n:] = 0
    return img


def iris(img, p, centro=(0.5, 0.5), color=(0, 0, 0)):
    """Cierre en círculo: p=0 abierto, 1 cerrado."""
    if p <= 0: return img
    h, w = img.shape[:2]
    dx, dy, r, _ = _polar(h, w)
    cx = (centro[0] - 0.5) * w / (h / 2); cy = (centro[1] - 0.5) * 1.0
    rr = np.hypot(dx - cx, dy - cy * 2)
    radio = (1 - p) * 2.2
    m = np.clip((rr - radio) * 12, 0, 1)[..., None]
    return img * (1 - m) + np.array(color, np.float32) * m


def cortina(img, p, angulo=20, color=(1, 1, 1)):
    """Barrido diagonal."""
    if p <= 0: return img
    h, w = img.shape[:2]
    dx, dy, _, _ = _polar(h, w)
    a = math.radians(angulo)
    d = dx * math.cos(a) + dy * math.sin(a)
    lim = -1.3 + p * 2.6
    m = np.clip((lim - d) * 10, 0, 1)[..., None]
    return img * (1 - m) + np.array(color, np.float32) * m


def a_uint8(img, semilla=0):
    rng = np.random.default_rng(semilla)
    x = np.clip(img, 0, 1) * 255 + rng.random(img.shape[:2], dtype=np.float32)[..., None] - 0.5      # tramado leve
    return np.clip(x, 0, 255).astype(np.uint8)
