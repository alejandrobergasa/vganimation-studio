"""Personaje custom «lincelucas»: un lince ibérico hecho con el modelo de gato `npc/model/16/17` de la ROM.

No hay modelos nuevos: se recolorean las texturas del propio juego (pelaje azul → arena anaranjado, pelo/línea de la boca →
marrón oscuro), se añaden las manchas negras del lince ibérico en cuerpo y mejillas y los mechones negros en la punta de las orejas.
Uso:
    from personajes.lincelucas import cargar
    asset = cargar(rom, clips)            # Asset listo para el motor (mismos clips y texturas e.N / m.N que el original)
    python -I video/personajes/lincelucas.py   # exporta biblioteca/animal-crossing/personalizados/lincelucas/*.png y vistas de prueba
"""
import colorsys
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
from motor import Asset, Rom, rutas      # noqa: E402

MODELO = 'npc/model/16/17.nsbmd'
TEXTURAS = 'npc/model/16/17.nsbtx'
HUE = 29 / 360.0                    # naranja arena
SAT = 0.88                          # factor de saturación del pelaje
VAL = 0.93
MANCHA = np.array([58, 34, 22], np.float32)
MECHON = np.array([28, 22, 22], np.float32)


def _recolor(arr):
    """Azul de pelaje → pelaje de lince; el blanco y los tonos no azules (rosa, rojo, negro) se conservan."""
    out = arr.copy()
    rgb = arr[..., :3].astype(np.float32) / 255.0
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    blue = (rgb[..., 2] >= mx - 1e-6) & (d > 0.16) & (rgb[..., 2] > rgb[..., 0] + 0.1)
    for y, x in zip(*np.nonzero(blue)):
        h, s, v = colorsys.rgb_to_hsv(*rgb[y, x])
        out[y, x, :3] = (np.array(colorsys.hsv_to_rgb(HUE, min(1.0, s * SAT), v * VAL)) * 255 + 0.5).astype(np.uint8)
    return out, blue


def _manchas(arr, fur, seed, n, region=None):
    """Salpica manchas pequeñas (1-2 px) de color oscuro solo sobre píxeles de pelaje."""
    rng = np.random.RandomState(seed)
    h, w = fur.shape
    y0, y1, x0, x1 = region or (0, h, 0, w)
    for _ in range(n):
        y, x = rng.randint(y0, y1), rng.randint(x0, x1)
        sz = rng.choice([1, 2, 2, 3])
        blob = fur[y:y + sz, x:x + sz]
        if blob.size and blob.all():
            arr[y:y + sz, x:x + sz, :3] = MANCHA.astype(np.uint8)


class BancoLince:
    """Banco de texturas con las del gato recoloreadas; se antepone a los del modelo (tiene prioridad al buscar por nombre)."""

    def __init__(self, orig_banks):
        self.orig = orig_banks
        self.texs = {}
        self.pals = {}
        for b in orig_banks:
            self.texs.update({k: b for k in b.texs})
            self.pals.update({k: b for k in b.pals})
        self.pal_size = 1024
        self._cache = {}

    def decode(self, name, pal, src=None):
        key = (name, pal)
        if key in self._cache:
            return self._cache[key]
        tb = self.texs[name]
        sb = self.pals.get(pal, tb)
        arr = np.array(tb.decode(name, pal, sb))
        if arr.shape[-1] == 4 and name in ('b0',) or name.startswith(('e.', 'm.')):
            out, fur = _recolor(arr)
            if name == 'b0':
                _manchas(out, fur & (out[..., 3] > 0), 7, 230)
                # mechones de las orejas: el degradado blanco de la esquina superior se vuelve negro hacia la punta
                reg = out[:14, :16, :3].astype(np.float32)
                w = np.clip((reg.min(-1) - 40) / 90.0, 0, 1)[..., None]
                out[:14, :16, :3] = (reg * (1 - w) + MECHON * w + 0.5).astype(np.uint8)
                # patas, manos y punta de la cola: crema en vez de blanco puro
                for ya, yb, xa, xb in ((0, 7, 40, 64), (12, 18, 54, 64)):
                    r2 = out[ya:yb, xa:xb, :3].astype(np.float32)
                    k = (r2.min(-1) > 220)[..., None]
                    out[ya:yb, xa:xb, :3] = np.where(k, np.array([246, 232, 205]), r2).astype(np.uint8)
            elif name.startswith('e.'):
                _manchas(out, fur & (out[..., 3] > 0), 5, 12)
            elif name.startswith('m.'):
                _manchas(out, fur & (out[..., 3] > 0), 11, 16)
            arr = out
        self._cache[key] = arr
        return arr


def cargar(rom, clips):
    a = Asset(rom, MODELO, [TEXTURAS], clips)
    a.banks.insert(0, BancoLince(list(a.banks)))
    return a


if __name__ == '__main__':
    from PIL import Image
    rom = Rom()
    a = cargar(rom, {})
    out = os.path.join(rutas.personalizados('animal-crossing'), 'lincelucas')
    os.makedirs(out, exist_ok=True)
    banco = a.banks[0]
    for name in sorted(banco.texs):
        pal = next(m.pal for m in a.model.materials if m.tex == name or m.name == name[0]) if False else None
        mat = [m for m in a.model.materials if m.name == name[0]]
        pal = mat[0].pal if mat else None
        if pal is None:
            continue
        arr = banco.decode(name, pal)
        Image.fromarray(np.asarray(arr).astype(np.uint8)).save(os.path.join(out, name.replace('.', '_') + '.png'))
    print('guardado en', os.path.abspath(out))
