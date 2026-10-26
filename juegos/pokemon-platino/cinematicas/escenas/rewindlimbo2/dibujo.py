"""Pixel art propio al estilo de Platino para los planos de objetos de REWINDLIMBO2 (v3): contorno oscuro de 1 px,
luz desde arriba a la izquierda y rampas de 3-4 tonos, sin degradados ni antialias.

Lienzo.forma(dibuja, rampa) rellena la máscara que pinta `dibuja(d)` (un ImageDraw en blanco y negro) con su rampa:
banda clara arriba a la izquierda, tono medio y sombra abajo a la derecha, más el contorno.
"""
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

N = (40, 36, 48)                                           # contorno general
PIEL = ((255, 213, 189), (236, 180, 144), (206, 140, 106), (150, 92, 72))   # la de EL MARÍA y dos sombras
MADERA = ((196, 124, 70), (158, 92, 50), (118, 64, 36), (78, 40, 26))       # brezo de la pipa
PLATA = ((244, 246, 250), (214, 220, 230), (172, 180, 196), (124, 132, 152))
CRISTAL = ((196, 226, 244), (128, 172, 212), (82, 118, 164), (56, 80, 120))
NEGRO = ((86, 86, 100), (60, 60, 72), (42, 42, 52), (28, 28, 36))
ROJO = ((248, 112, 96), (216, 56, 48), (152, 32, 40), (96, 20, 28))
TABACO = ((176, 128, 72), (132, 90, 48), (92, 60, 34))
PAPEL = ((250, 250, 242), (230, 230, 218), (196, 196, 184))
GRAVA = ((196, 188, 172), (170, 162, 146), (138, 130, 116))


class Lienzo:
    def __init__(self, w, h, fondo=None):
        self.w, self.h = w, h
        self.img = Image.new('RGBA', (w, h), (*fondo, 255) if fondo else (0, 0, 0, 0))

    # ---------------------------------------------------------------- primitivas
    def mascara(self, dibuja):
        m = Image.new('L', (self.w, self.h))
        dibuja(ImageDraw.Draw(m))
        return np.array(m) > 0

    def forma(self, dibuja, rampa, contorno=N, bandas=(0.28, 0.66, 0.9), bordes=True, mascara=None):
        """Rellena una forma con su rampa (2-4 tonos) y la perfila. dibuja: función que pinta en un ImageDraw 'L'."""
        m = mascara if mascara is not None else self.mascara(dibuja)
        if not m.any():
            return m
        a = np.array(self.img)
        ys, xs = np.nonzero(m)
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        t = ((yy - ys.min()) / max(1, ys.max() - ys.min()) + (xx - xs.min()) / max(1, xs.max() - xs.min())) / 2
        idx = np.zeros(m.shape, int)
        for k, b in enumerate(bandas[:len(rampa) - 1]):
            idx[t >= b] = k + 1
        if bordes:                                       # filo de luz arriba/izquierda y de sombra abajo/derecha
            arriba = m & ~np.roll(m, 1, 0)
            izq = m & ~np.roll(m, 1, 1)
            abajo = m & ~np.roll(m, -1, 0)
            der = m & ~np.roll(m, -1, 1)
            idx[(abajo | der) & m] = len(rampa) - 1
            idx[(arriba | izq) & m & (idx < len(rampa) - 1)] = 0
        col = np.array([tuple(c) + (255,) for c in rampa], np.uint8)
        a[m] = col[idx[m]]
        if contorno:
            borde = ndimage.binary_dilation(m, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])) & ~m
            a[borde] = (*contorno, 255)
        self.img = Image.fromarray(a, 'RGBA')
        return m

    def plano(self, dibuja, color, contorno=None):
        """Forma de un solo color (detalles, rayas, letras)."""
        return self.forma(dibuja, (color,), contorno, bandas=(), bordes=False)

    def pixeles(self, pts, color):
        a = np.array(self.img)
        for x, y in pts:
            if 0 <= x < self.w and 0 <= y < self.h:
                a[y, x] = (*color, 255)
        self.img = Image.fromarray(a, 'RGBA')

    def pegar(self, img, x, y):
        self.img.alpha_composite(img, (x, y))

    def copia(self):
        c = Lienzo(self.w, self.h)
        c.img = self.img.copy()
        return c


def contorno_exterior(img, color=N):
    """Perfila por fuera una imagen RGBA (silueta)."""
    a = np.array(img)
    m = a[..., 3] > 0
    b = ndimage.binary_dilation(m, np.array([[0, 1, 0], [1, 1, 1], [0, 1, 0]])) & ~m
    a[b] = (*color, 255)
    return Image.fromarray(a, 'RGBA')


def rayas_chandal(c, x0, y0, x1, y1, separacion=6):
    """Las tres rayas blancas del pantalón de chándal en diagonal sobre negro."""
    for k in range(3):
        o = k * separacion
        c.plano(lambda d, o=o: d.line([(x0 + o, y0), (x1 + o, y1)], fill=255, width=3), (232, 236, 244))
