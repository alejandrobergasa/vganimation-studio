"""GORGIBOT (REWINDLIMBO2): el inspector de obras robot. Cuerpo metálico oscuro sobre una rueda y una
cara humana que cambia de color (azul, rojo, amarillo).

  python tools/custom/gorgibot.py  ->  sprites_custom/gorgibot/, gorgibot_azul/, gorgibot_rojo/, gorgibot_amarillo/

Base: SANTOS (sprites_custom/santos, de man1): se queda la cabeza, el cuerpo pasa a placas de metal oscuro
con juntas y las piernas a una rueda que gira al avanzar.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import CUSTOM, DIRS, guardar_mapa, vista  # noqa

NEGRO = (12, 12, 18)
METAL = ((122, 128, 140), (84, 90, 104), (54, 58, 70), (34, 36, 46))
PIEL = {(255, 213, 189), (222, 156, 115), (123, 65, 65), (150, 106, 84), (196, 150, 122)}
CARAS = {'': None, '_azul': (96, 128, 255), '_rojo': (255, 56, 48), '_amarillo': (255, 224, 40)}


def _p(px, x, y, c):
    if 0 <= x < 32 and 0 <= y < 32:
        px[y, x] = (*c, 255)


def frame(px, direccion, fase, cara):
    px = px.copy()
    cuello = 21
    # cara de color: la piel brilla
    if cara:
        for y in range(6, 20):
            for x in range(32):
                if px[y, x, 3] and tuple(px[y, x, :3]) in PIEL:
                    lum = sum(px[y, x, :3]) / 765
                    px[y, x, :3] = [int(min(255, c * (0.55 + 0.6 * lum))) for c in cara]
    # cuerpo: todo lo que no es contorno pasa a metal según su luminosidad, con una junta horizontal
    for y in range(cuello, 26):
        for x in range(32):
            if px[y, x, 3] and tuple(px[y, x, :3]) != (0, 0, 0):
                lum = sum(int(v) for v in px[y, x, :3]) / 765
                k = 0 if lum > 0.75 else 1 if lum > 0.5 else 2 if lum > 0.3 else 3
                px[y, x, :3] = METAL[k]
                if y == 23 and k < 2:
                    px[y, x, :3] = METAL[2]
    if direccion == 'abajo':                       # piloto en el pecho
        _p(px, 15, 22, (120, 220, 255))
        _p(px, 16, 22, (60, 140, 220))
    # piernas -> rueda
    px[26:32] = 0
    cx = 15.5
    for y in range(25, 32):
        for x in range(10, 22):
            d = ((x - cx) / 5.5) ** 2 + ((y - 28.2) / 3.4) ** 2
            if d <= 1:
                borde = d > 0.62
                _p(px, x, y, NEGRO if borde else METAL[3])
    giro = fase in (1, 3)
    for x, y in (((14, 28), (17, 28), (15, 27), (16, 29)) if giro else ((15, 28), (16, 28), (15, 27), (16, 27))):
        _p(px, x, y, METAL[0])
    for x in range(12, 20):                         # eje / guardabarros
        if px[25, x, 3]:
            _p(px, x, 25, METAL[2])
    return px


def main():
    src = os.path.join(CUSTOM, 'santos', 'mapa')
    base = [np.array(Image.open(os.path.join(src, 'frame_%02d.png' % i)).convert('RGBA')) for i in range(16)]
    for suf, cara in CARAS.items():
        frames = [frame(px, DIRS[i], i % 4, cara) for i, px in enumerate(base)]
        guardar_mapa('gorgibot' + suf, frames, 'santos', 'GORGIBOT')
        print(vista('gorgibot' + suf))


if __name__ == '__main__':
    main()
