"""Extrae el casino de su NARC y genera vistas de comprobación. ROM sólo lectura."""
from pathlib import Path
import sys
import json
import math

import ndspy.narc
import ndspy.lz10
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'nsmb'))
import rom
import nitro3d as N
import chars

OUT = Path(rom.rutas.extraidos('nsmb')) / 'casino'


def load():
    ar = ndspy.narc.NARC(rom.get('ARCHIVE/casino.narc'))
    data = bytes(ar.files[0])
    if data.startswith(b'LZ77'):
        data = ndspy.lz10.decompress(data[4:])
    return N.Nitro(data)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    n = load()
    textures = []
    for b in n.banks:
        for name in b.texs:
            a = b.decode(name, name + '_pl')
            im = Image.fromarray(a)
            im.save(OUT / (name + '.png'))
            textures.append((name, im))
    sheet = Image.new('RGB', (640, 256), (33, 27, 41))
    for i, (name, im) in enumerate(textures):
        x, y = (i % 5) * 128, (i // 5) * 128
        sheet.paste(im.resize((96, 96), Image.Resampling.NEAREST), (x, y + 20))
        ImageDraw.Draw(sheet).text((x, y), name)
    sheet.save(OUT / 'texturas_contactos.png')
    mdl = n.models[0]
    tris = mdl.triangles()
    pts = np.array([v[:3] for _, t in tris for v in t])
    print('Límites casino:', pts.min(0), pts.max(0), flush=True)
    contact = Image.new('RGB', (768, 576), (25, 18, 36))
    for i, yaw in enumerate((0, 90, 180, 270, 30, -30)):
        a = math.radians(yaw)
        def camera(x, y, z):
            xx = math.cos(a) * x + math.sin(a) * z
            zz = -math.sin(a) * x + math.cos(a) * z
            return xx, -y * .9 + zz * .4
        # Revisar ambos sentidos de cámara sin ocultar las caras del decorado.
        for mat in mdl.materials:
            mat.cull_front = mat.cull_back = False
        img, _ = N.render(tris, mdl, N.TexLookup(n), scale=1.2, ortho=camera)
        im = Image.fromarray(img)
        im.thumbnail((256, 260), Image.Resampling.NEAREST)
        x, y = i % 3 * 256, i // 3 * 288
        contact.paste(im, (x + (256-im.width)//2, y + 20), im)
        ImageDraw.Draw(contact).text((x+4,y+2), 'Camara %d' % yaw)
    contact.save(OUT / 'casino_vistas.png')
    (OUT / 'procedencia.json').write_text(json.dumps({
        'archivo': 'ARCHIVE/casino.narc', 'miembro': 'casino/casino_back.nsbmd',
        'texturas': [name for name, _ in textures], 'rom_modificada': False
    }, ensure_ascii=False, indent=2), encoding='utf8')
    print(OUT, flush=True)


if __name__ == '__main__':
    main()
