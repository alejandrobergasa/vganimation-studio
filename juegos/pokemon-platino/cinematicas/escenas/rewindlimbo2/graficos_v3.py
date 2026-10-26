"""Gráficos nuevos de la v3 del tramo 1 (preparativos): el coche plateado del mapa, los primeros planos animados
(contacto, pipa, mechero, mapa) y las poses extra de EL MARÍA. Todo en pixel art propio con el estilo del juego
(ver dibujo.py). Vista previa: python escenas/rewindlimbo2/graficos_v3.py -> salida/_graficos_v3.png
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import humo as humo_juego, texto_img  # noqa
from dibujo import (CRISTAL, GRAVA, MADERA, N, NEGRO, PAPEL, PIEL, PLATA, ROJO, TABACO, Lienzo,  # noqa
                    contorno_exterior, rayas_chandal)

# ============================================================================ el coche (mapa)
# Utilitario plateado de tres puertas visto como los objetos del mapa del juego: el techo desde arriba y el
# costado izquierdo (el del conductor) de cara a la cámara, con el morro a la izquierda. 64x48; las ruedas
# apoyan en y = 40 y la puerta abierta sobresale hasta abajo.

W_COCHE, H_COCHE = 64, 48


def _coche_base(c, puerta=True):
    # ruedas (detrás de la carrocería)
    for cx in (15, 48):
        c.forma(lambda d, cx=cx: d.ellipse((cx - 6, 30, cx + 6, 41), fill=255), NEGRO[1:])
        c.forma(lambda d, cx=cx: d.ellipse((cx - 3, 33, cx + 3, 38), fill=255), PLATA[1:], contorno=NEGRO[3])
    # costado (chapa)
    c.forma(lambda d: d.polygon([(2, 26), (4, 22), (16, 20), (58, 19), (61, 22), (61, 33), (58, 36),
                                 (54, 36), (54, 33), (42, 33), (42, 36), (21, 36), (21, 33), (9, 33),
                                 (9, 36), (5, 36), (2, 33)], fill=255), PLATA)
    # capó, techo y portón vistos desde arriba (un tono más oscuros que el costado para separarlos)
    c.forma(lambda d: d.polygon([(3, 22), (5, 18), (12, 16), (18, 15), (24, 5), (28, 3), (52, 3), (56, 5),
                                 (61, 16), (61, 20), (16, 20), (4, 23)], fill=255), PLATA[1:], bandas=(0.45, 0.9))
    # lunas: parabrisas, techo, laterales y luneta
    c.forma(lambda d: d.polygon([(18, 15), (23, 6), (29, 6), (25, 14)], fill=255), CRISTAL)
    c.forma(lambda d: d.polygon([(25, 13), (29, 6), (50, 6), (51, 12)], fill=255), PLATA[:3], contorno=None,
            bandas=(0.5, 0.95))
    c.forma(lambda d: d.polygon([(20, 19), (25, 13), (54, 12), (57, 18)], fill=255), CRISTAL)
    c.plano(lambda d: d.line([(41, 13), (41, 18)], fill=255), PLATA[2])                  # pilar central
    c.forma(lambda d: d.polygon([(51, 6), (55, 6), (59, 13), (55, 13)], fill=255), CRISTAL[1:])
    # bandas de plástico gris oscuro (paragolpes y moldura lateral)
    c.plano(lambda d: d.line([(3, 30), (60, 30)], fill=255), NEGRO[1])
    c.plano(lambda d: d.line([(3, 31), (60, 31)], fill=255), NEGRO[2])
    c.plano(lambda d: d.rectangle((2, 27, 4, 31), fill=255), NEGRO[1])
    # faros y piloto
    c.forma(lambda d: d.polygon([(2, 23), (5, 21), (8, 21), (7, 25), (3, 25)], fill=255),
            ((255, 252, 220), (240, 224, 150), (196, 176, 96)))
    c.forma(lambda d: d.rectangle((59, 20, 61, 26), fill=255), ROJO[:3])
    # espejo
    c.forma(lambda d: d.rectangle((17, 16, 20, 19), fill=255), NEGRO[:3])
    if puerta:
        _puerta_cerrada(c)


def _puerta_cerrada(c):
    c.plano(lambda d: d.line([(22, 19), (22, 32)], fill=255), PLATA[3])
    c.plano(lambda d: d.line([(41, 18), (41, 32)], fill=255), PLATA[3])
    c.plano(lambda d: d.line([(37, 23), (39, 23)], fill=255), NEGRO[2])                # tirador


def coche(abierto=False):
    c = Lienzo(W_COCHE, H_COCHE)
    _coche_base(c, puerta=not abierto)
    if abierto:
        # hueco de la puerta: el asiento y el interior oscuro
        c.forma(lambda d: d.polygon([(22, 13), (41, 12), (41, 32), (22, 32)], fill=255), NEGRO, contorno=N)
        c.forma(lambda d: d.polygon([(30, 15), (37, 14), (38, 27), (31, 27)], fill=255),
                ((120, 120, 136), (96, 96, 112), (72, 72, 86)))                           # respaldo
        c.forma(lambda d: d.rectangle((27, 26, 40, 31), fill=255), ((108, 108, 124), (84, 84, 100), (64, 64, 78)))
        # la puerta abierta hacia la cámara, girando sobre la bisagra delantera
        c.forma(lambda d: d.polygon([(20, 14), (29, 22), (29, 46), (20, 37)], fill=255), PLATA)      # chapa
        c.forma(lambda d: d.polygon([(21, 15), (28, 22), (28, 29), (21, 23)], fill=255), CRISTAL[1:])  # ventanilla
        c.plano(lambda d: d.line([(21, 31), (28, 37)], fill=255), NEGRO[1])                           # moldura
        c.plano(lambda d: d.line([(24, 28), (26, 30)], fill=255), NEGRO[2])                           # tirador
    return c.img


# ============================================================================ manos
# Las manos de EL MARÍA en los primeros planos, con su piel (PIEL) y 4 tonos. Los dedos son cápsulas.

def _dedo(c, x0, y0, x1, y1, grosor=5, rampa=PIEL):
    r = grosor / 2
    def dib(d):
        d.line([(x0, y0), (x1, y1)], fill=255, width=grosor)
        d.ellipse((x0 - r + .5, y0 - r + .5, x0 + r - .5, y0 + r - .5), fill=255)
        d.ellipse((x1 - r + .5, y1 - r + .5, x1 + r - .5, y1 + r - .5), fill=255)
    return c.forma(dib, rampa)


def _brazo(c, x0, y0, x1, y1, grosor=16, manga=None):
    """Antebrazo de (x0, y0) (codo, fuera de cuadro) a (x1, y1) (muñeca)."""
    _dedo(c, x0, y0, x1, y1, grosor)
    if manga:
        _dedo(c, x0, y0, x0 + (x1 - x0) * 0.25, y0 + (y1 - y0) * 0.25, grosor + 4, manga)


def puno(c, x, y, desde=(1, 1), brazo=True):
    """Puño derecho que pinza algo entre el pulgar y el lado del índice; la pinza queda en (x, y) y el puño a la
    derecha. desde: hacia dónde sale el antebrazo (fuera de cuadro)."""
    ux, uy = desde
    if brazo:
        _brazo(c, x + 14 + ux * 90, y + 6 + uy * 70, x + 16, y + 6, 15)
    # dorso de la mano
    c.forma(lambda d: d.rounded_rectangle((x + 4, y - 9, x + 24, y + 11), 6, fill=255), PIEL)
    # dedos doblados hacia la pinza: cuatro falanges apiladas a la izquierda
    for k in range(4):
        yy = y - 6 + k * 5
        _dedo(c, x + 9, yy, x + 2 + (k == 0) * 1, yy + 1, 5)
    # pulgar por encima, apretando contra el índice
    _dedo(c, x + 16, y - 10, x + 3, y - 6, 6)
    c.pixeles([(x + 3, y - 8), (x + 4, y - 8)], PIEL[0])                                     # uña
    c.pixeles([(x + 12, y + 1), (x + 12, y + 6), (x + 13, y - 4)], PIEL[3])                  # nudillos


def mano_sujeta(c, x, y, ancho=22, dedos=3, grosor=5):
    """Mano izquierda que agarra un objeto por debajo: los dedos cruzan por delante en horizontal, con la punta en
    x + ancho, y el pulgar sube por el lado izquierdo. (x, y): nudillo del índice."""
    _brazo(c, x - 70, y + 80, x - 6, y + 8, 15)
    c.forma(lambda d: d.ellipse((x - 12, y - 2, x + 6, y + 4 + dedos * (grosor - 1)), fill=255), PIEL)    # palma
    for k in range(dedos):
        yy = y + k * (grosor - 1)
        _dedo(c, x - 2, yy, x + ancho - 2 * k, yy + 1, grosor)
    _dedo(c, x - 8, y + 2, x - 3, y - 8, 6)                                                         # pulgar
    c.pixeles([(x - 4, y - 9), (x - 3, y - 9)], PIEL[0])


# ============================================================================ plano: la llave en el contacto

TAB = ((84, 86, 100), (64, 66, 78), (48, 50, 60), (34, 36, 44))        # plástico del salpicadero


def _llave(c, cx, cy, giro):
    """Llave en el bombín: cabeza negra con la hoja dentro. giro 0 = vertical, 1 = girada 90° (contacto)."""
    a = np.radians(-60 * giro)
    def rot(px, py):
        return (cx + px * np.cos(a) - py * np.sin(a), cy + px * np.sin(a) + py * np.cos(a))
    cabeza = [rot(-5, -20), rot(5, -20), rot(6, -9), rot(2, -5), rot(-2, -5), rot(-6, -9)]
    c.forma(lambda d: d.polygon(cabeza, fill=255), NEGRO)
    c.forma(lambda d: d.polygon([rot(-1.5, -5), rot(1.5, -5), rot(1.5, 0), rot(-1.5, 0)], fill=255), PLATA[1:],
            contorno=None)
    c.pixeles([tuple(int(round(v)) for v in rot(-2, -17))], NEGRO[0])


def contacto(mano=1.0, giro=0.0, luces=False, temblor=0):
    """mano: 0 fuera de cuadro .. 1 en la llave. giro: 0..1. luces: testigos encendidos."""
    W, H = 160, 96
    c = Lienzo(W, H, TAB[2])
    # salpicadero: parte alta y consola
    c.forma(lambda d: d.rectangle((0, 0, W, 26), fill=255), TAB[1:], contorno=TAB[3])
    c.forma(lambda d: d.rounded_rectangle((96, 34, 158, 74), 4, fill=255), TAB, contorno=N)      # consola
    for k, col in enumerate(((248, 104, 72), (240, 240, 240), (96, 160, 248))):                  # mandos
        x = 108 + 20 * k
        c.forma(lambda d, x=x: d.ellipse((x - 7, 47, x + 7, 61), fill=255), NEGRO, contorno=N)
        c.pixeles([(x, 49), (x, 50)], col)
    for k in range(4):                                                                         # testigos
        on = ((248, 168, 48), (232, 64, 48), (120, 216, 96), (248, 168, 48))[k]
        x = 104 + 13 * k
        c.forma(lambda d, x=x: d.rectangle((x, 38, x + 7, 42), fill=255),
                (on, on) if luces else (TAB[3], TAB[3]), contorno=N)
    # volante (abajo del aro) y columna
    c.forma(lambda d: d.rectangle((14, 20, 44, 96), fill=255), TAB[1:], contorno=N, bandas=(0.15, 0.85))
    m_aro = c.mascara(lambda d: d.ellipse((-48, -78, 106, 62), fill=255)) & \
        ~c.mascara(lambda d: d.ellipse((-36, -68, 94, 50), fill=255))
    c.forma(None, NEGRO[1:], mascara=m_aro, bandas=(0.5, 0.9))
    c.forma(lambda d: d.ellipse((-6, -40, 64, 26), fill=255), NEGRO[1:])                         # piña
    c.forma(lambda d: d.ellipse((24, 4, 34, 10), fill=255), PLATA[1:])                           # emblema
    # rodilla con el pantalón de chándal (asoma bajo la consola)
    c.forma(lambda d: d.ellipse((70, 78, 190, 140), fill=255), NEGRO, bandas=(0.4, 0.8, 0.95))
    rayas_chandal(c, 84, 96, 158, 80, separacion=6)
    # bombín
    c.forma(lambda d: d.ellipse((60, 46, 78, 64), fill=255), PLATA)
    c.forma(lambda d: d.ellipse((64, 50, 74, 60), fill=255), PLATA[2:], contorno=NEGRO[3])
    _llave(c, 69, 55, giro)
    # mano
    if mano > 0:
        dx, dy = int((1 - mano) * 80), int((1 - mano) * 50)
        a = np.radians(-60 * giro)                    # la pinza agarra el lado derecho de la cabeza de la llave
        px, py = 6, -13
        puno(c, int(69 + px * np.cos(a) - py * np.sin(a)) + dx, int(55 + px * np.sin(a) + py * np.cos(a)) + dy)
    img = c.img
    if temblor:
        img = img.transform(img.size, Image.AFFINE, (1, 0, 0, 0, 1, temblor), Image.NEAREST)
    return img


# ============================================================================ plano: la pipa en las manos

AMARILLO = ((252, 236, 120), (232, 196, 64), (176, 140, 40))
LLAMA = ((255, 252, 224), (252, 216, 80), (244, 140, 48), (200, 64, 40))
HUMO = ((240, 240, 246), (208, 210, 222), (170, 172, 188))


def _fondo_pipa(c, fondo):
    W, H = c.w, c.h
    if fondo == 'coche':                         # el regazo: pantalón de chándal, y el aro del volante arriba
        c.forma(lambda d: d.rectangle((0, 0, W, H), fill=255), NEGRO[1:], contorno=None, bandas=(0.5, 0.95))
        rayas_chandal(c, -10, 70, 60, 96, separacion=6)
        rayas_chandal(c, 110, 96, 168, 62, separacion=6)
        m = c.mascara(lambda d: d.ellipse((60, -150, 260, 22), fill=255)) & \
            ~c.mascara(lambda d: d.ellipse((72, -140, 248, 10), fill=255))
        c.forma(None, NEGRO[1:], mascara=m, bandas=(0.5, 0.9))
    else:                                        # en la calle: camiseta negra con letras amarillas y grava
        c.forma(lambda d: d.rectangle((0, 0, W, H), fill=255), GRAVA, contorno=None, bandas=(0.4, 0.8))
        rng = np.random.default_rng(3)
        c.pixeles([(int(x), int(y)) for x, y in rng.uniform((0, 0), (W, H), (260, 2))], GRAVA[2])
        c.pixeles([(int(x), int(y)) for x, y in rng.uniform((0, 0), (W, H), (120, 2))], (226, 220, 206))
        c.forma(lambda d: d.polygon([(0, 0), (70, 0), (52, 30), (20, 50), (0, 56)], fill=255), NEGRO)
        letras = texto_img('MADE IN HELL', AMARILLO[1], AMARILLO[2]).rotate(24, expand=True, resample=Image.NEAREST)
        c.pegar(letras, 2, 4)                   # la camiseta del original pone «MADE IN HELL»


def _pipa_grande(c, relleno, brasa):
    # caña y boquilla
    c.forma(lambda d: d.polygon([(74, 60), (118, 54), (119, 61), (74, 70)], fill=255), MADERA)
    c.forma(lambda d: d.rectangle((117, 52, 121, 62), fill=255), PLATA[1:])
    c.forma(lambda d: d.polygon([(121, 54), (146, 49), (148, 53), (121, 60)], fill=255), NEGRO)
    # cazoleta con la veta del brezo
    c.forma(lambda d: d.polygon([(54, 38), (80, 38), (80, 58), (77, 68), (71, 74), (63, 74), (57, 68),
                                 (54, 58)], fill=255), MADERA)
    for y in (48, 55, 62):
        c.plano(lambda d, y=y: d.arc((56, y - 4, 76, y + 4), 20, 160, fill=255), MADERA[2])
    # boca
    c.forma(lambda d: d.ellipse((54, 32, 80, 44), fill=255), MADERA[:3])
    hueco = c.mascara(lambda d: d.ellipse((58, 34, 76, 42), fill=255))
    c.forma(None, NEGRO[2:], mascara=hueco, contorno=None)
    if relleno:
        h = 2 if relleno == 1 else 0                                # colmada: asoma por encima del borde
        tab = c.mascara(lambda d: d.ellipse((58, 34 + h, 76, 42), fill=255))
        if relleno == 2:
            tab |= c.mascara(lambda d: d.ellipse((59, 31, 75, 39), fill=255))
        c.forma(None, TABACO, mascara=tab, contorno=None, bandas=(0.35, 0.75))
        rng = np.random.default_rng(relleno)
        ys, xs = np.nonzero(tab)
        sel = rng.choice(len(ys), min(18, len(ys)), replace=False)
        c.pixeles([(xs[i], ys[i]) for i in sel[:9]], TABACO[0])     # hebras
        c.pixeles([(xs[i], ys[i]) for i in sel[9:]], TABACO[2])
        if brasa:
            sel = rng.choice(len(ys), min(10 * brasa, len(ys)), replace=False)
            cols = ((255, 200, 96), (248, 120, 48), (216, 56, 48))
            c.pixeles([(xs[i], ys[i]) for i in sel], cols[0])
            c.pixeles([(xs[i] + 1, ys[i]) for i in sel[::2]], cols[1])
            c.pixeles([(xs[i], ys[i] + 1) for i in sel[::3]], cols[2])


def _llama(c, x, y, fase, tirar=0.0, destino=(67, 38)):
    """Llama de mechero con la base en (x, y). fase alterna la forma; tirar (0-1) la dobla hacia destino (la boca
    de la cazoleta) cuando se chupa de la pipa."""
    alto = (16, 19, 14)[fase % 3]
    ancho = (4, 5, 4)[fase % 3]
    tx = x + (destino[0] - x) * tirar + (fase % 2) * (1 - tirar)
    ty = (y - alto) * (1 - tirar) + (destino[1] + (fase % 2) * 2) * tirar
    exterior = [(x - ancho, y), (x - ancho - 1, y - 4), (tx, ty), (x + ancho + 1, y - 5), (x + ancho, y)]
    c.forma(lambda d: d.polygon(exterior, fill=255), LLAMA[1:3], contorno=LLAMA[3], bandas=(0.6,), bordes=False)
    mx, my = (x + tx) / 2, (y + ty) / 2 + 2
    c.plano(lambda d: d.polygon([(x - 2, y), (mx - 1, my), (x + 2, y)], fill=255), LLAMA[0])
    c.plano(lambda d: d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=255), (120, 160, 248))       # base azul


def _mechero(c, x, y, llama=None, tirar=0.0):
    """Mechero rojo de pie con la parte de arriba en (x, y); el puño lo agarra por debajo."""
    if llama is not None:
        _llama(c, x - 3, y - 1, llama, tirar)
    c.forma(lambda d: d.rounded_rectangle((x - 5, y + 4, x + 6, y + 28), 3, fill=255), ROJO)
    c.forma(lambda d: d.rectangle((x - 5, y - 1, x + 6, y + 5), fill=255), PLATA)
    c.forma(lambda d: d.ellipse((x + 1, y - 3, x + 7, y + 2), fill=255), NEGRO[1:])              # ruedecilla
    puno(c, x + 6, y + 16, desde=(1, 0.6))


def _humo(c, x, y, fase):
    """Bocanada con el humo del juego (efectos_mapa/058), subiendo desde (x, y). fase: frame (0-23)."""
    imgs = humo_juego()
    img = imgs[min(3, fase // 6)]
    c.pegar(img, x - 16, y - 18 - fase // 2)


def plano_pipa(fondo='coche', relleno=0, mano=None, alto=0, llama=None, tirar=0.0, brasa=0, humo=None):
    """La pipa sujeta con la mano izquierda. mano: None, 'pinza' (cargando tabaco; alto = px por encima de la boca)
    o 'mechero' (llama: fase o None; tirar: la llama se mete en la cazoleta)."""
    W, H = 160, 96
    c = Lienzo(W, H)
    _fondo_pipa(c, fondo)
    _pipa_grande(c, relleno, brasa)
    mano_sujeta(c, 52, 64, ancho=22, dedos=3, grosor=5)
    if humo is not None:
        _humo(c, 67, 30, humo)
    if mano == 'pinza':
        y = 30 - alto
        hebras = [(66 + k % 3, y + 3 + k // 3) for k in range(7)]
        c.pixeles(hebras, TABACO[1])
        c.pixeles(hebras[::2], TABACO[0])
        puno(c, 68, y, desde=(1, -0.5))
    elif mano == 'mechero':
        _mechero(c, 84, 18, llama, tirar)
    return c.img


# ============================================================================ plano: el mapa dibujado a mano

AZUL_BOLI = (56, 80, 200)


def _dibujo_mapa(w, h):
    """El folio con el mapa del tesoro a rotulador: caminos azules, árboles, el lago y la X roja."""
    c = Lienzo(w, h)
    c.forma(lambda d: d.rectangle((0, 0, w - 1, h - 1), fill=255), PAPEL[:2], contorno=None, bandas=(0.97,))
    c.plano(lambda d: d.line([(w // 2, 1), (w // 2, h - 2)], fill=255), PAPEL[2])          # pliegues
    c.plano(lambda d: d.line([(1, h // 2), (w - 2, h // 2)], fill=255), PAPEL[2])
    sx, sy = w / 120, h / 80
    P = lambda pts: [(int(x * sx), int(y * sy)) for x, y in pts]
    c.plano(lambda d: d.line(P([(8, 70), (28, 58), (48, 62), (64, 44), (84, 38), (102, 18)]), fill=255, width=2),
            AZUL_BOLI)
    c.plano(lambda d: d.line(P([(28, 58), (26, 38), (38, 18)]), fill=255, width=2), AZUL_BOLI)
    c.plano(lambda d: d.ellipse(tuple(P([(56, 52), (82, 72)])[0] + P([(56, 52), (82, 72)])[1]), outline=255, width=2),
            (72, 150, 228))                                                                     # el lago
    for x, y in ((10, 40), (18, 50), (46, 32), (88, 46), (104, 64)):
        c.plano(lambda d, x=x, y=y: d.polygon(P([(x, y - 7), (x - 5, y + 3), (x + 5, y + 3)]), outline=255),
                (40, 144, 64))
    for a, b in (((98, 10), (110, 22)), ((110, 10), (98, 22))):
        c.plano(lambda d, a=a, b=b: d.line(P([a, b]), fill=255, width=3), (216, 40, 40))       # la X
    rot = texto_img('EL PROYECTO', AZUL_BOLI).rotate(6, expand=True, resample=Image.NEAREST)
    c.pegar(rot, int(8 * sx), int(3 * sy))
    return c.img


def plano_mapa(abierto=2):
    """Las manos sujetan el mapa sobre la grava; la derecha lleva además la pipa. abierto: 0 doblado en cuatro,
    1 a medias, 2 desplegado."""
    W, H = 176, 104
    c = Lienzo(W, H)
    c.forma(lambda d: d.rectangle((0, 0, W, H), fill=255), GRAVA, contorno=None, bandas=(0.4, 0.8))
    rng = np.random.default_rng(5)
    c.pixeles([(int(x), int(y)) for x, y in rng.uniform((0, 0), (W, H), (300, 2))], GRAVA[2])
    c.pixeles([(int(x), int(y)) for x, y in rng.uniform((0, 0), (W, H), (140, 2))], (226, 220, 206))
    pw, ph = 128, 84
    lleno = _dibujo_mapa(pw, ph)
    if abierto == 2:
        papel, x0 = lleno, (W - pw) // 2
    elif abierto == 1:                                                    # media hoja abierta: la mitad de abajo
        papel, x0 = lleno.crop((0, ph // 2, pw, ph)), (W - pw) // 2
    else:                                                                 # doblado en cuatro
        papel, x0 = lleno.crop((pw // 2, ph // 2, pw, ph)), (W - pw // 2) // 2
    y0 = 10 + (ph - papel.height)
    c.pegar(contorno_exterior(papel), x0, y0)
    if abierto < 2:                                                       # lomo del pliegue con sombra
        c.plano(lambda d: d.line([(x0, y0), (x0 + papel.width - 1, y0)], fill=255), PAPEL[2])
    xi, xd = x0 - 2, x0 + papel.width + 2
    yb = y0 + papel.height - 14
    # mano izquierda: pulgar por encima del papel, dedos por detrás
    _brazo(c, xi - 50, H + 40, xi + 2, yb + 10, 15)
    c.forma(lambda d: d.ellipse((xi - 6, yb, xi + 10, yb + 18), fill=255), PIEL)
    _dedo(c, xi + 2, yb + 4, xi + 12, yb - 2, 6)
    # mano derecha con la pipa: la cazoleta asoma por debajo del puño
    c.forma(lambda d: d.polygon([(xd - 8, yb + 14), (xd + 4, yb + 14), (xd + 4, yb + 26), (xd - 2, yb + 30),
                                 (xd - 8, yb + 26)], fill=255), MADERA)
    c.forma(lambda d: d.ellipse((xd - 9, yb + 11, xd + 5, yb + 17), fill=255), MADERA[:3])
    c.forma(None, NEGRO[2:], mascara=c.mascara(lambda d: d.ellipse((xd - 6, yb + 12, xd + 2, yb + 16), fill=255)),
            contorno=None)
    _brazo(c, xd + 50, H + 40, xd - 2, yb + 10, 15)
    c.forma(lambda d: d.ellipse((xd - 10, yb, xd + 6, yb + 18), fill=255), PIEL)
    _dedo(c, xd - 2, yb + 4, xd - 12, yb - 2, 6)
    return c.img


# ============================================================================ vista previa

def hoja(piezas=None, k=3, ancho=1500):
    piezas = piezas or [plano_pipa('coche', 0, 'pinza', 14), plano_pipa('coche', 1, 'pinza', 0),
                        plano_pipa('calle', 2, 'mechero', llama=1), plano_pipa('calle', 2, 'mechero', llama=0, tirar=1, brasa=2, humo=6),
                        plano_pipa('calle', 2, None, brasa=1, humo=12), plano_mapa(0), plano_mapa(1), plano_mapa(2)]
    pos, x, y, alto = [], 8, 8, 0
    for p in piezas:
        w, h = p.width * k, p.height * k
        if x + w > ancho:
            x, y, alto = 8, y + alto + 8, 0
        pos.append((x, y))
        x += w + 8
        alto = max(alto, h)
    out = Image.new('RGBA', (ancho, y + alto + 8), (152, 208, 120, 255))
    for p, (x, y) in zip(piezas, pos):
        out.alpha_composite(p.resize((p.width * k, p.height * k), Image.NEAREST), (x, y))
    return out


if __name__ == '__main__':
    from motor.recursos import TRABAJO
    ruta = os.path.join(TRABAJO, '_graficos_v3.png')
    hoja().save(ruta)
    print(os.path.abspath(ruta))
