"""Lectores de formatos 3D de Nintendo DS: NSBMD (BMD0), NSBTX (BTX0) y NSBCA (BCA0).

- Texturas TEX0 -> arrays RGBA (los 7 formatos del hardware).
- Modelos MDL0 -> geometría local por forma, jerarquía de nodos y bytecode SBC.
- Animaciones JNT0 -> transformaciones por nodo y fotograma.
Las matrices son 4x4 numpy con vectores columna (M @ v).
"""
import struct
import numpy as np


def fx(v, shift=12):
    return v / float(1 << shift)


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def sx(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def read_dict(d, off, unit_is_fn=None):
    """Diccionario 3D de Nitro. Devuelve [(nombre, bytes_de_datos)] con unidades de tamaño fijo."""
    count = d[off + 1]
    pos = off + 8 + (count + 1) * 4
    usize = struct.unpack_from('<H', d, pos + 2)[0] if False else struct.unpack_from('<H', d, pos)[0]
    pos += 4
    datas = [d[pos + i * usize: pos + (i + 1) * usize] for i in range(count)]
    pos += count * usize
    names = [bytes(d[pos + i * 16: pos + (i + 1) * 16]).split(b'\0')[0].decode('latin-1') for i in range(count)]
    return list(zip(names, datas))


def sections(d):
    n = struct.unpack_from('<H', d, 0xE)[0]
    out = {}
    for i in range(n):
        o = struct.unpack_from('<I', d, 0x10 + i * 4)[0]
        out[bytes(d[o:o + 4]).decode('ascii')] = o
    return out


# ---------------------------------------------------------------- texturas

def _rgb555(c):
    c = c.astype(np.uint32)
    r = (c & 31) * 255 // 31
    g = ((c >> 5) & 31) * 255 // 31
    b = ((c >> 10) & 31) * 255 // 31
    return np.stack([r, g, b, np.full_like(r, 255)], -1).astype(np.uint8)


class TexBank:
    """Contenido de un TEX0: texturas y paletas con nombre."""

    def __init__(self, d):
        self.d = d
        t = sections(d)['TEX0']
        self.t = t
        g = lambda o, f: struct.unpack_from(f, d, t + o)[0]
        self.tex_data = t + g(0x14, '<I')
        self.comp_data = t + g(0x24, '<I')
        self.comp_info = t + g(0x28, '<I')
        self.pal_data = t + g(0x38, '<I')
        self.pal_size = g(0x30, '<I') << 3
        self.texs = {n: x for n, x in read_dict(d, t + g(0x0E, '<H'))} if False else self._tex_dict(t, g(0x0E, '<H'))
        self.pals = self._pal_dict(t, g(0x34, '<I'))
        self.cache = {}

    def _tex_dict(self, t, off):
        # las unidades de textura miden 8 bytes
        return dict(read_dict(self.d, t + off))

    def _pal_dict(self, t, off):
        return dict(read_dict(self.d, t + off))

    def names(self):
        return list(self.texs), list(self.pals)

    def decode(self, tex, pal=None, pal_source=None):
        """pal_source: otro TexBank del que tomar la paleta (los edificios usan la paleta compartida house_pl)."""
        key = (tex, pal, id(pal_source))
        if key in self.cache:
            return self.cache[key]
        img = self._decode(tex, pal, pal_source or self)
        self.cache[key] = img
        return img

    def _decode(self, tex, pal, pb):
        d = self.d
        info = self.texs[tex]
        off = struct.unpack_from('<H', info, 0)[0] << 3
        params = struct.unpack_from('<H', info, 2)[0]
        w, h = 8 << ((params >> 4) & 7), 8 << ((params >> 7) & 7)
        fmt = (params >> 10) & 7
        c0t = (params >> 13) & 1
        n = w * h
        cols = None
        if fmt != 7 and fmt != 5 and fmt != 0:
            poff = 0
            if pal is not None and pal in pb.pals:
                poff = struct.unpack_from('<H', pb.pals[pal], 0)[0] << 3
            raw = bytes(pb.d[pb.pal_data + poff: pb.pal_data + pb.pal_size]) + b'\0' * 512
            cols = _rgb555(np.frombuffer(raw[:512], '<u2'))
        if fmt == 0:
            return np.zeros((h, w, 4), np.uint8)
        if fmt in (1, 6):
            a = np.frombuffer(bytes(d[self.tex_data + off: self.tex_data + off + n]), np.uint8).astype(np.int32)
            if fmt == 1:
                idx, al = a & 31, (a >> 5) * 255 // 7
            else:
                idx, al = a & 7, (a >> 3) * 255 // 31
            px = cols[idx].copy()
            px[:, 3] = al
        elif fmt in (2, 3, 4):
            bpp = {2: 2, 3: 4, 4: 8}[fmt]
            a = np.frombuffer(bytes(d[self.tex_data + off: self.tex_data + off + n * bpp // 8]), np.uint8)
            per = 8 // bpp
            idx = np.empty(a.size * per, np.uint8)
            for k in range(per):
                idx[k::per] = (a >> (k * bpp)) & ((1 << bpp) - 1)
            px = cols[idx].copy()
            if c0t:
                px[idx == 0, 3] = 0
        elif fmt == 5:
            px = self._compressed(w, h, off, pal, pb)
        else:
            a = np.frombuffer(bytes(d[self.tex_data + off: self.tex_data + off + n * 2]), '<u2')
            px = _rgb555(a).copy()
            px[:, 3] = np.where(a & 0x8000, 255, 0)
        return px[:n].reshape(h, w, 4)

    def _compressed(self, w, h, off, pal, pb):
        d = self.d
        poff = 0
        if pal is not None and pal in pb.pals:
            poff = struct.unpack_from('<H', pb.pals[pal], 0)[0] << 3
        raw = bytes(pb.d[pb.pal_data + poff: pb.pal_data + pb.pal_size]) + b'\0' * 4096
        raw = raw[:len(raw) // 2 * 2]
        call = _rgb555(np.frombuffer(raw, '<u2')).astype(np.int32)
        px = np.zeros((h, w, 4), np.uint8)
        bw = w // 4
        for b in range(w * h // 16):
            blk = struct.unpack_from('<I', d, self.comp_data + off + b * 4)[0]
            info = struct.unpack_from('<H', d, self.comp_info + off // 2 + b * 2)[0]
            pa, mode = (info & 0x3FFF) * 2, info >> 14
            c = [call[pa + k] for k in range(4)]
            if mode == 1:
                c[2] = (c[0] + c[1]) // 2
            elif mode == 3:
                c[2] = (c[0] * 5 + c[1] * 3) // 8
                c[3] = (c[0] * 3 + c[1] * 5) // 8
            if mode in (0, 1):
                c[3] = np.array([0, 0, 0, 0])
            by, bx = (b // bw) * 4, (b % bw) * 4
            for yy in range(4):
                for xx in range(4):
                    px[by + yy, bx + xx] = c[(blk >> ((yy * 4 + xx) * 2)) & 3]
        return px.reshape(-1, 4)


# ---------------------------------------------------------------- modelo

PARAMS = {0x00: 0, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x14: 1, 0x15: 0, 0x16: 16, 0x17: 12, 0x18: 16, 0x19: 12,
          0x1A: 9, 0x1B: 3, 0x1C: 3, 0x20: 1, 0x21: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1,
          0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1, 0x41: 0,
          0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1}


class Vert:
    __slots__ = ('p', 's', 't', 'n', 'c', 'mi')


def run_displaylist(dl, scale):
    """Interpreta una lista de visualización GX. Devuelve triángulos [(v0,v1,v2)] con
    v = (x,y,z,u,v,(nx,ny,nz),(r,g,b),indice_matriz|None)."""
    words = np.frombuffer(dl[:len(dl) // 4 * 4], '<u4').tolist()
    i = 0
    x = y = z = 0.0
    st = (0.0, 0.0)
    col = (1.0, 1.0, 1.0)
    nrm = (0.0, 1.0, 0.0)
    mi = None
    prim = 0
    verts = []
    out = []
    vscale = (1.0, 1.0, 1.0)

    def flush():
        if prim == 0:
            for k in range(0, len(verts) - 2, 3):
                out.append(tuple(verts[k:k + 3]))
        elif prim == 1:
            for k in range(0, len(verts) - 3, 4):
                a, b, c, d = verts[k:k + 4]
                out.append((a, b, c)); out.append((a, c, d))
        elif prim == 2:
            for k in range(len(verts) - 2):
                t = verts[k:k + 3]
                out.append((t[0], t[1], t[2]) if k % 2 == 0 else (t[1], t[0], t[2]))
        elif prim == 3:
            for k in range(0, len(verts) - 3, 2):
                a, b, c, d = verts[k:k + 4]
                out.append((a, b, d)); out.append((a, d, c))

    while i < len(words):
        cmds = [(words[i] >> (8 * k)) & 0xFF for k in range(4)]
        i += 1
        for c in cmds:
            n = PARAMS.get(c, 0)
            p = words[i:i + n]
            i += n
            if c == 0x40:
                verts = []
                prim = p[0] & 3
            elif c == 0x41:
                flush()
                verts = []
            elif c == 0x14:
                mi = p[0] & 0x1F
            elif c == 0x22:
                st = (s16(p[0] & 0xFFFF) / 16.0, s16(p[0] >> 16) / 16.0)
            elif c == 0x20:
                v = p[0]
                col = ((v & 31) / 31.0, ((v >> 5) & 31) / 31.0, ((v >> 10) & 31) / 31.0)
            elif c == 0x21:
                v = p[0]
                nrm = (sx(v & 0x3FF, 10) / 512.0, sx((v >> 10) & 0x3FF, 10) / 512.0, sx((v >> 20) & 0x3FF, 10) / 512.0)
            elif c == 0x1B:
                vscale = tuple(sx(v, 32) / 4096.0 for v in p)
            elif c in (0x23, 0x24, 0x25, 0x26, 0x27, 0x28):
                if c == 0x23:
                    x, y, z = fx(s16(p[0] & 0xFFFF)), fx(s16(p[0] >> 16)), fx(s16(p[1] & 0xFFFF))
                elif c == 0x24:
                    v = p[0]
                    x, y, z = sx(v & 0x3FF, 10) / 64.0, sx((v >> 10) & 0x3FF, 10) / 64.0, sx((v >> 20) & 0x3FF, 10) / 64.0
                elif c == 0x25:
                    x, y = fx(s16(p[0] & 0xFFFF)), fx(s16(p[0] >> 16))
                elif c == 0x26:
                    x, z = fx(s16(p[0] & 0xFFFF)), fx(s16(p[0] >> 16))
                elif c == 0x27:
                    y, z = fx(s16(p[0] & 0xFFFF)), fx(s16(p[0] >> 16))
                else:
                    v = p[0]
                    x += sx(v & 0x3FF, 10) / 4096.0
                    y += sx((v >> 10) & 0x3FF, 10) / 4096.0
                    z += sx((v >> 20) & 0x3FF, 10) / 4096.0
                verts.append((x * vscale[0] * scale, y * vscale[1] * scale, z * vscale[2] * scale,
                              st[0], st[1], nrm, col, mi))
    return out


class Material:
    pass


def rot_pivot(select, neg, a, b):
    one = -1.0 if neg & 1 else 1.0
    c = -b if neg & 2 else b
    d = -a if neg & 4 else a
    tbl = {
        0: [one, 0, 0, 0, a, b, 0, c, d],
        1: [0, one, 0, a, 0, b, c, 0, d],
        2: [0, 0, one, a, b, 0, c, d, 0],
        3: [0, a, b, one, 0, 0, 0, c, d],
        4: [a, 0, b, 0, one, 0, c, 0, d],
        5: [a, b, 0, 0, 0, one, c, d, 0],
        6: [0, a, b, 0, c, d, one, 0, 0],
        7: [a, 0, b, c, 0, d, 0, one, 0],
        8: [a, b, 0, c, d, 0, 0, 0, one],
    }
    return np.array(tbl[select], np.float64).reshape(3, 3)


def trs(t=None, r=None, s=None):
    m = np.eye(4)
    rr = np.eye(3) if r is None else r
    ss = np.ones(3) if s is None else np.asarray(s)
    m[:3, :3] = rr * ss[None, :]
    if t is not None:
        m[:3, 3] = t
    return m


class Node:
    pass


class Model:
    def __init__(self, data, name=None):
        d = self.d = bytes(data)
        sec = sections(d)
        mdl = sec['MDL0']
        models = read_dict(d, mdl + 8)
        self.name, md = models[0] if name is None else next(m for m in models if m[0] == name)
        mo = self.mo = mdl + struct.unpack_from('<I', md, 0)[0]
        sbc, mat, shp, evp = struct.unpack_from('<IIII', d, mo + 4)
        self.sbc_off, self.mat_off, self.shp_off, self.evp_off = mo + sbc, mo + mat, mo + shp, mo + evp
        self.scale = fx(struct.unpack_from('<i', d, mo + 0x1C)[0])
        self._nodes(mo + 0x40)
        self._materials()
        self._shapes()
        self.sbc = self._sbc()

    # nodos ---------------------------------------------------
    def _nodes(self, off):
        d = self.d
        self.nodes = []
        for name, e in read_dict(d, off):
            p = off + struct.unpack_from('<I', e, 0)[0]
            flags, a0 = struct.unpack_from('<Hh', d, p)
            p += 4
            n = Node()
            n.name = name
            t = r = s = None
            if not flags & 1:
                t = np.array(struct.unpack_from('<3i', d, p), np.float64) / 4096.0
                p += 12
            if flags & 8:
                a, b = struct.unpack_from('<2h', d, p)
                p += 4
                r = rot_pivot((flags >> 4) & 15, (flags >> 8) & 15, a / 4096.0, b / 4096.0)
            elif not flags & 2:
                v = struct.unpack_from('<8h', d, p)
                p += 16
                r = np.array([a0, *v], np.float64).reshape(3, 3) / 4096.0
            if not flags & 4:
                s = np.array(struct.unpack_from('<3i', d, p), np.float64) / 4096.0
            n.t, n.r, n.s = t, (r.T if r is not None else None), s
            self.nodes.append(n)

    def node_matrix(self, i, override=None):
        n = self.nodes[i]
        if override and i in override:
            t, r, s = override[i]
            return trs(t, r, s)
        return trs(n.t, n.r, n.s)

    # materiales -----------------------------------------------
    def _materials(self):
        d, m0 = self.d, self.mat_off
        toff, poff = struct.unpack_from('<HH', d, m0)
        self.materials = []
        for name, e in read_dict(d, m0 + 4):
            o = m0 + struct.unpack_from('<I', e, 0)[0]
            m = Material()
            m.name = name
            dif_amb, spe_emi, pattr, pmask, tip = struct.unpack_from('<IIIII', d, o + 4)
            m.diffuse = tuple(((dif_amb >> (5 * k)) & 31) / 31.0 for k in range(3))
            m.alpha = ((pattr >> 16) & 31) / 31.0
            m.cull = (pattr >> 6) & 3
            m.rep_s, m.rep_t = bool(tip & 0x10000), bool(tip & 0x20000)
            m.flip_s, m.flip_t = bool(tip & 0x40000), bool(tip & 0x80000)
            flags, w, h = struct.unpack_from('<HHH', d, o + 0x1E)
            m.w, m.h = w, h
            p = o + 0x2C
            m.sx = m.sy = 1.0
            m.tx = m.ty = 0.0
            if flags & 1:
                if not flags & 2:
                    m.sx, m.sy = [sx(v, 32) / 4096.0 for v in struct.unpack_from('<2I', d, p)]
                    p += 8
                if not flags & 4:
                    p += 4
                if not flags & 8:
                    m.tx, m.ty = [sx(v, 32) / 4096.0 for v in struct.unpack_from('<2I', d, p)]
            m.tex = m.pal = None
            self.materials.append(m)
        for attr, off in (('tex', toff), ('pal', poff)):
            for name, e in read_dict(d, m0 + off):
                o, cnt = struct.unpack_from('<HB', e, 0)
                for mi in d[m0 + o: m0 + o + cnt]:
                    if mi < len(self.materials):
                        setattr(self.materials[mi], attr, name)

    # formas ----------------------------------------------------
    def _shapes(self):
        d = self.d
        self.shapes = []
        for name, e in read_dict(d, self.shp_off):
            so = self.shp_off + struct.unpack_from('<I', e, 0)[0]
            dl_off, dl_size = struct.unpack_from('<II', d, so + 8)
            self.shapes.append(run_displaylist(d[so + dl_off: so + dl_off + dl_size], self.scale))

    # matrices inversas de enlace (huesos con pesos) ----------
    def inv_bind_matrix(self, k):
        pos = self.evp_off + k * 84
        v = struct.unpack_from('<12i', self.d, pos)
        m = np.eye(4)
        m[:3, 0] = v[0:3]
        m[:3, 1] = v[3:6]
        m[:3, 2] = v[6:9]
        m[:3, 3] = v[9:12]
        m[:3, :] /= 4096.0
        return m

    # bytecode SBC ----------------------------------------------
    def _sbc(self):
        d, p = self.d, self.sbc_off
        sizes = {0x00: 0, 0x01: 0, 0x02: 2, 0x03: 1, 0x04: 1, 0x24: 1, 0x44: 1, 0x05: 1, 0x06: 3, 0x26: 4,
                 0x46: 4, 0x66: 5, 0x07: 1, 0x47: 2, 0x08: 1, 0x48: 2, 0x0B: 0, 0x2B: 0, 0x0C: 2, 0x0D: 2}
        ops = []
        while True:
            op = d[p]
            if op == 0x01:
                break
            if op == 0x09:
                n = d[p + 2]
                ents = [tuple(d[p + 3 + 3 * j: p + 6 + 3 * j]) for j in range(n)]
                ents = []
                q = p + 3
                for _ in range(n):
                    ents.append((d[q], d[q + 1], d[q + 2]))
                    q += 3
                ops.append((0x09, d[p + 1], ents))
                p = q
                continue
            if op not in sizes:
                break
            ops.append((op & 0x1F | (op & 0xE0), *d[p + 1:p + 1 + sizes[op]]))
            p += 1 + sizes[op]
        return ops

    def pose(self, override=None):
        """Recorre el SBC y devuelve [(forma, material, matriz_actual, pila)]."""
        cur = np.eye(4)
        stack = {}
        mats = {}
        draws = []
        mat = 0
        cur_node = 0
        for op in self.sbc:
            code = op[0]
            if code in (0x06, 0x26, 0x46, 0x66):
                node, parent = op[1], op[2]
                rest = store = None
                if code & 0x20:
                    store = op[4]
                if code & 0x40:
                    rest = op[4] if code == 0x46 else op[5]
                if rest is not None:
                    cur = stack.get(rest, np.eye(4)).copy()
                local = self.node_matrix(node, override)
                cur = cur @ local
                mats[node] = cur
                if store is not None:
                    stack[store] = cur.copy()
                cur_node = node
            elif code == 0x03:
                cur = stack.get(op[1], np.eye(4)).copy()
            elif code in (0x04, 0x24, 0x44):
                mat = op[1]
            elif code == 0x05:
                draws.append((op[1], mat, cur.copy(), dict(stack)))
            elif code == 0x09:
                dst, ents = op[1], op[2]
                acc = np.zeros((4, 4))
                for src, inv, w in ents:
                    acc += (w / 256.0) * (stack.get(src, np.eye(4)) @ self.inv_bind_matrix(inv))
                acc[3, 3] = 1.0
                stack[dst] = acc
                cur = acc
        self.node_world = mats      # matrices de modelo de cada nodo en esta pose (para acoplar objetos a la mano)
        return draws
