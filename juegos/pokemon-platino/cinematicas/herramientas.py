"""Utilidades para preparar escenas.

  python herramientas.py personajes            -> <trabajo>/_personajes.png  (todos, con su número)
  python herramientas.py personaje <nombre>    -> <trabajo>/_personaje_<nombre>.png (frames numerados)
  python herramientas.py catalogo              -> <trabajo>/_catalogo.png (suelos y objetos del motor)
  python herramientas.py mapa <zona> [hora]     -> <trabajo>/_mapa_<zona>.png (mapa real con rejilla de tiles)
  python herramientas.py mapa <fila> <col> <filas> <cols>   (cualquier trozo de la matriz de Sinnoh)
  python herramientas.py mapa land <id>         (un interior suelto de land_data)
  python herramientas.py frames escenas/<x>.py 10 55 120     -> <trabajo>/_frames_<x>.png (frames ampliados x2,
                                                    con su número; sin argumentos: 12 frames repartidos)
"""
import os
import sys
import glob

from PIL import Image, ImageDraw

from motor import catalogo
from motor.mapa_real import MapaReal, ZONAS, INTERIORES
from motor.recursos import SPR, TRABAJO, frames_personaje, carpeta_personaje

SALIDA = TRABAJO          # las imágenes de revisión van a la carpeta de trabajo


def personajes():
    dirs = sorted(glob.glob(os.path.join(SPR, 'personajes_mapa', '*')))
    cols, cw, ch = 12, 96, 52
    hoja = Image.new('RGBA', (cols * cw, ((len(dirs) + cols - 1) // cols) * ch), (90, 150, 190, 255))
    d = ImageDraw.Draw(hoja)
    for k, p in enumerate(dirs):
        fr = sorted(glob.glob(os.path.join(p, 'frame_*.png')))
        if not fr:
            continue
        im = Image.open(fr[4] if len(fr) >= 16 else fr[0]).convert('RGBA')  # mirando abajo
        x, y = (k % cols) * cw, (k // cols) * ch
        hoja.alpha_composite(im, (x + 32, y + 18))
        d.text((x + 2, y + 2), os.path.basename(p)[:15], fill='black')
    hoja.save(os.path.join(SALIDA, '_personajes.png'))
    print(os.path.join(SALIDA, '_personajes.png'))


def personaje(nombre):
    fr = frames_personaje(nombre)
    hoja = Image.new('RGBA', (len(fr) * 34, 48), (90, 150, 190, 255))
    d = ImageDraw.Draw(hoja)
    for i, im in enumerate(fr):
        hoja.alpha_composite(im, (i * 34, 14))
        d.text((i * 34 + 2, 0), str(i), fill='black')
    hoja = hoja.resize((hoja.width * 3, hoja.height * 3), Image.NEAREST)
    d = carpeta_personaje(nombre)
    etiqueta = os.path.basename(os.path.dirname(d)) if os.path.basename(d) == 'mapa' else os.path.basename(d)
    out = os.path.join(SALIDA, '_personaje_%s.png' % etiqueta)
    hoja.save(out)
    print(out)


def catalogo_png():
    items = [('suelo', n, catalogo.frames_suelo(n)[0]) for n in catalogo.SUELOS]
    for n in catalogo.OBJETOS:
        piezas = catalogo.piezas_objeto(n)
        im = Image.new('RGBA', (48, 64))
        for p, (ox, oy) in piezas:
            im.alpha_composite(p, (8 + ox, 40 + oy))
        items.append(('objeto', n, im))
    cols, cw, ch = 6, 110, 90
    hoja = Image.new('RGBA', (cols * cw, ((len(items) + cols - 1) // cols) * ch), (90, 150, 190, 255))
    d = ImageDraw.Draw(hoja)
    for k, (tipo, n, im) in enumerate(items):
        x, y = (k % cols) * cw, (k // cols) * ch
        hoja.alpha_composite(im.crop((0, 0, min(im.width, 64), min(im.height, 64))), (x + 4, y + 14))
        d.text((x + 2, y + 2), '%s: %s' % (tipo, n), fill='black')
    out = os.path.join(SALIDA, '_catalogo.png')
    hoja.save(out)
    print(out)


def frames(ruta, indices):
    """Renderiza una escena sin exportar y guarda los frames pedidos ampliados para revisarlos."""
    import runpy
    g = runpy.run_path(ruta, run_name='revision')
    fr = list(g['esc'].frames())
    if not indices:
        indices = [round(i * (len(fr) - 1) / 11) for i in range(12)]
    cols = 3
    w, h = 512, 384
    hoja = Image.new('RGB', (cols * w, ((len(indices) + cols - 1) // cols) * (h + 14)), (255, 255, 255))
    d = ImageDraw.Draw(hoja)
    for k, i in enumerate(indices):
        i = min(max(i, 0), len(fr) - 1)
        x, y = (k % cols) * w, (k // cols) * (h + 14)
        d.text((x + 2, y), 'frame %d / %d  (%.1f s)' % (i, len(fr) - 1, i / 30), fill='black')
        hoja.paste(fr[i].resize((w, h), Image.NEAREST), (x, y + 14))
    out = os.path.join(SALIDA, '_frames_%s.png' % os.path.splitext(os.path.basename(ruta))[0])
    hoja.save(out)
    print('%d frames en total ->' % len(fr), out)


if __name__ == '__main__':
    os.makedirs(SALIDA, exist_ok=True)
    cmd = sys.argv[1] if len(sys.argv) > 1 else ''
    if cmd == 'personajes':
        personajes()
    elif cmd == 'personaje':
        personaje(sys.argv[2])
    elif cmd == 'catalogo':
        catalogo_png()
    elif cmd == 'frames':
        frames(sys.argv[2], [int(v) for v in sys.argv[3:]])
    elif cmd == 'mapa':
        a = sys.argv[2:]
        if a and (a[0] in ZONAS or a[0] in INTERIORES):
            m = MapaReal(a[0], hora=float(a[1]) if len(a) > 1 else 12)
        elif a and a[0] == 'land':
            m = MapaReal(land=int(a[1]))
        else:
            m = MapaReal(fila=int(a[0]), col=int(a[1]), filas=int(a[2]), cols=int(a[3]))
        print(m.plano(os.path.join(SALIDA, '_mapa_%s.png' % m.nombre)))
    else:
        print(__doc__)
