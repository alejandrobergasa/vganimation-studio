"""REWINDLIMBO2 · tramo 8 (6:05-7:02). El grupo.

Original: la conversación del grupo de los valedores va apareciendo mensaje a mensaje y subiendo por la pantalla
mientras se oyen las voces: dónde y cuándo hacer la gala, el «modo esquimal», el 20 de enero y la tabla de surf
polar del Gorgi.

Versión Platino: cada mensaje es una ventana del juego con el nombre en color y una cara del juego como avatar.
Los de EL MARÍA (el móvil es suyo) van a la derecha en la ventana verde de ladrillos, como los mensajes propios.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import exportar, textos  # noqa
from motor import Escena, MapaReal
from motor.escena import envolver
from motor.recursos import fuente, frames_personaje, ventana_mensaje

T0, T1 = 365.0, 422.0
mapa = MapaReal(fila=22, col=1, filas=2, cols=1, hora=12)
esc = Escena(mapa, t0=T0)
esc.camara_fija(15, 30)
F = fuente()

GENTE = {   # quién: (sprite para la cara, color del nombre)
    'POPS': ('man3', (208, 40, 96)),
    'CHIQUITÍN': ('boy1', (200, 112, 32)),
    'VIVI': ('man2', (88, 72, 200)),
    'MANDARÍN': ('boy4', (224, 120, 160)),
    'EL MARÍA': ('el_maria', (40, 136, 56)),
    'CHINI': ('chini', (32, 144, 176)),
    'PANINI': ('sportsman', (216, 112, 40)),
    'FRANKY': ('cyclem', (40, 160, 64)),
}


def _claro(c):
    return tuple(min(255, v + 120) for v in c)


def cara(sprite):
    """Avatar de 20x20: la cabeza del sprite del mapa en una ventanita redonda."""
    im = frames_personaje(sprite)[4]
    cab = im.crop((8, 4, 24, 20))
    a = np.zeros((20, 20, 4), np.uint8)
    yy, xx = np.mgrid[0:20, 0:20]
    d = (xx - 9.5) ** 2 + (yy - 9.5) ** 2
    a[d <= 90] = (232, 240, 248, 255)
    a[(d > 72) & (d <= 90)] = (64, 72, 96, 255)
    out = Image.fromarray(a, 'RGBA')
    out.alpha_composite(cab, (2, 3))
    m = np.array(out)
    m[d > 90] = 0
    return Image.fromarray(m, 'RGBA')


def burbuja(quien, texto, con_nombre):
    lineas = envolver(texto, 160)
    propio = quien == 'EL MARÍA'
    h = 10 + 14 * len(lineas) + (14 if con_nombre and not propio else 0)
    w = max(F.ancho(l) for l in lineas) + 42
    if con_nombre and not propio:
        w = max(w, F.ancho(quien) + 42)
    w, h = max(40, (w + 7) // 8 * 8), max(24, (h + 7) // 8 * 8)
    v = ventana_mensaje(w, h, 9 if propio else 1)
    y = 5
    if con_nombre and not propio:
        col = GENTE[quien][1]
        F.dibujar(v, quien, 17, y, col, _claro(col))
        y += 14
    for l in lineas:
        F.dibujar(v, l, 17, y)
        y += 14
    return v


def fondo():
    a = np.zeros((192, 256, 4), np.uint8)
    a[:] = (222, 230, 218, 255)
    for y in range(6, 192, 24):
        for x in range(6 + (y // 24 % 2) * 12, 256, 24):
            a[y:y + 3, x:x + 3] = (206, 216, 202, 255)
    return Image.fromarray(a, 'RGBA')


# maqueta de la conversación: (instante, imagen, x, y en la tira)
FONDO = fondo()
mensajes = []
y, anterior = 4, None
for t, quien, texto in textos.chat():
    con_nombre = quien != anterior
    b = burbuja(quien, texto, con_nombre)
    if con_nombre and anterior is not None:
        y += 4
    if quien == 'EL MARÍA':
        x = 252 - b.width
        av = None
    else:
        x = 28
        av = cara(GENTE[quien][0]) if con_nombre else None
    mensajes.append((t, b, x, y, av))
    y += b.height + 2
    anterior = quien


def conversacion(frames):
    """Compone la pantalla del chat en cada frame: los mensajes ya llegados, con la tira subiendo suave."""
    def acc():
        scroll = 0.0
        vistos = 0
        for f in range(frames):
            ahora = esc.ahora
            llegados = [m for m in mensajes if m[0] <= ahora]
            if len(llegados) > vistos:
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_SELECT', 0.15))
                vistos = len(llegados)
            fondo_y = (llegados[-1][3] + llegados[-1][1].height) if llegados else 0
            objetivo = max(0.0, fondo_y - 186)
            scroll += (objetivo - scroll) * 0.15
            lienzo = FONDO.copy()
            for t, b, x, yy, av in llegados:
                edad = (ahora - t) * 30
                dy = int(max(0, 8 - edad) * 2)               # entra subiendo un poco
                py = int(yy - scroll) + dy
                if py > 192 or py + b.height < 0:
                    continue
                lienzo.alpha_composite(b, (x, py)) if py >= 0 else lienzo.paste(b.crop((0, -py, b.width, b.height)),
                                                                                 (x, 0), b.crop((0, -py, b.width, b.height)))
                if av is not None and py >= 0:
                    lienzo.alpha_composite(av, (4, py + 2))
            esc.capas['chat'] = [lienzo, 0, 0, 1.0, 0]
            yield
    return acc()


esc.hacer(conversacion(int((T1 - T0) * 30) - 20), esc.fundido(entrada=True, frames=15))
esc.hacer(esc.fundido(entrada=False, frames=12))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't8_grupo', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
