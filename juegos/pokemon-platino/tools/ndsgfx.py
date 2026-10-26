"""Decodificadores de formatos gráficos de Nintendo DS (Nitro).

NCGR (RGCN) tiles, NCLR (RLCN) paletas, NCER (RECN) celdas/OAM, NANR (RNAN)
animaciones, NSCR (RCSN) pantallas, y texturas 3D TEX0 dentro de BTX0/BMD0.
"""
import struct
import difflib
import numpy as np
from PIL import Image


# ---------------------------------------------------------------- utilidades

def lz_decompress(data):
    """Descomprime LZ10/LZ11 (BIOS). Devuelve None si no es válido."""
    if len(data) < 4 or data[0] not in (0x10, 0x11):
        return None
    typ = data[0]
    size = data[1] | (data[2] << 8) | (data[3] << 16)
    pos = 4
    if size == 0:
        if len(data) < 8:
            return None
        size = struct.unpack_from('<I', data, 4)[0]
        pos = 8
    if size == 0 or size > 16 * 1024 * 1024:
        return None
    out = bytearray()
    try:
        while len(out) < size:
            flags = data[pos]; pos += 1
            for bit in range(8):
                if len(out) >= size:
                    break
                if not flags & (0x80 >> bit):
                    out.append(data[pos]); pos += 1
                    continue
                if typ == 0x10:
                    b1, b2 = data[pos], data[pos + 1]; pos += 2
                    length = (b1 >> 4) + 3
                    disp = (((b1 & 0xF) << 8) | b2) + 1
                else:
                    b1 = data[pos]
                    ind = b1 >> 4
                    if ind == 0:
                        b2, b3 = data[pos + 1], data[pos + 2]; pos += 3
                        length = (((b1 & 0xF) << 4) | (b2 >> 4)) + 0x11
                        disp = (((b2 & 0xF) << 8) | b3) + 1
                    elif ind == 1:
                        b2, b3, b4 = data[pos + 1], data[pos + 2], data[pos + 3]; pos += 4
                        length = (((b1 & 0xF) << 12) | (b2 << 4) | (b3 >> 4)) + 0x111
                        disp = (((b3 & 0xF) << 8) | b4) + 1
                    else:
                        b2 = data[pos + 1]; pos += 2
                        length = ind + 1
                        disp = (((b1 & 0xF) << 8) | b2) + 1
                if disp > len(out):
                    return None
                for _ in range(length):
                    out.append(out[-disp])
    except IndexError:
        return None
    if pos < len(data) - 4 and any(data[pos:]):  # mucha basura sobrante => no era LZ
        if len(data) - pos > 16:
            return None
    return bytes(out[:size])


def magic(b):
    return bytes(b[:4])


def unwrap(data):
    """Devuelve el contenido real (descomprimiendo LZ si procede)."""
    if magic(data) in KNOWN:
        return data
    d = lz_decompress(data)
    if d is not None and magic(d) in KNOWN:
        return d
    return data


KNOWN = {b'RGCN', b'RLCN', b'RECN', b'RNAN', b'RCSN', b'BTX0', b'BMD0', b'NARC', b'RCMN', b'RAMN'}


def sections(data):
    """Itera secciones de un fichero Nitro estándar -> {magic: (offset, bytes)}."""
    hsize = struct.unpack_from('<H', data, 0xC)[0]
    nsec = struct.unpack_from('<H', data, 0xE)[0]
    pos = hsize
    res = {}
    for _ in range(nsec):
        if pos + 8 > len(data):
            break
        m = bytes(data[pos:pos + 4]); sz = struct.unpack_from('<I', data, pos + 4)[0]
        res[m] = (pos, data[pos:pos + sz])
        if sz == 0:
            break
        pos += sz
    return res


def bgr555(v, alpha=255):
    return ((v & 31) * 255 // 31, ((v >> 5) & 31) * 255 // 31, ((v >> 10) & 31) * 255 // 31, alpha)


# ---------------------------------------------------------------- NCLR

class Palette:
    def __init__(self, data):
        s = sections(data)
        off, sec = s[b'TTLP']
        self.bpp = 4 if struct.unpack_from('<I', sec, 8)[0] == 3 else 8
        dsize, doff = struct.unpack_from('<II', sec, 16)
        raw = sec[8 + doff: 8 + doff + dsize]
        if len(raw) < dsize:  # tamaño erróneo en algunos ficheros
            raw = sec[8 + doff:]
        n = len(raw) // 2
        self.colors = [struct.unpack_from('<H', raw, i * 2)[0] for i in range(n)]
        self.rgba = np.array([bgr555(c) for c in self.colors] or [(0, 0, 0, 255)], dtype=np.uint8)

    def table(self, bank=0, depth=4, transparent=True):
        """Tabla RGBA de 16 o 256 colores empezando en el banco indicado."""
        size = 16 if depth == 4 else 256
        start = bank * 16 if depth == 4 else 0
        t = np.zeros((size, 4), dtype=np.uint8)
        seg = self.rgba[start:start + size]
        t[:len(seg)] = seg
        if len(seg) < size:  # rellena con gris para ver índices fuera de rango
            t[len(seg):] = (255, 0, 255, 255)
        if transparent:
            t[0, 3] = 0
        return t

    @property
    def nbanks(self):
        return max(1, len(self.colors) // 16)

    def swatch(self):
        n = len(self.colors)
        rows = max(1, (n + 15) // 16)
        img = np.zeros((rows, 16, 4), dtype=np.uint8)
        flat = img.reshape(-1, 4); flat[:n] = self.rgba[:n]
        return Image.fromarray(img, 'RGBA').resize((16 * 8, rows * 8), Image.NEAREST)


def grayscale_palette(depth):
    n = 16 if depth == 4 else 256
    t = np.zeros((n, 4), dtype=np.uint8)
    for i in range(n):
        v = 255 - i * 255 // (n - 1)
        t[i] = (v, v, v, 255)
    t[0, 3] = 0
    return t


# ---------------------------------------------------------------- NCGR

class Graphic:
    def __init__(self, data):
        s = sections(data)
        off, sec = s[b'RAHC']
        self.h_tiles, self.w_tiles = struct.unpack_from('<HH', sec, 8)
        self.depth = 4 if struct.unpack_from('<I', sec, 12)[0] == 3 else 8
        self.mapping = struct.unpack_from('<I', sec, 16)[0]
        self.linear = struct.unpack_from('<I', sec, 20)[0] & 0xFF  # 1 = "scanned"
        dsize, doff = struct.unpack_from('<II', sec, 24)
        self.data_offset = off + 8 + doff  # posición absoluta en el fichero
        self.raw = bytes(sec[8 + doff: 8 + doff + dsize])
        self.has_dims = self.h_tiles != 0xFFFF

    def indices(self):
        """Array plano de índices de color (un byte por píxel) en orden de bytes."""
        a = np.frombuffer(self.raw, dtype=np.uint8)
        if self.depth == 4:
            out = np.empty(a.size * 2, dtype=np.uint8)
            out[0::2] = a & 0xF; out[1::2] = a >> 4
            return out
        return a.copy()

    @property
    def ntiles(self):
        return len(self.raw) // (32 if self.depth == 4 else 64)

    def tiles(self):
        """Array (n,8,8) de índices por tile (asumiendo datos en tiles)."""
        px = self.indices()
        n = px.size // 64
        return px[:n * 64].reshape(n, 8, 8)

    def image_indices(self, width_tiles=None, pixels=None):
        """Matriz de índices de la imagen completa."""
        px = self.indices() if pixels is None else pixels
        if self.has_dims and width_tiles is None:
            w, h = self.w_tiles * 8, self.h_tiles * 8
        else:
            n = px.size // 64
            w = (width_tiles or min(32, max(1, n))) * 8
            h = ((n * 64 + w * 8 - 1) // (w * 8)) * 8
        need = w * h
        if px.size < need:
            px = np.concatenate([px, np.zeros(need - px.size, dtype=np.uint8)])
        px = px[:need]
        if self.linear and self.has_dims and width_tiles is None:
            return px.reshape(h, w)
        tw = w // 8
        t = px.reshape(h // 8, tw, 8, 8)
        return t.transpose(0, 2, 1, 3).reshape(h, w)


def render(idx, table):
    return Image.fromarray(table[idx], 'RGBA')


# ---------------------------------------------------------------- NSCR

class Screen:
    def __init__(self, data):
        s = sections(data)
        off, sec = s[b'NRCS']
        self.w, self.h = struct.unpack_from('<HH', sec, 8)
        self.mode = struct.unpack_from('<I', sec, 12)[0]
        dsize = struct.unpack_from('<I', sec, 16)[0]
        raw = sec[20:20 + dsize]
        self.entries = np.frombuffer(bytes(raw[:len(raw) // 2 * 2]), dtype='<u2')

    def render(self, gfx, pal):
        tiles = gfx.tiles()
        tw, th = self.w // 8, self.h // 8
        n = min(tw * th, self.entries.size)
        img = np.zeros((th * 8, tw * 8, 4), dtype=np.uint8)
        affine = (self.entries.size == tw * th // 2) and gfx.depth == 8 and False
        for i in range(n):
            e = int(self.entries[i])
            ti, hf, vf, pb = e & 0x3FF, (e >> 10) & 1, (e >> 11) & 1, e >> 12
            if ti >= len(tiles):
                continue
            t = tiles[ti]
            if hf: t = t[:, ::-1]
            if vf: t = t[::-1, :]
            tab = pal.table(pb if gfx.depth == 4 else 0, gfx.depth, transparent=False)
            y, x = (i // tw) * 8, (i % tw) * 8
            img[y:y + 8, x:x + 8] = tab[t]
        return Image.fromarray(img, 'RGBA')


def seam_score(scr, gfx):
    """Discontinuidad media en los bordes entre tiles (menor = más probable que sea el NCGR correcto)."""
    tiles = gfx.tiles().astype(np.int16)
    tw, th = scr.w // 8, scr.h // 8
    n = min(tw * th, scr.entries.size)
    e = scr.entries[:n].astype(np.int64)
    ti = e & 0x3FF
    if ti.max() >= len(tiles):
        return 1e9
    t = tiles[ti]
    hf = ((e >> 10) & 1).astype(bool); vf = ((e >> 11) & 1).astype(bool)
    t[hf] = t[hf][:, :, ::-1]; t[vf] = t[vf][:, ::-1, :]
    rows = n // tw
    if rows < 1:
        return 1e9
    img = t[:rows * tw].reshape(rows, tw, 8, 8).transpose(0, 2, 1, 3).reshape(-1, tw * 8)
    dx = np.abs(np.diff(img, axis=1)); dy = np.abs(np.diff(img, axis=0))
    seam = dx[:, 7::8].mean() + dy[7::8, :].mean()
    inner = (dx.mean() + dy.mean()) + 0.01
    return seam / inner


# ---------------------------------------------------------------- NCER

OBJ_SIZES = {
    (0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
    (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
    (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64),
}


class Cells:
    def __init__(self, data):
        s = sections(data)
        off, sec = s[b'KBEC']
        ncells, self.attr = struct.unpack_from('<HH', sec, 8)
        cell_off, self.mapping = struct.unpack_from('<II', sec, 12)
        base = 8 + cell_off
        stride = 16 if self.attr == 1 else 8
        oam_base = base + ncells * stride
        self.cells = []
        for c in range(ncells):
            noam, cattr, ooff = struct.unpack_from('<HHI', sec, base + c * stride)
            oams = []
            for k in range(noam):
                p = oam_base + ooff + k * 6
                if p + 6 > len(sec):
                    break
                a0, a1, a2 = struct.unpack_from('<HHH', sec, p)
                y = a0 & 0xFF; y = y - 256 if y >= 128 else y
                x = a1 & 0x1FF; x = x - 512 if x >= 256 else x
                rs = (a0 >> 8) & 1
                shape, size = a0 >> 14, a1 >> 14
                if (shape, size) not in OBJ_SIZES:
                    continue
                w, h = OBJ_SIZES[(shape, size)]
                oams.append(dict(x=x, y=y, w=w, h=h, tile=a2 & 0x3FF, pal=a2 >> 12,
                                 depth=8 if (a0 >> 13) & 1 else 4,
                                 hf=(not rs) and (a1 >> 12) & 1, vf=(not rs) and (a1 >> 13) & 1,
                                 dbl=rs and (a0 >> 9) & 1, prio=(a2 >> 10) & 3))
            self.cells.append(oams)

    def render_cell(self, i, gfx, pal, pal_offset=0, bounds=None, tile_base=0):
        oams = self.cells[i]
        if not oams:
            return None
        if bounds is None:
            bounds = self.bounds([i])
        x0, y0, x1, y1 = bounds
        img = np.zeros((y1 - y0, x1 - x0, 4), dtype=np.uint8)
        px = gfx.indices()
        shift = self.mapping & 7 if self.mapping < 4 else 0
        two_d = self.mapping == 4 or (gfx.mapping & 0x10) == 0 and self.mapping == 4
        # dibujar en orden inverso: el primer OAM queda encima
        for o in reversed(oams):
            d = o['depth'] if gfx.depth == 4 else gfx.depth
            d = gfx.depth
            tile_bytes = 32 if d == 4 else 64
            ppt = 64
            w, h = o['w'], o['h']
            sub = np.zeros((h, w), dtype=np.uint8)
            tw, th = w // 8, h // 8
            for ty in range(th):
                for tx in range(tw):
                    if two_d and gfx.has_dims:
                        rowlen = gfx.w_tiles if gfx.w_tiles else 32
                        tnum = o['tile'] + ty * rowlen + tx
                        start = tnum * 64
                    else:
                        unit = 32 << shift
                        start_byte = o['tile'] * unit + (ty * tw + tx) * tile_bytes + tile_base * tile_bytes
                        start = start_byte * 2 if d == 4 else start_byte
                    t = px[start:start + ppt]
                    if t.size < 64:
                        continue
                    sub[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = t.reshape(8, 8)
            if o['hf']: sub = sub[:, ::-1]
            if o['vf']: sub = sub[::-1, :]
            tab = pal.table((o['pal'] + pal_offset) % max(1, pal.nbanks), d) if d == 4 else pal.table(0, 8)
            rgba = tab[sub]
            ox, oy = o['x'] - x0, o['y'] - y0
            if o['dbl']:
                ox += w // 2; oy += h // 2
            ys, xs = max(0, -oy), max(0, -ox)
            ye, xe = min(h, img.shape[0] - oy), min(w, img.shape[1] - ox)
            if ye <= ys or xe <= xs:
                continue
            region = img[oy + ys:oy + ye, ox + xs:ox + xe]
            src = rgba[ys:ye, xs:xe]
            m = src[..., 3] > 0
            region[m] = src[m]
        return Image.fromarray(img, 'RGBA')

    def tiles_used(self, i, depth=4):
        tb = 32 if depth == 4 else 64
        unit = 32 << (self.mapping & 7 if self.mapping < 4 else 0)
        end = 0
        for o in self.cells[i]:
            end = max(end, (o['tile'] * unit) // tb + (o['w'] // 8) * (o['h'] // 8))
        return end

    def bounds(self, which=None):
        xs, ys, xe, ye = [], [], [], []
        for i in (which if which is not None else range(len(self.cells))):
            for o in self.cells[i]:
                f = 2 if o['dbl'] else 1
                xs.append(o['x']); ys.append(o['y'])
                xe.append(o['x'] + o['w'] * f); ye.append(o['y'] + o['h'] * f)
        if not xs:
            return (0, 0, 8, 8)
        return (min(xs), min(ys), max(xe), max(ye))


# ---------------------------------------------------------------- NANR

def parse_nanr(data):
    s = sections(data)
    off, sec = s[b'KNBA']
    nanim, nframes, aoff, foff, poff = struct.unpack_from('<HHIII', sec, 8)
    base = 8
    anims = []
    for a in range(nanim):
        p = base + aoff + a * 16
        nf, dtype, unk, mode, fo = struct.unpack_from('<IHHII', sec, p)
        frames = []
        for f in range(nf):
            q = base + foff + fo + f * 8
            doff, dur = struct.unpack_from('<IH', sec, q)
            r = base + poff + doff
            cell = struct.unpack_from('<H', sec, r)[0]
            fr = {'cell': cell, 'duration': dur}
            if dtype == 1:
                rot, sx, sy, x, y = struct.unpack_from('<HhhhH', sec, r + 2)
                fr.update(rot=rot, sx=sx / 4096, sy=sy / 4096, x=struct.unpack_from('<h', sec, r + 12)[0], y=struct.unpack_from('<h', sec, r + 14)[0])
            elif dtype == 2:
                x, y = struct.unpack_from('<hh', sec, r + 4)
                fr.update(x=x, y=y)
            frames.append(fr)
        anims.append({'index': a, 'play_mode': mode, 'frames': frames})
    return anims


# ---------------------------------------------------------------- TEX0 (BTX0 / BMD0)

def _dict3d(sec, off, unit):
    count = sec[off + 1]
    pos = off + 4
    pos += 8 + count * 4  # bloque de "unknown" + entradas
    usize = struct.unpack_from('<H', sec, pos)[0]
    pos += 4
    data = [sec[pos + i * usize: pos + (i + 1) * usize] for i in range(count)]
    pos += count * usize
    names = [bytes(sec[pos + i * 16: pos + (i + 1) * 16]).split(b'\0')[0].decode('latin-1') for i in range(count)]
    return list(zip(names, data))


def find_tex0(data):
    if magic(data) not in (b'BTX0', b'BMD0'):
        return None
    nsec = struct.unpack_from('<H', data, 0xE)[0]
    for i in range(nsec):
        o = struct.unpack_from('<I', data, 0x10 + i * 4)[0]
        if data[o:o + 4] == b'TEX0':
            return data[o:o + struct.unpack_from('<I', data, o + 4)[0]]
    return None


def decode_textures(data, overrides=None, extra_pals=None):
    """Devuelve lista de (nombre_textura, nombre_paleta, PIL.Image)."""
    sec = find_tex0(data)
    if sec is None:
        return []
    own = material_pairs(data)
    if overrides:
        own = {**overrides, **own}
    overrides = own
    tex_size = struct.unpack_from('<H', sec, 0xC)[0] << 3
    tex_info = struct.unpack_from('<H', sec, 0xE)[0]
    tex_data = struct.unpack_from('<I', sec, 0x14)[0]
    comp_data = struct.unpack_from('<I', sec, 0x24)[0]
    comp_info = struct.unpack_from('<I', sec, 0x28)[0]
    pal_size = struct.unpack_from('<I', sec, 0x30)[0] << 3
    pal_info = struct.unpack_from('<I', sec, 0x34)[0]
    pal_data = struct.unpack_from('<I', sec, 0x38)[0]
    texs = _dict3d(sec, tex_info, 8)
    pals = _dict3d(sec, pal_info, 4)
    pal_raw = sec[pal_data:pal_data + pal_size]
    palnames = [p[0] for p in pals]
    out = []
    for ti, (name, d) in enumerate(texs):
        offset = struct.unpack_from('<H', d, 0)[0] << 3
        params = struct.unpack_from('<H', d, 2)[0]
        w, h = 8 << ((params >> 4) & 7), 8 << ((params >> 7) & 7)
        fmt = (params >> 10) & 7
        c0t = (params >> 13) & 1
        # elegir paleta: nombre exacto, o el más parecido de tipo compatible
        pname = None
        want = overrides.get(name) if overrides else None
        want = [want] if isinstance(want, str) else (want or [])
        if extra_pals and want and want[0] not in palnames and want[0] in extra_pals:
            # la paleta que usan los mapas no está en este set: tomarla de otro set
            pname = want[0]
            cols = np.frombuffer(extra_pals[pname] + b'\0' * 512, dtype='<u2')
        if pname is None:
            pname = choose_palette(name, ti, fmt, pals, len(texs), overrides)
            poff = 0
            if pname is not None:
                pd = dict(pals)[pname]
                poff = struct.unpack_from('<H', pd, 0)[0] << 3
            cols = np.frombuffer(bytes(pal_raw[poff:]) + b'\0' * 512, dtype='<u2')
        try:
            img = _decode_tex(sec, fmt, w, h, tex_data + offset, comp_data + offset, comp_info + offset // 2, cols, c0t)
        except Exception:
            continue
        if img is not None:
            out.append((name, pname, img))
    return out


def choose_palette(name, ti, fmt, pals, ntex, overrides=None):
    if not pals or fmt == 7:
        return None
    names = [p[0] for p in pals]
    if overrides and name in overrides:
        cands = overrides[name]
        for c in ([cands] if isinstance(cands, str) else cands):
            if c in names:
                return c
    for cand in (name + '_pl', name + '_p', name):
        if cand in names:
            return cand
    if len(pals) == 1:
        return names[0]
    four = fmt == 2
    compat = [n for n, d in pals if (struct.unpack_from('<H', d, 2)[0] & 1) == four] or names
    base = name.rsplit('.', 1)[0]
    for cand in (base + '_pl', base):
        if cand in compat:
            return cand

    def score(p):
        k = 0
        while k < min(len(p), len(name)) and p[k] == name[k]:
            k += 1
        return (k, difflib.SequenceMatcher(None, name, p).ratio())
    best = max(compat, key=score)
    if score(best)[0] == 0 and len(pals) == ntex:
        return names[ti]
    return best


def _cols(cols):
    c = cols.astype(np.uint32)
    r = (c & 31) * 255 // 31; g = ((c >> 5) & 31) * 255 // 31; b = ((c >> 10) & 31) * 255 // 31
    return np.stack([r, g, b, np.full_like(r, 255)], -1).astype(np.uint8)


def _decode_tex(sec, fmt, w, h, off, coff, cioff, cols, c0t):
    n = w * h
    rgb = _cols(cols[:256])
    if fmt == 0:
        return None
    if fmt in (1, 6):  # A3I5 / A5I3
        a = np.frombuffer(bytes(sec[off:off + n]), dtype=np.uint8).astype(np.int32)
        if fmt == 1:
            idx, al = a & 31, (a >> 5) * 255 // 7
        else:
            idx, al = a & 7, (a >> 3) * 255 // 31
        px = rgb[idx].copy(); px[:, 3] = al
    elif fmt in (2, 3, 4):
        bpp = {2: 2, 3: 4, 4: 8}[fmt]
        a = np.frombuffer(bytes(sec[off:off + n * bpp // 8]), dtype=np.uint8)
        per = 8 // bpp
        idx = np.empty(a.size * per, dtype=np.uint8)
        for k in range(per):
            idx[k::per] = (a >> (k * bpp)) & ((1 << bpp) - 1)
        px = rgb[idx].copy()
        if c0t:
            px[idx == 0, 3] = 0
    elif fmt == 5:
        px = np.zeros((h, w, 4), dtype=np.uint8)
        call = _cols(cols[:2048] if cols.size >= 2048 else np.concatenate([cols, np.zeros(2048 - cols.size, dtype=cols.dtype)]))
        bw = w // 4
        for b in range(n // 16):
            blk = struct.unpack_from('<I', sec, coff + b * 4)[0]
            info = struct.unpack_from('<H', sec, cioff + b * 2)[0]
            pa = (info & 0x3FFF) * 2; mode = info >> 14
            c = [call[pa + k] if pa + k < len(call) else np.array([0, 0, 0, 255], np.uint8) for k in range(4)]
            c = [x.astype(np.int32) for x in c]
            if mode == 1:
                c[2] = (c[0] + c[1]) // 2
            elif mode == 3:
                c[2] = (c[0] * 5 + c[1] * 3) // 8; c[3] = (c[0] * 3 + c[1] * 5) // 8
            if mode in (0, 1):
                c[3] = np.array([0, 0, 0, 0])
            by, bx = (b // bw) * 4, (b % bw) * 4
            for yy in range(4):
                for xx in range(4):
                    v = (blk >> ((yy * 4 + xx) * 2)) & 3
                    px[by + yy, bx + xx] = c[v]
        return Image.fromarray(px, 'RGBA')
    elif fmt == 7:
        a = np.frombuffer(bytes(sec[off:off + n * 2]), dtype='<u2')
        px = _cols(a).copy(); px[:, 3] = np.where(a & 0x8000, 255, 0)
    if px.shape[0] < n:
        px = np.concatenate([px, np.zeros((n - px.shape[0], 4), np.uint8)])
    return Image.fromarray(px[:n].reshape(h, w, 4), 'RGBA')


def palettes_of(data):
    """{nombre_paleta: bytes} de un BTX0/BMD0 (hasta la siguiente paleta)."""
    sec = find_tex0(data)
    if sec is None:
        return {}
    pal_size = struct.unpack_from('<I', sec, 0x30)[0] << 3
    pal_info = struct.unpack_from('<I', sec, 0x34)[0]
    pal_data = struct.unpack_from('<I', sec, 0x38)[0]
    pals = [(n, struct.unpack_from('<H', d, 0)[0] << 3) for n, d in _dict3d(sec, pal_info, 4)]
    offs = sorted({o for _, o in pals} | {pal_size})
    out = {}
    for n, o in pals:
        end = next(x for x in offs if x > o) if o < pal_size else o
        out[n] = bytes(sec[pal_data + o: pal_data + end])
    return out


# ---------------------------------------------------------------- MDL0: textura -> paleta vía materiales

def material_pairs(data):
    """Devuelve {textura: paleta} leyendo los materiales de los modelos de un BMD0."""
    out = {}
    if magic(data) != b'BMD0':
        return out
    nsec = struct.unpack_from('<H', data, 0xE)[0]
    for i in range(nsec):
        so = struct.unpack_from('<I', data, 0x10 + i * 4)[0]
        if data[so:so + 4] != b'MDL0':
            continue
        try:
            for _, md in _dict3d(data, so + 8, 4):
                mo = so + struct.unpack_from('<I', md, 0)[0]
                mat = mo + struct.unpack_from('<I', data, mo + 8)[0]
                toff, poff = struct.unpack_from('<HH', data, mat)
                tex_mats, pal_mats = {}, {}
                for dst, off in ((tex_mats, toff), (pal_mats, poff)):
                    for name, d in _dict3d(data, mat + off, 4):
                        o, n = struct.unpack_from('<HB', d, 0)
                        dst[name] = set(data[mat + o: mat + o + n])
                for t, ms in tex_mats.items():
                    for p, pm in pal_mats.items():
                        if ms & pm:
                            out[t] = p
                            break
        except (struct.error, IndexError):
            continue
    return out
