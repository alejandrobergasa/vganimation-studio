"""Niveles de NSMB: objetos de tilemap (bgdat) + definiciones de objetos de tileset (BG_unt) + render."""
import struct
import numpy as np
from PIL import Image
import rom, raw2d as R


class ObjDefs:
    """Definiciones de objetos de un tileset: BG_unt/<n>.bin + <n>_hd.bin."""
    def __init__(self, name):
        u = rom.get(f'BG_unt/{name}.bin'); hd = rom.get(f'BG_unt/{name}_hd.bin')
        self.objs = []
        for i in range(len(hd) // 4):
            off, w, h = struct.unpack_from('<HBB', hd, i * 4)
            p = off; rows = [[]]
            while p < len(u) and u[p] != 0xff:
                if u[p] == 0xfe:
                    rows.append([]); p += 1; continue
                if u[p] & 0x80:
                    rows[-1].append(('S', u[p])); p += 1; continue
                rows[-1].append((u[p], u[p+1], u[p+2])); p += 3
            if rows and not rows[-1]: rows.pop()
            self.objs.append((w, h, rows))

    def render(self, idx, w, h):
        """-> dict {(dx,dy): (num, tsid)} del objeto expandido a w x h (sin pendientes)."""
        if idx >= len(self.objs): return {}
        _, _, rows = self.objs[idx]
        rows = [[t for t in r if t[0] != 'S'] for r in rows]
        if not rows: return {}
        slope = any(t[0] == 'S' for r in self.objs[idx][2] for t in r)
        out = {}
        ry = [i for i, r in enumerate(rows) if any(t[0] & 2 for t in r)]
        fixed = len(rows) - len(ry)
        extra = max(0, h - fixed)
        # filas expandidas
        seq = []
        if ry:
            first = ry[0]
            seq = list(range(first))
            n = extra + len(ry) if len(ry) > 1 else extra + 1
            for k in range(n): seq.append(ry[k % len(ry)])
            seq += list(range(ry[-1] + 1, len(rows)))
        else:
            seq = list(range(len(rows)))
        for dy, ri in enumerate(seq[:h] if not ry else seq):
            row = rows[ri]
            rx = [i for i, t in enumerate(row) if t[0] & 1]
            fixedc = len(row) - len(rx)
            extrac = max(0, w - fixedc)
            cols = []
            if rx:
                first = rx[0]
                cols = list(range(first))
                n = extrac + len(rx) if len(rx) > 1 else extrac + 1
                for k in range(n): cols.append(rx[k % len(rx)])
                cols += list(range(rx[-1] + 1, len(row)))
            else:
                cols = list(range(len(row)))
            for dx, ci in enumerate(cols):
                t = row[ci]; out[(dx, dy)] = (t[1], t[2])
        return out


class Tileset:
    """Tres ficheros de tileset por nivel, con espacio de tiles común:
    Jyotyu (tiles 0-191, comun a todos), stage (192-639) y, opcional, un tercero (640+).
    Los ids de Map16 de los objetos son (num, th): th 0 = jyotyu (o stage si jyotyu vacío),
    th 1-3 = bloque (th-1) del pnl del stage, th 4-5 = bloque (th-4) del pnl del tercero."""
    def __init__(self, stage, tikei, third=None, third_tikei=None, jy='A_J_jyotyu'):
        tj = R.tiles(f'BG_ncg/d_2d_{jy}_ncg.bin', 8)
        ts = R.tiles(f'BG_ncg/d_2d_{tikei}_ncg.bin', 8)
        parts = [tj, ts]
        self.pj = R.palette(f'BG_ncl/d_2d_{jy}_ncl.bin')
        self.ps = R.palette(f'BG_ncl/d_2d_{tikei}_ncl.bin')
        self.pnl_j = R.map16(f'BG_pnl/d_2d_PA_{jy}.bin')
        self.pnl_s = R.map16(f'BG_pnl/d_2d_PA_{stage}.bin')
        self.defs_j = ObjDefs(jy); self.defs_s = ObjDefs(stage)
        self.pnl_t = self.pt = self.defs_t = None
        if third:
            parts.append(R.tiles(f'BG_ncg/d_2d_{third_tikei}_ncg.bin', 8))
            self.pt = R.palette(f'BG_ncl/d_2d_{third_tikei}_ncl.bin')
            self.pnl_t = R.map16(f'BG_pnl/d_2d_PA_{third}.bin')
            self.defs_t = ObjDefs(third)
        self.tl = np.concatenate(parts)
        self._cache = {}

    def slot_defs(self):
        return {0: self.defs_j, 1: self.defs_s, 2: self.defs_t}

    @staticmethod
    def _ne(e):
        return bool((e & 0x3ff).any())

    def lookup(self, th, num):
        if th == 0:
            if self._ne(self.pnl_j[num]): return self.pnl_j[num], self.pj
            idx = num
            if idx < len(self.pnl_s): return self.pnl_s[idx], self.ps
            return None
        if 1 <= th <= 3:
            idx = (th - 1) * 256 + num
            if idx < len(self.pnl_s): return self.pnl_s[idx], self.ps
        if th >= 4 and self.pnl_t is not None:
            idx = (th - 4) * 256 + num
            if idx < len(self.pnl_t): return self.pnl_t[idx], self.pt
        return None

    def map16_img(self, th, num):
        key = (th, num)
        if key in self._cache: return self._cache[key]
        r = self.lookup(th, num)
        if r is None:
            self._cache[key] = None; return None
        e, pal = r
        im = R.render_map16(e, self.tl, lambda s: pal[(s % 2) * 256:(s % 2) * 256 + 256])
        if not (im[..., 3] > 0).any(): im = None
        self._cache[key] = im
        return im


def read_bgdat(name):
    b = rom.get(name); p = 0; objs = []
    while p + 2 <= len(b):
        t = struct.unpack_from('<H', b, p)[0]
        if t == 0xffff: break
        objs.append(struct.unpack_from('<5H', b, p)); p += 10
    return objs


PIPE_OBJ = 0x66   # tuberías verdes: en la ROM son polígonos 3D; aquí se montan con sus texturas (I_dokan)
_pipe_tiles = {}


def pipe_image(h):
    """Tubería vertical de 2 tiles de ancho y h de alto con las texturas I_do_{lu,ru,ld,rd} de polygon_unit/I_dokan.nsbtx."""
    if not _pipe_tiles:
        import nitro3d as N
        bank = N.Nitro(rom.get('polygon_unit/I_dokan.nsbtx')).banks[0]
        for n in ('lu', 'ru', 'ld', 'rd'):
            _pipe_tiles[n] = Image.fromarray(bank.decode('I_do_' + n, 'I_dokan'), 'RGBA')
    im = Image.new('RGBA', (32, h * 16))
    for row in range(h):
        a, b = ('lu', 'ru') if row == 0 else ('ld', 'rd')
        im.paste(_pipe_tiles[a], (0, row * 16)); im.paste(_pipe_tiles[b], (16, row * 16))
    return im


def render_level(objs, ts, slot_defs, W=None, H=None, bg=(0, 0, 0, 0), skip=(), pipes=True):
    W = W or max(o[1] + o[3] for o in objs) + 1
    H = H or max(o[2] + o[4] for o in objs) + 1
    img = np.zeros((H * 16, W * 16, 4), np.uint8); img[:] = bg
    for typ, x, y, w, h in objs:
        if typ == PIPE_OBJ or typ in skip: continue
        slot, oid = typ >> 12, typ & 0xfff
        d = slot_defs.get(slot)
        if d is None: continue
        cells = d.render(oid, w, h)
        for (dx, dy), (num, tsid) in cells.items():
            if num == 0 and tsid == 0: continue      # celda vacía de la definición
            X, Y = x + dx, y + dy
            if X >= W or Y >= H: continue
            m = ts.map16_img(tsid, num)
            if m is None: continue
            reg = img[Y*16:Y*16+16, X*16:X*16+16]
            reg[:] = np.where(m[..., 3:4] > 0, m, reg)
    im = Image.fromarray(img, 'RGBA')
    for typ, x, y, w, h in objs:
        if pipes and typ == PIPE_OBJ:
            im.alpha_composite(pipe_image(h), (x * 16, y * 16))
    return im
