"""Gráficos propios de ECLIPSE (el juego no trae eclipses, ni buscadores, ni camisetas): se dibujan en código
con la paleta y el contorno de Platino. Vista previa: python escenas/eclipse_gfx.py"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, 'rewindlimbo2'))
import comun  # noqa
from comun import escalar, texto_img, inserto  # noqa
from motor.recursos import RAIZ, SPR, CUSTOM, TRABAJO, SALIDA, CACHE, fuente, imagen, ventana_mensaje  # noqa

N = (24, 24, 32, 255)


def cielo_eclipse(fase):
    """Pantalla completa (256x192) del cielo. fase 0: sol normal; 1: media luna de sol; 2: anillo total."""
    w, h = 256, 192
    y, x = np.mgrid[0:h, 0:w].astype(float)
    cx, cy = 128, 92
    d = np.hypot(x - cx, y - cy)
    if fase == 0:
        c0, c1 = np.array([88, 150, 208]), np.array([200, 224, 248])
    elif fase == 1:
        c0, c1 = np.array([40, 84, 128]), np.array([136, 168, 192])
    else:
        c0, c1 = np.array([8, 16, 40]), np.array([24, 40, 72])
    t = np.clip(1 - d / 150, 0, 1)[..., None]
    img = (c0 * (1 - t) + c1 * t)
    # nubes pixeladas
    out = Image.fromarray(img.astype(np.uint8)).convert('RGBA')
    dr = ImageDraw.Draw(out)
    nube = (230, 240, 250, 255) if fase < 2 else (40, 56, 88, 255)
    for nx, ny in ((30, 150), (190, 40), (210, 160)):
        for i, (dx, dy, r) in enumerate(((0, 0, 9), (10, -3, 11), (22, 1, 8), (11, 4, 9))):
            dr.ellipse((nx + dx - r, ny + dy - r // 2, nx + dx + r, ny + dy + r // 2), fill=nube)
    # sol y luna
    R = 26
    if fase == 0:
        dr.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(255, 252, 214, 255), outline=(255, 255, 255, 255), width=2)
    elif fase == 1:
        sol = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sol)
        sd.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(255, 248, 200, 255))
        sd.ellipse((cx - R + 14, cy - R - 4, cx + R + 14, cy + R - 4), fill=(0, 0, 0, 0))   # la luna lo tapa
        out.alpha_composite(sol)
        dr = ImageDraw.Draw(out)
    else:
        for r, a in ((R + 12, 40), (R + 8, 80), (R + 4, 140)):
            glow = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 220, 140, a))
            out.alpha_composite(glow)
        dr = ImageDraw.Draw(out)
        dr.ellipse((cx - R, cy - R, cx + R, cy + R), fill=(255, 236, 170, 255))
        dr.ellipse((cx - R + 3, cy - R + 3, cx + R - 3, cy + R - 3), fill=(6, 8, 16, 255))
        for ang in (-35,):   # el «diamante»
            px, py = cx + (R) * math.cos(math.radians(ang)), cy + R * math.sin(math.radians(ang))
            dr.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(255, 255, 240, 255))
    # franjas negras de cine arriba y abajo, como en el juego cuando hay cinemática
    dr.rectangle((0, 0, w, 15), fill=(0, 0, 0, 255))
    dr.rectangle((0, h - 16, w, h), fill=(0, 0, 0, 255))
    return out


def tumbado(frame, losa=True):
    """El sprite de frente (32x32) girado 90 grados y tumbado sobre una losa de piedra. Mide 48x32."""
    s = frame.rotate(-90, expand=True)         # cabeza a la derecha
    w, h = 48, 32
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    if losa:
        d = ImageDraw.Draw(im)
        d.rectangle((0, 17, 47, 31), fill=(120, 116, 128, 255), outline=N)
        d.rectangle((1, 18, 46, 21), fill=(168, 164, 176, 255))
        d.rectangle((1, 28, 46, 30), fill=(84, 80, 96, 255))
        for x in (10, 22, 34):
            d.line((x, 23, x + 4, 23), fill=(96, 92, 108, 255))
    im.alpha_composite(s, (8, 4 if losa else 8))
    return im


def cuchillo():
    """Daga de obsidiana vista de frente (5x12)."""
    im = Image.new('RGBA', (5, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(2, 0), (4, 6), (0, 6)], fill=(80, 84, 104, 255), outline=N)
    d.line((2, 1, 2, 5), fill=(190, 200, 224, 255))
    d.rectangle((0, 6, 4, 7), fill=(200, 160, 40, 255))
    d.rectangle((1, 8, 3, 11), fill=(120, 60, 40, 255), outline=N)
    return im


def corazon(k=1, color=(224, 40, 56, 255)):
    pat = ['.XX..XX.', 'XXXXXXXX', 'XXXXXXXX', 'XXXXXXXX', '.XXXXXX.', '..XXXX..', '...XX...']
    im = Image.new('RGBA', (8, 7), (0, 0, 0, 0))
    for y, row in enumerate(pat):
        for x, c in enumerate(row):
            if c == 'X':
                im.putpixel((x, y), color)
    im.putpixel((1, 1), (255, 200, 210, 255))
    return escalar(contorno(im), k)


def contorno(im):
    a = np.array(im.getchannel('A')) > 0
    big = Image.new('RGBA', (im.width + 2, im.height + 2), (0, 0, 0, 0))
    ab = np.pad(a, 1)
    borde = np.zeros_like(ab)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        borde |= np.roll(np.roll(ab, dy, 0), dx, 1)
    borde &= ~ab
    for y, x in zip(*np.nonzero(borde)):
        big.putpixel((int(x), int(y)), N)
    big.alpha_composite(im, (1, 1))
    return big


def _texto(im, txt, x, y, color=(40, 40, 48), sombra=None):
    fuente().dibujar(im, txt, x, y, color, sombra)


def google():
    """Pantalla de buscador (240x128) con «lunar» tecleado y un resultado con foto."""
    w, h = 240, 128
    im = Image.new('RGBA', (w, h), (250, 250, 250, 255))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, w - 1, 13), fill=(214, 220, 232, 255))
    d.rectangle((22, 3, w - 22, 11), fill=(255, 255, 255, 255), outline=(130, 140, 160, 255))
    _texto(im, 'www.buscador.es', 25, 2, (90, 100, 120))
    # logo
    x = 8
    for ch, col in zip('BUSCA', ((60, 100, 220), (220, 60, 50), (240, 180, 20), (60, 100, 220), (40, 160, 70))):
        _texto(im, ch, x, 17, col, (200, 200, 200))
        x += 10
    d.rectangle((70, 19, 190, 31), fill=(255, 255, 255, 255), outline=(150, 156, 170, 255))
    _texto(im, 'lunar', 74, 17, (20, 20, 30))
    d.line((111, 21, 111, 29), fill=(20, 20, 30, 255))
    d.line((8, 36, w - 8, 36), fill=(200, 204, 214, 255))
    # resultado con foto
    _texto(im, 'Lunar - Wikipedia', 8, 40, (30, 60, 200))
    _texto(im, 'Mancha oscura de la piel', 8, 54, (60, 60, 70))
    _texto(im, 'que sale en la cara.', 8, 66, (60, 60, 70))
    _texto(im, 'No confundir con la Luna.', 8, 78, (60, 60, 70))
    d.rectangle((164, 40, 232, 100), fill=(236, 190, 160, 255), outline=(120, 120, 130, 255))
    d.ellipse((190, 62, 196, 68), fill=(70, 36, 24, 255))
    d.line((178, 52, 186, 60), fill=(220, 30, 30, 255), width=2)
    d.polygon([(186, 60), (181, 59), (185, 55)], fill=(220, 30, 30, 255))
    _texto(im, 'Lunar - Eclipses', 8, 96, (30, 60, 200))
    _texto(im, 'lunares y solares.', 8, 108, (60, 60, 70))
    return escalar_marco(im)


def escalar_marco(im, tipo=1):
    """Pega la imagen dentro de una ventana del juego."""
    w, h = (im.width + 16 + 7) // 8 * 8, (im.height + 16 + 7) // 8 * 8
    v = ventana_mensaje(w, h, tipo)
    v.alpha_composite(im, ((w - im.width) // 2, (h - im.height) // 2))
    return v


def zoom_cara(frente, lunar=False):
    """Primer plano (x4) de la cabeza del sprite de combate con una flecha roja a la mejilla (sin lunar)."""
    bb = frente.getbbox()
    cab = frente.crop((bb[0], bb[1], bb[2], bb[1] + 24))
    im = escalar(cab, 4)
    d = ImageDraw.Draw(im)
    px, py = 4 * 22, 4 * 15                    # la mejilla
    d.line((px + 44, py - 36, px + 10, py - 8), fill=(200, 24, 24, 255), width=3)
    d.polygon([(px + 2, py - 2), (px + 16, py - 4), (px + 8, py - 16)], fill=(200, 24, 24, 255))
    if lunar:
        d.ellipse((px - 4, py - 4, px + 4, py + 4), fill=(70, 36, 24, 255))
    return im


def camiseta(texto='EL LUNAR'):
    """Tarjeta «I ♥ EL LUNAR» (256x192, fondo blanco como las camisetas del vídeo original)."""
    im = Image.new('RGBA', (256, 192), (255, 255, 255, 255))
    i = texto_img('I', (24, 24, 32), None, 4)
    im.alpha_composite(i, (92, 52))
    im.alpha_composite(corazon(5), (118, 48))
    t = texto_img(texto, (24, 24, 32), None, 2)
    im.alpha_composite(t, ((256 - t.width) // 2, 112))
    return im


if __name__ == '__main__':
    hoja = Image.new('RGBA', (256 * 3 + 20, 192 * 2 + 10), (60, 60, 60, 255))
    for i in range(3):
        hoja.alpha_composite(cielo_eclipse(i), (i * 266, 0))
    hoja.alpha_composite(camiseta(), (0, 202))
    hoja.alpha_composite(google(), (266, 202))
    sp = imagen(os.path.join(CUSTOM, 'chini', 'mapa', 'frame_04.png'))
    hoja.alpha_composite(escalar(tumbado(sp), 2), (532, 202))
    hoja.save(os.path.join(TRABAJO, '_eclipse_gfx.png'))
    print('ok')
