"""Mundo 1-1: capas, máscara de colisión, monedas, enemigos y flag. Todo sale de la ROM."""
import sys, os, struct, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'nsmb'))
import numpy as np
from PIL import Image
import rom, level as L, backgrounds as B
from rom import rutas

TS = ('I_M_nohara', 'I_M_tikei_nohara', 'I_S_nohara', 'I_S_tikei_nohara')
COIN, VINE = 0x14, 0x35
SOLID = {0x0, 0x2, 0xd, 0x1e, 0x25, 0x2b, 0x2c, 0x2d, 0x2f, 0x30, 0x31, 0x32, 0x7a,
         0x1000, 0x1006, 0x1007, 0x1008, 0x1009, 0x100a, 0x100e, 0x100f, 0x1038, 0x1048, 0x1049, 0x104a, 0x104b, L.PIPE_OBJ}
CACHE = rutas.cache('nsmb')


class World:
    def __init__(self):
        ts = L.Tileset(*TS); sd = ts.slot_defs()
        self.objs = L.read_bgdat('course/A01_1_bgdat.bin')
        self.W, self.H = 268, 33
        o = self.objs
        self.layer = L.render_level(o, ts, sd, self.W, self.H, skip={COIN, VINE})   # RGBA, sin coin ni vid
        self.solid = np.zeros((self.H * 16, self.W * 16), bool)
        for ob in o:
            if ob[0] in SOLID:
                m = L.render_level([ob], ts, sd, self.W, self.H)
                self.solid |= np.asarray(m)[..., 3] > 0
        # monedas
        cd = sd[0].render(COIN, 1, 1)
        (num, tsid) = next(iter(cd.values()))
        self.coin_img = Image.fromarray(ts.map16_img(tsid, num), 'RGBA')
        self.coins = []
        for typ, x, y, w, h in o:
            if typ == COIN:
                self.coins += [(x + i, y + j) for i in range(w) for j in range(h)]
        # sprites
        b = rom.get('course/A01_1.bin'); off, ln = struct.unpack_from('<2I', b, 6 * 8); p = off; self.sprites = []
        while p + 12 <= off + ln:
            t, x, y = struct.unpack_from('<3H', b, p)
            if t == 0xffff: break
            self.sprites.append((t, x, y)); p += 12
        self.goombas = [(x, y) for t, x, y in self.sprites if t == 0x94]
        self.koopas = [(x, y) for t, x, y in self.sprites if t == 0x95]
        self.pole = next((x, y, h) for t, x, y, w, h in o if t == 0x7b)
        self.back = B.layer('back'); self.free = B.layer('free', alpha2=0.7)

    def ground(self, x, y, reach=400):
        """y del primer píxel sólido en la columna x a partir de y (o None)."""
        x = int(x)
        if x < 0 or x >= self.solid.shape[1]: return None
        y = max(0, int(y))
        col = self.solid[y:y + reach, x]
        if col.size == 0: return None
        i = np.argmax(col)
        return y + int(i) if col[i] else None


def get():
    return World()


if __name__ == '__main__':
    w = get()
    im = Image.new('RGBA', w.layer.size, (90, 160, 255, 255)); im.alpha_composite(w.layer)
    m = np.zeros(w.solid.shape + (4,), np.uint8); m[w.solid] = (255, 0, 0, 110)
    im.alpha_composite(Image.fromarray(m, 'RGBA'))
    for cx, cy in w.coins: im.alpha_composite(w.coin_img, (cx * 16, cy * 16))
    im.convert('RGB').save(os.path.join(CACHE, 'world_dbg.png'))
    print(len(w.coins), w.pole, w.goombas, w.koopas)
