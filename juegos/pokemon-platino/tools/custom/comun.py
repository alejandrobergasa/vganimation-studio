"""Utilidades compartidas para crear personajes custom en estilo Platino (ver tools/custom/el_pana.py).

Técnica: partir de sprites del juego parecidos y recolorear POR ZONAS (cabeza / torso / piernas), porque
el juego reutiliza los mismos colores de la paleta en pelo, ropa y botas. Después se pintan a mano los
rasgos (gafas, barba...) con coordenadas fijas.
"""
import glob
import sys
import json
import os

import numpy as np
from PIL import Image, ImageDraw

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
from valrutas import SPR, CUSTOM  # noqa: E402
DIRS = ['arriba'] * 4 + ['abajo'] * 4 + ['izquierda'] * 4 + ['derecha'] * 4
FONDO = (200, 210, 235, 255)


# ====================================================================== cargar bases

def carpeta_mapa(base):
    """Carpeta de un personaje del mapa por número ('027') o fragmento ('assistantm'). También vale el
    nombre exacto de un personaje custom ('el_pana')."""
    propio = os.path.join(CUSTOM, base, 'mapa')
    if os.path.isdir(propio):
        return propio
    cands = sorted(glob.glob(os.path.join(SPR, 'personajes_mapa', '*')))
    for c in cands:
        n = os.path.basename(c)
        if n.split('_', 1)[0] == base or n == base:
            return c
    for c in cands:
        if base in os.path.basename(c):
            return c
    raise FileNotFoundError(base)


def frames_mapa(base):
    """Los 16 frames (32x32 RGBA, como arrays numpy) de un personaje del mapa del juego."""
    d = carpeta_mapa(base)
    return [np.array(Image.open(os.path.join(d, 'frame_%02d.png' % i)).convert('RGBA')) for i in range(16)]


def frente_base(nombre):
    """Sprite frontal de entrenador (80x80) por número ('024') o fragmento del nombre."""
    for f in sorted(glob.glob(os.path.join(SPR, 'entrenadores', 'frente', 'estatico', '*.png'))):
        n = os.path.basename(f)
        if n.split('_', 1)[0] == nombre or nombre in n:
            return np.array(Image.open(f).convert('RGBA'))[:, :80].copy()
    raise FileNotFoundError(nombre)


def espalda_base(nombre):
    """Sprite de espalda (tira de 160x80 con 2 poses; la 2.ª desplazada) por número o fragmento."""
    for f in sorted(glob.glob(os.path.join(SPR, 'entrenadores', 'espalda', 'estatico', '*.png'))):
        n = os.path.basename(f)
        if n.split('_', 1)[0] == nombre or nombre in n:
            return np.array(Image.open(f).convert('RGBA'))
    raise FileNotFoundError(nombre)


# ====================================================================== retocar

def recolorear(px, tabla, y0=0, y1=None, x0=0, x1=None):
    """Cambia colores exactos {(r,g,b): (r,g,b)} dentro de la caja. Se compara con el original, así que
    las cadenas (A->B y B->C) no se pisan."""
    sub = px[y0:y1, x0:x1]
    orig = sub.copy()
    for a, b in tabla.items():
        m = (orig[..., 0] == a[0]) & (orig[..., 1] == a[1]) & (orig[..., 2] == a[2]) & (orig[..., 3] > 0)
        sub[m, :3] = b
    return px


def pon(px, pts, color):
    """Pinta píxeles (x, y) que ya sean opacos (no añade silueta)."""
    for x, y in pts:
        if 0 <= y < px.shape[0] and 0 <= x < px.shape[1] and px[y, x, 3]:
            px[y, x, :3] = color
    return px


def pon_opaco(px, pts, color):
    """Pinta píxeles (x, y) aunque sean transparentes (para añadir pelo, coleta, gorra...)."""
    for x, y in pts:
        if 0 <= y < px.shape[0] and 0 <= x < px.shape[1]:
            px[y, x] = (*color, 255)
    return px


def colores(px, y0=0, y1=None, x0=0, x1=None):
    """[(color, n)] de los píxeles opacos de la caja, de más a menos frecuente."""
    sub = px[y0:y1, x0:x1]
    m = sub[..., 3] > 0
    c, n = np.unique(sub[m][:, :3], axis=0, return_counts=True)
    return sorted(((tuple(int(v) for v in k), int(q)) for k, q in zip(c, n)), key=lambda t: -t[1])


def es_borde(px, x, y, vecinos=((-1, 0), (1, 0), (0, 1))):
    """True si algún vecino es transparente o negro (para oscurecer el contorno de lo que se pinta)."""
    for dx, dy in vecinos:
        X, Y = x + dx, y + dy
        if not (0 <= Y < px.shape[0] and 0 <= X < px.shape[1]):
            return True
        if px[Y, X, 3] == 0 or tuple(px[Y, X, :3]) == (0, 0, 0):
            return True
    return False


# ====================================================================== guardar

def _img(px):
    return px if isinstance(px, Image.Image) else Image.fromarray(px)


def guardar_mapa(nombre, frames, base, titulo=None):
    """sprites_custom/<nombre>/mapa/frame_00..15.png + _tira.png + info.json (lo que usa el motor)."""
    dst = os.path.join(CUSTOM, nombre, 'mapa')
    os.makedirs(dst, exist_ok=True)
    frames = [_img(f) for f in frames]
    for i, f in enumerate(frames):
        f.save(os.path.join(dst, 'frame_%02d.png' % i))
    tira = Image.new('RGBA', (32 * 16, 32))
    for i, f in enumerate(frames):
        tira.alpha_composite(f, (32 * i, 0))
    tira.save(os.path.join(dst, '_tira.png'))
    json.dump({'nombre': titulo or nombre.upper().replace('_', ' '), 'tam_frame': [32, 32], 'base': base,
               'frames': '0-3 arriba, 4-7 abajo, 8-11 izquierda, 12-15 derecha [quieto, paso, quieto, paso]'},
              open(os.path.join(dst, 'info.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return frames


def guardar_combate(nombre, frente=None, espalda=None):
    """combate/frente.png (80x80), espalda_tira.png, espalda_0.png y espalda_1_lanzar.png."""
    dst = os.path.join(CUSTOM, nombre, 'combate')
    os.makedirs(dst, exist_ok=True)
    if frente is not None:
        _img(frente).save(os.path.join(dst, 'frente.png'))
    if espalda is not None:
        e = _img(espalda)
        e.save(os.path.join(dst, 'espalda_tira.png'))
        e.crop((0, 0, 80, 80)).save(os.path.join(dst, 'espalda_0.png'))
        e.crop((80, 0, 160, 80)).save(os.path.join(dst, 'espalda_1_lanzar.png'))


def vista(nombre):
    """sprites_custom/<nombre>/_vista.png: los 16 frames del mapa x2 y los de combate x3. Es la imagen que
    se enseña al usuario y la referencia de la skill de cinemáticas."""
    d = os.path.join(CUSTOM, nombre)
    hoja = Image.new('RGBA', (1024, 324), FONDO)
    for i in range(16):
        f = os.path.join(d, 'mapa', 'frame_%02d.png' % i)
        if os.path.exists(f):
            hoja.alpha_composite(Image.open(f).convert('RGBA').resize((64, 64), Image.NEAREST), (i * 64, 0))
    x = 96
    for n in ('frente.png', 'espalda_0.png', 'espalda_1_lanzar.png'):
        f = os.path.join(d, 'combate', n)
        if os.path.exists(f):
            hoja.alpha_composite(Image.open(f).convert('RGBA').resize((240, 240), Image.NEAREST), (x, 80))
            x += 300
    ruta = os.path.join(d, '_vista.png')
    hoja.save(ruta)
    return ruta


def revision(nombre, base=None, escala=6):
    """sprites_custom/<nombre>/_revision.png: cada frame del mapa ampliado con rejilla, la base del juego
    al lado (si se da) y el número de colores. Para revisar píxel a píxel antes de enseñarlo."""
    d = os.path.join(CUSTOM, nombre, 'mapa')
    nuevos = [Image.open(os.path.join(d, 'frame_%02d.png' % i)).convert('RGBA') for i in range(16)]
    viejos = [Image.fromarray(f) for f in frames_mapa(base)] if base else [None] * 16
    t = 32 * escala
    filas = 2 if base else 1
    hoja = Image.new('RGBA', (8 * (t + 6), 2 * filas * (t + 18)), (255, 255, 255, 255))
    dr = ImageDraw.Draw(hoja)
    for i in range(16):
        for k, im in enumerate((nuevos[i], viejos[i])[:filas]):
            x = (i % 8) * (t + 6)
            y = ((i // 8) * filas + k) * (t + 18)
            fondo = Image.new('RGBA', (32, 32), FONDO)
            fondo.alpha_composite(im)
            hoja.paste(fondo.resize((t, t), Image.NEAREST), (x, y + 14))
            for g in range(0, 33, 4):
                c = (150, 150, 170, 255) if g % 8 else (90, 90, 120, 255)
                dr.line([(x + g * escala, y + 14), (x + g * escala, y + 14 + t)], fill=c)
                dr.line([(x, y + 14 + g * escala), (x + t, y + 14 + g * escala)], fill=c)
            ncol = len(colores(np.array(im)))
            dr.text((x + 2, y + 1), '%s %d %s  %d col' % ('nuevo' if k == 0 else 'base', i, DIRS[i], ncol),
                    fill=(200, 0, 0) if ncol > 15 else (0, 0, 0))
    ruta = os.path.join(CUSTOM, nombre, '_revision.png')
    hoja.save(ruta)
    return ruta
