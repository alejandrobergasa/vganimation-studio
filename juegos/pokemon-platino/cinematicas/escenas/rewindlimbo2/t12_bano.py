"""REWINDLIMBO2 · tramo 12 (8:45-8:59). El baño de minusválidos.

Original: Santos abre la puerta del baño, «aquí están los…» (8:45-8:48). Una nube amarilla envuelve al inspector y el
suelo arde a su alrededor mientras dice que el tamaño del baño no cumple la normativa (8:48-8:56). Santos: «Espera un
momento, lo podemos arreglar» (8:56-8:59).

Versión Platino: una sala pequeña de suelo gris (interior land 210). La nube es el humo del juego teñido de amarillo y
el fuego, las llamaradas de los ataques.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import escalar, exportar, humo, llamas, textos  # noqa
from motor import Escena, MapaReal

T0, T1 = 525.6, 538.8
mapa = MapaReal(land=210, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
santos = esc.personaje('santos_camisa', 7, 8, mira='arriba')
gorgi = esc.personaje('gorgibot_rojo', 5, 9, mira='arriba')
esc.camara_fija(5, 6)
esc.negro = 1.0
FUEGO = llamas()


def amarillo(img):
    a = np.array(img).astype(np.float32)
    a[..., 0] = a[..., 0] * 0.3 + 255 * 0.7
    a[..., 1] = a[..., 1] * 0.3 + 224 * 0.7
    a[..., 2] = a[..., 2] * 0.3 + 64 * 0.7
    return escalar(Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA'), 2)


NUBE = [amarillo(h) for h in humo()]


def nube(frames):
    """Nube amarilla alrededor del inspector: varias bocanadas que crecen y se mueven."""
    def acc():
        for f in range(frames):
            for i, (dx, dy) in enumerate(((-14, -6), (14, -10), (0, -22), (-6, 6), (12, 4))):
                img = NUBE[(f // 6 + i) % len(NUBE)]
                esc.efectos.append((img, gorgi.x + 8 + dx - img.width // 2, gorgi.y + dy - img.height // 2))
            if f % 60 == 0:
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_W025', 0.14))
            yield
    return acc()


def suelo_ardiendo(frames):
    def acc():
        for f in range(frames):
            for i, (x, y) in enumerate(((1, 4), (3, 4), (2, 6), (9, 4), (9, 6), (4, 6), (6, 6), (8, 7))):
                img = FUEGO[(f // 4 + i) % 2]                     # alrededor de los dos, sin taparles la cara
                esc.efectos.append((img, x * 16 + 8 - img.width // 2, y * 16 + 14 - img.height))
            if f % 120 == 0:                                  # W053 dura casi 4 s: no solaparlo
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_W053', 0.14))
            yield
    return acc()


esc.hacer(esc.fundido(entrada=True, frames=10), gorgi.andar('arriba', 5))                 # -> (5,4)
esc.hacer(santos.andar('arriba', 3), gorgi.mirar('abajo'))                               # -> (7,5)
esc.hacer(santos.mirar('izquierda'))
esc.hacer(esc.hasta(528.0))
esc.hacer(gorgi.cambiar_sprite('gorgibot_amarillo'), nube(int(3.0 * 30)), gorgi.temblar(40, 1))
esc.hacer(esc.hasta(531.0))
esc.hacer(esc.en_paralelo(suelo_ardiendo(int(5.4 * 30))), santos.temblar(12, 1), santos.emocion('!', 24))
esc.hacer(esc.hasta(532.7))
esc.hacer(gorgi.cambiar_sprite('gorgibot_azul'), gorgi.mirar('derecha'))
esc.hacer(esc.hasta(536.7))
esc.hacer(santos.saltar(4, 8))                                                         # «Espera, lo arreglamos»
esc.hacer(esc.hasta(538.2))
esc.hacer(esc.fundido(entrada=False, frames=10))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't12_bano', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
