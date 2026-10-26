"""FORMIGAL: cuatro amigos de los vídeos casaformigal y fiestaformigal (solo sprites del mapa).
  chini_verde  CHINI en casa: camiseta verde oliva, pantalón claro (base 066 man5)
  maria_gris   EL MARÍA en casa: sudadera gris (base 008 man1)
  chini_gafas  CHINI en la fiesta: gorro negro, gafas de sol, braga roja y plumas negro (base 147)
  maria_rojo   EL MARÍA en la fiesta: chaqueta roja con capucha gris (base 008)

  python tools/custom/formigal.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import frames_mapa, guardar_mapa, recolorear, pon, vista  # noqa

# ---- 066 (man5): torso naranja (230,139,65)/(164,98,65), camiseta beige (230,222,189)/(172,164,131)
PELO_CLARO = {(106, 139, 131): (136, 96, 64), (74, 90, 98): (96, 64, 44), (57, 57, 65): (60, 40, 32)}
VERDE = {(230, 139, 65): (112, 128, 64), (164, 98, 65): (72, 88, 44),
         (230, 222, 189): (112, 128, 64), (172, 164, 131): (72, 88, 44)}
PANT_CLARO = {(74, 90, 98): (196, 184, 152), (57, 57, 65): (150, 138, 112), (106, 139, 131): (196, 184, 152)}
ROJO = {(230, 139, 65): (226, 56, 72), (164, 98, 65): (160, 32, 48),
        (230, 222, 189): (226, 56, 72), (172, 164, 131): (160, 32, 48)}
CAPUCHA = {(106, 139, 131): (176, 176, 184), (74, 90, 98): (128, 128, 140), (57, 57, 65): (88, 88, 100)}
PANT_OSC = {(74, 90, 98): (52, 56, 76), (57, 57, 65): (36, 38, 54), (106, 139, 131): (52, 56, 76)}
# ---- 008 (man1): torso (230,222,189)/(172,164,131), pelo (164,123,82)/(98,74,65)
PELO_OSC8 = {(213, 164, 115): (92, 78, 74), (164, 123, 82): (60, 50, 50), (98, 74, 65): (40, 34, 36)}   # pelo de EL MARÍA
GRIS = {(230, 222, 189): (166, 168, 176), (172, 164, 131): (116, 118, 130), (74, 90, 131): (116, 118, 130)}
PANT8 = {(74, 90, 131): (44, 48, 72), (65, 139, 189): (44, 48, 72), (164, 123, 82): (44, 48, 72),
         (98, 74, 65): (30, 32, 50)}
# ---- 147 (sunglasses)
GORRO = {(156, 123, 74): (48, 50, 58), (98, 74, 57): (28, 28, 36)}
PLUMAS = {(180, 172, 106): (40, 44, 52), (238, 230, 172): (64, 68, 78), (189, 131, 180): (40, 44, 52),
          (139, 90, 131): (28, 30, 38), (106, 65, 98): (28, 30, 38), (156, 123, 74): (40, 44, 52),
          (98, 74, 57): (28, 30, 38)}
PANT147 = {(156, 123, 74): (30, 32, 44), (98, 74, 57): (20, 22, 32)}
BRAGA = (214, 48, 52)


def _066(pelo, torso, pant):
    out = []
    for px in frames_mapa('066'):
        recolorear(px, pelo, 0, 17)
        recolorear(px, torso, 17, 28)
        recolorear(px, pant, 24, 32)
        out.append(px)
    return out


ROJO8 = {(230, 222, 189): (226, 56, 72), (172, 164, 131): (160, 32, 48), (74, 90, 131): (160, 32, 48)}
CAPUCHA8 = {(213, 164, 115): (176, 176, 184), (164, 123, 82): (128, 128, 140), (98, 74, 65): (88, 88, 100)}


def _maria(rojo=False):
    out = []
    for px in frames_mapa('008'):
        recolorear(px, CAPUCHA8 if rojo else PELO_OSC8, 0, 17)
        recolorear(px, ROJO8 if rojo else GRIS, 17, 27)
        recolorear(px, PANT8, 26, 32)
        out.append(px)
    return out


def _gafas():
    out = []
    for i, px in enumerate(frames_mapa('147')):
        recolorear(px, GORRO, 0, 17)
        recolorear(px, PLUMAS, 17, 27)
        recolorear(px, PANT147, 26, 32)
        # braga roja: dos filas bajo la cara (de espaldas, tras el cuello)
        if i < 4:
            pon(px, [(x, 18) for x in range(12, 21)], BRAGA)
        elif i < 8:
            pon(px, [(x, 19) for x in range(12, 21)], BRAGA)
            pon(px, [(x, 20) for x in range(13, 20)], BRAGA)
        else:
            pon(px, [(x, 19) for x in range(13, 18)], BRAGA)
        out.append(px)
    return out


def main():
    guardar_mapa('chini_verde', _066(PELO_CLARO, VERDE, PANT_CLARO), 'man5', 'CHINI')
    guardar_mapa('maria_rojo', _maria(True), 'man1', 'EL MARIA')
    guardar_mapa('maria_gris', _maria(False), 'man1', 'EL MARIA')
    guardar_mapa('chini_gafas', _gafas(), 'sunglasses', 'CHINI')
    for n in ('chini_verde', 'maria_rojo', 'maria_gris', 'chini_gafas'):
        print(vista(n))


if __name__ == '__main__':
    main()
