"""Carga de recursos extraídos del ROM (biblioteca/pokemon-platino/extraidos/) con caché."""
import os
import sys
import json
import glob
from functools import lru_cache

import numpy as np
from PIL import Image

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))


def _repo():
    d = RAIZ
    while not os.path.isfile(os.path.join(d, 'valedores.toml')):
        d = os.path.dirname(d)
    return d


sys.path.insert(0, os.path.join(_repo(), 'nucleo'))
from valedores import rutas  # noqa: E402

JUEGO = 'pokemon-platino'
SPR = rutas.extraidos(JUEGO)           # sprites sacados de la ROM (regenerables)
CUSTOM = rutas.personalizados(JUEGO)   # personajes propios
CACHE = rutas.cache(JUEGO)             # mapas renderizados y audio en caché
TRABAJO = rutas.trabajo(JUEGO)         # hojas de revisión, audio de trabajo
SALIDA = rutas.salida(JUEGO)           # vídeos y gifs finales


@lru_cache(maxsize=None)
def imagen(ruta):
    """Carga un PNG (ruta relativa a biblioteca/pokemon-platino/extraidos/) como RGBA."""
    p = ruta if os.path.isabs(ruta) else os.path.join(SPR, ruta)
    return Image.open(p).convert('RGBA')


def recolorear_cian(img, oscuro=(64, 152, 72), claro=(168, 224, 128)):
    """Los tiles de césped vienen en tonos cian (el juego los tiñe con la luz 3D).
    Convierte los píxeles cian/verdosos en una rampa de verdes naturales según su luminosidad."""
    a = np.array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (g > r + 30) & (b > r) & (a[..., 3] > 0)
    lum = (0.3 * r + 0.59 * g + 0.11 * b) / 255.0
    lo, hi = lum[mask].min() if mask.any() else 0, lum[mask].max() if mask.any() else 1
    t = np.clip((lum - lo) / max(hi - lo, 1e-3), 0, 1)
    for c in range(3):
        a[..., c] = np.where(mask, oscuro[c] + (claro[c] - oscuro[c]) * t, a[..., c])
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')


# ------------------------------------------------------------------ personajes del mapa

DIRS = {'arriba': 0, 'abajo': 1, 'izquierda': 2, 'derecha': 3}


@lru_cache(maxsize=None)
def carpeta_personaje(nombre):
    """Acepta el nombre de la carpeta completo ('090_pl_boy01c_heroe_andar_correr'),
    su número ('090') o un fragmento ('babyboy1', 'heroe_andar').
    Los personajes propios están en biblioteca/pokemon-platino/personalizados/<nombre>/mapa/ (p. ej. 'el_pana')."""
    propio = os.path.join(CUSTOM, nombre, 'mapa')
    if os.path.isdir(propio):
        return propio
    base = os.path.join(SPR, 'personajes_mapa')
    exacto = os.path.join(base, nombre)
    if os.path.isdir(exacto):
        return exacto
    cands = sorted(glob.glob(os.path.join(base, '*')))
    for c in cands:
        n = os.path.basename(c)
        if n.startswith(nombre + '_') or n.split('_', 1)[0] == nombre:
            return c
    for c in cands:
        if nombre in os.path.basename(c):
            return c
    raise FileNotFoundError('No hay personaje que coincida con %r en personajes_mapa/' % nombre)


@lru_cache(maxsize=None)
def frames_personaje(nombre):
    d = carpeta_personaje(nombre)
    fs = sorted(glob.glob(os.path.join(d, 'frame_*.png')))
    return [imagen(f) for f in fs]


# ------------------------------------------------------------------ fuente del juego

class Fuente:
    def __init__(self):
        with open(os.path.join(SPR, 'interfaz', 'fuente', 'fuente_juego.json'), encoding='utf-8') as f:
            meta = json.load(f)
        self.cols = meta['columnas_atlas']
        self.chars = meta['caracteres']
        self.atlas = imagen('interfaz/fuente/fuente_juego.png')
        self.cache = {}

    def glifo(self, ch):
        info = self.chars.get(ch) or self.chars.get(' ')
        i = info['glifo']
        if i not in self.cache:
            x, y = (i % self.cols) * 16, (i // self.cols) * 16
            self.cache[i] = self.atlas.crop((x, y, x + 16, y + 16))
        return self.cache[i], info['ancho']

    def ancho(self, texto):
        return sum(self.glifo(c)[1] for c in texto)

    def dibujar(self, lienzo, texto, x, y, color=None, sombra=None):
        """Dibuja una línea. color/sombra opcionales (RGB) recolorean el texto."""
        for ch in texto:
            g, w = self.glifo(ch)
            if color or sombra:
                g = _recolor_glifo(g, color, sombra)
            lienzo.alpha_composite(g, (int(x), int(y)))
            x += w
        return x


def _recolor_glifo(g, color, sombra):
    a = np.array(g)
    t = (a[..., 0] == 80) & (a[..., 3] > 0)
    s = (a[..., 0] == 168) & (a[..., 3] > 0)
    if color:
        a[t, :3] = color
    if sombra:
        a[s, :3] = sombra
    return Image.fromarray(a, 'RGBA')


@lru_cache(maxsize=None)
def fuente():
    return Fuente()


# ------------------------------------------------------------------ ventana de mensaje

def ventana_mensaje(ancho, alto, tipo=1):
    """Construye la ventana de diálogo con el marco 'tipo_XX' del juego (9-slice).
    El marco original son 6x3 tiles: columnas 0-1 = lado izq., 2 = interior, 3-5 = lado dcho."""
    src = imagen('interfaz/marcos_mensaje/tipo_%02d.png' % tipo)
    L, M, R = src.crop((0, 0, 16, 24)), src.crop((16, 0, 24, 24)), src.crop((24, 0, 48, 24))
    out = Image.new('RGBA', (ancho, alto))

    def columna(img, x):
        w = img.width
        top, mid, bot = img.crop((0, 0, w, 8)), img.crop((0, 8, w, 16)), img.crop((0, 16, w, 24))
        out.alpha_composite(top, (x, 0))
        for y in range(8, alto - 8, 8):
            out.alpha_composite(mid, (x, y))
        out.alpha_composite(bot, (x, alto - 8))

    columna(L, 0)
    for x in range(16, ancho - 24, 8):
        columna(M, x)
    columna(R, ancho - 24)
    return out


@lru_cache(maxsize=None)
def frames_flecha():
    src = imagen('interfaz/marcos_mensaje/flechas.png')
    return [src.crop((k * 16, 0, k * 16 + 16, 8)) for k in range(src.width // 16)]
