"""CHINI (REWINDLIMBO2): el hijo pródigo de los valedores. Joven de pelo castaño corto. Dos versiones:
  chini           camiseta negra (frente al ordenador)
  chini_chaqueta  chaqueta roja sobre camiseta azul (el montaje del ángel)
Base: 066 man5 (pelo corto oscuro, camiseta naranja), recoloreado por zonas.

  python tools/custom/chini.py  ->  sprites_custom/chini/, sprites_custom/chini_chaqueta/
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import frames_mapa, guardar_mapa, recolorear, vista  # noqa

PELO = {(106, 139, 131): (136, 96, 64), (74, 90, 98): (96, 64, 44), (57, 57, 65): (60, 40, 32)}
CAMISETA = {(230, 139, 65): (78, 78, 88), (164, 98, 65): (46, 46, 54),
            (230, 222, 189): (78, 78, 88), (172, 164, 131): (46, 46, 54)}
CHAQUETA = {(230, 139, 65): (226, 56, 72), (164, 98, 65): (160, 32, 48),
            (230, 222, 189): (72, 88, 208), (172, 164, 131): (44, 52, 150)}


def _frames(torso):
    out = []
    for px in frames_mapa('066'):
        recolorear(px, PELO, 0, 17)
        recolorear(px, torso, 17, 28)
        out.append(px)
    return out


def main():
    guardar_mapa('chini', _frames(CAMISETA), 'man5', 'CHINI')
    guardar_mapa('chini_chaqueta', _frames(CHAQUETA), 'man5', 'CHINI')
    print(vista('chini'))
    print(vista('chini_chaqueta'))


if __name__ == '__main__':
    main()
