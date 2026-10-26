"""REWINDLIMBO2 · tramo 9 (7:02-7:28). Chini y el ordenador.

Original: Chini sonríe junto a un ordenador viejo con luz verde. El ordenador dice «¿Te has quedado sin tokens?
Suscríbete» y él se queja de la IA (7:02-7:12). Se pone los cascos y en el monitor sale un juego (7:12-7:17).
Le echan en cara que se mete a jugar en vez de currar en la obra del gimnasio y él promete meterle duro mañana
(7:17-7:26). «Mañana todo empezará» y corte a negro (7:26-7:28).

Versión Platino: un cuarto con PC (interior land 313). El monitor es un inserto: primero el aviso de tokens en una
ventana del juego y luego un combate (fondo de combate con un Infernape). Los cascos están dibujados encima.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import escalar, exportar, inserto, texto_img, textos  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 422.0, 447.0
mapa = MapaReal(land=313, hora=21)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
chini = esc.personaje('chini', 7, 4, mira='arriba')
esc.camara_fija(5, 5)


def monitor(pantalla):
    """Monitor viejo de 120x96 con la imagen 'pantalla' (104x72) dentro y un brillo verdoso."""
    m = Image.new('RGBA', (120, 96), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    d.rounded_rectangle((0, 0, 119, 95), 6, fill=(208, 204, 184, 255), outline=(40, 40, 40, 255))
    d.rectangle((6, 6, 113, 81), fill=(24, 24, 24, 255))
    m.alpha_composite(pantalla.resize((104, 72), Image.NEAREST), (8, 8))
    d.rectangle((102, 85, 108, 88), fill=(64, 200, 96, 255))         # piloto encendido
    a = np.array(m).astype(np.int16)
    a[8:80, 8:112, 1] = np.clip(a[8:80, 8:112, 1] + 18, 0, 255)     # tono verde de pantalla vieja
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def pantalla_tokens():
    p = Image.new('RGBA', (104, 72), (232, 236, 240, 255))
    for i, l in enumerate(('¿Sin tokens?', '', 'SUSCRÍBETE')):
        if l:
            t = texto_img(l, (200, 40, 48) if i == 2 else (48, 48, 56))
            p.alpha_composite(t, ((104 - t.width) // 2, 12 + i * 16))
    return p


def pantalla_juego():
    p = imagen('combate/fondos/fondo_04_dia.png').crop((0, 0, 256, 80)).resize((104, 72), Image.NEAREST).convert('RGBA')
    poke = imagen('pokemon/frente/normal/392_infernape.png')
    poke = poke.crop((0, 0, 80, 80))
    p.alpha_composite(poke.resize((60, 60), Image.NEAREST), (22, 8))
    return p


def cascos():
    """Cascos con micro (16x14): diadema negra y dos almohadillas grises."""
    a = Image.new('RGBA', (18, 14))
    d = ImageDraw.Draw(a)
    d.arc((2, 0, 15, 12), 180, 360, fill=(24, 24, 28, 255), width=2)
    d.rectangle((0, 5, 3, 11), fill=(56, 56, 64, 255), outline=(16, 16, 20, 255))
    d.rectangle((14, 5, 17, 11), fill=(56, 56, 64, 255), outline=(16, 16, 20, 255))
    d.line((15, 11, 11, 13), fill=(24, 24, 28, 255))                 # micro
    return a


MON_TOKENS = monitor(pantalla_tokens())
MON_JUEGO = monitor(pantalla_juego())

esc.hacer(esc.fundido(entrada=True, frames=10))
# ---------------------------------------------------------------- 7:02 sin tokens
esc.hacer(esc.hasta(422.4))
esc.hacer(esc.mostrar('pc', MON_TOKENS, x=6, y=10, efecto='zoom', frames=8), esc.sonido('SEQ_SE_DP_BOX03', 0.4))
esc.hacer(chini.emocion('!', 24), chini.saltar(4, 8))
esc.hacer(esc.hasta(424.8))
esc.hacer(chini.mirar('abajo'))
esc.hacer(esc.hasta(427.1))
esc.hacer(chini.temblar(14, 1))                                   # «la puta IA no me deja cocinar»
esc.hacer(esc.hasta(429.9))

# ---------------------------------------------------------------- 7:10 se pone los cascos y juega
esc.hacer(chini.mirar('arriba'))
esc.hacer(chini.llevar(cascos(), dy=4), esc.sonido('SEQ_SE_DP_BOX01', 0.3))
esc.hacer(esc.cambiar_capa('pc', MON_JUEGO), esc.sonido('SEQ_SE_DP_PINPON', 0.3))
esc.hacer(esc.hasta(434.0))
esc.hacer(chini.mirar('abajo'))
esc.hacer(esc.hasta(437.3))
esc.hacer(chini.saltar(3, 8))                                     # «mañana le meto duro a la obra»
esc.hacer(esc.hasta(439.5))
esc.hacer(chini.mirar('arriba'))
esc.hacer(esc.hasta(442.9))
esc.hacer(esc.ocultar('pc', 8), chini.mirar('abajo'))
esc.hacer(esc.hasta(444.1))
esc.hacer(chini.saltar(4, 8))
esc.hacer(esc.hasta(446.0))
esc.hacer(esc.fundido(entrada=False, frames=12))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't9_ordenador', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
