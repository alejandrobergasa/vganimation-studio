"""Recursos del casino: modelos y animaciones originales; caché de sprites verificable."""
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
sys.path.insert(0, str(ROOT / 'tools'))
import chars
import nitro3d as N
import extraer_casino
import rom
from rom import rutas

CACHE = Path(rutas.cache('nsmb')) / 'casino' / 'sprites'


def actor(name):
    if name in ('mario', 'luigi'):
        return chars.mario(luigi=name == 'luigi')
    if name == 'koopa':
        return chars.koopa()
    if name == 'toad':
        ar = ndspy.narc.NARC(rom.get('ARCHIVE/luigi_model_mg.narc'))
        def member(i):
            d = bytes(ar.files[i])
            return N.Nitro(ndspy.lz10.decompress(d[4:]) if d.startswith(b'LZ77') else d)
        m = member(0)
        an = chars.anims_of(member(1), member(2))
        pts = np.array([v[:3] for _, tri in m.models[0].triangles(an['kino_wait'], 0) for v in tri])
        return chars.Actor([chars.Part(m)], an, px_per_unit=25/np.ptp(pts[:, 1]),
                           canvas=(112, 112), origin=(56, 100), yaw=20, ambient=.8)
    base, height = {'bowser': ('koopa_new', 48), 'peach': ('peach', 34),
                    'toad': ('kinoji', 25)}[name]
    m = chars.load('enemy/' + base + '.nsbmd')
    an = chars.anims_of(chars.load('enemy/' + base + '.nsbca'))
    key = {'bowser': 'kp_wait', 'peach': 'p_wait', 'toad': 'wait'}[name]
    pts = np.array([v[:3] for _, tri in m.models[0].triangles(an[key], 0) for v in tri])
    scale = height / np.ptp(pts[:, 1])
    return chars.Actor([chars.Part(m)], an, px_per_unit=scale,
                       canvas=(112, 112), origin=(56, 100), yaw=0, ambient=.80)


POSES = {
    'mario': {'wait': 'wait', 'walk': 'walk', 'run': 'run', 'bet': 'carry_throw',
              'mad': 'net_attack', 'shock': 'find_surprise', 'dead': 'dead', 'hold': 'carry_wait'},
    'luigi': {'wait': 'wait', 'walk': 'walk', 'shock': 'find_surprise', 'fear': 'lost'},
    'bowser': {'wait': 'kp_wait', 'laugh': 'kp_roar', 'walk': 'kp_walk'},
    'peach': {'wait': 'p_bt_wait', 'spin': 'p_kiss2', 'shock': 'p_surprise'},
    'toad': {'wait': 'kino_wait', 'run': 'kino_walk'},
    'koopa': {'walk': 'walk', 'wait': 'walk_st', 'attack': 'dive_st', 'recover':'dive_ed'},
}


class Assets:
    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        if not (extraer_casino.OUT / 'floor.png').exists():
            extraer_casino.main()
        self.tex = {p.stem: Image.open(p).convert('RGBA') for p in extraer_casino.OUT.glob('*.png')
                    if p.stem not in ('casino_vistas', 'texturas_contactos')}
        self.sprites = {}
        manifest = {}
        for name, poses in POSES.items():
            a = None
            for pose, animation in poses.items():
                # Dos ángulos: tres cuartos de frente y lateral. El reflejo da el otro sentido.
                for angle in (20, 65):
                    key = (name, pose, angle)
                    version = 'v3' if name == 'peach' else 'v2'
                    path = CACHE / (('%s_%s_%d_' % key) + version + '.png')
                    info = path.with_suffix('.json')
                    if path.exists() and info.exists():
                        meta = json.loads(info.read_text(encoding='utf8'))
                        atlas = Image.open(path).convert('RGBA')
                    else:
                        if a is None:
                            a = actor(name)
                        nf = a.anims[animation].num_frames
                        count = 12
                        frames = np.linspace(0, nf - 1, count, dtype=int)
                        if pose in ('dead', 'shock', 'mad', 'bet', 'spin'):
                            frames = np.linspace(0, min(nf - 1, 35), count, dtype=int)
                        cv = a.canvas
                        atlas = Image.new('RGBA', (cv[0] * count, cv[1]))
                        for i, frame in enumerate(frames):
                            im, origin = a.sprite(animation, int(frame), yaw=angle)
                            atlas.alpha_composite(im, (i * cv[0], 0))
                        meta = {'canvas': cv, 'origin': origin, 'count': count,
                                'animation': animation, 'frames': frames.tolist()}
                        atlas.save(path)
                        info.write_text(json.dumps(meta), encoding='utf8')
                    cw, ch = meta['canvas']
                    self.sprites[key] = ([atlas.crop((i*cw, 0, (i+1)*cw, ch))
                                          for i in range(meta['count'])], tuple(meta['origin']))
                    manifest['%s/%s/%d' % key] = meta
            print('Personaje preparado:', name, flush=True)
        (CACHE.parent / 'animaciones.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')

    def draw(self, im, name, x, feet, pose='wait', t=0, scale=2, facing=1, angle=20, once=False):
        frames, origin = self.sprites[name, pose, angle]
        k = int(t * 12)
        k = min(k, len(frames)-1) if once else k % len(frames)
        s = frames[max(0, k)]
        ox, oy = origin
        if facing < 0:
            s = s.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            ox = s.width - 1 - ox
        size = (max(1, round(s.width * scale)), max(1, round(s.height * scale)))
        s = s.resize(size, Image.Resampling.NEAREST)
        # Una sombra de contacto discreta procede de la textura oscura del taburete.
        shadow = Image.new('RGBA', im.size)
        ImageDraw.Draw(shadow).ellipse((x-11*scale, feet-3*scale, x+11*scale, feet+3*scale), fill=(20, 10, 25, 85))
        im.alpha_composite(shadow)
        im.alpha_composite(s, (round(x - ox * scale), round(feet - oy * scale)))

    def contacts(self):
        names = list(POSES)
        sheet = Image.new('RGBA', (600, 130 * len(names)), (38, 27, 55, 255))
        for row, name in enumerate(names):
            for col, pose in enumerate(list(POSES[name])[:5]):
                self.draw(sheet, name, 60 + col*120, row*130+112, pose, .4, 1.8)
                ImageDraw.Draw(sheet).text((col*120+4, row*130+2), name+'/'+pose)
        sheet.convert('RGB').save(CACHE.parent / 'personajes_contactos.png')


if __name__ == '__main__':
    Assets().contacts()
