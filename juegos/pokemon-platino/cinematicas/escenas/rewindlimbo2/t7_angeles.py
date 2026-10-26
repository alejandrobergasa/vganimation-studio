"""REWINDLIMBO2 · tramo 7 (5:30-6:05). Los ángeles.

Original: montaje de tele vieja sobre Logroño en llamas. El María, con alas oscuras y una luz en el pecho, sobrevuela
el puente mientras el narrador habla de su segunda venida (5:30-5:41). Chini, el hijo pródigo, aparece con
chaqueta roja, alas blancas y halo (5:41-5:48). Una mano enseña el móvil con el grupo donde se cocina la gala
(5:48-5:57) y todo se funde a negro (5:57-6:05).

Versión Platino: Ciudad Canal (zona 22,1) con el filtro CRT, tinte anaranjado y llamas de los ataques de fuego.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import angel, escalar, exportar, llamas, movil, textos  # noqa
from motor import Escena, MapaReal
from motor.recursos import frames_personaje

T0, T1 = 330.0, 365.0
mapa = MapaReal(fila=22, col=1, filas=2, cols=1, hora=18)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
maria = esc.personaje('el_maria', 15, 26, mira='abajo')
chini = esc.personaje('chini_chaqueta', 15, 26, mira='abajo')
maria.visible = chini.visible = False
ANGEL_MARIA = escalar(angel(frames_personaje('el_maria')[4], oscuro=True, luz=True), 2)
ANGEL_CHINI = escalar(angel(frames_personaje('chini_chaqueta')[4], halo=True), 2)
FUEGO = llamas()
esc.camara_fija(15, 25)


def flotar(p, frames):
    """Sube y baja despacio, como suspendido en el aire."""
    def acc():
        for f in range(frames):
            p.empuje = (0, round(3 * math.sin(f / 12)) - 10)
            yield
        p.empuje = (0, 0)
    return acc()


def incendio(frames, focos):
    """Llamas parpadeando en varios puntos (px de mapa)."""
    def acc():
        for f in range(frames):
            for i, (x, y) in enumerate(focos):
                img = FUEGO[(f // 5 + i) % len(FUEGO)]
                esc.efectos.append((img, x - img.width // 2, y - img.height))
            yield
    return acc()


FOCOS = [(9 * 16, 24 * 16), (22 * 16, 22 * 16), (10 * 16, 20 * 16), (21 * 16, 28 * 16), (8 * 16, 29 * 16)]

esc.hacer(esc.poner_filtro('crt'), esc.tenir_pantalla((255, 120, 32), 0.18, 1), maria.posar(ANGEL_MARIA),
          chini.posar(ANGEL_CHINI))
esc.hacer(esc.fundido(entrada=True, frames=15), maria.desvanecer(True, 20),
          esc.en_paralelo(flotar(maria, int(11.5 * 30)), flotar(chini, int(24 * 30))))
esc.hacer(esc.hasta(336.0))
esc.hacer(esc.en_paralelo(incendio(int((359.0 - 336.0) * 30), FOCOS)), esc.sonido('SEQ_SE_DP_W053', 0.25))
esc.hacer(esc.hasta(341.2))

# ---------------------------------------------------------------- 5:41 Chini, el hijo pródigo
esc.hacer(esc.destello((255, 255, 255), 14), maria.desaparecer(), chini.aparecer(),
          esc.sonido('SEQ_SE_DP_KIRAKIRA2', 0.5))
esc.hacer(esc.hasta(348.5))

# ---------------------------------------------------------------- 5:48 el móvil con el grupo
esc.hacer(esc.mostrar('movil', escalar(movil(), 2), x=16, y=24, efecto='subir', frames=14),
          esc.sonido('SEQ_SE_DP_PINPON', 0.4))
esc.hacer(esc.hasta(356.4))
esc.hacer(esc.ocultar('movil', 12, 'bajar'))
esc.hacer(esc.hasta(357.4))
esc.hacer(esc.fundido(entrada=False, frames=75))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't7_angeles', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
