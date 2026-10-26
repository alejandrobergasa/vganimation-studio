"""Genera los sprites custom de SANTOS (estilo Pokémon Platino) a partir de sprites base del juego.
Plantilla y utilidades: el_pana.py y comun.py.

  python tools/custom/santos.py   ->  sprites_custom/santos/

Rasgos (fotos en buzon/santos): chico joven y deportista, pelo castaño corto con la frente despejada, barba
de pocos días y chándal azul marino. Bases: man1 (mapa: joven y delgado; se le despeja la frente a mano),
el entrenador guay 053 (frente: su mono con cuello pasa a chándal y se le quita el flequillo) e Israel
(espalda, con el tupé recortado).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import DIRS, es_borde, espalda_base, frames_mapa, frente_base, guardar_combate, guardar_mapa,     pon, recolorear, revision, vista  # noqa

NOMBRE = 'santos'
BASE_MAPA = '008'               # man1: joven, delgado y con ojos normales

PELO_C, PELO_M, PELO_O, PELO_OO = (150, 104, 68), (115, 78, 50), (80, 54, 37), (52, 36, 30)
CHANDAL_C, CHANDAL_M, CHANDAL_O, CHANDAL_OO = (82, 108, 178), (58, 80, 146), (40, 56, 108), (28, 36, 72)
BLANCO, BLANCO_S = (236, 240, 248), (184, 192, 212)
BARBA = ((150, 106, 84), (196, 150, 122))   # oscuro (borde de la mandíbula), claro

PELO = {(213, 164, 115): PELO_C, (164, 123, 82): PELO_M, (98, 74, 65): PELO_O}
CHAQUETA = {(230, 222, 189): CHANDAL_C, (172, 164, 131): CHANDAL_M, (98, 74, 65): CHANDAL_O}
PANTALON = {(230, 222, 189): CHANDAL_C, (172, 164, 131): CHANDAL_M, (65, 139, 189): CHANDAL_M, (74, 90, 131): CHANDAL_O, (57, 57, 82): CHANDAL_OO,
            (164, 123, 82): BLANCO, (98, 74, 65): BLANCO_S}          # zapatillas blancas
PIEL = {(255, 213, 189), (222, 156, 115)}
S, R = (255, 213, 189), (123, 65, 65)                 # piel y contorno de piel del juego


def _ojos(px):
    """Fila de los ojos (la del blanco del ojo) o None si mira arriba."""
    ys = [y for y in range(10, 22) for x in range(32) if px[y, x, 3] and tuple(px[y, x, :3]) == (238, 238, 255)]
    return ys[0] if ys else None


def _frente(px, direccion):
    """Despeja la frente: la base lleva el pelo en casco hasta las cejas."""
    ey = _ojos(px)
    if ey is None:
        return
    if direccion == 'abajo':
        pon(px, [(x, ey - 3) for x in range(10, 21)], S)
        pon(px, [(10, ey - 2), (11, ey - 2), (19, ey - 2), (20, ey - 2)], S)
        pon(px, [(12, ey - 2), (18, ey - 2)], PELO_OO)                     # cejas
        pon(px, [(10, ey - 4), (11, ey - 4), (19, ey - 4), (20, ey - 4)], S)  # entradas
        return
    m = (lambda x: x) if direccion == 'izquierda' else (lambda x: 31 - x)
    pon(px, [(m(10), ey - 3), (m(10), ey - 2)], R)
    pon(px, [(m(x), ey - 3) for x in (11, 12, 13)] + [(m(14), ey - 2)], S)
    pon(px, [(m(13), ey - 2)], PELO_OO)                                     # ceja
    pon(px, [(m(10), ey - 4)], R)                                           # entrada
    pon(px, [(m(11), ey - 4), (m(12), ey - 4)], S)


def frame_mapa(px, direccion):
    cuello = 21
    piernas = 25
    _frente(px, direccion)
    orig = px.copy()
    # barba de pocos días: en cada columna de la cara, los 2 píxeles de piel más bajos de la cabeza
    if direccion != 'arriba':
        for x in range(32):
            ys = [y for y in range(12, cuello) if tuple(orig[y, x, :3]) in PIEL and orig[y, x, 3]]
            if len(ys) < 3:
                continue
            ys = [y for y in ys if y >= 17]
            for k, y in enumerate(sorted(ys, reverse=True)[:2]):
                px[y, x, :3] = BARBA[k]
    recolorear(px, PELO, 0, cuello)
    recolorear(px, {(230, 222, 189): CHANDAL_C, (172, 164, 131): CHANDAL_M}, 17, cuello)   # hombros al andar
    recolorear(px, CHAQUETA, cuello, piernas)
    recolorear(px, PANTALON, piernas, 32)
    if direccion == 'abajo':                       # cremallera
        for y in range(cuello, piernas + 1):
            if tuple(px[y, 15, :3]) in (CHANDAL_C, CHANDAL_M, CHANDAL_O):
                px[y, 15, :3] = BLANCO
    return px


def mapa():
    frames = [frame_mapa(px, DIRS[i]) for i, px in enumerate(frames_mapa(BASE_MAPA))]
    return guardar_mapa(NOMBRE, frames, '008_man1', 'SANTOS')


# ====================================================================== combate

PIEL_C, PIEL_M, PIEL_O = (255, 213, 189), (222, 164, 123), (189, 123, 98)


def _caja(px, x0, y0, x1, y1, tabla):
    recolorear(px, tabla, y0, y1, x0, x1)


BARBA_F = ((176, 128, 104), (218, 172, 142))      # en combate, más suave: a 80x80 se ve más


def frente():
    """Sprite frontal (80x80) a partir del entrenador guay 053."""
    px = frente_base('053')
    # sin flequillo: frente despejada bajo una línea de pelo recta (fila 14)
    for y in (15, 16):
        for x in range(32, 41):
            px[y, x] = (*PIEL_C, 255)
    for y in range(9, 15):                  # las mechas negras de dentro del pelo pasan a castaño oscuro
        for x in range(30, 44):
            if tuple(px[y, x, :3]) == (0, 0, 0) and not es_borde(px, x, y, ((-1, 0), (1, 0), (0, -1))):
                px[y, x, :3] = (49, 41, 49)
    pon(px, [(x, 14) for x in range(34, 39)], (65, 74, 82))
    pon(px, [(32, 14), (33, 14), (39, 14)], PIEL_C)                      # entradas
    pon(px, [(32, 15), (40, 15)], PIEL_M)
    # pelo gris oscuro -> castaño
    _caja(px, 0, 0, 80, 24, {(90, 123, 115): PELO_C, (65, 74, 82): PELO_M, (49, 41, 49): PELO_O})
    # guantes -> manos
    for caja in ((18, 39, 28, 49), (28, 42, 30, 45), (50, 36, 64, 46)):
        _caja(px, *caja, {(230, 222, 189): PIEL_C, (180, 172, 131): PIEL_M, (82, 74, 65): PIEL_O})
    # mono naranja con cuello beige -> chaqueta de chándal con cuello blanco
    _caja(px, 25, 20, 80, 46, {(255, 98, 57): BLANCO, (238, 238, 255): BLANCO})
    _caja(px, 0, 20, 80, 28, {(230, 222, 189): BLANCO, (180, 172, 131): BLANCO_S})        # cuello blanco
    _caja(px, 0, 20, 80, 46, {(230, 139, 65): CHANDAL_C, (172, 106, 65): CHANDAL_M, (82, 74, 65): CHANDAL_OO,
                              (230, 222, 189): CHANDAL_C, (180, 172, 131): CHANDAL_M})
    # pantalón naranja, rodilleras y caña de las botas -> pantalón de chándal; pie -> zapatillas blancas
    _caja(px, 0, 44, 80, 73, {(230, 139, 65): CHANDAL_C, (172, 106, 65): CHANDAL_M, (82, 74, 65): CHANDAL_O,
                              (230, 222, 189): CHANDAL_C, (180, 172, 131): CHANDAL_M,
                              (65, 74, 82): CHANDAL_M, (49, 41, 49): CHANDAL_O})
    _caja(px, 0, 73, 80, 80, {(65, 74, 82): BLANCO, (49, 41, 49): BLANCO_S, (90, 123, 115): BLANCO_S})
    _caja(px, 30, 41, 50, 46, {(49, 41, 49): CHANDAL_OO, (65, 74, 82): CHANDAL_O, (90, 123, 115): CHANDAL_M})  # sin cinturón
    # raya blanca por el lado de fuera de cada pernera
    for y in range(48, 73):
        fila = [x for x in range(80) if px[y, x, 3] and tuple(px[y, x, :3]) != (0, 0, 0)]
        if fila:
            izq = [x for x in fila if x < 38]
            der = [x for x in fila if x >= 38]
            if izq:
                px[y, min(izq), :3] = BLANCO
            if der:
                px[y, max(der), :3] = BLANCO_S
    # barba de pocos días en la mandíbula
    for y in range(20, 27):
        for x in range(26, 48):
            if tuple(px[y, x, :3]) in (PIEL_C, PIEL_M, PIEL_O) and px[y, x, 3] and y >= 23:
                px[y, x, :3] = BARBA_F[0] if es_borde(px, x, y) else BARBA_F[1]
    return px


def _pelo_corto(px):
    """Recorta el tupé de Israel a una cabeza redonda de pelo corto, en las dos poses."""
    pelo = {(255, 222, 123), (197, 164, 115), (123, 65, 65), (0, 0, 0)}
    for ox, oy in ((0, 0), (74, 3)):
        cx, cy, r = 35 + ox, 25 + oy, 15
        caja = [(x, y) for y in range(5 + oy, 39 + oy) for x in range(10 + ox, 39 + ox)]
        for x, y in caja:
            if tuple(px[y, x, :3]) not in pelo or not px[y, x, 3]:
                continue
            d = ((x - cx) / r) ** 2 + ((y - cy) / r) ** 2
            nuca = y - oy >= 27 + (x - ox - 20) * 0.6 and x < 32 + ox    # nuca corta y en diagonal
            if d > 1 or nuca:
                px[y, x] = 0
            elif d > 0.6 and x < cx and y > cy - 6 and tuple(px[y, x, :3]) == (255, 222, 123):
                px[y, x, :3] = (197, 164, 115)                             # sombra en la parte de atrás
        alfa = px[..., 3].copy()
        for x, y in caja:                                   # contorno nuevo
            if alfa[y, x] and tuple(px[y, x, :3]) in ((255, 222, 123), (197, 164, 115)) and                     any(alfa[y + dy, x + dx] == 0 for dx, dy in ((-1, 0), (0, -1), (0, 1))):
                px[y, x, :3] = (0, 0, 0)


def espalda():
    """Sprite de espalda (2 poses de 80x80) a partir del de Israel/Barry."""
    px = espalda_base('02')
    _pelo_corto(px)
    for ox, oy in ((0, 0), (74, 3)):
        # barba de pocos días en mejilla y mandíbula
        for y in range(36, 40):
            for x in range(30, 48):
                X, Y = x + ox, y + oy
                if tuple(px[Y, X, :3]) in ((222, 164, 123), (255, 213, 189)) and px[Y, X, 3]:
                    px[Y, X, :3] = BARBA[0] if es_borde(px, X, Y, ((1, 0), (0, 1), (1, 1))) else BARBA[1]
    # pelo rubio -> castaño (solo en la cabeza)
    _caja(px, 0, 0, 160, 42, {(255, 222, 123): PELO_M, (197, 164, 115): PELO_O})
    # camiseta naranja a rayas -> chaqueta de chándal
    _caja(px, 0, 40, 160, 80, {(139, 189, 106): BLANCO, (255, 148, 74): CHANDAL_C, (238, 238, 255): CHANDAL_C,
                               (197, 115, 57): CHANDAL_M, (205, 205, 222): CHANDAL_M, (172, 164, 205): CHANDAL_O})
    _caja(px, 0, 70, 160, 80, {(131, 148, 156): CHANDAL_M, (82, 90, 106): CHANDAL_O})     # pantalón
    return px


def combate():
    guardar_combate(NOMBRE, frente(), espalda())


if __name__ == '__main__':
    mapa()
    combate()
    print(vista(NOMBRE))
    print(revision(NOMBRE, BASE_MAPA))
