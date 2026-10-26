"""Herramientas para elegir bases y medir colores al crear personajes custom.

  python tools/custom/herramientas.py bases mapa      -> sprites_custom/_bases/mapa.png (todos mirando abajo)
  python tools/custom/herramientas.py bases frente    -> sprites_custom/_bases/frente.png (frontales de combate)
  python tools/custom/herramientas.py bases espalda   -> sprites_custom/_bases/espalda.png
  python tools/custom/herramientas.py ampliar mapa 027 [el_pana ...] -> los 16 frames x8 con rejilla y coordenadas
                                                    (bases del juego o personajes custom)
  python tools/custom/herramientas.py ampliar frente 024 / espalda 02 -> el sprite x6 con rejilla
  python tools/custom/herramientas.py paleta mapa 027 -> colores por zona (cabeza / torso / piernas) en consola
  python tools/custom/herramientas.py paleta frente 024
"""
import glob
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comun  # noqa: E402

OUT = os.path.join(comun.CUSTOM, '_bases')


def _hoja(items, cw, ch, escala, cols, ruta):
    hoja = Image.new('RGBA', (cols * cw, ((len(items) + cols - 1) // cols) * ch), comun.FONDO)
    d = ImageDraw.Draw(hoja)
    for k, (et, im) in enumerate(items):
        x, y = (k % cols) * cw, (k // cols) * ch
        hoja.alpha_composite(im.resize((im.width * escala, im.height * escala), Image.NEAREST), (x + 2, y + 12))
        d.text((x + 2, y), et[:22], fill='black')
    hoja.save(ruta)
    print(ruta)


def bases(tipo):
    os.makedirs(OUT, exist_ok=True)
    if tipo == 'mapa':
        items = []
        for c in sorted(glob.glob(os.path.join(comun.SPR, 'personajes_mapa', '*'))):
            fr = sorted(glob.glob(os.path.join(c, 'frame_*.png')))
            if len(fr) < 16 or 'ketsuban' in c:
                continue               # solo personas que andan (16 frames) y sin huecos vacíos
            im = Image.open(fr[4]).convert('RGBA')
            if im.getbbox() is None:
                continue
            items.append((os.path.basename(c), im))
        _hoja(items, 100, 78, 2, 16, os.path.join(OUT, 'mapa.png'))
    elif tipo == 'frente':
        items = [(os.path.basename(f)[:-4], Image.open(f).convert('RGBA').crop((0, 0, 80, 80)))
                 for f in sorted(glob.glob(os.path.join(comun.SPR, 'entrenadores', 'frente', 'estatico', '*.png')))]
        _hoja(items, 164, 176, 2, 10, os.path.join(OUT, 'frente.png'))
    else:
        items = [(os.path.basename(f)[:-4], Image.open(f).convert('RGBA'))
                 for f in sorted(glob.glob(os.path.join(comun.SPR, 'entrenadores', 'espalda', 'estatico', '*.png')))]
        _hoja(items, 330, 176, 2, 4, os.path.join(OUT, 'espalda.png'))


def _rejilla(im, escala, paso):
    big = Image.new('RGBA', im.size, comun.FONDO)
    big.alpha_composite(im)
    big = big.resize((im.width * escala, im.height * escala), Image.NEAREST)
    lienzo = Image.new('RGBA', (big.width + 24, big.height + 14), (255, 255, 255, 255))
    lienzo.paste(big, (24, 14))
    d = ImageDraw.Draw(lienzo)
    for g in range(0, im.width + 1):
        c = (90, 90, 120, 255) if g % paso == 0 else (175, 175, 195, 255)
        if g % paso == 0 or escala >= 8:
            d.line([(24 + g * escala, 14), (24 + g * escala, 14 + big.height)], fill=c)
        if g % paso == 0 and g < im.width:
            d.text((24 + g * escala + 1, 2), str(g), fill='black')
    for g in range(0, im.height + 1):
        c = (90, 90, 120, 255) if g % paso == 0 else (175, 175, 195, 255)
        if g % paso == 0 or escala >= 8:
            d.line([(24, 14 + g * escala), (24 + big.width, 14 + g * escala)], fill=c)
        if g % paso == 0 and g < im.height:
            d.text((2, 14 + g * escala + 1), str(g), fill='black')
    return lienzo


def ampliar(tipo, nombres):
    os.makedirs(OUT, exist_ok=True)
    for nombre in nombres:
        if tipo == 'mapa':
            fr = [Image.fromarray(f) for f in comun.frames_mapa(nombre)]
            celdas = [_rejilla(f, 8, 4) for f in fr]
            w, h = celdas[0].size
            hoja = Image.new('RGBA', (4 * w, 4 * (h + 12)), (255, 255, 255, 255))
            d = ImageDraw.Draw(hoja)
            for i, c in enumerate(celdas):
                x, y = (i % 4) * w, (i // 4) * (h + 12)
                d.text((x + 24, y), 'frame %d (%s)' % (i, comun.DIRS[i]), fill=(200, 0, 0))
                hoja.paste(c, (x, y + 12))
            d = comun.carpeta_mapa(nombre)
            etiqueta = nombre if d.startswith(comun.CUSTOM) else os.path.basename(d)
            ruta = os.path.join(OUT, 'ampliar_mapa_%s.png' % etiqueta)
        else:
            px = comun.frente_base(nombre) if tipo == 'frente' else comun.espalda_base(nombre)
            hoja = _rejilla(Image.fromarray(px), 6, 8)
            ruta = os.path.join(OUT, 'ampliar_%s_%s.png' % (tipo, nombre))
        hoja.save(ruta)
        print(ruta)


def paleta(tipo, nombre):
    if tipo == 'mapa':
        fr = comun.frames_mapa(nombre)
        print('Mapa %s. Zonas orientativas (filas): cabeza 0-20, torso 21-25, piernas 26-31.'
              % os.path.basename(comun.carpeta_mapa(nombre)))
        for zona, y0, y1 in (('cabeza', 0, 21), ('torso', 21, 26), ('piernas', 26, 32)):
            tot = {}
            for f in fr:
                for c, n in comun.colores(f, y0, y1):
                    tot[c] = tot.get(c, 0) + n
            print('  %-8s' % zona + '  '.join('%s x%d' % (c, n) for c, n in sorted(tot.items(), key=lambda t: -t[1])))
        todos = {c for f in fr for c, _ in comun.colores(f)}
        print('  total: %d colores' % len(todos))
    else:
        px = comun.frente_base(nombre) if tipo == 'frente' else comun.espalda_base(nombre)
        for y0 in range(0, px.shape[0], 10):
            cs = comun.colores(px, y0, y0 + 10)
            if cs:
                print('  filas %2d-%2d: ' % (y0, y0 + 9) + '  '.join('%s x%d' % (c, n) for c, n in cs))


if __name__ == '__main__':
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == 'bases':
        bases(a[1] if len(a) > 1 else 'mapa')
    elif a[0] == 'ampliar':
        ampliar(a[1], a[2:])
    elif a[0] == 'paleta':
        paleta(a[1], a[2])
    else:
        print(__doc__)
