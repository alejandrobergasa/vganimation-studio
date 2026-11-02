"""Transiciones entre planos y postproceso del fotograma, comunes a todos los motores DS.

Transición: `plano.transicion = ('estrella', 0.6)` entre el plano anterior y ese; queda centrada en el corte.
Efecto: `plano.efecto(destello(1.2, 0.3))`: función (imagen, t) -> imagen, con t relativo al plano.
"""
import math

import numpy as np
from PIL import Image


def _mascara(tipo, W, H, u):
    """Máscara 0..1 (1 = se ve el plano nuevo) de una transición con forma, en el progreso u."""
    y, x = np.mgrid[0:H, 0:W].astype(np.float32)
    nx, ny = (x - W / 2) / (H / 2), (y - H / 2) / (H / 2)
    radio = math.hypot(W, H) / H * 1.02
    if tipo == 'iris':
        return (np.hypot(nx, ny) < u * radio).astype(np.float32)
    if tipo == 'estrella':
        # Radio en polares de una estrella de cinco puntas: el cierre clásico de Mario.
        ang = np.arctan2(nx, -ny)
        k = np.abs(((ang * 5 / (2 * np.pi)) % 1) - 0.5) * 2
        forma = 0.52 + 0.48 * k ** 1.25
        return (np.hypot(nx, ny) < u * radio * 1.9 * forma).astype(np.float32)
    if tipo == 'barrido':
        return (x < u * W).astype(np.float32)
    if tipo == 'barrido_inverso':
        return (x > (1 - u) * W).astype(np.float32)
    if tipo == 'cortina':
        return (np.abs(x - W / 2) < u * W / 2).astype(np.float32)
    if tipo == 'persiana':
        return (((y / max(H / 12, 1)) % 1) < u).astype(np.float32)
    if tipo == 'diagonal':
        return ((x + y) / (W + H) < u).astype(np.float32)
    raise ValueError('Transición desconocida: ' + tipo)


TRANSICIONES = ('fundido', 'negro', 'blanco', 'pixelado', 'iris', 'estrella', 'barrido', 'barrido_inverso',
                'cortina', 'persiana', 'diagonal')


def transicion(tipo, a, b, u):
    """Mezcla el fotograma `a` (saliente) con `b` (entrante); u va de 0 a 1."""
    u = max(0.0, min(1.0, u))
    A, B = np.asarray(a.convert('RGB'), np.float32), np.asarray(b.convert('RGB'), np.float32)
    if tipo == 'fundido':
        return Image.fromarray((A + (B - A) * u).astype(np.uint8))
    if tipo in ('negro', 'blanco'):
        col = 0.0 if tipo == 'negro' else 255.0
        origen, k = (A, u * 2) if u < 0.5 else (B, (1 - u) * 2)
        return Image.fromarray((origen + (col - origen) * k).astype(np.uint8))
    if tipo == 'pixelado':
        im = a if u < 0.5 else b
        k = 1 - abs(u - 0.5) * 2
        lado = max(1, round(k * 48))
        peq = im.convert('RGB').resize((max(1, im.width // lado), max(1, im.height // lado)), Image.Resampling.BILINEAR)
        return peq.resize(im.size, Image.Resampling.NEAREST)
    if tipo in ('iris', 'estrella'):
        # Se cierra sobre negro y se abre con el plano nuevo.
        H, W = A.shape[:2]
        if u < 0.5:
            m = _mascara(tipo, W, H, 1 - u * 2)
            return Image.fromarray((A * m[..., None]).astype(np.uint8))
        m = _mascara(tipo, W, H, (u - 0.5) * 2)
        return Image.fromarray((B * m[..., None]).astype(np.uint8))
    H, W = A.shape[:2]
    m = _mascara(tipo, W, H, u)[..., None]
    return Image.fromarray((A * (1 - m) + B * m).astype(np.uint8))


def _pulso(t, desde, duracion):
    return max(0.0, 1 - (t - desde) / duracion) if desde <= t < desde + duracion else 0.0


def destello(desde, duracion=0.25, color=(255, 255, 255), fuerza=1.0):
    """Fogonazo que cae en `duracion` segundos."""
    col = np.array(color, np.float32)

    def f(im, t):
        k = _pulso(t, desde, duracion) * fuerza
        if not k:
            return im
        A = np.asarray(im, np.float32)
        return Image.fromarray((A + (col - A) * k).astype(np.uint8))
    return f


def fundido(desde, duracion, hacia=(0, 0, 0), entrada=False):
    """Fundido a color (o desde color con `entrada=True`)."""
    col = np.array(hacia, np.float32)

    def f(im, t):
        u = max(0.0, min(1.0, (t - desde) / duracion))
        k = 1 - u if entrada else u
        if k <= 0:
            return im
        A = np.asarray(im, np.float32)
        return Image.fromarray((A + (col - A) * k).astype(np.uint8))
    return f


def vineta(fuerza=0.55):
    """Oscurece las esquinas; concentra la atención en el centro del cuadro."""
    memo = {}

    def f(im, t):
        if im.size not in memo:
            H, W = im.height, im.width
            y, x = np.mgrid[0:H, 0:W].astype(np.float32)
            d = np.hypot((x - W / 2) / (W / 2), (y - H / 2) / (H / 2)) / math.sqrt(2)
            memo[im.size] = (1 - fuerza * np.clip(d * 1.25 - 0.35, 0, 1) ** 2)[..., None]
        return Image.fromarray((np.asarray(im, np.float32) * memo[im.size]).astype(np.uint8))
    return f


def tinte(color, fuerza=0.35, desde=0, hasta=math.inf):
    """Baño de color en un intervalo: rojo de tensión, azul de noche, sepia de recuerdo."""
    col = np.array(color, np.float32)

    def f(im, t):
        if not desde <= t < hasta:
            return im
        A = np.asarray(im, np.float32)
        return Image.fromarray((A + (A / 255.0 * col - A) * fuerza).astype(np.uint8))
    return f


def desaturar(fuerza=1.0, desde=0, hasta=math.inf):
    """Blanco y negro total o parcial en un intervalo."""
    def f(im, t):
        if not desde <= t < hasta:
            return im
        A = np.asarray(im, np.float32)
        g = (A @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        return Image.fromarray((A + (g - A) * fuerza).astype(np.uint8))
    return f


def franjas_cine(alto=0.11, desde=0, hasta=math.inf, entrada=0.3):
    """Bandas negras que entran y salen del cuadro para un momento dramático."""
    def f(im, t):
        if not desde <= t < hasta:
            return im
        k = min(1.0, (t - desde) / entrada, (hasta - t) / entrada) if math.isfinite(hasta) else min(1.0, (t - desde) / entrada)
        h = round(im.height * alto * k)
        if h <= 0:
            return im
        A = np.asarray(im).copy()
        A[:h] = 0
        A[-h:] = 0
        return Image.fromarray(A)
    return f


def lineas_velocidad(desde, duracion, cantidad=44, color=(255, 255, 255), semilla=3):
    """Líneas radiales de manga: impacto, sorpresa, carrera."""
    def f(im, t):
        if not desde <= t < desde + duracion:
            return im
        from PIL import ImageDraw
        capa = im.convert('RGBA')
        dib = ImageDraw.Draw(capa)
        W, H = im.size
        r = np.random.default_rng(semilla + int(t * 15))
        R = math.hypot(W, H) / 2
        for ang in r.uniform(0, 2 * math.pi, cantidad):
            ini = R * r.uniform(0.58, 0.86)
            ancho = r.uniform(0.004, 0.012)
            cx, cy = W / 2, H / 2
            pts = [(cx + math.cos(ang - ancho) * R * 1.1, cy + math.sin(ang - ancho) * R * 1.1),
                   (cx + math.cos(ang + ancho) * R * 1.1, cy + math.sin(ang + ancho) * R * 1.1),
                   (cx + math.cos(ang) * ini, cy + math.sin(ang) * ini)]
            dib.polygon(pts, fill=(*color, 255))
        return capa.convert('RGB')
    return f


def temblor_2d(desde, duracion, intensidad=12, frecuencia=30):
    """Sacude el fotograma entero (para planos sin cámara 3D o para reforzar la de la escena)."""
    def f(im, t):
        k = _pulso(t, desde, duracion)
        if not k:
            return im
        dx = round(math.sin(t * frecuencia * 2.1) * intensidad * k)
        dy = round(math.cos(t * frecuencia * 1.7) * intensidad * k)
        salida = Image.new('RGB', im.size)
        salida.paste(im, (dx, dy))
        return salida
    return f
