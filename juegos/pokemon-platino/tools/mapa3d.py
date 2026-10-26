"""Renderiza zonas reales de Sinnoh (terreno + edificios) a PNG con profundidad.

Uso:  python mapa3d.py <rom> <salida.png> <fila0> <col0> <filas> <cols> [K] [hora]
(filas/cols en chunks de la matriz 0 = mapa de Sinnoh; cada chunk = 32x32 tiles = 512x512 px)
"""
import sys
import struct
import functools

import numpy as np
import ndspy.rom
import ndspy.narc
from PIL import Image

import ndsgfx as G
import nsbmd as N

CHUNK = 512
Y0 = 128   # margen por arriba: el suelo está a ~y=80 y se proyecta hacia arriba


class Mundo:
    def __init__(self, rom_path, matriz=0):
        """matriz: fichero de map_matrix.narc (0 = Sinnoh; los interiores y cuevas tienen la suya, p. ej. 1
        = 'single', un solo trozo cuyo land_data se elige con usar_land())."""
        self.rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        n = lambda p: ndspy.narc.NARC(self.rom.getFileByName(p)).files
        self.land = n('fielddata/land_data/land_data.narc')
        self.texsets = n('fielddata/areadata/area_map_tex/map_tex_set.narc')
        self.bmtex = n('fielddata/areadata/area_build_model/areabm_texset.narc')
        self.builds = n('fielddata/build_model/build_model.narc')
        self.luz_txt = bytes(n('data/arealight.narc')[0]).decode('latin-1')
        d = bytes(n('fielddata/mapmatrix/map_matrix.narc')[matriz])
        w, h, hh, hm, nl = d[0], d[1], d[2], d[3], d[4]
        p = 5 + nl + (w * h * 2 if hh else 0) + (w * h if hm else 0)
        self.mw, self.mh = w, h
        self.matrix = struct.unpack_from('<%dH' % (w * h), d, p)
        self._names = {}

    def usar_land(self, idx):
        """Usa una matriz de 1x1 con ese land_data (interiores: casas, Centros Pokémon, guaridas...)."""
        self.mw, self.mh, self.matrix = 1, 1, (idx,)

    def tex_names(self, data):
        key = id(data)
        if key not in self._names:
            sec = G.find_tex0(data)
            self._names[key] = {nm for nm, _ in G._dict3d(sec, struct.unpack_from('<H', sec, 0xE)[0], 8)} if sec else set()
        return self._names[key]

    def best_set(self, sets, need):
        return max(sets, key=lambda d: len(need & self.tex_names(d)))

    @functools.lru_cache(maxsize=None)
    def chunk_model(self, idx):
        x = bytes(self.land[idx])
        return N.Model(x[x.find(b'BMD0'):]), x

    @functools.lru_cache(maxsize=None)
    def build_model(self, mid):
        return N.Model(bytes(self.builds[mid]))

    def triangles(self, fila0, col0, filas, cols, edificios=True):
        """Triángulos de mundo + caches de textura para la zona."""
        tris_terr, tris_edif = [], []
        need_t, need_b = set(), set()
        for r in range(filas):
            for c in range(cols):
                idx = self.matrix[(fila0 + r) * self.mw + col0 + c]
                if idx == 0xFFFF:
                    continue
                m, raw = self.chunk_model(idx)
                ox, oz = c * CHUNK + CHUNK / 2, r * CHUNK + CHUNK / 2
                for mat, vs in m.triangles():
                    tris_terr.append((mat, [(x + ox, y, z + oz) + v[3:] for v, (x, y, z) in zip(vs, [v[:3] for v in vs])]))
                need_t |= {mt.texture for mt in m.materials if mt.texture}
                if not edificios:
                    continue
                ps, bs = struct.unpack_from('<II', raw, 0)
                for k in range(bs // 48):
                    v = struct.unpack_from('<I9i', raw, 16 + ps + k * 48)
                    mid = v[0]
                    bx, by, bz = (a / 4096 for a in v[1:4])
                    sx, sy, sz = (a / 4096 for a in v[7:10])
                    try:
                        bm = self.build_model(mid)
                    except Exception:
                        continue
                    need_b |= {mt.texture for mt in bm.materials if mt.texture}
                    for mat, vs in bm.triangles():
                        tris_edif.append((mat, [(x * sx + bx + ox, y * sy + by, z * sz + bz + oz) + v2[3:]
                                                for v2, (x, y, z) in zip(vs, [q[:3] for q in vs])], mid))
        tc_t = N.TexCache([self.best_set(self.texsets, need_t)])
        bset = self.best_set(self.bmtex, need_b) if need_b else None
        return tris_terr, tris_edif, tc_t, bset

    def permisos(self, fila0, col0, filas, cols):
        """Rejilla de tiles (filas*32, cols*32) con el u16 de permisos de cada tile: el byte bajo es
        el comportamiento (hierba, agua...) y el bit 0x8000 indica que no se puede pisar."""
        out = np.full((filas * 32, cols * 32), 0x8000, np.uint16)
        for r in range(filas):
            for c in range(cols):
                idx = self.matrix[(fila0 + r) * self.mw + col0 + c]
                if idx == 0xFFFF:
                    continue
                raw = bytes(self.land[idx])
                out[r * 32:(r + 1) * 32, c * 32:(c + 1) * 32] = np.frombuffer(raw, '<u2', 1024, 16).reshape(32, 32)
        return out

    @staticmethod
    def alturas(tris_terr, filas, cols):
        """Altura del suelo en el centro de cada tile: la superficie casi horizontal más baja que lo
        cubre (así las copas de los árboles no cuentan)."""
        H, W = filas * 32, cols * 32
        alt = np.full((H, W), np.inf, np.float32)
        for _, vs in tris_terr:
            (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (v[:3] for v in vs)
            nx = (by - ay) * (cz - az) - (bz - az) * (cy - ay)
            ny = (bz - az) * (cx - ax) - (bx - ax) * (cz - az)
            nz = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            if abs(ny) < 0.7 * (nx * nx + ny * ny + nz * nz) ** 0.5:
                continue
            tx0, tx1 = max(int(min(ax, bx, cx) // 16), 0), min(int(max(ax, bx, cx) // 16) + 1, W)
            tz0, tz1 = max(int(min(az, bz, cz) // 16), 0), min(int(max(az, bz, cz) // 16) + 1, H)
            if tx0 >= tx1 or tz0 >= tz1:
                continue
            gx, gz = np.meshgrid(np.arange(tx0, tx1) * 16 + 8.0, np.arange(tz0, tz1) * 16 + 8.0)
            den = (bz - cz) * (ax - cx) + (cx - bx) * (az - cz)
            if abs(den) < 1e-9:
                continue
            w0 = ((bz - cz) * (gx - cx) + (cx - bx) * (gz - cz)) / den
            w1 = ((cz - az) * (gx - cx) + (ax - cx) * (gz - cz)) / den
            w2 = 1 - w0 - w1
            dentro = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
            y = w0 * ay + w1 * by + w2 * cy
            reg = alt[tz0:tz1, tx0:tx1]
            reg[dentro] = np.minimum(reg[dentro], y[dentro])
        alt[np.isinf(alt)] = 0
        return alt

    def render(self, fila0, col0, filas, cols, K=1.0, hora=12.0, edificios=True, y_edif=None, completo=False):
        """Imagen RGBA del trozo de mapa. Con completo=True devuelve un dict con la imagen, la z del
        mundo por píxel, la altura del suelo y los permisos por tile."""
        tt, te, tc_t, bset = self.triangles(fila0, col0, filas, cols, edificios)
        luz = N.parse_arealight(self.luz_txt, hora)
        allt = [(m, vs, tc_t) for m, vs in tt]
        caches = {}
        for m, vs, mid in te:
            if y_edif is not None:
                vs = [(x, y + y_edif, z) + v[3:] for (x, y, z), v in zip([q[:3] for q in vs], vs)]
            if mid not in caches:
                caches[mid] = N.TexCache([bytes(self.builds[mid])] + ([bset] if bset else []))
            allt.append((m, vs, caches[mid]))
        r = N.render_multi(allt, K=K, luz=luz, bounds=(0, -Y0, cols * CHUNK, filas * CHUNK), con_z=completo)
        if not completo:
            return r
        return {'imagen': r[0], 'z': r[3], 'altura': self.alturas(tt, filas, cols),
                'permisos': self.permisos(fila0, col0, filas, cols), 'K': K, 'y0': -Y0}


if __name__ == '__main__':
    rom, out, f0, c0, nf, nc = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
    K = float(sys.argv[7]) if len(sys.argv) > 7 else 1.0
    hora = float(sys.argv[8]) if len(sys.argv) > 8 else 12.0
    w = Mundo(rom)
    img, depth, b = w.render(f0, c0, nf, nc, K, hora)
    Image.fromarray(img).save(out)
    np.save(out.rsplit('.', 1)[0] + '_prof.npy', depth)
    print(out, img.shape)
