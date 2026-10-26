"""ROBOT VALEDORES (REWINDLIMBO2): el robot de píxeles que defiende la caja de EL PROYECTO.

  python tools/custom/robot_valedores.py  ->  sprites_custom/robot_valedores/

En el vídeo es un robot superpuesto: cuerpo rectangular metálico con pantalla oscura, pilotos rojos, brazos
y piernas de tubos segmentados y una llave inglesa en una mano. Base del juego: el microondas de la
habitación de Rotom (406_firebox), al que se le suben el cuerpo y se le añaden patas, brazos con llave
inglesa, antena y los pilotos rojos en el panel. Frames 16-17: brazos arriba (forcejeo/queja).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import DIRS, frames_mapa, guardar_mapa, vista  # noqa

NEGRO = (16, 16, 24)
METAL = ((232, 236, 244), (176, 184, 196), (120, 128, 144), (72, 78, 92))
ROJO = ((255, 82, 66), (176, 32, 32))


def _p(px, x, y, c):
    if 0 <= x < 32 and 0 <= y < 32:
        px[y, x] = (*c, 255)


def _tubo_v(px, x, y0, y1):
    """Tubo vertical segmentado de 2 px con contorno."""
    for y in range(y0, y1 + 1):
        _p(px, x - 1, y, NEGRO)
        _p(px, x + 2, y, NEGRO)
        seg = (y - y0) % 3 == 2
        _p(px, x, y, METAL[2] if seg else METAL[0])
        _p(px, x + 1, y, METAL[3] if seg else METAL[1])


def _tubo_h(px, x0, x1, y):
    for x in range(x0, x1 + 1):
        _p(px, x, y - 1, NEGRO)
        _p(px, x, y + 2, NEGRO)
        seg = (x - x0) % 3 == 2
        _p(px, x, y, METAL[2] if seg else METAL[0])
        _p(px, x, y + 1, METAL[3] if seg else METAL[1])


def _llave(px, x, y):
    """Llave inglesa pequeña con la boca hacia arriba en (x, y) = base del mango."""
    for k in range(4):
        _p(px, x, y - k, METAL[1])
        _p(px, x + 1, y - k, METAL[2])
        _p(px, x - 1, y - k, NEGRO)
        _p(px, x + 2, y - k, NEGRO)
    for dx in (-1, 0, 1, 2):
        _p(px, x + dx, y - 4, METAL[0])
        _p(px, x + dx, y - 5, NEGRO if dx in (0, 1) else METAL[1])
    for dx in (-2, 3):
        for dy in (4, 5, 6):
            _p(px, x + dx, y - dy, NEGRO)
    _p(px, x - 1, y - 6, METAL[1])
    _p(px, x + 2, y - 6, METAL[1])


def frame(base, direccion, paso, brazos_arriba=False):
    src = base
    px = np.zeros_like(src)
    px[0:26] = src[6:32]                 # cuerpo 6 px más arriba: y 9-23 (las patitas del microondas se van)
    px[24:26] = 0
    # cierra la base del cuerpo
    for x in range(9, 23):
        if px[23, x, 3]:
            px[23, x, :3] = NEGRO
    # piernas (al andar se alterna cuál baja)
    dl, dr = (1, 0) if paso == 1 else (0, 1) if paso == 3 else (0, 0)
    _tubo_v(px, 11, 24, 28 - dl)
    _tubo_v(px, 19, 24, 28 - dr)
    for x0, d in ((10, dl), (18, dr)):          # pies
        for x in range(x0, x0 + 5):
            _p(px, x, 29 - d, METAL[3])
            _p(px, x, 30 - d, NEGRO)
        _p(px, x0 - 1, 29 - d, NEGRO)
    # brazos
    if brazos_arriba:
        _tubo_h(px, 5, 8, 16)
        _tubo_v(px, 5, 8, 16)
        _tubo_h(px, 23, 26, 16)
        _tubo_v(px, 26, 8, 16)
        _llave(px, 26, 7)
    else:
        izq_y = 16 + (1 if paso == 3 else 0)
        der_y = 16 + (1 if paso == 1 else 0)
        _tubo_h(px, 5, 8, izq_y)
        _tubo_v(px, 5, izq_y, izq_y + 6)
        _tubo_h(px, 23, 26, der_y)
        _tubo_v(px, 26, der_y - 6, der_y)
        _llave(px, 26, der_y - 7)
        for dx, dy in ((0, 7), (1, 7), (-1, 8), (2, 8)):      # pinza en la mano izquierda
            _p(px, 5 + dx, izq_y + dy, METAL[3] if 0 <= dx <= 1 else NEGRO)
    # antena
    for y in range(5, 9):
        _p(px, 15, y, METAL[2])
        _p(px, 16, y, NEGRO)
    _p(px, 15, 4, ROJO[0])
    _p(px, 16, 4, ROJO[1])
    _p(px, 15, 3, NEGRO)
    if direccion != 'arriba':
        # pilotos rojos en el panel oscuro (ojos)
        for x0 in (12, 18):
            _p(px, x0, 16, ROJO[0])
            _p(px, x0 + 1, 16, ROJO[1])
            _p(px, x0, 17, ROJO[1])
            _p(px, x0 + 1, 17, ROJO[1])
    else:
        # de espaldas: tapa metálica en lugar de la pantalla
        for y in range(14, 21):
            for x in range(10, 22):
                if px[y, x, 3] and tuple(px[y, x, :3]) != NEGRO:
                    px[y, x, :3] = METAL[1] if (x + y) % 5 else METAL[2]
    if direccion == 'izquierda':
        px = px[:, ::-1].copy()
    return px


def main():
    base = frames_mapa('406')[4]
    fases = [0, 1, 0, 3]
    frames = [frame(base, DIRS[i], fases[i % 4]) for i in range(16)]
    frames += [frame(base, 'abajo', 0, True), frame(base, 'izquierda', 0, True)]
    guardar_mapa('robot_valedores', frames, '406_firebox', 'VALEDORES')
    print(vista('robot_valedores'))


if __name__ == '__main__':
    main()
