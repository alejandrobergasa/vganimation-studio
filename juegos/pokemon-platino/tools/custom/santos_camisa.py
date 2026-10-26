"""SANTOS con camisa (REWINDLIMBO2): el mismo SANTOS de santos.py, pero con camisa azul clarito y pantalón
y zapatos negros, como sale en el gimnasio. Se genera recoloreando los sprites ya hechos de SANTOS.

  python tools/custom/santos.py && python tools/custom/santos_camisa.py  ->  sprites_custom/santos_camisa/
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import CUSTOM, guardar_combate, guardar_mapa, recolorear, vista  # noqa
import santos as S

CAMISA = ((214, 226, 246), (172, 188, 220), (124, 140, 180), (88, 100, 140))
PANT = ((66, 66, 76), (46, 46, 54), (32, 32, 40), (22, 22, 28))
CHANDAL = (S.CHANDAL_C, S.CHANDAL_M, S.CHANDAL_O, S.CHANDAL_OO)


def _mapa(px):
    cuello, piernas = 21, 25
    recolorear(px, dict(zip(CHANDAL, CAMISA)), 17, piernas)
    recolorear(px, {S.BLANCO: CAMISA[0]}, cuello, piernas)          # cremallera -> botones claros
    recolorear(px, dict(zip(CHANDAL, PANT)), piernas, 32)
    recolorear(px, {S.BLANCO: PANT[2], S.BLANCO_S: PANT[3]}, piernas, 32)   # zapatos negros
    return px


def _frente(px):
    recolorear(px, dict(zip(CHANDAL, CAMISA)), 18, 47)
    recolorear(px, dict(zip(CHANDAL, PANT)), 47, 80)
    recolorear(px, {S.BLANCO: PANT[2], S.BLANCO_S: PANT[3]}, 47, 80)
    return px


def main():
    src = os.path.join(CUSTOM, 'santos')
    frames = [_mapa(np.array(Image.open(os.path.join(src, 'mapa', 'frame_%02d.png' % i)).convert('RGBA')))
              for i in range(16)]
    guardar_mapa('santos_camisa', frames, 'santos', 'SANTOS')
    fr = np.array(Image.open(os.path.join(src, 'combate', 'frente.png')).convert('RGBA'))
    guardar_combate('santos_camisa', _frente(fr))
    print(vista('santos_camisa'))


if __name__ == '__main__':
    main()
