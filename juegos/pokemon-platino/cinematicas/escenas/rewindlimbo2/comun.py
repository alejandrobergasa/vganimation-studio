"""Piezas compartidas por los tramos de REWINDLIMBO2: rutas, insertos con objetos del juego, cartel, caja de
EL PROYECTO, títulos grandes con la fuente del juego y la exportación de cada tramo."""
import os
import sys

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
CINE = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, CINE)
sys.path.insert(0, AQUI)
from motor.recursos import RAIZ, SPR, CUSTOM, TRABAJO, fuente, imagen, ventana_mensaje  # noqa
from motor.recursos import SALIDA as _SALIDA  # noqa
import textos  # noqa

AUDIO = os.path.join(TRABAJO, 'rewindlimbo2', 'audio', 'mezcla_final.wav')
SALIDA = os.path.join(_SALIDA, 'rewindlimbo2')
ICONOS = 'objetos/iconos/'


def icono(nombre):
    """Icono de objeto del juego por fragmento del nombre ('mapa', 'palo', 'llave_suite'...)."""
    import glob
    fs = sorted(glob.glob(os.path.join(SPR, 'objetos', 'iconos', '*%s*.png' % nombre)))
    return imagen(fs[0])


def escalar(img, k):
    return img.resize((img.width * k, img.height * k), Image.NEAREST)


def texto_img(texto, color=None, sombra=None, k=1):
    """Una línea con la fuente del juego como imagen (escalada xk)."""
    f = fuente()
    im = Image.new('RGBA', (f.ancho(texto) + 2, 16))
    f.dibujar(im, texto, 0, 0, color, sombra)
    im = im.crop(im.getbbox() or (0, 0, 1, 1))
    return escalar(im, k)


def inserto(img, k=2, texto=None, tipo=1, ancho=None):
    """Ventana del juego con un objeto ampliado dentro (y un rótulo opcional debajo): los «planos detalle»."""
    obj = escalar(img, k) if k > 1 else img
    rot = texto_img(texto) if texto else None
    w = max(ancho or 0, obj.width + 28, (rot.width + 28) if rot else 0)
    h = obj.height + 20 + ((rot.height + 6) if rot else 0)
    w, h = (w + 7) // 8 * 8, (h + 7) // 8 * 8
    v = ventana_mensaje(w, h, tipo)
    v.alpha_composite(obj, ((w - obj.width) // 2, 10))
    if rot:
        v.alpha_composite(rot, ((w - rot.width) // 2, 10 + obj.height + 4))
    return v


def cartel(lineas, tipo=1):
    """Cartel de madera en dos postes (para el del parque): ventana del juego sobre postes."""
    f = fuente()
    w = max(f.ancho(l) for l in lineas) + 36
    w = max(32, (w + 7) // 8 * 8)
    h = 10 + 14 * len(lineas)
    h = (h + 7) // 8 * 8
    panel = ventana_mensaje(w, max(24, h), tipo)
    for i, l in enumerate(lineas):
        f.dibujar(panel, l, (w - f.ancho(l)) // 2, 5 + i * 14)
    out = Image.new('RGBA', (w, panel.height + 10))
    for x in (6, w - 9):
        for y in range(panel.height - 2, panel.height + 10):
            out.putpixel((x, y), (0, 0, 0, 255))
            out.putpixel((x + 1, y), (150, 100, 60, 255))
            out.putpixel((x + 2, y), (110, 70, 40, 255))
            out.putpixel((x + 3, y), (0, 0, 0, 255))
    out.alpha_composite(panel, (0, 0))
    return out


def pipa():
    """Icono 24x24 de una pipa de fumar, al estilo de los iconos de objetos (contorno oscuro, 3 tonos)."""
    M = ((178, 112, 64), (138, 82, 46), (96, 56, 32))
    N = (40, 28, 24)
    a = np.zeros((24, 24, 4), np.uint8)
    for y in range(8, 18):                 # cazoleta
        for x in range(4, 12):
            a[y, x] = (*M[0 if x < 7 else 1 if x < 10 else 2], 255)
    a[8, 5:11] = (*N, 255)                 # boca negra
    a[9, 6:10] = (60, 40, 30, 255)
    for x in range(12, 21):                # boquilla
        y = 14 - (x - 12) // 3
        a[y, x] = (*M[1], 255)
        a[y + 1, x] = (*M[2], 255)
    alfa = a[..., 3].copy()
    for y in range(24):
        for x in range(24):
            if not alfa[y, x] and any(0 <= y + dy < 24 and 0 <= x + dx < 24 and alfa[y + dy, x + dx]
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                a[y, x] = (*N, 255)
    return Image.fromarray(a, 'RGBA')


def mapa_dibujado():
    """El mapa del tesoro dibujado a mano en un folio: caminos a rotulador azul, árboles y una X roja."""
    w, h = 72, 52
    a = np.zeros((h, w, 4), np.uint8)
    a[:, :] = (246, 246, 236, 255)
    a[0, :] = a[-1, :] = a[:, 0] = a[:, -1] = (150, 150, 140, 255)
    img = Image.fromarray(a, 'RGBA')
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    azul = (64, 88, 208, 255)
    d.line([(6, 44), (18, 36), (30, 38), (40, 26), (52, 22), (60, 12)], fill=azul, width=1)
    d.line([(18, 36), (16, 22), (24, 10)], fill=azul, width=1)
    d.ellipse((34, 32, 50, 44), outline=(64, 140, 220, 255))          # el lago
    for x, y in ((8, 14), (12, 20), (46, 8), (30, 18)):               # arbolitos
        d.polygon([(x, y - 4), (x - 3, y + 2), (x + 3, y + 2)], outline=(40, 140, 64, 255))
    d.line([(57, 9), (63, 15)], fill=(216, 40, 40, 255), width=2)     # la X
    d.line([(63, 9), (57, 15)], fill=(216, 40, 40, 255), width=2)
    return inserto(img, 2, 'EL MAPA')


def cartel_pintado(k=1):
    """El cartel del parque con la pintada WU-TANG encima (en rojo, torcida)."""
    c = cartel(['PARQUE', 'LA GRAJERA'])
    p = texto_img('WU-TANG', (224, 40, 48), (120, 16, 24))
    p = p.rotate(12, expand=True, resample=Image.NEAREST)
    c.alpha_composite(p, ((c.width - p.width) // 2, 2))
    return escalar(c, k)


def banco():
    """Banco de madera del parque (32x16): tablas con los colores de las vallas del juego."""
    M = ((214, 162, 104), (170, 118, 70), (120, 80, 48))
    N = (48, 32, 24)
    a = np.zeros((16, 32, 4), np.uint8)
    for y, c in ((3, 0), (4, 1), (6, 0), (7, 1), (8, 2)):
        a[y, 1:31] = (*M[c], 255)
    a[2, 1:31] = a[9, 1:31] = (*N, 255)
    a[2:10, 0] = a[2:10, 31] = (*N, 255)
    a[5, 1:31] = (*N, 255)
    for x in (4, 26):
        a[10:15, x:x + 2] = (*M[2], 255)
        a[10:15, x - 1] = a[10:15, x + 2] = (*N, 255)
        a[15, x - 1:x + 3] = (*N, 255)
    return Image.fromarray(a, 'RGBA')


def rama():
    """Rama seca de pino (icono 32x32 con contorno, como los objetos del juego)."""
    M = ((170, 120, 72), (124, 84, 50))
    N = (48, 32, 24)
    a = np.zeros((32, 32, 4), np.uint8)
    for k in range(22):                       # tronco en diagonal
        x, y = 5 + k, 26 - k
        a[y, x] = (*M[0], 255)
        a[y + 1, x] = (*M[1], 255)
    for k in range(7):                        # ramita
        x, y = 15 + k, 16 - k // 2 - k
        if y >= 0:
            a[y, x - 6] = (*M[0], 255)
    for x, y in ((10, 9), (11, 10), (9, 8), (22, 4), (23, 5), (21, 3)):   # agujas
        a[y, x] = (96, 140, 64, 255)
    alfa = a[..., 3].copy()
    for y in range(32):
        for x in range(32):
            if not alfa[y, x] and any(0 <= y + dy < 32 and 0 <= x + dx < 32 and alfa[y + dy, x + dx]
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                a[y, x] = (*N, 255)
    return Image.fromarray(a, 'RGBA')


def caja_proyecto(k=1):
    """La caja blanca de EL PROYECTO (prop del mapa, 20x14) dibujada con colores del juego."""
    w, h = 20, 14
    a = np.zeros((h, w, 4), np.uint8)
    a[1:h - 1, 1:w - 1] = (236, 240, 248, 255)
    a[1:4, 1:w - 1] = (248, 248, 255, 255)          # tapa
    a[4, 1:w - 1] = (184, 192, 212, 255)
    a[h - 3:h - 1, 1:w - 1] = (200, 206, 224, 255)
    a[0, :] = a[h - 1, :] = a[:, 0] = a[:, w - 1] = (40, 40, 56, 255)
    a[0, 0] = a[0, w - 1] = a[h - 1, 0] = a[h - 1, w - 1] = 0
    for x in range(4, 16, 2):                        # rótulo azul a rotulador
        a[7, x] = (72, 96, 200, 255)
        a[9, x + 1] = (72, 96, 200, 255)
    img = Image.fromarray(a, 'RGBA')
    return escalar(img, k)


def caja_grande():
    """Inserto de la caja con «EL PROYECTO» escrito a rotulador azul."""
    w, h = 120, 64
    a = np.zeros((h, w, 4), np.uint8)
    a[2:h - 2, 2:w - 2] = (240, 242, 250, 255)
    a[2:12, 2:w - 2] = (250, 250, 255, 255)
    a[12:14, 2:w - 2] = (190, 196, 214, 255)
    a[:2, :] = a[h - 2:, :] = a[:, :2] = a[:, w - 2:] = (40, 40, 56, 255)
    img = Image.fromarray(a, 'RGBA')
    azul = ((60, 84, 200), (150, 170, 240))
    t1, t2 = texto_img('EL', *azul), texto_img('PROYECTO', *azul)
    img.alpha_composite(t1, ((w - t1.width) // 2, 20))
    img.alpha_composite(t2, ((w - t2.width) // 2, 38))
    return inserto(img, 1)


def escenario(fase=0):
    """Pantalla completa de concierto: fondo de combate morado de noche, tablas del escenario, un foco y el
    guitarrista del juego (x2). fase 0/1 lo sube y baja 2 px (lleva el ritmo)."""
    fondo = imagen('combate/fondos/fondo_15_noche.png').crop((0, 0, 256, 80)).resize((256, 152), Image.NEAREST)
    out = Image.new('RGBA', (256, 192), (0, 0, 0, 255))
    out.alpha_composite(fondo, (0, 0))
    a = np.array(out)
    for y in range(152, 192):                                   # tablas del escenario
        a[y, :] = (96, 60, 40, 255) if (y - 152) % 8 else (48, 28, 20, 255)
    a[152, :] = (200, 150, 96, 255)
    luz = np.zeros((192, 256), np.float32)                      # cono del foco
    for y in range(192):
        m = 20 + y * 0.35
        luz[y, int(max(0, 128 - m)):int(min(256, 128 + m))] = 0.22
    a[..., :3] = np.clip(a[..., :3] + luz[..., None] * 255, 0, 255).astype(np.uint8)
    out = Image.fromarray(a, 'RGBA')
    g = imagen('entrenadores/frente/estatico/052_guitarrista.png')
    g = escalar(g.crop((0, 0, 80, 80)), 2)
    out.alpha_composite(g, (128 - 80, 166 - 160 + 2 * fase))
    return out


def _contorno(a, color=(32, 24, 32)):
    alfa = a[..., 3].copy()
    h, w = alfa.shape
    for y in range(h):
        for x in range(w):
            if not alfa[y, x] and any(0 <= y + dy < h and 0 <= x + dx < w and alfa[y + dy, x + dx]
                                      for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                a[y, x] = (*color, 255)
    return a


def ala(oscura=False):
    """Ala izquierda de 20x18 en plumas escalonadas (3 tonos + contorno)."""
    T = ((88, 72, 96), (60, 48, 72), (40, 32, 52)) if oscura else ((252, 252, 255), (216, 222, 240), (172, 180, 208))
    a = np.zeros((18, 20, 4), np.uint8)
    for x in range(1, 19):                        # x=1 punta exterior (arriba), x=18 junto a la espalda
        top = 1 + x * 5 // 18
        bot = min(16, 5 + x * 9 // 18 + (2 if x % 4 < 2 else 0))     # plumas festoneadas
        for y in range(top, bot + 1):
            c = 0 if y < top + 3 else (2 if x % 4 == 3 else 1)
            a[y, x] = (*T[c], 255)
    return Image.fromarray(_contorno(a), 'RGBA')


def angel(sprite, oscuro=False, halo=False, luz=False):
    """Compone un ángel: alas detrás del sprite (32x32, frame de frente), halo dorado y/o luz en el pecho."""
    out = Image.new('RGBA', (64, 44))
    iz = ala(oscuro)
    out.alpha_composite(iz, (6, 10))
    out.alpha_composite(iz.transpose(Image.FLIP_LEFT_RIGHT), (38, 10))
    out.alpha_composite(sprite, (16, 12))
    if halo:
        from PIL import ImageDraw
        d = ImageDraw.Draw(out)
        d.ellipse((25, 5, 38, 10), outline=(248, 216, 72, 255), width=2)
    if luz:
        a = np.array(out).astype(np.float32)
        yy, xx = np.mgrid[0:44, 0:64]
        g = np.exp(-((xx - 32) ** 2 + (yy - 35) ** 2) / 14.0)[..., None]
        a[..., :3] = a[..., :3] * (1 - g) + np.array((255, 244, 200)) * g
        a[..., 3] = np.maximum(a[..., 3], (g[..., 0] * 255))
        out = Image.fromarray(a.clip(0, 255).astype(np.uint8), 'RGBA')
    return out


def movil(mensajes=4):
    """Móvil en la mano (40x70): carcasa negra con una pantalla de chat (burbujas blancas y verdes)."""
    a = np.zeros((70, 40, 4), np.uint8)
    a[1:69, 1:39] = (40, 40, 48, 255)
    a[6:62, 4:36] = (236, 232, 224, 255)
    a[6:12, 4:36] = (72, 136, 104, 255)                        # cabecera del grupo
    for i in range(mensajes):
        y = 15 + i * 11
        if i % 3 == 2:
            a[y:y + 8, 14:34] = (208, 244, 184, 255)
        else:
            a[y:y + 8, 6:28] = (255, 255, 255, 255)
            a[y + 1, 8:16] = ((216, 64, 96, 255), (120, 96, 200, 255), (224, 128, 48, 255))[i % 3]
        a[y + 4, (16 if i % 3 == 2 else 8):(30 if i % 3 == 2 else 24)] = (120, 120, 120, 255)
    a[64:66, 17:23] = (90, 90, 100, 255)
    return Image.fromarray(_contorno(a, (16, 16, 20)), 'RGBA')


def llamas():
    """Llamaradas: las tres bolas rojas y naranjas del impacto de los ataques (efectos_ataques/33)."""
    return efecto(33)


def titulo(texto, k=3, color=(248, 248, 248), sombra=(80, 80, 96)):
    return texto_img(texto, color, sombra, k)


def efecto(n, celdas=None):
    """Celdas de efectos_ataques/<n> como lista de imágenes."""
    import glob
    fs = sorted(glob.glob(os.path.join(SPR, 'efectos_ataques', '%02d' % n, 'celda_*.png')))
    ims = [imagen(f) for f in fs]
    ims = [im.crop(im.getbbox()) for im in ims if im.getbbox()]
    return ims if celdas is None else [ims[i] for i in celdas]


def humo():
    return [imagen('efectos_mapa/058/ug_ef_smoke_%d.png' % i) for i in (1, 2, 3, 4)]


def polvo():
    return [imagen('efectos_mapa/112/kemuri_%d.png' % i) for i in (1, 2)]


def exportar(esc, nombre, t_ini, t_fin, desde=None):
    """Exporta el tramo [t_ini, t_fin] del vídeo con su trozo de la mezcla final (voces + música Platino)."""
    os.makedirs(SALIDA, exist_ok=True)
    esc.exportar(os.path.join(SALIDA, nombre), duracion=t_fin - t_ini, audio_base=AUDIO, desde=desde)
