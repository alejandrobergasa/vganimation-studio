"""Personajes 3D renderizados como sprites 2D (cámara ortográfica de frente, vista lateral)."""
import numpy as np
from PIL import Image
import rom, nitro3d as N


def rot_y(deg, s=1.0):
    t = np.radians(deg); c, sn = np.cos(t), np.sin(t)
    m = np.eye(4)
    m[0, 0] = c * s; m[0, 2] = sn * s; m[2, 0] = -sn * s; m[2, 2] = c * s; m[1, 1] = s
    return m


class Part:
    """Un modelo (de un fichero BMD0) con su banco de texturas y su ancla al esqueleto."""
    def __init__(self, nitro, idx=0, attach=None):
        self.nitro, self.model, self.attach = nitro, nitro.models[idx], attach


class Actor:
    """parts[0] es el esqueleto; las demás partes se anclan a una de sus pilas (attach).
    anims: {nombre: Anim}. patterns: {nombre: Pattern}."""

    def __init__(self, parts, anims, patterns=None, px_per_unit=1.0, canvas=(64, 64), origin=(32, 56),
                 extra_tex=(), yaw=90.0, light=N.DEFAULT_LIGHT, ambient=0.62):
        self.parts = parts
        self.anims = anims
        self.patterns = patterns or {}
        self.scale = px_per_unit
        self.canvas, self.origin = canvas, origin
        self.yaw = yaw
        self.light, self.ambient = light, ambient
        self.tex = N.TexLookup(*([p.nitro for p in parts] + list(extra_tex)))
        self.cache = {}

    def _items(self, anim, frame, yaw, pattern=None, pframe=0, only=None):
        a = self.anims.get(anim) if anim else None
        base = self.parts[0].model
        R = rot_y(yaw)
        tris = base.triangles(a, frame, root=R)
        stack = base.last_stack
        items = [(tris, base, self.patterns.get(pattern) if pattern else None, pframe)]
        for p in self.parts[1:]:
            root = stack[p.attach] if p.attach is not None else R
            t = p.model.triangles(None, 0, root=root)
            items.append((t, p.model, self.patterns.get(pattern) if pattern else None, pframe))
        return items

    def sprite(self, anim=None, frame=0, facing=1, yaw=None, pattern=None, pframe=0, canvas=None, origin=None, scale=None):
        """RGBA PIL con el origen del modelo en `origin`. facing=-1 refleja horizontalmente."""
        key = (anim, int(frame), facing, yaw, pattern, pframe, canvas, origin, scale)
        if key in self.cache:
            return self.cache[key]
        sc = scale or self.scale
        items = self._items(anim, frame, self.yaw if yaw is None else yaw, pattern, pframe)
        cv = canvas or self.canvas; og = origin or self.origin
        img, _ = N.render_items(items, self.tex, scale=sc, size=cv, origin=og, light=self.light, ambient=self.ambient)
        im = Image.fromarray(img, 'RGBA')
        if facing < 0:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            og = (cv[0] - 1 - og[0], og[1])
        self.cache[key] = (im, og)
        return self.cache[key]


def load(path):
    return N.Nitro(rom.getu(path) if path.endswith('_LZ.bin') else rom.get(path))


def anims_of(*nitros):
    d = {}
    for n in nitros:
        for a in n.anims: d[a.name] = a
    return d


def patterns_of(*nitros):
    d = {}
    for n in nitros:
        for p in n.patterns: d[p.name] = p
    return d


# ---------------------------------------------------------------- fábricas

def mario(small=False, luigi=False, cap=True):
    pre = 'luigi' if luigi else 'mario'
    body = load(f'player/{pre}_model_LZ.bin')
    head = load(f'player/{pre}_head_{"cap" if cap else "nocap"}_LZ.bin')
    anim_files = ['pl_luigi' if luigi else 'pl_mario', 'pl2', 'pl', 'plnovs', 'pl_map']
    an = anims_of(*[load(f'player/{a}_LZ.bin') for a in anim_files])
    pat = patterns_of(load(f'player/{pre}_LZ.bin'))
    mi = 1 if small else 0
    return Actor([Part(body, mi), Part(head, mi, attach=15)], an, pat,
                 px_per_unit=1.6 * (0.6 if small else 1.0), canvas=(64, 64), origin=(32, 58))   # el modelo small_model usa otra escala


def goomba():
    m = load('enemy/kuribo.nsbmd')
    an = anims_of(load('enemy/kuribo.nsbca'))
    pat = patterns_of(load('enemy/kuribo.nsbtp'))
    return Actor([Part(m)], an, pat, px_per_unit=1.0, canvas=(40, 36), origin=(20, 31))


def koopa():
    m = load('enemy/nokonoko.nsbmd')
    an = anims_of(load('enemy/nokonoko.nsbca'))
    return Actor([Part(m)], an, {}, px_per_unit=0.85, canvas=(56, 56), origin=(28, 42))


def goal_flag():
    m = load('enemy/obj_goal_flag.nsbmd')
    an = anims_of(load('enemy/obj_goal_flag.nsbca'))
    return Actor([Part(m)], an, {}, px_per_unit=1.0, canvas=(64, 64), origin=(32, 32), yaw=0.0)
