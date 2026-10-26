"""Mapas reales de Sinnoh renderizados desde el ROM (terreno 3D + edificios) como fondo de escena.

El juego no dibuja los mapas con tiles 2D: cada trozo de 32x32 tiles es un modelo 3D con sus
texturas (árboles por capas, orillas del agua, vallas...). Aquí se renderiza ese modelo con la
misma proyección cenital del juego y se guarda, por píxel, la z del mundo para que los árboles y
edificios que están delante tapen a los personajes.

Coordenadas: tiles de 16x16 contados desde la esquina superior izquierda de la zona. La pantalla
usa el plano proyectado: y_pantalla = z - altura_del_suelo * K.
"""
import glob
import os
import sys

import numpy as np
from PIL import Image

from .recursos import RAIZ, JUEGO, rutas
from .recursos import CACHE

TILE = 16

# Zonas comprobadas: (fila, columna, filas, columnas) en la matriz del mapa de Sinnoh.
# Para ver una zona con su rejilla de tiles: python herramientas.py mapa <zona>
ZONAS = {
    'aromaflor': (19, 5, 2, 1),       # Pueblo Aromaflor: prado de flores arriba, pueblo abajo
    'hojaverde': (26, 3, 2, 1),       # Pueblo Hojaverde y el bosque de la ruta 201
    'ruta_204_sur': (21, 5, 2, 1),    # Ruta 204: hierba alta, estanques con valla, caminos de grava
    'jubileo': (23, 4, 2, 2),         # Ciudad Jubileo: avenidas asfaltadas, aceras, farolas, edificios
}

# Interiores (casas, guaridas...): no están en la matriz de Sinnoh, son un solo trozo de land_data.
# MapaReal(land=<id>). Para ver candidatos, renderiza varios ids (ver CONOCIMIENTO.md).
INTERIORES = {
    'celda': 289,                     # sala oscura con valla de postes en U: sirve de celda/jaula
}


def _rom():
    return rutas.rom(JUEGO)


def cargar_zona(fila, col, filas, cols, K=1.0, hora=12, land=None):
    """Renderiza la zona (o la lee de la caché) y devuelve sus capas. Con land=<id> renderiza
    ese trozo de land_data suelto (interiores)."""
    os.makedirs(CACHE, exist_ok=True)
    if land is not None:
        ruta = os.path.join(CACHE, 'land_%d_K%g_h%g.npz' % (land, K, hora))
    else:
        ruta = os.path.join(CACHE, 'zona_%d_%d_%d_%d_K%g_h%g.npz' % (fila, col, filas, cols, K, hora))
    if not os.path.exists(ruta):
        sys.path.insert(0, os.path.join(RAIZ, 'tools'))
        import mapa3d
        print('Renderizando zona %s desde el ROM (se guarda en caché)...' % ((fila, col, filas, cols, land),))
        mundo = mapa3d.Mundo(_rom())
        if land is not None:
            mundo.usar_land(land)
            fila, col, filas, cols = 0, 0, 1, 1
        d = mundo.render(fila, col, filas, cols, K, hora, completo=True)
        np.savez_compressed(ruta, **d)
    d = np.load(ruta)
    return {k: d[k] for k in d.files}


class MapaReal:
    def __init__(self, zona=None, fila=None, col=None, filas=1, cols=1, hora=12, K=1.0, land=None):
        """zona: nombre de ZONAS o de INTERIORES, o fila/col/filas/cols de la matriz de Sinnoh, o
        land=<id> para un interior suelto. hora: luz del juego a esa hora (0-24; p. ej. 7 amanecer,
        12 día, 18 atardecer, 22 noche)."""
        if zona in INTERIORES:
            land = INTERIORES[zona]
        elif zona is not None:
            fila, col, filas, cols = ZONAS[zona]
        self.nombre = zona or ('land_%d' % land if land is not None else '%d_%d' % (fila, col))
        d = cargar_zona(fila, col, filas, cols, K, hora, land)
        self.fondo = Image.fromarray(d['imagen']).convert('RGBA')
        self.zbuf = d['z']
        self.alt = d['altura']
        self.perm = d['permisos']
        self.K = float(d['K'])
        self.y0 = int(d['y0'])               # fila de la imagen = y_pantalla - y0
        self.alto, self.ancho = self.alt.shape
        filas = np.nonzero((d['imagen'][..., 3] > 0).mean(1) > 0.9)[0]   # filas completas, sin huecos negros
        if len(filas):
            self.limites = (0, self.y0 + int(filas[0]), self.fondo.width, self.y0 + int(filas[-1]) + 1)
        else:   # interior: la sala flota en negro; la cámara se limita a la parte pintada
            ys, xs = np.nonzero(d['imagen'][..., 3] > 0)
            self.limites = (int(xs.min()), self.y0 + int(ys.min()), int(xs.max()) + 1, self.y0 + int(ys.max()) + 1)

    # -------------------------------------------------- consultas

    def bloqueado(self, tx, ty):
        if not (0 <= tx < self.ancho and 0 <= ty < self.alto):
            return True
        return bool(self.perm[ty, tx] & 0x8000)

    def elevacion(self, x, y):
        """Desplazamiento en pantalla (px hacia arriba) del suelo bajo un personaje cuyo tile empieza
        en (x, y) píxeles. Interpola entre tiles para que escaleras y rampas queden suaves."""
        fx, fy = x / TILE, y / TILE
        x0, y0 = int(np.floor(fx)), int(np.floor(fy))
        ax, ay = fx - x0, fy - y0

        def h(tx, ty):
            return self.alt[min(max(ty, 0), self.alto - 1), min(max(tx, 0), self.ancho - 1)]
        v = (h(x0, y0) * (1 - ax) * (1 - ay) + h(x0 + 1, y0) * ax * (1 - ay)
             + h(x0, y0 + 1) * (1 - ax) * ay + h(x0 + 1, y0 + 1) * ax * ay)
        return float(v) * self.K

    # -------------------------------------------------- dibujo (interfaz que usa Escena)

    def dibujar_suelo(self, lienzo, camx, camy, t):
        lienzo.alpha_composite(self.fondo.crop((camx, camy - self.y0, camx + lienzo.width,
                                                camy - self.y0 + lienzo.height)))

    def dibujables(self):
        return []

    def tapar(self, lienzo, camx, camy, caja, z_pies):
        """Vuelve a pintar, dentro de 'caja' (en pantalla), los píxeles del mapa que están delante de
        unos pies en z_pies: copas de árboles, tejados y fachadas de la fila de abajo."""
        x0, y0, x1, y1 = (int(v) for v in caja)
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, lienzo.width), min(y1, lienzo.height)
        if x0 >= x1 or y0 >= y1:
            return
        ix0, iy0 = x0 + camx, y0 + camy - self.y0
        z = self.zbuf[max(iy0, 0):iy0 + (y1 - y0), max(ix0, 0):ix0 + (x1 - x0)]
        if z.shape != (y1 - y0, x1 - x0):
            return
        m = z > z_pies + 0.5
        if not m.any():
            return
        trozo = self.fondo.crop((ix0, iy0, ix0 + (x1 - x0), iy0 + (y1 - y0)))
        mask = Image.fromarray((m * 255).astype(np.uint8))
        lienzo.paste(trozo, (x0, y0), mask)

    # -------------------------------------------------- ayuda para escribir escenas

    def plano(self, ruta, escala=2):
        """PNG con la zona, rejilla de tiles numerada y en rojo los tiles que no se pueden pisar."""
        from PIL import ImageDraw
        im = self.fondo.copy()
        capa = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(capa)
        for ty in range(self.alto):
            for tx in range(self.ancho):
                y = ty * TILE - self.alt[ty, tx] * self.K - self.y0
                if self.bloqueado(tx, ty):
                    d.rectangle((tx * TILE, y, tx * TILE + 15, y + 15), fill=(255, 0, 0, 70))
                d.rectangle((tx * TILE, y, tx * TILE + 15, y + 15), outline=(0, 0, 0, 40))
        im.alpha_composite(capa)
        im = im.resize((im.width * escala, im.height * escala), Image.NEAREST)
        d = ImageDraw.Draw(im)
        for ty in range(0, self.alto, 2):
            for tx in range(0, self.ancho, 2):
                yy = (ty * TILE - self.alt[ty, tx] * self.K - self.y0) * escala
                d.text((tx * TILE * escala + 2, yy + 1), '%d,%d' % (tx, ty), fill=(0, 0, 0))
        im.save(ruta)
        return ruta
