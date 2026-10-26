"""Escenario del pueblo: suelo, tienda de Nook, árboles y flores, todo con modelos/texturas de la ROM."""
import numpy as np

from motor import (Rom, Asset, load_clips, Canvas, perspective, look_at, draw_model, build_mesh, TexBank,
                   world_matrix, W, H)

VIEW_FOV = 28.0


class Village:
    def __init__(self, rom):
        self.rom = rom
        self.static = []   # (asset, mesh, world)
        self._ground = TexBank(rom.get('bg/ct0/grd_set0a.nsbtx'))
        self.grass = self._ground.decode('grd_grs', 'grd_pl')
        self.dirt = self._ground.decode('grd_soi', 'grd_pl')
        sx = lambda p, t=(): Asset(rom, p, t)
        shop = sx('str/shop/a/1/obj_ngSs.arc', ['str/shop/n/1/obj_ngSs.nsbtx'])
        cedar = sx('fg/tree/cedar_mdl/cedar_01s.nsbmd', ['fg/tree/cedar_tex/cedar_01s.nsbtx'])
        cedar2 = sx('fg/tree/cedar_mdl/cedar_03s.nsbmd', ['fg/tree/cedar_tex/cedar_03s.nsbtx'])
        tree = sx('fg/tree/tree_mdl/tree_01s.nsbmd', ['fg/tree/tree_tex/tree_01s.nsbtx'])
        tree3 = sx('fg/tree/tree_mdl/tree_03s.nsbmd', ['fg/tree/tree_tex/tree_03s.nsbtx'])
        cosmos = sx('fg/flower/cosmos/cosmos.nsbmd', ['fg/flower/cosmos/cosmos.nsbtx'])
        tulip = sx('fg/flower/tulip/tulip.nsbmd', ['fg/flower/tulip/tulip.nsbtx'])
        pansy = sx('fg/flower/pansy/pansy.nsbmd', ['fg/flower/pansy/pansy.nsbtx'])
        self.add(shop, (0.0, 0, -6.5), 0.0, 1.0)
        for a, p, y, s in [(cedar, (-11, 0, -4), 0.3, 2.6), (cedar2, (-8.5, 0, -9), 1.0, 2.8), (tree, (10, 0, -4), 2.0, 2.4),
                           (tree3, (7.5, 0, -10), 0.5, 2.7), (cedar, (13, 0, -9), 0.0, 2.9), (tree, (-14, 0, 1), 1.0, 2.5),
                           (tree3, (15, 0, 2), 2.5, 2.4)]:
            self.add(a, p, y, s)
        rng = np.random.RandomState(7)
        for i in range(34):
            a = [cosmos, tulip, pansy][i % 3]
            p = (rng.uniform(-12, 12), 0.0, rng.uniform(-6.0, 2.0))
            if abs(p[0]) < 4.5 and p[2] > -1.0:
                continue
            self.add(a, p, rng.uniform(0, 6), 1.0)

    def add(self, asset, pos, yaw, scale):
        w = world_matrix(pos, yaw, scale)
        self.static.append((asset, build_mesh(asset.model), w))

    def sky(self, cv, t_day=0.5):
        top = np.array([96, 168, 248], np.float32) / 255
        hor = np.array([214, 238, 255], np.float32) / 255
        y = np.linspace(0, 1, cv.h)[:, None, None]
        grad = (top * (1 - y) + hor * y) * np.ones((1, cv.w, 1), np.float32)
        cv.color[..., :3] = grad
        cv.color[..., 3] = 1.0

    def draw_ground(self, cv, view, proj):
        tex = self.grass
        th, tw = tex.shape[:2]
        k = 4.0                      # unidades de mundo por repetición
        vp = proj @ view
        step = 4.0
        xs = np.arange(-40, 40 + step, step)
        zs = np.arange(-40, 28 + step, step)
        tris, uvs = [], []
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                x0, x1, z0, z1 = xs[i], xs[i + 1], zs[j], zs[j + 1]
                q = [(x0, 0, z0), (x1, 0, z0), (x1, 0, z1), (x0, 0, z1)]
                uq = [(x0 / k * tw, z0 / k * th), (x1 / k * tw, z0 / k * th), (x1 / k * tw, z1 / k * th), (x0 / k * tw, z1 / k * th)]
                for tri in ((0, 1, 2), (0, 2, 3)):
                    tris.append([q[n] for n in tri])
                    uvs.append([uq[n] for n in tri])
        P = np.array(tris, np.float64)
        clip = np.concatenate([P, np.ones(P.shape[:2] + (1,))], -1) @ vp.T
        cv.draw(clip, np.array(uvs), tex, np.ones((len(P), 3, 3)) * 0.92, 1.0, 0, (True, True, False, False))

    def render(self, view, actors, lights=1.0, tint=(1, 1, 1), fov=VIEW_FOV):
        cv = Canvas(W, H)
        proj = perspective(fov, W / H, 0.5, 200)
        self.sky(cv)
        self.draw_ground(cv, view, proj)
        for asset, mesh, w in self.static:
            draw_model(cv, asset.model, asset.banks, w, view, proj, mesh=mesh, tint=tint)
        for a in actors:
            draw_model(cv, a['asset'].model, a['asset'].banks, a['world'], view, proj, override=a.get('pose'),
                       tex_override=a.get('tex'), tint=tint, ambient=0.78)
        return cv
