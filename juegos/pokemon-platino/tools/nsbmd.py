"""Lector de modelos NSBMD (BMD0) y renderizador por software de mapas de Pokémon Platino.

Proyección: oblicua ortográfica tipo cámara de la DS. pantalla_x = x, pantalla_y = z - y * K.
El orden de profundidad usa z + y (más al sur o más alto = más cerca de la cámara).
"""
import struct
import numpy as np

import ndsgfx as G


def fx32(v):
    return v / 4096.0


def s(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


class Material:
    def __init__(self, name, data, off):
        self.name = name
        dif_amb, spe_emi, pattr, pmask, tip = struct.unpack_from('<IIIII', data, off + 4)
        self.diffuse = tuple(((dif_amb >> (5 * i)) & 31) / 31.0 for i in range(3))
        self.diffuse_is_vtx = bool(dif_amb & 0x8000)
        self.ambient = tuple(((dif_amb >> (16 + 5 * i)) & 31) / 31.0 for i in range(3))
        self.emission = tuple(((spe_emi >> (16 + 5 * i)) & 31) / 31.0 for i in range(3))
        self.alpha = ((pattr >> 16) & 31) / 31.0
        self.lights = pattr & 0xF
        self.cull = (pattr >> 6) & 3
        self.rep_s = bool(tip & (1 << 16)); self.rep_t = bool(tip & (1 << 17))
        self.flip_s = bool(tip & (1 << 18)); self.flip_t = bool(tip & (1 << 19))
        flags, w, h = struct.unpack_from('<HHH', data, off + 0x1E)
        self.flags, self.tw, self.th = flags, w, h
        p = off + 0x2C
        self.sx = self.sy = 1.0
        self.tx = self.ty = 0.0
        if flags & 1:  # usa matriz de textura
            if not flags & 2:
                self.sx, self.sy = fx32(s(struct.unpack_from('<I', data, p)[0], 32)), fx32(s(struct.unpack_from('<I', data, p + 4)[0], 32))
                p += 8
            if not flags & 4:
                p += 4
            if not flags & 8:
                self.tx, self.ty = fx32(s(struct.unpack_from('<I', data, p)[0], 32)), fx32(s(struct.unpack_from('<I', data, p + 4)[0], 32))
        self.texture = None
        self.palette = None


def _dict(data, off, unit):
    return G._dict3d(data, off, unit)


class Model:
    def __init__(self, data):
        self.data = data = bytes(data)
        nsec = struct.unpack_from('<H', data, 0xE)[0]
        mdl = None
        for i in range(nsec):
            so = struct.unpack_from('<I', data, 0x10 + i * 4)[0]
            if data[so:so + 4] == b'MDL0':
                mdl = so
        name, md = _dict(data, mdl + 8, 4)[0]
        mo = mdl + struct.unpack_from('<I', md, 0)[0]
        self.mo = mo
        sbc, mat, shp = struct.unpack_from('<III', data, mo + 4)
        self.sbc, self.mat_off, self.shp_off = mo + sbc, mo + mat, mo + shp
        self.up_scale = fx32(struct.unpack_from('<i', data, mo + 0x1C)[0])
        # materiales
        toff, poff = struct.unpack_from('<HH', data, self.mat_off)
        self.materials = []
        for n, d in _dict(data, self.mat_off + 4, 4):
            self.materials.append(Material(n, data, self.mat_off + struct.unpack_from('<I', d, 0)[0]))
        for dst, off in (('texture', toff), ('palette', poff)):
            for n, d in _dict(data, self.mat_off + off, 4):
                o, cnt = struct.unpack_from('<HB', d, 0)
                for m in data[self.mat_off + o: self.mat_off + o + cnt]:
                    if m < len(self.materials):
                        setattr(self.materials[m], dst, n)
        # shapes
        self.shapes = []
        for n, d in _dict(data, self.shp_off, 4):
            so = self.shp_off + struct.unpack_from('<I', d, 0)[0]
            dl_off, dl_size = struct.unpack_from('<II', data, so + 8)
            self.shapes.append(data[so + dl_off: so + dl_off + dl_size])
        self.draws = self._parse_sbc()

    def _parse_sbc(self):
        d, p = self.data, self.sbc
        mat = 0
        out = []
        sizes = {0x00: 0, 0x01: 0, 0x02: 2, 0x03: 1, 0x04: 1, 0x24: 1, 0x44: 1, 0x05: 1, 0x06: 3, 0x26: 4, 0x46: 4,
                 0x66: 5, 0x07: 1, 0x47: 2, 0x08: 1, 0x48: 2, 0x0B: 0, 0x2B: 0, 0x0C: 2, 0x0D: 2}
        for _ in range(100000):
            op = d[p]
            if op == 0x01:
                break
            if op in (0x04, 0x24, 0x44):
                mat = d[p + 1]
            elif op == 0x05:
                out.append((d[p + 1], mat))
            if op == 0x09:
                n = d[p + 2]
                p += 3 + n * 3
                continue
            if op not in sizes:
                break
            p += 1 + sizes[op]
        return out

    # ------------------------------------------------------------- geometría
    def triangles(self):
        """Lista de (material, [(x,y,z,s,t,(r,g,b))]*3) en coordenadas de mundo."""
        tris = []
        for shp, mat in self.draws:
            if shp >= len(self.shapes):
                continue
            for tri in _run_dl(self.shapes[shp]):
                tris.append((self.materials[mat], [(x * self.up_scale, y * self.up_scale, z * self.up_scale, s_, t_, c, n)
                                                   for x, y, z, s_, t_, c, n in tri]))
        return tris


PARAMS = {0x00: 0, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 16, 0x17: 12, 0x18: 16, 0x19: 12,
          0x1A: 9, 0x1B: 3, 0x1C: 3, 0x20: 1, 0x21: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1,
          0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1, 0x41: 0,
          0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1}


def _run_dl(dl):
    words = np.frombuffer(dl[:len(dl) // 4 * 4], '<u4').tolist()
    i = 0
    x = y = z = 0.0
    st = (0.0, 0.0)
    col = (1.0, 1.0, 1.0)
    nrm = (0.0, 1.0, 0.0)
    prim = 0
    verts = []
    out = []
    scale = (1.0, 1.0, 1.0)

    def flush():
        if prim == 0:
            for k in range(0, len(verts) - 2, 3):
                out.append(verts[k:k + 3])
        elif prim == 1:
            for k in range(0, len(verts) - 3, 4):
                a, b, c, d = verts[k:k + 4]
                out.append([a, b, c]); out.append([a, c, d])
        elif prim == 2:
            for k in range(len(verts) - 2):
                out.append(verts[k:k + 3] if k % 2 == 0 else [verts[k + 1], verts[k], verts[k + 2]])
        elif prim == 3:
            for k in range(0, len(verts) - 3, 2):
                a, b, c, d = verts[k:k + 4]
                out.append([a, b, d]); out.append([a, d, c])

    while i < len(words):
        cmds = [(words[i] >> (8 * k)) & 0xFF for k in range(4)]
        i += 1
        for c in cmds:
            n = PARAMS.get(c, 0)
            p = words[i:i + n]
            i += n
            if c == 0x40:
                verts = []; prim = p[0] & 3
            elif c == 0x41:
                flush(); verts = []
            elif c == 0x22:
                st = (s(p[0] & 0xFFFF, 16) / 16.0, s(p[0] >> 16, 16) / 16.0)
            elif c == 0x20:
                v = p[0]
                col = ((v & 31) / 31.0, ((v >> 5) & 31) / 31.0, ((v >> 10) & 31) / 31.0)
            elif c == 0x21:
                v = p[0]
                nrm = (s(v & 0x3FF, 10) / 512.0, s((v >> 10) & 0x3FF, 10) / 512.0, s((v >> 20) & 0x3FF, 10) / 512.0)
            elif c == 0x1B:
                scale = tuple(fx32(s(v, 32)) for v in p)
            elif c in (0x23, 0x24, 0x25, 0x26, 0x27, 0x28):
                if c == 0x23:
                    x, y, z = fx32(s(p[0] & 0xFFFF, 16)), fx32(s(p[0] >> 16, 16)), fx32(s(p[1] & 0xFFFF, 16))
                elif c == 0x24:
                    v = p[0]
                    x, y, z = s(v & 0x3FF, 10) / 64.0, s((v >> 10) & 0x3FF, 10) / 64.0, s((v >> 20) & 0x3FF, 10) / 64.0
                elif c == 0x25:
                    x, y = fx32(s(p[0] & 0xFFFF, 16)), fx32(s(p[0] >> 16, 16))
                elif c == 0x26:
                    x, z = fx32(s(p[0] & 0xFFFF, 16)), fx32(s(p[0] >> 16, 16))
                elif c == 0x27:
                    y, z = fx32(s(p[0] & 0xFFFF, 16)), fx32(s(p[0] >> 16, 16))
                else:
                    v = p[0]
                    x += s(v & 0x3FF, 10) / 4096.0
                    y += s((v >> 10) & 0x3FF, 10) / 4096.0
                    z += s((v >> 20) & 0x3FF, 10) / 4096.0
                verts.append((x * scale[0], y * scale[1], z * scale[2], st[0], st[1], col, nrm))
    return out


# ------------------------------------------------------------------ texturas para render

class TexCache:
    def __init__(self, texsets, pairs=None):
        """texsets: lista de datos BTX0/BMD0 donde buscar texturas y paletas por nombre."""
        self.src = texsets
        self.cache = {}

    def get(self, tex, pal):
        key = (tex, pal)
        if key in self.cache:
            return self.cache[key]
        img = None
        for data in self.src:
            for tn, pn, im in G.decode_textures(data, {tex: [pal]} if pal else None):
                if tn == tex:
                    img = np.array(im)
                    break
            if img is not None:
                break
        self.cache[key] = img
        return img


# ------------------------------------------------------------------ rasterizador

def parse_arealight(text, hora=12.0):
    """Bloque de luz del fichero data/arealight.narc más cercano a la hora (0-24)."""
    import re
    best = None
    for b in re.split(r'\n\s*\n', text.replace(chr(13), '')):
        nums = [int(v) for v in re.findall(r'-?\d+', b)]
        if len(nums) < 41:
            continue
        t = nums[0] * 2 / 3600.0
        if t <= hora:
            best = nums
    nums = best
    lights = []
    for k in range(4):
        e, r, g, b, x, y, z = nums[1 + k * 7: 8 + k * 7]
        lights.append((bool(e), (r / 31, g / 31, b / 31), (x / 4096, y / 4096, z / 4096)))
    m = nums[29:41]
    return {'luces': lights, 'difusa': [v / 31 for v in m[0:3]], 'ambiente': [v / 31 for v in m[3:6]],
            'especular': [v / 31 for v in m[6:9]], 'emision': [v / 31 for v in m[9:12]]}


def vertex_light(n, mat_lights, luz):
    out = np.array(luz['emision'], np.float32)
    for k, (on, color, d) in enumerate(luz['luces']):
        if not on or not (mat_lights >> k) & 1:
            continue
        ndl = max(0.0, -(d[0] * n[0] + d[1] * n[1] + d[2] * n[2]))
        c = np.array(color)
        out = out + c * (np.array(luz['difusa']) * ndl + np.array(luz['ambiente']))
    return np.clip(out, 0, 1)


def render(tris, texcache, K=1.0, bounds=None, scale_px=1.0, modulate=True, luz=None):
    return render_multi([(m, vs, texcache) for m, vs in tris], K, bounds, scale_px, modulate, luz)


def render_multi(items, K=1.0, bounds=None, scale_px=1.0, modulate=True, luz=None, con_z=False):
    """items: (material, vértices, TexCache). Devuelve (imagen RGBA, profundidad, bounds) y, con
    con_z, también la z del mundo de cada píxel opaco (para tapar personajes)."""
    tris = [(m, vs) for m, vs, _ in items]
    caches = [tc for _, _, tc in items]
    proj = []
    for m, vs in tris:
        pts = [(x * scale_px, (z - y * K) * scale_px, z + y) for x, y, z, _, _, _, _ in vs]
        proj.append(pts)
    if bounds is None:
        xs = [p[0] for pts in proj for p in pts]; ys = [p[1] for pts in proj for p in pts]
        bounds = (int(np.floor(min(xs))), int(np.floor(min(ys))), int(np.ceil(max(xs))), int(np.ceil(max(ys))))
    x0, y0, x1, y1 = bounds
    W, H = x1 - x0, y1 - y0
    img = np.zeros((H, W, 4), np.float32)
    depth = np.full((H, W), -1e9, np.float32)
    zw = np.full((H, W), -1e9, np.float32)
    # opacos primero, luego translúcidos (orden por profundidad)
    order = sorted(range(len(tris)), key=lambda i: (tris[i][0].alpha < 1, np.mean([p[2] for p in proj[i]])))
    for i in order:
        m, vs = tris[i]
        tex = caches[i].get(m.texture, m.palette) if m.texture else None
        pts = proj[i]
        (ax, ay, ad), (bx, by, bd), (cx, cy, cd) = pts
        ax -= x0; bx -= x0; cx -= x0; ay -= y0; by -= y0; cy -= y0
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9:
            continue
        minx, maxx = max(int(np.floor(min(ax, bx, cx))), 0), min(int(np.ceil(max(ax, bx, cx))), W)
        miny, maxy = max(int(np.floor(min(ay, by, cy))), 0), min(int(np.ceil(max(ay, by, cy))), H)
        if minx >= maxx or miny >= maxy:
            continue
        gx, gy = np.meshgrid(np.arange(minx, maxx) + 0.5, np.arange(miny, maxy) + 0.5)
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        d = w0 * ad + w1 * bd + w2 * cd
        if tex is not None:
            su = w0 * vs[0][3] + w1 * vs[1][3] + w2 * vs[2][3]
            tv = w0 * vs[0][4] + w1 * vs[1][4] + w2 * vs[2][4]
            su = su * m.sx + m.tx; tv = tv * m.sy + m.ty
            th, tw = tex.shape[:2]
            ui = np.floor(su).astype(int); vi = np.floor(tv).astype(int)
            ui = _wrap(ui, tw, m.rep_s, m.flip_s); vi = _wrap(vi, th, m.rep_t, m.flip_t)
            texel = tex[vi, ui].astype(np.float32) / 255.0
        else:
            texel = np.ones(gx.shape + (4,), np.float32)
        if luz is not None:
            vc = [vertex_light(v[6], m.lights, luz) for v in vs]
        else:
            vc = [v[5] for v in vs]
        col = np.stack([w0 * vc[0][k] + w1 * vc[1][k] + w2 * vc[2][k] for k in range(3)], -1)
        rgb = texel[..., :3]
        if modulate:
            rgb = rgb * col
        a = texel[..., 3] * m.alpha
        ok = inside & (a > 0.01) & (d >= depth[miny:maxy, minx:maxx] - 1e-3)
        if not ok.any():
            continue
        reg = img[miny:maxy, minx:maxx]
        aa = a[..., None]
        blended = rgb * aa + reg[..., :3] * (1 - aa)
        reg[..., :3] = np.where(ok[..., None], blended, reg[..., :3])
        reg[..., 3] = np.where(ok, np.maximum(reg[..., 3], a), reg[..., 3])
        if m.alpha >= 1:
            dz = depth[miny:maxy, minx:maxx]
            dz[ok & (a > 0.5)] = d[ok & (a > 0.5)]
            zr = zw[miny:maxy, minx:maxx]
            zr[ok & (a > 0.5)] = (w0 * vs[0][2] + w1 * vs[1][2] + w2 * vs[2][2])[ok & (a > 0.5)]
    out = (np.clip(img, 0, 1) * 255).astype(np.uint8), depth, bounds
    return out + (zw,) if con_z else out


def _wrap(i, n, rep, flip):
    if not rep:
        return np.clip(i, 0, n - 1)
    if flip:
        period = i // n
        r = i % n
        return np.where(period % 2 == 1, n - 1 - r, r)
    return i % n
