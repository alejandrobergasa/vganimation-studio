"""REWINDLIMBO2 · tramo 14 (9:28-10:18,6). Los escondidos y los 2.000 pavos.

Original: tres valedores sentados en un cuarto escuchan un corrido y uno enseña su abrigo verde nuevo (9:28-9:36).
El inspector se disculpa: creía que Santos escondía fontaneros mexicanos, y se marcha recordando el maletín
(9:36-9:48). Santos los deja salir, un obrero saca bíceps y Santos cuenta que tiene que soplarle 2.000 pavos al
inspector; pide ayuda a los valedores, que le dicen que monte un side hustle (9:48-10:15). Negro hasta el final.

Versión Platino: un cuarto pequeño y oscuro (interior land 280) como escondite. Los valedores son personajes del
juego; el abrigo verde es un inserto con una prenda verde dibujada.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import efecto, escalar, exportar, inserto, textos  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 567.6, 618.624
mapa = MapaReal(land=280, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
v1 = esc.personaje('boy2', 1, 3, mira='abajo')
v2 = esc.personaje('campboy', 2, 3, mira='abajo')
v3 = esc.personaje('man2', 4, 3, mira='abajo')
santos = esc.personaje('santos_camisa', 5, 4, mira='izquierda')
santos.visible = False
gorgi = esc.personaje('gorgibot_rojo', 3, 5, mira='arriba')
gorgi.visible = False
esc.camara_fija(3, 4)
esc.negro = 1.0
NOTAS = efecto(29)


def corrido(frames):
    """Las notas del corrido que suena en el escondite."""
    def acc():
        for f in range(frames):
            g = f % 40
            img = NOTAS[(f // 8) % len(NOTAS)]
            esc.efectos.append((img, 3 * 16 + (3 if g % 10 < 5 else -3), 3 * 16 - 10 - g))
            yield
    return acc()


def abrigo():
    """Abrigo verde de montaña (40x44) con capucha y cremallera."""
    a = Image.new('RGBA', (40, 44))
    d = ImageDraw.Draw(a)
    V, VO, N = (56, 200, 104, 255), (32, 140, 72, 255), (16, 48, 24, 255)
    d.polygon([(8, 10), (14, 2), (26, 2), (32, 10), (39, 34), (32, 36), (31, 43), (9, 43), (8, 36), (1, 34)],
              fill=V, outline=N)
    d.polygon([(14, 2), (26, 2), (24, 10), (16, 10)], fill=VO, outline=N)          # capucha
    d.line((20, 10, 20, 42), fill=N)                                               # cremallera
    d.line((9, 14, 9, 36), fill=VO)
    d.line((31, 14, 31, 36), fill=VO)
    return inserto(escalar(a, 2), 1)


def bicep():
    ob = imagen('entrenadores/frente/estatico/059_obrero.png').crop((0, 0, 80, 80))
    return inserto(ob, 1)


# ---------------------------------------------------------------- 9:28 el escondite
esc.hacer(esc.fundido(entrada=True, frames=10), esc.en_paralelo(corrido(int((576.4 - 568.0) * 30))))
esc.hacer(esc.hasta(568.7))
esc.hacer(v2.saltar(3, 8))
esc.hacer(esc.hasta(570.8))
esc.hacer(v1.mirar('derecha'), v3.saltar(3, 8))                                # «un corrido de putísima madre»
esc.hacer(esc.hasta(573.7))
esc.hacer(esc.mostrar('abrigo', abrigo(), x=136, y=8, efecto='zoom', frames=8), v2.saltar(4, 8))
esc.hacer(esc.hasta(576.2))
esc.hacer(esc.ocultar('abrigo', 6))

# ---------------------------------------------------------------- 9:36 el inspector se disculpa
esc.hacer(gorgi.desvanecer(True, 8), v1.mirar('abajo'), esc.sonido('SEQ_SE_DP_DOOR_OPEN', 0.4))
esc.hacer(v1.emocion('!', 20), v2.emocion('!', 20), v3.emocion('!', 20))
esc.hacer(esc.hasta(577.4))
esc.hacer(gorgi.cambiar_sprite('gorgibot_azul'))
esc.hacer(esc.hasta(581.2))
esc.hacer(santos.desvanecer(True, 8), gorgi.mirar('derecha'))
esc.hacer(santos.saltar(3, 8))                                                  # «¿Cómo puedes pensar eso?»
esc.hacer(esc.hasta(584.0))
esc.hacer(gorgi.cambiar_sprite('gorgibot'))
esc.hacer(esc.hasta(587.6))
esc.hacer(gorgi.mirar('abajo'))
esc.hacer(gorgi.desvanecer(False, 12), esc.sonido('SEQ_SE_DP_DOOR_CLOSE', 0.4))
esc.hacer(esc.hasta(589.3))

# ---------------------------------------------------------------- 9:49 ya pueden salir
esc.hacer(santos.mirar('arriba'))
esc.hacer(esc.hasta(590.8))
esc.hacer(esc.mostrar('bicep', bicep(), x=0, y=8, efecto='zoom', frames=8), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.4))
esc.hacer(esc.hasta(593.0))
esc.hacer(esc.ocultar('bicep', 6))
esc.hacer(santos.andar('izquierda', 2), v1.mirar('abajo'), v2.mirar('abajo'), v3.mirar('abajo'))   # -> (3,4)
esc.hacer(santos.mirar('arriba'))
esc.hacer(esc.hasta(595.3))
esc.hacer(santos.temblar(16, 1))                                                # «2.000 pavos»
esc.hacer(esc.hasta(603.0))
esc.hacer(santos.saltar(4, 8))                                                  # «Valedores, necesito ayuda»
esc.hacer(esc.hasta(605.1))
esc.hacer(v1.mirar('derecha'), v3.mirar('izquierda'))
esc.hacer(esc.hasta(607.3))
esc.hacer(v1.mirar('abajo'), v3.mirar('abajo'), santos.temblar(16, 2))
esc.hacer(esc.hasta(610.1))
esc.hacer(v2.saltar(3, 8))                                                      # «montad un side hustle»
esc.hacer(esc.hasta(613.6))
esc.hacer(v3.saltar(3, 8))
esc.hacer(esc.hasta(614.6))
esc.hacer(esc.fundido(entrada=False, frames=14))                                # negro hacia 10:15,08
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't14_escondite', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
