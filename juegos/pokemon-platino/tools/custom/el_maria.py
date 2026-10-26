"""Genera los sprites custom de EL MARÍA (protagonista de REWINDLIMBO2) en estilo Pokémon Platino.
Plantilla y utilidades: el_pana.py, santos.py y comun.py.

  python tools/custom/el_maria.py   ->  sprites_custom/el_maria/, el_maria_sombrero/, el_maria_sudadera/

Rasgos (fotogramas del vídeo en buzon/analisis_parte_1): hombre joven de pelo oscuro corto, pantalón de
chándal negro con rayas blancas. Tres vestuarios:
  el_maria            camiseta negra, sin sombrero (base man1, 008)
  el_maria_sombrero   camiseta negra y sombrero beige de ala ancha con cinta violeta (base explorador, 048)
  el_maria_sudadera   sudadera gris y el mismo sombrero (base explorador, 048)
Frames extra (16-18) de los que llevan sombrero, para posar(): 16 agachado (abajo), 17 sentado (abajo),
18 agachado (de espaldas). Para levantar algo sobre la cabeza se usa llevar() del motor.
el_maria_sombrero además: 19 con la pipa en la boca, 20 con el mapa abierto, 21 agachado con la pipa.
el_maria (sin sombrero): 16 con el sombrero en las manos, a punto de ponérselo.
Combate (frente): el ruinamaníaco (048), agachado y con un papel en la mano (el mapa).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import (DIRS, CUSTOM, es_borde, frames_mapa, frente_base, guardar_combate, guardar_mapa, pon,  # noqa
                   recolorear, revision, vista)
from PIL import Image

PELO = ((92, 78, 74), (60, 50, 50), (40, 34, 36))           # claro, medio, oscuro (casi negro)
NEGRA = ((78, 78, 90), (56, 56, 66), (38, 38, 46))          # camiseta negra (con algo de luz para leerse)
GRIS = ((200, 204, 212), (156, 160, 172), (112, 116, 130))   # sudadera gris
PANT = ((70, 70, 80), (48, 48, 56), (32, 32, 40))           # pantalón de chándal negro
BLANCO, BLANCO_S = (236, 240, 248), (184, 192, 212)
VIOLETA = ((150, 112, 196), (112, 80, 160))                 # cinta del sombrero
BEIGE = ((214, 200, 156), (168, 152, 112), (118, 104, 80))  # sombrero (algo más claro que el del explorador)


def _tabla(orig, nuevo):
    return {o: n for o, n in zip(orig, nuevo)}


# ====================================================================== sin sombrero (man1)

def frame_sin_sombrero(px, direccion):
    cuello, piernas = 21, 25
    recolorear(px, {(213, 164, 115): PELO[0], (164, 123, 82): PELO[1], (98, 74, 65): PELO[2]}, 0, cuello)
    recolorear(px, {(230, 222, 189): NEGRA[0], (172, 164, 131): NEGRA[1]}, 17, cuello)   # hombros al andar
    recolorear(px, {(230, 222, 189): NEGRA[0], (172, 164, 131): NEGRA[1], (98, 74, 65): NEGRA[2],
                    (74, 90, 131): PANT[1], (65, 139, 189): PANT[0], (57, 57, 82): PANT[2]}, cuello, piernas)
    recolorear(px, {(74, 90, 131): PANT[1], (65, 139, 189): PANT[0], (57, 57, 82): PANT[2],
                    (164, 123, 82): BLANCO, (98, 74, 65): BLANCO_S}, piernas, 32)
    _rayas(px, piernas, 30, direccion)
    return px


def _rayas(px, y0, y1, direccion):
    """Raya blanca por fuera de cada pernera (en los laterales, solo la del lado que se ve)."""
    pant = set(PANT)
    for y in range(y0, y1):
        xs = [x for x in range(32) if px[y, x, 3] and tuple(px[y, x, :3]) in pant]
        if not xs:
            continue
        if direccion in ('abajo', 'arriba'):
            pon(px, [(min(xs), y)], BLANCO)
            pon(px, [(max(xs), y)], BLANCO_S)
        elif direccion == 'izquierda':
            pon(px, [(min(xs) + 1, y)], BLANCO)
        else:
            pon(px, [(max(xs) - 1, y)], BLANCO)


# ====================================================================== con sombrero (explorador)

def _cinta(px):
    """La franja oscura del sombrero del explorador pasa a cinta violeta."""
    oscuro = (65, 49, 41)
    for y in range(8, 16):
        fila = [x for x in range(32) if px[y, x, 3] and tuple(px[y, x, :3]) != (0, 0, 0)]
        if len(fila) < 6:
            continue
        osc = [x for x in fila if tuple(px[y, x, :3]) == oscuro]
        if len(osc) >= 0.6 * len(fila):
            for x in osc:
                px[y, x, :3] = VIOLETA[0] if y % 2 == 0 or not es_borde(px, x, y) else VIOLETA[1]


def frame_sombrero(px, direccion, ropa):
    ojos = [y for y in range(10, 22) for x in range(32) if px[y, x, 3] and tuple(px[y, x, :3]) == (238, 238, 255)]
    ala = (ojos[0] - 1) if ojos else 16          # por encima de los ojos: sombrero
    cuello, piernas = 21, 26
    _cinta(px)
    recolorear(px, {(189, 172, 131): BEIGE[0], (131, 115, 90): BEIGE[1]}, 0, ala)
    recolorear(px, {(65, 49, 41): PELO[2], (189, 172, 131): BEIGE[0], (131, 115, 90): BEIGE[1]}, ala, cuello)
    # de espaldas, la mochila del explorador pasa a ser la espalda de la prenda
    torso = {(189, 172, 131): ropa[0], (131, 115, 90): ropa[1], (65, 49, 41): ropa[2], (82, 131, 106): ropa[1],
             (98, 180, 139): ropa[0], (65, 74, 74): ropa[2], (238, 238, 255): ropa[0], (106, 98, 98): ropa[2]}
    recolorear(px, torso, cuello - (3 if direccion == 'arriba' else 0), piernas)
    recolorear(px, {(189, 172, 131): PANT[0], (131, 115, 90): PANT[1], (65, 49, 41): PANT[2],
                    (82, 131, 106): PANT[1], (98, 180, 139): PANT[0], (65, 74, 74): PANT[2]}, piernas, 32)
    _rayas(px, piernas + 1, 30, direccion)
    return px


def _agachado(px, bajar=5):
    """Pose agachada: el cuerpo baja 'bajar' píxeles y se pierden las piernas (en cuclillas)."""
    out = np.zeros_like(px)
    out[bajar:32] = px[0:32 - bajar]
    # recorta por abajo y cierra con contorno
    out[30:] = 0
    for x in range(32):
        if out[29, x, 3]:
            out[29, x, :3] = (0, 0, 0)
    return out


def _sentado(px):
    """Sentado en un banco, de frente: baja 3 px y las piernas se acortan (rodillas hacia delante)."""
    out = np.zeros_like(px)
    out[3:28] = px[0:25]
    out[28:31] = px[28:31]
    for x in range(32):
        if out[27, x, 3] and not out[28, x, 3]:
            out[27, x, :3] = (0, 0, 0)
    return out


# ====================================================================== poses con objetos (v3 del tramo 1)
# Sobre el frame de frente (4). Los brazos del explorador cuelgan en x 7-9 y 21-23, filas 22-25.

NEGRO_C = (0, 0, 0)
PIPA = ((178, 112, 64), (138, 82, 46), (96, 56, 32), (64, 40, 30))
PIEL_C = ((255, 213, 189), (222, 156, 115))
PAPEL_C = ((246, 246, 236), (206, 206, 196))


def _px(px, pts, color):
    for x, y in pts:
        px[y, x] = (*color, 255)


def _sin_brazo(px, lado):
    """Quita el brazo que cuelga a un lado (para dibujarlo haciendo otra cosa) y cierra el contorno del torso."""
    xs = range(6, 10) if lado == 'izq' else range(22, 26)
    borde = 9 if lado == 'izq' else 22
    for y in range(22, 26):
        for x in xs:
            px[y, x] = 0
        if px[y, borde + (1 if lado == 'izq' else -1), 3]:
            _px(px, [(borde, y)], NEGRO_C)
    return px


def _con_pipa(px):
    """De frente con la pipa en la boca, sujeta por la cazoleta con la mano derecha (a la izquierda en pantalla)."""
    px = _sin_brazo(px.copy(), 'izq')
    _px(px, [(x, y) for x in range(10, 14) for y in range(21, 25) if x in (10, 13) or y in (21, 24)], NEGRO_C)
    _px(px, [(11, 22)], PIPA[3])                                           # boca de la cazoleta
    _px(px, [(12, 22)], PIPA[1])
    _px(px, [(11, 23)], PIPA[0])
    _px(px, [(12, 23)], PIPA[2])
    _px(px, [(14, 21)], PIPA[2])                                           # caña
    _px(px, [(15, 20)], NEGRO_C)                                           # boquilla en la boca
    _px(px, [(10, 25), (11, 25), (12, 25)], PIEL_C[0])                     # mano por debajo
    _px(px, [(12, 25)], PIEL_C[1])
    _px(px, [(9, 25), (9, 24), (10, 26), (11, 26), (12, 26), (13, 25)], NEGRO_C)
    _px(px, [(9, 23)], NEGRA[1])                                           # manga
    _px(px, [(8, 23), (8, 24), (9, 22)], NEGRO_C)
    return px


def _con_mapa(px):
    """De frente sujetando el mapa abierto delante del pecho con las dos manos."""
    px = _sin_brazo(_sin_brazo(px.copy(), 'izq'), 'der')
    _px(px, [(x, y) for x in range(9, 23) for y in range(20, 27) if x in (9, 22) or y in (20, 26)], NEGRO_C)
    _px(px, [(x, y) for x in range(10, 22) for y in range(21, 26)], PAPEL_C[0])
    _px(px, [(16, y) for y in range(21, 26)] + [(x, 25) for x in range(10, 22)], PAPEL_C[1])
    _px(px, [(11, 24), (12, 23), (13, 23), (14, 22), (17, 22), (18, 23)], (64, 88, 208))   # caminos
    _px(px, [(20, 22)], (216, 40, 40))                                                      # la X
    _px(px, [(9, 22), (9, 23), (22, 22), (22, 23)], PIEL_C[0])                              # manos
    _px(px, [(8, 22), (8, 23), (23, 22), (23, 23), (9, 21), (22, 21), (9, 24), (22, 24)], NEGRO_C)
    return px


def _sombrero_en_mano(px, sombrero):
    """Sin sombrero, con el sombrero cogido con las dos manos delante del pecho (a punto de ponérselo)."""
    px = _sin_brazo(_sin_brazo(px.copy(), 'izq'), 'der')
    copa = sombrero[6:15].copy()
    hueco = copa[..., 3] > 0
    px[20:29][hueco] = copa[hueco]
    _px(px, [(7, 25), (7, 26), (24, 25), (24, 26)], PIEL_C[0])                              # manos en el ala
    _px(px, [(6, 25), (6, 26), (25, 25), (25, 26), (7, 24), (24, 24), (7, 27), (24, 27)], NEGRO_C)
    return px


def mapa():
    sin = [frame_sin_sombrero(px, DIRS[i]) for i, px in enumerate(frames_mapa('008'))]
    for nombre, ropa in (('el_maria_sombrero', NEGRA), ('el_maria_sudadera', GRIS)):
        fr = [frame_sombrero(px, DIRS[i], ropa) for i, px in enumerate(frames_mapa('048'))]
        extra = [_agachado(fr[4]), _sentado(fr[4]), _agachado(fr[0])]
        if nombre == 'el_maria_sombrero':        # 19 pipa en la boca, 20 con el mapa, 21 agachado con la pipa
            extra += [_con_pipa(fr[4]), _con_mapa(fr[4]), _agachado(_con_pipa(fr[4]))]
            sombrero = fr[4]
        guardar_mapa(nombre, fr + extra, '048_explore', 'EL MARÍA')
    guardar_mapa('el_maria', sin + [_sombrero_en_mano(sin[4], sombrero)], '008_man1', 'EL MARÍA')   # 16


# ====================================================================== combate

def frente():
    """Ruinamaníaco agachado con el mapa en la mano: sombrero con cinta violeta y sudadera gris."""
    px = frente_base('048')
    return px


def combate():
    guardar_combate('el_maria_sudadera', frente())


if __name__ == '__main__':
    mapa()
    for n in ('el_maria', 'el_maria_sombrero', 'el_maria_sudadera'):
        print(vista(n))
    print(revision('el_maria_sudadera', '048'))
