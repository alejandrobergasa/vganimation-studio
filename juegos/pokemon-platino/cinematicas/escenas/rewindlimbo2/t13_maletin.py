"""REWINDLIMBO2 · tramo 13 (8:59-9:28). El maletín en el sofá gorila.

Original: de vuelta en el gimnasio, el inspector repite que el maletín está en el sofá gorila de la entrada y Santos le
pide que haga la vista gorda (8:59-9:14). Suena una música; el inspector sospecha y pregunta dónde los esconde:
¿bajo el suelo?, ¿debajo del ring? (9:14-9:26). «Ya os tengo» (9:26-9:28).

Versión Platino: el almacén-gimnasio de la obra (land 254), con el sofá Slaking en la entrada y el maletín del juego
encima. La música que se oye sale, en notas, de detrás de las cajas.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import efecto, exportar, textos  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 538.8, 567.6
mapa = MapaReal(land=254, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
GORILA = imagen('pokemon/frente/normal/289_slaking.png').crop((0, 0, 80, 80))
GORILA = GORILA.crop(GORILA.getbbox())
GORILA = GORILA.resize((GORILA.width * 3 // 4, GORILA.height * 3 // 4), Image.NEAREST)
MALETIN = imagen('personajes_mapa/153_bag/frame_00.png')
MALETIN = MALETIN.crop(MALETIN.getbbox())
SOFA = GORILA.copy()
SOFA.alpha_composite(MALETIN, (SOFA.width // 2 - MALETIN.width // 2 + 4, SOFA.height - MALETIN.height - 8))
sofa = esc.objeto(SOFA, 6, 9)
santos = esc.personaje('santos_camisa', 8, 6, mira='derecha')
gorgi = esc.personaje('gorgibot_azul', 9, 6, mira='izquierda')
esc.camara_fija(8, 7)
esc.negro = 1.0
NOTAS = efecto(29)


def musica(frames):
    """Notas que suben desde detrás de las cajas (la música escondida)."""
    def acc():
        for f in range(frames):
            for i in range(2):
                g = (f + i * 22) % 44
                img = NOTAS[(f // 8 + i) % len(NOTAS)]
                esc.efectos.append((img, 2 * 16 + i * 10 + (2 if g % 12 < 6 else -2), 6 * 16 - g))
            yield
    return acc()


def cara(color):
    return gorgi.cambiar_sprite('gorgibot_' + color if color else 'gorgibot')


esc.hacer(esc.fundido(entrada=True, frames=10))
esc.hacer(gorgi.mirar('abajo'), cara('rojo'))                                     # «El maletín está en el sofá…»
esc.hacer(esc.hasta(540.6))
esc.hacer(gorgi.mirar('izquierda'), cara('azul'))
esc.hacer(esc.hasta(541.8))
esc.hacer(santos.saltar(4, 8))                                                     # «Espera.»
esc.hacer(esc.hasta(543.5))
esc.hacer(santos.mirar('abajo'))                                                  # señala el sofá
esc.hacer(esc.hasta(545.0))
esc.hacer(santos.mirar('derecha'))
esc.hacer(esc.hasta(546.1))
esc.hacer(cara('rojo'), gorgi.temblar(10, 1))
esc.hacer(esc.hasta(549.1))
esc.hacer(cara(None))
esc.hacer(santos.temblar(16, 1))                                                  # «lo estoy dando todo»
esc.hacer(esc.hasta(553.4))

# ---------------------------------------------------------------- 9:14 la música
esc.hacer(esc.en_paralelo(musica(int((567.4 - 553.4) * 30))))
esc.hacer(esc.hasta(554.2))
esc.hacer(gorgi.emocion('!', 24), cara('amarillo'))
esc.hacer(gorgi.mirar('arriba'))
esc.hacer(esc.hasta(555.2))
esc.hacer(gorgi.mirar('izquierda'))
esc.hacer(esc.hasta(555.9))
esc.hacer(santos.mirar('derecha'))                                                # «te lo debes de imaginar»
esc.hacer(esc.hasta(559.0))
esc.hacer(cara('rojo'), gorgi.saltar(4, 8))                                         # «¿Dónde los escondes?»
esc.hacer(esc.hasta(561.5))
esc.hacer(gorgi.mirar('abajo'))                                                   # «¿Bajo el suelo?»
esc.hacer(esc.hasta(563.4))
esc.hacer(gorgi.andar('arriba', 3))                                               # «¿Debajo del ring?» -> (9,3)
esc.hacer(gorgi.mirar('izquierda'), santos.mirar('arriba'))
esc.hacer(esc.hasta(566.6))
esc.hacer(gorgi.emocion('!', 24), gorgi.saltar(6, 8), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.4))   # «Ya os tengo.»
esc.hacer(esc.fundido(entrada=False, frames=10))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't13_maletin', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
