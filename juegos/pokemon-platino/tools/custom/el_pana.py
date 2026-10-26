"""Genera los sprites custom de EL PANA (estilo Pokémon Platino) a partir de sprites base del juego.
Es el ejemplo de referencia para la skill /personaje; las utilidades están en comun.py.

  python tools/custom/el_pana.py   ->  sprites_custom/el_pana/

Rasgos (fotos en buzon/el_pana): pelo castaño oscuro revuelto, gafas de pasta, barba y bigote,
camiseta verde. El mapa parte del ayudante de laboratorio (gafas y pelo revuelto); se recolorea y se
le dibuja la barba.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import (CUSTOM, DIRS, es_borde, espalda_base, frames_mapa, frente_base, guardar_combate,  # noqa
                   guardar_mapa, pon, recolorear, revision, vista)

NOMBRE = 'el_pana'
BASE_MAPA = '027'               # ayudante de laboratorio: gafas y pelo revuelto

PELO = {(49, 49, 57): (41, 27, 21), (74, 82, 90): (70, 46, 33), (106, 115, 139): (106, 70, 49)}
CAMISETA = {(238, 238, 255): (131, 222, 98), (189, 189, 222): (82, 180, 74), (156, 156, 164): (82, 180, 74),
            (131, 131, 148): (57, 131, 57), (74, 82, 90): (41, 98, 49)}
PANTALON = {(238, 238, 255): (90, 98, 123), (189, 189, 222): (65, 74, 98), (156, 156, 164): (49, 57, 74),
            (131, 131, 148): (49, 57, 74), (74, 82, 90): (41, 41, 57)}
ZAPAS = {(65, 148, 82): (106, 74, 57), (65, 106, 65): (74, 49, 41)}
PIEL = {(255, 213, 189), (222, 164, 123)}
BARBA = ((74, 49, 41), (106, 74, 57))   # oscuro (contorno de la mandíbula), claro


def frame_mapa(px, direccion):
    cuello = 21                       # filas < cuello: cabeza
    piernas = 26 if direccion in ('arriba', 'abajo') else 25
    orig = px.copy()
    # barba: en cada columna de la cara, los 2 píxeles de piel más bajos de la cabeza
    if direccion != 'arriba':
        for x in range(32):
            ys = [y for y in range(12, cuello) if tuple(orig[y, x, :3]) in PIEL and orig[y, x, 3]]
            if not ys or len(ys) < 3:
                continue
            ys = [y for y in ys if y >= 17]
            for k, y in enumerate(sorted(ys, reverse=True)[:2]):
                px[y, x, :3] = BARBA[0] if k == 0 else BARBA[1]
    recolorear(px, PELO, 0, cuello)
    recolorear(px, CAMISETA, cuello, piernas)
    recolorear(px, PANTALON, piernas, 32)
    recolorear(px, ZAPAS, 0, 32)
    return px


def mapa():
    frames = [frame_mapa(px, DIRS[i]) for i, px in enumerate(frames_mapa(BASE_MAPA))]
    return guardar_mapa(NOMBRE, frames, '027_assistantm', 'EL PANA')


# ====================================================================== combate

GAFAS = (41, 33, 41)
CRISTAL = (189, 205, 222)
BARBA_M = (106, 74, 57)
BARBA_O = (74, 49, 41)
LABIO = (172, 98, 90)
PELO_O, PELO_M, PELO_C = (41, 27, 21), (70, 46, 33), (106, 70, 49)
VERDE_C, VERDE_M, VERDE_O, VERDE_OO = (131, 222, 98), (82, 180, 74), (57, 131, 57), (41, 98, 49)
VAQ_C, VAQ_M, VAQ_O = (90, 98, 123), (65, 74, 98), (49, 57, 82)


def _caja(px, x0, y0, x1, y1, tabla):
    recolorear(px, tabla, y0, y1, x0, x1)


_pon = pon


def frente():
    """Sprite frontal (80x80) a partir del Entrenador Guay (024)."""
    px = frente_base('024')
    # pelo verde -> castaño oscuro
    _caja(px, 0, 0, 80, 23, {(98, 148, 82): PELO_C, (65, 106, 74): PELO_M, (49, 65, 57): PELO_O})
    # gafas de pasta (3/4 mirando a la derecha)
    for x in list(range(34, 38)) + list(range(39, 43)):
        _pon(px, [(x, 16)], GAFAS)
    _pon(px, [(34, 17), (37, 17), (38, 17), (39, 17), (42, 17), (43, 16), (33, 16), (34, 18), (37, 18),
              (39, 18), (42, 18)], GAFAS)
    _pon(px, [(35, 18), (36, 18), (40, 18), (41, 18)], (255, 213, 189))
    _pon(px, [(35, 17), (40, 17)], CRISTAL)
    _pon(px, [(36, 17), (41, 17)], (0, 0, 0))            # pupilas
    # patillas y barba
    _pon(px, [(33, 17), (33, 18), (34, 19), (44, 17), (44, 18), (45, 18)], PELO_O)
    for y in range(20, 24):
        for x in range(30, 48):
            if y == 20 and 35 <= x <= 42:
                continue                                  # mejillas a la vista
            if tuple(px[y, x, :3]) in ((255, 213, 189), (222, 164, 123), (189, 123, 98), (139, 82, 82)) and px[y, x, 3]:
                borde = any(px[y + dy, x + dx, 3] == 0 or tuple(px[y + dy, x + dx, :3]) == (0, 0, 0)
                            for dx, dy in ((-1, 0), (1, 0), (0, 1)))
                px[y, x, :3] = BARBA_O if borde or y >= 23 else BARBA_M
    _pon(px, [(37, 20), (38, 20), (39, 20), (40, 20), (41, 20)], BARBA_O)   # bigote
    _pon(px, [(38, 21), (39, 21), (40, 21)], LABIO)                          # boca
    # ropa: camiseta verde de manga larga, vaqueros oscuros, zapatillas marrones
    _caja(px, 0, 23, 80, 46, {(98, 74, 65): VERDE_M, (65, 49, 65): VERDE_O, (139, 82, 82): VERDE_C,
                              (123, 74, 90): VERDE_OO})
    _caja(px, 34, 23, 49, 46, {(205, 123, 90): VERDE_C})
    _caja(px, 0, 42, 80, 47, {(98, 148, 82): (57, 49, 49), (65, 106, 74): (41, 33, 33), (49, 65, 57): (33, 25, 25)})
    _caja(px, 22, 44, 32, 52, {(98, 74, 65): (222, 164, 123), (65, 49, 65): (189, 123, 98),
                               (123, 74, 90): (139, 82, 82)})       # mano izquierda sin guante
    _caja(px, 0, 46, 80, 67, {(98, 74, 65): VAQ_C, (65, 49, 65): VAQ_M, (123, 74, 90): VAQ_O})
    _caja(px, 0, 65, 80, 80, {(98, 148, 82): (139, 98, 74), (65, 106, 74): (106, 74, 57), (49, 65, 57): (74, 49, 41),
                              (98, 74, 65): VAQ_C, (65, 49, 65): VAQ_M})
    return px


def espalda():
    """Sprite de espalda (2 poses de 80x80) a partir del de Israel/Barry."""
    px = espalda_base('02')
    for ox, oy in ((0, 0), (74, 3)):
        # gafas vistas de lado: cristal delante del ojo y patilla hasta la oreja
        _pon(px, [(43 + ox, y + oy) for y in range(27, 32)], GAFAS)
        _pon(px, [(x + ox, 27 + oy) for x in range(40, 44)], GAFAS)
        _pon(px, [(x + ox, 31 + oy) for x in range(40, 44)], GAFAS)
        _pon(px, [(x + ox, 29 + oy) for x in range(34, 40)], GAFAS)
        # patilla del pelo y barba en mejilla y mandíbula
        _pon(px, [(x + ox, y + oy) for x in range(33, 37) for y in range(30, 34)], PELO_M)
        for y in range(35, 40):
            for x in range(30, 48):
                X, Y = x + ox, y + oy
                if tuple(px[Y, X, :3]) in ((222, 164, 123), (255, 213, 189)) and px[Y, X, 3]:
                    borde = any(px[Y + dy, X + dx, 3] == 0 or tuple(px[Y + dy, X + dx, :3]) == (0, 0, 0)
                                for dx, dy in ((1, 0), (0, 1), (1, 1)))
                    px[Y, X, :3] = BARBA_O if borde else BARBA_M
        _pon(px, [(44 + ox, 34 + oy), (45 + ox, 34 + oy)], BARBA_O)   # bigote asomando
    # pelo rubio -> castaño (solo en la cabeza)
    _caja(px, 0, 0, 160, 42, {(255, 222, 123): PELO_C, (197, 164, 115): PELO_M})
    # camiseta naranja a rayas -> verde
    _caja(px, 0, 40, 160, 80, {(255, 148, 74): VERDE_C, (238, 238, 255): VERDE_C, (197, 115, 57): VERDE_M,
                               (205, 205, 222): VERDE_M, (172, 164, 205): VERDE_O, (197, 164, 115): VERDE_O})
    return px


def combate():
    guardar_combate(NOMBRE, frente(), espalda())


if __name__ == '__main__':
    mapa()
    combate()
    print(vista(NOMBRE))
    print(revision(NOMBRE, BASE_MAPA))
