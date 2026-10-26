"""Compositor 2D de 256x192 (vecino más cercano) para las escenas del vídeo."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'nsmb'))
import numpy as np
from PIL import Image
import chars, text

SW, SH = 256, 192
CAMY = 336                     # fila 21 del nivel: la ventana de 192 px acaba en el borde inferior (528)
SKY = (24, 144, 255)


def tile_h(img, off, w=SW):
    """Recorta w px de una imagen repitiéndola horizontalmente (parallax)."""
    iw = img.width; off = int(off) % iw
    out = Image.new('RGBA', (w, img.height))
    x = -off
    while x < w:
        out.alpha_composite(img, (x, 0)); x += iw
    return out


class Scene:
    def __init__(self, world):
        self.w = world
        self.mario = chars.mario()
        self.goomba, self.koopa, self.flag = chars.goomba(), chars.koopa(), chars.goal_flag()
        self.coin_ico = world.coin_img
        self.back_full = world.back; self.free_full = world.free
        self.level = world.layer

    # ---------------------------------------------------------------- piezas
    def paste(self, dst, im, og, x, y, cam, camy=CAMY):
        dst.alpha_composite(im, (int(round(x - cam - og[0])), int(round(y - camy - og[1]))))

    def mario_pose(self, f, t60):
        st = f['state']
        if st == 'pole':
            return 'tree_pose', 0
        if st == 'walk' and f['st'] > 20:
            return 'walk', int(f['x'] * 0.9) % 60
        if st == 'walk':
            return 'goal_jump', min(19, f['st'])
        if f['air']:
            return ('jump', 5) if f['vy'] < 0 else ('jumped', 4)
        if f.get('wait'):
            return 'wait', (t60 // 2) % 160
        return 'run', int(f['x'] * 0.9) % 60

    def frame(self, f, t60, hud=True, wait=False, time_left=None):
        w = self.w; cam = int(round(f['cam'])); cy = int(round(f.get('camy', CAMY)))
        img = Image.new('RGBA', (SW, SH), (*SKY, 255))
        yb = SH - 512 + 22 + int((CAMY - cy) * 0.5)
        img.alpha_composite(tile_h(self.back_full, cam * 0.18), (0, yb))
        img.alpha_composite(tile_h(self.free_full, cam * 0.45), (0, yb + 8))
        img.alpha_composite(self.level.crop((cam, cy, cam + SW, cy + SH)))
        for cx, cy_ in f['coins']:
            px, py = cx * 16 - cam, cy_ * 16 - cy
            if -16 < px < SW: img.alpha_composite(self.coin_ico, (px, py))
        # bandera: baja con Mario
        px_ = w.pole[0] * 16 + 8
        top = w.pole[1] * 16 + 20; base = (w.pole[1] + w.pole[2]) * 16 - 30
        fy = top
        if f['state'] in ('pole', 'walk'):
            fy = top + (base - top) * min(1.0, max(0.0, (f['y'] - (w.pole[1] * 16 + 40)) / max(1, base + 20 - (w.pole[1] * 16 + 40))))
        fim, fog = self.flag.sprite('wait', (t60 // 2) % 120)
        fim, fog = self.flag.sprite('wait', (t60 // 2) % 120, facing=-1)
        self.paste(img, fim, fog, px_ + 1, fy, cam, cy)
        for kind, ex, ey, sq in f['foes']:
            if kind == 'g':
                if sq: im, og = self.goomba.sprite('damage', 6)
                else: im, og = self.goomba.sprite('walk', (t60 // 2) % int(self.goomba.anims['walk'].num_frames))
            else:
                im, og = self.koopa.sprite('walk', (t60 // 2) % int(self.koopa.anims['walk'].num_frames), facing=-1)
            self.paste(img, im, og, ex, ey, cam, cy)
        an, fr = self.mario_pose(dict(f, wait=wait), t60)
        mim, mog = self.mario.sprite(an, fr)
        self.paste(img, mim, mog, f['x'], f['y'], cam, cy)
        if hud: self.hud(img, f, time_left)
        return img

    def hud(self, img, f, time_left):
        img.alpha_composite(text.render('MARIO'), (6, 2))
        img.alpha_composite(self.coin_ico.resize((12, 12), Image.NEAREST), (62, 4))
        img.alpha_composite(text.render('x%02d' % f['ncoin']), (76, 2))
        img.alpha_composite(text.render('MUNDO 1-1'), (112, 2))
        if time_left is not None:
            img.alpha_composite(text.render('TIEMPO %03d' % time_left), (SW - 72, 2))


def fade(img, k):
    """k 0 = negro, 1 = normal."""
    a = np.asarray(img.convert('RGB')).astype(np.float32) * k
    return Image.fromarray(a.astype(np.uint8), 'RGB')
