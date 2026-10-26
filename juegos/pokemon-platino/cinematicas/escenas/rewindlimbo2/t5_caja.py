"""REWINDLIMBO2 · tramo 5 (4:54-5:15). La caja.

Original: se arrodilla, abre la caja y una luz amarilla le ilumina la cara mientras el narrador cuenta que el
Rewind desapareció en 2024 y que El María ha encontrado un «Rewind limbo» (4:54-5:09). Títulos REWIND LIMBO 2 y
REWIND 2024 - 2025 (5:09-5:15).

Versión Platino: el camino de arena junto a la hierba alta de la ruta 202 (zona 26,4). El primer plano de la
cara es el sprite de combate del ruinamaníaco (la base de su ropa) teñido de amarillo.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import caja_proyecto, efecto, escalar, exportar, inserto, textos, titulo  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 294.0, 315.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
maria = esc.personaje('el_maria_sudadera', 18, 20, mira='abajo')
caja = esc.objeto(caja_proyecto(), 18, 21, visible=False)
esc.camara_fija(18, 20)
esc.subtitulos(textos.subtitulos(T0, T1))
CHISPA = []
for n in (1, 2):                                                    # chispa en cruz de 3 y 5 px
    c = Image.new('RGBA', (5, 5))
    for d in range(-n, n + 1):
        c.putpixel((2 + d, 2), (255, 240, 120, 255))
        c.putpixel((2, 2 + d), (255, 240, 120, 255))
    c.putpixel((2, 2), (255, 255, 255, 255))
    CHISPA.append(c.resize((10, 10), Image.NEAREST))
AMARILLO = (255, 216, 64)


def cara_iluminada():
    """Primer plano: frente de combate del ruinamaníaco con la luz amarilla de la caja desde abajo."""
    im = imagen('entrenadores/frente/estatico/048_ruinamaniaco.png').crop((4, 18, 76, 72))   # solo la cara
    a = np.array(im).astype(np.float32)
    h = a.shape[0]
    k = np.linspace(0.15, 0.6, h)[:, None]                        # más luz cuanto más abajo (viene de la caja)
    for c in range(3):
        a[..., c] = a[..., c] * (1 - k) + AMARILLO[c] * k
    im = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    fondo = Image.new('RGBA', im.size, (40, 32, 16, 255))
    fondo.alpha_composite(im)
    return inserto(fondo, 2, tipo=1)


def resplandor(frames):
    """Destellos amarillos que salen de la caja abierta."""
    def acc():
        for f in range(frames):
            for i in range(3):                                    # tres chispas que suben y se apagan
                g = (f + i * 9) % 27
                if g < 22:
                    x = caja.x + 4 + i * 6 + (1 if g % 6 < 3 else -1)
                    esc.efectos.append((CHISPA[g // 8 % 2], x, caja.y - g))
            yield
    return acc()


# ---------------------------------------------------------------- 4:54 deja la caja y se arrodilla
esc.hacer(esc.fundido(entrada=True, frames=10))
esc.hacer(maria.llevar(caja_proyecto(), dy=-12))
esc.hacer(esc.hasta(295.5))
esc.hacer(maria.posar(16), maria.llevar(None), caja.aparecer(), esc.sonido('SEQ_SE_DP_BOX01', 0.4))
esc.hacer(esc.hasta(298.0))
esc.hacer(maria.temblar(10, 1))                                   # quita la tapa
esc.hacer(esc.destello(AMARILLO, 20, 0.9), esc.tenir_pantalla(AMARILLO, 0.25, 20),
          esc.sonido('SEQ_SE_DP_KIRAKIRA2', 0.6))
esc.hacer(maria.tenir(AMARILLO, 0.35), esc.en_paralelo(resplandor(int((309.0 - 299.3) * 30))))
esc.hacer(esc.hasta(302.2))
esc.hacer(esc.mostrar('cara', cara_iluminada(), y=8, efecto='zoom', frames=10))
esc.hacer(esc.hasta(307.6))
esc.hacer(esc.ocultar('cara', 8))
esc.hacer(esc.hasta(308.6))

# ---------------------------------------------------------------- 5:09 títulos
esc.hacer(esc.destello((255, 255, 255), 10), esc.fundido(entrada=False, frames=10))
esc.hacer(esc.tenir_pantalla(None, frames=1), esc.mostrar('negro', Image.new('RGBA', (256, 192), (0, 0, 0, 255)),
                                                          0, 0, frames=1, efecto=None, orden=4))
esc.hacer(esc.fundido(entrada=True, frames=1))                    # los títulos van sobre una capa negra
esc.hacer(esc.hasta(309.3))
esc.hacer(esc.mostrar('t1', titulo('REWIND LIMBO 2', k=2), y=64, efecto='zoom', frames=12, orden=5),
          esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.5))
esc.hacer(esc.hasta(311.6))
esc.hacer(esc.mostrar('t2', titulo('REWIND 2024 - 2025', k=1, color=(248, 216, 96)), y=104, frames=12, orden=5))
esc.hacer(esc.hasta(314.4))
esc.hacer(esc.ocultar('t1', 12), esc.ocultar('t2', 12))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't5_caja', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
