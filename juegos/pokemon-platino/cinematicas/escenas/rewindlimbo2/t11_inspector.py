"""REWINDLIMBO2 · tramo 11 (8:11-8:45). Llega el inspector GORGIBOT.

Original: los obreros, en rojo, bajo el rótulo GORGIBOT (8:11-8:15). Santos: «No me jodas, recogedlo todo». Aparece
el inspector, un robot con ruedas y la cara del Gorgi que cambia de color, y repite «¿Dónde tienes los baños de
minusválidos?» mientras Santos le enseña la licencia (8:15-8:31). Suben por la escalera; el techo arde y el
inspector da por buena la normativa de ignifugado (8:31-8:45).

Versión Platino: un interior con escaleras mecánicas (land 237). El rótulo es una pantalla con dos obreros de
combate teñidos de rojo. El fuego son las llamaradas de los ataques.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import escalar, exportar, llamas, textos, titulo  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 491.0, 525.6
mapa = MapaReal(land=237, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
santos = esc.personaje('santos_camisa', 13, 10, mira='derecha')
gorgi = esc.personaje('gorgibot_azul', 15, 10, mira='izquierda')
gorgi.visible = False
esc.camara_fija(13, 7)
FUEGO = llamas()


def rotulo():
    """Pantalla roja: dos obreros (sprite de combate) sacando bíceps y GORGIBOT en grande."""
    p = Image.new('RGBA', (256, 192), (200, 40, 40, 255))
    ob = imagen('entrenadores/frente/estatico/059_obrero.png').crop((0, 0, 80, 80))
    ob = escalar(ob, 2)
    p.alpha_composite(ob, (-6, 32))
    p.alpha_composite(ob.transpose(Image.FLIP_LEFT_RIGHT), (102, 32))
    a = np.array(p).astype(np.float32)
    g = a[..., :3].mean(axis=2, keepdims=True) / 255
    a[..., :3] = np.concatenate([g * 255, g * 70, g * 60], axis=2) * 0.8 + np.array((200, 40, 40)) * 0.2
    p = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    letrero = Image.new('RGBA', (124, 30), (232, 220, 220, 255))
    t = titulo('GORGIBOT', k=2, color=(200, 40, 40), sombra=(90, 16, 16))
    letrero.alpha_composite(t, ((124 - t.width) // 2, (30 - t.height) // 2))
    p.alpha_composite(letrero.rotate(-6, expand=True, resample=Image.NEAREST), (120, 10))
    return p


def cara(color):
    return gorgi.cambiar_sprite('gorgibot_' + color if color else 'gorgibot')


def incendio(frames, focos):
    def acc():
        for f in range(frames):
            for i, (x, y) in enumerate(focos):
                img = FUEGO[(f // 4 + i) % 2]
                esc.efectos.append((img, x - img.width // 2, y - img.height))
            if f % 120 == 0:                                  # W053 dura casi 4 s: no solaparlo
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_W053', 0.14))
            yield
    return acc()


# ---------------------------------------------------------------- 8:11 el rótulo rojo
esc.hacer(esc.mostrar('rotulo', rotulo(), 0, 0, frames=1, efecto=None), esc.sonido('SEQ_SE_DP_KOUKA_H', 0.5))
esc.hacer(esc.hasta(494.4))
esc.hacer(esc.ocultar('rotulo', 6))
esc.hacer(santos.saltar(6, 8), santos.emocion('!', 30))                     # «No me jodas, recogedlo todo»
esc.hacer(esc.hasta(495.7))

# ---------------------------------------------------------------- 8:15 el inspector
esc.hacer(gorgi.desvanecer(True, 15), esc.sonido('SEQ_SE_DP_W043', 0.4))
esc.hacer(esc.hasta(496.5))
esc.hacer(cara('rojo'), esc.sonido('SEQ_SE_DP_PINPON', 0.3))
esc.hacer(esc.hasta(499.0))
esc.hacer(cara('azul'))
esc.hacer(esc.hasta(501.4))
esc.hacer(cara('rojo'), gorgi.temblar(8, 1))
esc.hacer(esc.hasta(503.8))
esc.hacer(cara(None))
esc.hacer(esc.hasta(505.5))
esc.hacer(santos.mirar('abajo'))                                              # le enseña los papeles
esc.hacer(esc.hasta(506.8))
esc.hacer(santos.mirar('derecha'))
esc.hacer(esc.hasta(508.0))
esc.hacer(cara('rojo'), gorgi.temblar(10, 2))
esc.hacer(esc.hasta(510.3))
esc.hacer(cara('azul'))

# ---------------------------------------------------------------- 8:30 «sígueme»: a la escalera
esc.hacer(santos.ruta(('derecha', 1), ('arriba', 4)), gorgi.andar('arriba', 3))   # -> (14,6) y (15,7)
esc.hacer(santos.mirar('izquierda'), gorgi.mirar('izquierda'))
esc.hacer(esc.hasta(513.0))

# ---------------------------------------------------------------- 8:33 el techo ardiendo
esc.hacer(esc.fundido(entrada=False, frames=8))
esc.hacer(santos.teletransportar(6, 10), gorgi.teletransportar(4, 10), santos.mirar('izquierda'),
          gorgi.mirar('arriba'), esc.accion(lambda: esc.camara_fija(8, 7)))
esc.hacer(esc.fundido(entrada=True, frames=8),
          esc.en_paralelo(incendio(int((525.6 - 513.6) * 30), [(x * 16 + 8, 6 * 16 + 2) for x in range(1, 9, 2)])))
esc.hacer(esc.hasta(515.4))
esc.hacer(cara('amarillo'), gorgi.saltar(3, 8))
esc.hacer(esc.hasta(520.3))
esc.hacer(santos.temblar(14, 1), santos.mirar('izquierda'))
esc.hacer(esc.hasta(522.3))
esc.hacer(cara('rojo'), gorgi.mirar('derecha'))
esc.hacer(esc.hasta(524.8))
esc.hacer(santos.mirar('abajo'))
esc.hacer(esc.hasta(525.1))
esc.hacer(esc.fundido(entrada=False, frames=12))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't11_inspector', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
