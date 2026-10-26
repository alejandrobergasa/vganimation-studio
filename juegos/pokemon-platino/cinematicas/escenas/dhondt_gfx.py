"""Pizarras (256x140) de la cinemática «eleccionesdont»: gráficos en pixel art con la fuente del juego.

Los partidos son inventados (tipos de Pokémon) para no mezclar la explicación con política real; solo los datos
reales (2008 y noviembre de 2019) llevan siglas. Vista previa:  python escenas/dhondt_gfx.py
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from motor.recursos import fuente  # noqa

W, H = 256, 140
FONDO = (26, 66, 60)
FONDO2 = (36, 88, 78)
MADERA = (196, 148, 88)
MADERA2 = (140, 96, 56)
BLANCO = (248, 248, 240)
AMARILLO = (255, 226, 96)
GRIS = (150, 176, 168)
ROJO = (255, 120, 104)
VERDE = (140, 236, 140)
SOMBRA = (10, 30, 28)

PARTIDOS = [('FUEGO', (232, 84, 64)), ('AGUA', (72, 136, 240)), ('PLANTA', (80, 190, 96)),
            ('RAYO', (248, 208, 56)), ('HADA', (200, 112, 220))]
VOTOS = [340, 280, 160, 60, 20]       # miles de votos de la provincia de ejemplo
ESCANOS = 7


# ---------------------------------------------------------------- utilidades

def dhondt(votos, n, divisor=lambda k: k + 1):
    c = sorted(((v / divisor(k), i) for i, v in enumerate(votos) for k in range(n)), key=lambda t: (-t[0], t[1]))[:n]
    r = [0] * len(votos)
    for _, i in c:
        r[i] += 1
    return r, c


def hare(votos, n):
    q = sum(votos) / n
    r = [int(v // q) for v in votos]
    for i in sorted(range(len(votos)), key=lambda i: (-(votos[i] / q - r[i]), i))[:n - sum(r)]:
        r[i] += 1
    return r


def lienzo():
    im = Image.new('RGBA', (W, H), MADERA2 + (255,))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, H - 1), outline=(60, 36, 20))
    d.rectangle((1, 1, W - 2, H - 2), outline=MADERA)
    d.rectangle((3, 3, W - 4, H - 4), fill=FONDO, outline=(16, 44, 40))
    return im


def tx(im, s, x, y, color=BLANCO, k=1, centro=False, derecha=False):
    f = fuente()
    w = f.ancho(s)
    if centro:
        x = x - w * k // 2
    elif derecha:
        x = x - w * k
    if k == 1:
        f.dibujar(im, s, x, y, color, SOMBRA)
        return
    t = Image.new('RGBA', (w + 2, 16))
    f.dibujar(t, s, 0, 0, color, SOMBRA)
    im.alpha_composite(t.resize((t.width * k, 16 * k), Image.NEAREST), (int(x), int(y)))


def titulo(im, s):
    tx(im, s, W // 2, 5, AMARILLO, centro=True)
    ImageDraw.Draw(im).line((14, 20, W - 15, 20), fill=GRIS)


def bola(d, cx, cy, color, r=4):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color, outline=(16, 20, 20))
    d.point((cx - r // 2, cy - r // 2), fill=(255, 255, 255))


def escanos(d, x, y, cuantos, color, paso=11, r=4):
    for k in range(cuantos):
        bola(d, x + k * paso, y, color, r)


def recuadro(d, caja, color=FONDO2, borde=GRIS):
    d.rectangle(caja, fill=color, outline=borde)


# ---------------------------------------------------------------- paneles

def p_titulo():
    im = lienzo()
    tx(im, 'LA LEY', W // 2, 22, BLANCO, 2, centro=True)
    tx(im, "D'HONDT", W // 2, 50, AMARILLO, 3, centro=True)
    tx(im, 'ELECCIONES GENERALES DE ESPAÑA', W // 2, 100, GRIS, centro=True)
    d = ImageDraw.Draw(im)
    for k, (_, c) in enumerate(PARTIDOS):
        bola(d, 88 + k * 20, 125, c, 5)
    return im


def p_congreso(paso=0):
    im = lienzo()
    titulo(im, 'EL CONGRESO DE LOS DIPUTADOS')
    d = ImageDraw.Draw(im)
    tx(im, '350', W // 2, 26, AMARILLO, 3, centro=True)
    tx(im, 'DIPUTADOS Y 52 CIRCUNSCRIPCIONES', W // 2, 70, BLANCO, centro=True)
    if paso >= 1:
        x0, x1 = 14, W - 14
        corte = x0 + (x1 - x0) * 102 // 350
        d.rectangle((x0, 92, corte, 108), fill=(232, 84, 64), outline=(16, 20, 20))
        d.rectangle((corte + 1, 92, x1, 108), fill=(72, 136, 240), outline=(16, 20, 20))
        tx(im, '102', (x0 + corte) // 2, 93, BLANCO, centro=True)
        tx(im, '248', (corte + x1) // 2, 93, BLANCO, centro=True)
        tx(im, 'FIJOS: 2 POR PROVINCIA', x0, 112, ROJO)
        tx(im, 'SEGÚN POBLACIÓN', x1, 112, (150, 196, 255), derecha=True)
        tx(im, '2 + 2 + ... Y 1 CEUTA, 1 MELILLA', W // 2, 124, GRIS, centro=True) if False else None
    return im


def p_listas():
    im = lienzo()
    titulo(im, 'LISTAS CERRADAS Y BLOQUEADAS')
    d = ImageDraw.Draw(im)
    for k, (nombre, c) in enumerate(PARTIDOS[:3]):
        x = 18 + k * 78
        d.rectangle((x, 28, x + 66, 126), fill=(248, 244, 228), outline=(20, 20, 20))
        d.rectangle((x, 28, x + 66, 42), fill=c, outline=(20, 20, 20))
        tx(im, nombre, x + 33, 28, BLANCO, centro=True)
        for j in range(5):
            tx(im, '%d. ........' % (j + 1), x + 6, 46 + j * 14, (60, 60, 60))
    tx(im, 'SE VOTA LA LISTA ENTERA', W // 2, 127, AMARILLO, centro=True) if False else None
    return im


def p_votos(umbral=False):
    im = lienzo()
    titulo(im, 'PROVINCIA DE 7 ESCAÑOS')
    d = ImageDraw.Draw(im)
    base, alto = 118, 74
    mx = 340
    for k, ((nombre, c), v) in enumerate(zip(PARTIDOS, VOTOS)):
        x = 20 + k * 46
        h = alto * v // mx
        d.rectangle((x, base - h, x + 32, base), fill=c, outline=(16, 20, 20))
        tx(im, str(v), x + 16, base - h - 14, BLANCO, centro=True)
        tx(im, nombre, x + 16, base + 1, BLANCO if (not umbral or v >= 26) else (130, 130, 130), centro=True)
    tx(im, 'MILES DE VOTOS', W - 8, 24, GRIS, derecha=True)
    if umbral:
        y = base - alto * 25.8 // mx
        for x in range(10, W - 10, 6):
            d.line((x, y, x + 2, y), fill=ROJO)
        tx(im, 'BARRERA: 3 POR CIENTO', W - 8, 40, ROJO, derecha=True)
        tx(im, 'DE 860 SON 25,8 MIL', W - 8, 54, ROJO, derecha=True)
        x = 20 + 4 * 46
        d.line((x, base - 12, x + 32, base - 2), fill=ROJO, width=2)
        d.line((x, base - 2, x + 32, base - 12), fill=ROJO, width=2)
    return im


def p_tabla(n=0):
    """Tabla de cocientes; n = cuántos escaños se han adjudicado ya."""
    im = lienzo()
    titulo(im, "REPARTO CON LA REGLA D'HONDT")
    d = ImageDraw.Draw(im)
    v = VOTOS[:4]
    _, orden = dhondt(v, ESCANOS)
    marcados = {}
    for pos, (_, i) in enumerate(orden):
        pass
    # celdas elegidas por orden: cociente valor -> (partido, divisor)
    elegidas = []
    cont = [0] * 4
    for q, i in orden:
        cont[i] += 1
        elegidas.append((i, cont[i]))
    x0, y0, cw, ch = 50, 38, 33, 17
    for j in range(6):
        tx(im, '÷%d' % (j + 1), x0 + j * cw + cw // 2, 23, AMARILLO, centro=True)
    res = [0] * 4
    for k in range(n):
        res[elegidas[k][0]] += 1
    for i in range(4):
        nombre, c = PARTIDOS[i]
        y = y0 + i * ch
        d.rectangle((3, y, 47, y + ch - 2), fill=c, outline=(16, 20, 20))
        tx(im, nombre, 25, y + 1, (20, 20, 20) if i == 3 else BLANCO, centro=True)
        for j in range(6):
            x = x0 + j * cw
            sel = [m for m, (pi, dj) in enumerate(elegidas[:n]) if pi == i and dj == j + 1]
            d.rectangle((x, y, x + cw - 2, y + ch - 2), fill=(c if sel else FONDO2), outline=GRIS)
            col = (20, 20, 20) if sel and i == 3 else BLANCO
            cifra = str(round(v[i] / (j + 1)))
            if sel:
                tx(im, cifra, x + 1, y + 1, col)
                d.ellipse((x + cw - 13, y + 2, x + cw - 3, y + 12), fill=(20, 24, 24), outline=BLANCO)
                tx(im, str(sel[0] + 1), x + cw - 8, y, AMARILLO, centro=True)
            else:
                tx(im, cifra, x + (cw - 2) // 2, y + 1, col, centro=True)
    tx(im, 'ESCAÑOS:', 4, 112, AMARILLO)
    for i in range(4):
        escanos(d, 82 + i * 42, 119, res[i], PARTIDOS[i][1], 9, 4)
        if not res[i] and n == ESCANOS:
            tx(im, '0', 82 + i * 42 - 3, 111, ROJO)
    if n < ESCANOS:
        tx(im, '%d DE %d' % (n, ESCANOS), W - 8, 112, GRIS, derecha=True)
    return im


def p_resultado():
    im = lienzo()
    titulo(im, 'VOTOS CONTRA ESCAÑOS')
    d = ImageDraw.Draw(im)
    tot = sum(VOTOS)
    res, _ = dhondt(VOTOS[:4], ESCANOS)
    for fila, (nombre, vals, total, y) in enumerate([('VOTOS', VOTOS, tot, 34), ('ESCAÑOS', res + [0], ESCANOS, 80)]):
        tx(im, nombre, 10, y - 14, BLANCO)
        x = 10
        for (n, c), v in zip(PARTIDOS, vals):
            w = round(236 * v / total)
            if w:
                d.rectangle((x, y, x + w - 1, y + 22), fill=c, outline=(16, 20, 20))
                pct = 100 * v / total
                if w > 26:
                    tx(im, ('%.1f' % pct).replace('.', ',') if fila == 0 else str(v), x + w // 2, y + 4,
                       (20, 20, 20) if n == 'RAYO' else BLANCO, centro=True)
            x += w
    tx(im, 'CADA COLOR = UN PARTIDO. LA PLANTA PIERDE', W // 2, 110, GRIS, centro=True) if False else None
    tx(im, 'RAYO: 7 POR CIENTO DE VOTOS, 0 ESCAÑOS', W // 2, 112, ROJO, centro=True)
    return im


def p_comparar():
    im = lienzo()
    titulo(im, 'MISMOS VOTOS, OTRO MÉTODO')
    d = ImageDraw.Draw(im)
    v = VOTOS[:4]
    filas = [("D'HONDT", dhondt(v, ESCANOS)[0]), ('RESTOS MAYORES', hare(v, ESCANOS)),
             ('SAINTE-LAGUË', dhondt(v, ESCANOS, lambda k: 2 * k + 1)[0])]
    for r, (nombre, res) in enumerate(filas):
        y = 25 + r * 32
        recuadro(d, (6, y, W - 7, y + 28))
        tx(im, nombre, 10, y + 1, AMARILLO if r == 0 else BLANCO)
        x = 10
        for i in range(4):
            for _ in range(res[i]):
                bola(d, x + 4, y + 20, PARTIDOS[i][1], 4)
                x += 10
            x += 6
        tx(im, 'RAYO: %d' % res[3], W - 10, y + 1, VERDE if res[3] else ROJO, derecha=True)
    tx(im, 'VOTOS: 340, 280, 160 Y 60 MIL', W // 2, 123, GRIS, centro=True)
    return im


def p_historia(paso=4):
    im = lienzo()
    titulo(im, '¿POR QUÉ ESTE SISTEMA?')
    d = ImageDraw.Draw(im)
    hitos = [('1878', "D'HONDT, JURISTA BELGA, LA IDEA"),
             ('1977', 'TRANSICIÓN: ELECCIONES LIBRES'),
             ('1978', 'CONSTITUCIÓN: POR PROVINCIAS'),
             ('1985', 'LEY ELECTORAL: 350 DIPUTADOS')]
    d.line((40, 30, 40, 128), fill=MADERA, width=2)
    for k, (a, t) in enumerate(hitos[:paso]):
        y = 28 + k * 25
        d.ellipse((35, y + 3, 45, y + 13), fill=AMARILLO, outline=(16, 20, 20))
        tx(im, a, 4, y, AMARILLO) if False else None
        tx(im, a, 30, y, AMARILLO, derecha=True)
        tx(im, t, 52, y, BLANCO)
    return im


def p_objetivos():
    im = lienzo()
    titulo(im, 'LO QUE BUSCABAN EN 1977')
    d = ImageDraw.Draw(im)
    pts = [('ESTABILIDAD', 'EVITAR PARLAMENTOS DE MIL PARTIDOS'), ('REPRESENTAR', 'QUE CADA PROVINCIA TENGA VOZ'),
           ('SENCILLEZ', 'UNA CUENTA QUE CUALQUIERA PUEDE HACER')]
    for k, (a, b) in enumerate(pts):
        y = 28 + k * 36
        recuadro(d, (6, y, W - 7, y + 32))
        tx(im, a, 12, y + 1, AMARILLO)
        tx(im, b, 12, y + 16, BLANCO)
    return im


def _lista(titulo_txt, items, color):
    im = lienzo()
    titulo(im, titulo_txt)
    d = ImageDraw.Draw(im)
    for k, (a, b) in enumerate(items):
        y = 26 + k * 28
        d.rectangle((10, y + 3, 17, y + 10), fill=color, outline=(16, 20, 20))
        tx(im, a, 24, y, color)
        tx(im, b, 24, y + 13, BLANCO)
    return im


def p_ventajas():
    return _lista('VENTAJAS', [('SIMPLE Y TRANSPARENTE', 'SE CALCULA CON UNA TABLA'),
                               ('MAYORÍAS MÁS CLARAS', 'GOBIERNOS MÁS ESTABLES'),
                               ('CADA PROVINCIA PESA', 'HAY DIPUTADOS DE TODO EL TERRITORIO'),
                               ('SIN PARADOJA DE ALABAMA', 'MÁS ESCAÑOS NUNCA QUITAN ESCAÑOS')], VERDE)


def p_desventajas():
    return _lista('DESVENTAJAS', [('PREMIA A LOS GRANDES', 'LOS PEQUEÑOS PIERDEN ESCAÑOS'),
                                  ('NO TODOS LOS VOTOS VALEN LO MISMO', 'DEPENDE DE LA PROVINCIA'),
                                  ('VOTOS A LA BASURA', 'SI TU LISTA NO LLEGA, NO CUENTA'),
                                  ('LISTAS CERRADAS', 'NO ELIGES A LA PERSONA')], ROJO)


def _barras(titulo_txt, datos, maximo, pie, unidad=''):
    im = lienzo()
    titulo(im, titulo_txt)
    d = ImageDraw.Draw(im)
    for k, (nombre, v, c, extra) in enumerate(datos):
        y = 27 + k * (92 // len(datos) + 1)
        h = 92 // len(datos) - 4
        tx(im, nombre, 8, y + max(0, (h - 12) // 2), BLANCO)
        w = int(104 * v / maximo)
        d.rectangle((76, y, 76 + w, y + h), fill=c, outline=(16, 20, 20))
        ty = y + max(0, (h - 12) // 2)
        tx(im, str(v) + unidad, 80 + w, ty, BLANCO)
        if extra:
            if 80 + w + fuente().ancho(str(v) + unidad) + fuente().ancho(extra) + 10 < W - 8:
                tx(im, extra, W - 8, ty, GRIS, derecha=True)
            else:
                tx(im, extra, 76 + w - 4, ty, BLANCO, derecha=True)
    tx(im, pie, W // 2, 124, AMARILLO, centro=True)
    return im


def p_votos_escano():
    c = [(232, 84, 64), (72, 136, 240), (80, 190, 96), (248, 208, 56), (200, 112, 220), (160, 160, 160)]
    return _barras('MILES DE VOTOS POR ESCAÑO, NOV 2019',
                   [('PP', 56, c[0], ''), ('PSOE', 57, c[1], ''), ('PNV', 63, c[2], ''), ('VOX', 70, c[3], ''),
                    ('UP', 89, c[4], ''), ('CS', 165, c[5], '')], 165,
                   'UN ESCAÑO DE CS COSTÓ TRES DE PP')


def p_provincias():
    return _barras('HABITANTES POR DIPUTADO, EN MILES',
                   [('SORIA', 44, (232, 150, 64), '2 DIPUTADOS'), ('MADRID', 180, (72, 136, 240), '37 DIPUTADOS')], 180,
                   'EL VOTO EN SORIA PESA CUATRO VECES MÁS')


def p_umbral():
    return _barras('POR CIENTO NECESARIO PARA UN ESCAÑO',
                   [('2 ESCAÑOS', 33, (232, 84, 64), 'CASI 1 DE 3'), ('3 ESCAÑOS', 25, (232, 150, 64), '1 DE 4'),
                    ('5 ESCAÑOS', 17, (248, 208, 56), ''), ('10 ESCAÑOS', 9, (80, 190, 96), ''),
                    ('37 ESCAÑOS', 3, (72, 136, 240), 'LA BARRERA LEGAL')], 33,
                   'PROVINCIA PEQUEÑA, MANDAN LOS GRANDES')


def p_disperso():
    im = lienzo()
    titulo(im, 'ELECCIONES DE 2008')
    d = ImageDraw.Draw(im)
    for k, (nombre, votos, esc, c, h) in enumerate([('IU', '963 MIL VOTOS', 2, (232, 84, 64), 46),
                                                    ('PNV', '306 MIL VOTOS', 6, (80, 190, 96), 15)]):
        cx = 64 + k * 128
        top = 114 - h
        d.rectangle((cx - 20, top, cx + 20, 114), fill=c, outline=(16, 20, 20))
        tx(im, nombre, cx, 115, BLANCO, centro=True)
        tx(im, votos, cx, top - 42, BLANCO, centro=True)
        tx(im, '%d ESCAÑOS' % esc, cx, top - 28, AMARILLO, centro=True)
        escanos(d, cx - (esc - 1) * 5, top - 8, esc, c, 10, 4)
    return im


def p_alabama(paso=1):
    im = lienzo()
    titulo(im, 'LA PARADOJA DE ALABAMA')
    d = ImageDraw.Draw(im)
    votos = [290, 180, 130]
    cols = [PARTIDOS[0][1], PARTIDOS[1][1], PARTIDOS[2][1]]
    tx(im, 'VOTOS: 290, 180 Y 130 MIL', W // 2, 24, GRIS, centro=True)
    for col, n in enumerate((11, 12)):
        if col + 1 > paso + 0 and paso < 2 and col == 1:
            continue
        x = 8 + col * 124
        recuadro(d, (x, 38, x + 116, 112))
        tx(im, '%d ESCAÑOS' % n, x + 58, 40, AMARILLO, centro=True)
        r = hare(votos, n)
        for i in range(3):
            tx(im, PARTIDOS[i][0], x + 6, 58 + i * 16, BLANCO)
            escanos(d, x + 62, 66 + i * 16, r[i], cols[i], 8, 3)
        if col == 1 and paso >= 2:
            tx(im, 'PLANTA: 3 A 2', x + 58, 112, ROJO, centro=True) if False else None
    if paso >= 2:
        tx(im, 'MÁS ESCAÑOS, Y PLANTA PIERDE UNO', W // 2, 118, ROJO, centro=True)
    return im


def p_coalicion(paso=1):
    im = lienzo()
    titulo(im, 'UNIRSE COMPENSA CON D\'HONDT')
    d = ImageDraw.Draw(im)
    tx(im, '4 ESCAÑOS EN JUEGO', W // 2, 24, GRIS, centro=True)
    sep = dhondt([35, 10, 25], 4)[0]
    uni = dhondt([45, 25], 4)[0]
    recuadro(d, (6, 38, 124, 112))
    tx(im, 'SEPARADOS', 65, 40, AMARILLO, centro=True)
    for i, (nom, v, c) in enumerate([('FUEGO', 35, PARTIDOS[0][1]), ('AGUA', 10, PARTIDOS[1][1]),
                                     ('PLANTA', 25, PARTIDOS[2][1])]):
        tx(im, '%s %d' % (nom, v), 10, 56 + i * 16, BLANCO)
        escanos(d, 86, 64 + i * 16, sep[i], c, 9, 3)
    tx(im, 'FUEGO Y AGUA: %d' % (sep[0] + sep[1]), 65, 118, BLANCO, centro=True)
    if paso >= 2:
        recuadro(d, (132, 38, 250, 112))
        tx(im, 'UNIDOS', 191, 40, AMARILLO, centro=True)
        tx(im, 'FUEGO Y AGUA 45', 136, 56, BLANCO)
        escanos(d, 140, 78, uni[0], PARTIDOS[0][1], 9, 3)
        tx(im, 'PLANTA 25', 136, 88, BLANCO)
        escanos(d, 140, 106, uni[1], PARTIDOS[2][1], 9, 3)
        tx(im, 'FUEGO Y AGUA: %d' % uni[0], 191, 118, VERDE, centro=True)
    return im


def p_resumen():
    return _lista('EN RESUMEN', [("D'HONDT: DIVIDIR Y ELEGIR LOS MAYORES", 'ES SENCILLO Y DA ESTABILIDAD'),
                                 ('PREMIA A LOS GRANDES Y UNIDOS', 'Y CASTIGA EL VOTO DISPERSO'),
                                 ('EL TAMAÑO DE LA PROVINCIA IMPORTA', 'UN VOTO NO PESA IGUAL EN TODAS'),
                                 ('NINGÚN SISTEMA ES NEUTRO', 'CADA UNO REPARTE PODER DISTINTO')], AMARILLO)


def p_final():
    im = lienzo()
    tx(im, 'SI QUIERES MÁS...', W // 2, 24, AMARILLO, 2, centro=True)
    tx(im, 'PRUEBA A HACER LA TABLA', W // 2, 66, BLANCO, centro=True)
    tx(im, 'CON LOS VOTOS DE TU PROVINCIA', W // 2, 82, BLANCO, centro=True)
    d = ImageDraw.Draw(im)
    for k, (_, c) in enumerate(PARTIDOS):
        bola(d, 88 + k * 20, 112, c, 5)
    return im


PANELES = [p_titulo(), p_congreso(1), p_listas(), p_votos(), p_votos(True)] + [p_tabla(n) for n in (0, 3, 7)] + [
    p_resultado(), p_comparar(), p_historia(), p_objetivos(), p_ventajas(), p_desventajas(), p_votos_escano(),
    p_provincias(), p_umbral(), p_disperso(), p_alabama(2), p_coalicion(2), p_resumen(), p_final()]

if __name__ == '__main__':
    cols = 3
    hoja = Image.new('RGB', (cols * (W + 4), ((len(PANELES) + cols - 1) // cols) * (H + 4)), (10, 10, 10))
    for i, p in enumerate(PANELES):
        hoja.paste(p.convert('RGB'), ((i % cols) * (W + 4), (i // cols) * (H + 4)))
    from motor.recursos import TRABAJO
    destino = os.path.join(TRABAJO, '_dhondt_paneles.png')
    hoja.resize((hoja.width * 2 // 1, hoja.height * 2 // 1), Image.NEAREST).save(destino)
    print(destino)
