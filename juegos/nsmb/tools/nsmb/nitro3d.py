"""Modelos 3D de Nintendo DS (NSBMD/BMD0, NSBTX/BTX0, NSBCA/BCA0, NSBTP/BTP0) y rasterizador ortográfico.

Formato según NitroSDK (documentación de apicula, referencia de formato). Matrices: los valores del fichero
se leen por columnas (convención M·v).
"""
import struct
import numpy as np
from PIL import Image
import ndsgfx as G

S = struct.Struct


def fx(v, bits_frac=12):
    return v / float(1 << bits_frac)


def s16(v):
    return v - 65536 if v >= 32768 else v


def s32(v):
    return v - (1 << 32) if v >= (1 << 31) else v


def cols(*v):
    """Matriz 3x3 a partir de 9 valores por columnas."""
    return np.array([[v[0], v[3], v[6]], [v[1], v[4], v[7]], [v[2], v[5], v[8]]], float)


def info_block(d, off, size):
    """Lista de (nombre, bytes_dato) de un info block con datos de `size` bytes."""
    count = d[off + 1]
    p = off + 4 + 8 + count * 4
    usize = struct.unpack_from('<H', d, p)[0]
    p += 4
    data = [d[p + i * usize:p + (i + 1) * usize] for i in range(count)]
    p += count * usize
    names = [bytes(d[p + i * 16:p + (i + 1) * 16]).split(b'\0')[0].decode('latin-1') for i in range(count)]
    return list(zip(names, data))


def pivot_mat(select, neg, a, b):
    if select >= 9:
        return np.zeros((3, 3))
    o = -1.0 if neg & 1 else 1.0
    c = -b if neg & 2 else b
    d = -a if neg & 4 else a
    z = 0.0
    v = {0: (o, z, z, z, a, b, z, c, d), 1: (z, o, z, a, z, b, c, z, d), 2: (z, z, o, a, b, z, c, d, z),
         3: (z, a, b, o, z, z, z, c, d), 4: (a, z, b, z, o, z, c, z, d), 5: (a, b, z, z, z, o, c, d, z),
         6: (z, a, b, z, c, d, o, z, z), 7: (a, z, b, c, z, d, z, o, z), 8: (a, b, z, c, d, z, z, z, o)}[select]
    return cols(*v)


def basis_mat(d):
    in0, in1, in2, in3, in4 = d
    inp = [in4, in0, in1, in2, in3]
    out = [0] * 6
    for i in range(5):
        out[i] = inp[i] >> 3
        out[5] = ((out[5] << 3) | (inp[i] & 7)) & 0xFFFF
    f = lambda x: fx(_fix13(x))
    a = np.array([_fix13(out[1]), _fix13(out[2]), _fix13(out[3])])
    b = np.array([_fix13(out[4]), _fix13(out[0]), _fix13(out[5])])
    c = np.cross(a, b)
    return np.stack([a, b, c], 1)


def _fix13(x):
    """fix16(x,1,0,12): 13 bits con signo, 12 de fracción."""
    x &= 0x1FFF
    if x & 0x1000:
        x -= 0x2000
    return x / 4096.0


# ---------------------------------------------------------------- modelo

class Material:
    pass


class Model:
    def __init__(self, d, mo, name):
        self.name = name
        self.d = d
        rd = lambda f, o: struct.unpack_from(f, d, mo + o)
        (_, self.rc_off, mat_off, piece_off, inv_off) = rd('<5I', 0)
        self.num_objects, self.num_materials, self.num_pieces = 0, 0, 0
        self.num_objects = d[mo + 0x17]
        self.num_materials = d[mo + 0x18]
        self.num_pieces = d[mo + 0x19]
        self.up_scale = fx(s32(rd('<I', 0x1C)[0]))
        self.down_scale = fx(s32(rd('<I', 0x20)[0]))
        self.bbox = [fx(s16(v)) for v in rd('<6H', 0x2C + 0)]
        self.mo = mo
        self.objects = self._objects(mo + 0x40)
        self.materials = self._materials(mo + mat_off)
        self.pieces = [d[mo + piece_off + s32(0) + 0:0] for _ in range(0)]
        self.pieces = self._pieces(mo + piece_off)
        self.inv_binds = self._inv_binds(mo + inv_off)
        self.ops = self._ops(mo + self.rc_off)

    # -- objetos (huesos)
    def _objects(self, off):
        d = self.d
        out = []
        for name, dat in info_block(d, off, 4):
            p = off + struct.unpack_from('<I', dat, 0)[0]
            flags, m0 = struct.unpack_from('<HH', d, p); p += 4
            t_id, r_id, s_id, piv = flags & 1, (flags >> 1) & 1, (flags >> 2) & 1, (flags >> 3) & 1
            trans = rot = scale = None
            if t_id == 0:
                trans = np.array([fx(s32(v)) for v in struct.unpack_from('<3I', d, p)]); p += 12
            if piv == 1:
                a, b = struct.unpack_from('<HH', d, p); p += 4
                rot = pivot_mat((flags >> 4) & 15, (flags >> 8) & 15, fx(s16(a)), fx(s16(b)))
            elif r_id == 0:
                m = struct.unpack_from('<8H', d, p); p += 16
                v = [fx(s16(x)) for x in (m0,) + m]
                rot = cols(*v)
            if s_id == 0:
                scale = np.array([fx(s32(v)) for v in struct.unpack_from('<3I', d, p)]); p += 12
            out.append({'name': name, 't': trans, 'r': rot, 's': scale})
        return out

    @staticmethod
    def trs_matrix(t, r, s):
        m = np.eye(4)
        if s is not None:
            m = np.diag([s[0], s[1], s[2], 1.0])
        if r is not None:
            R4 = np.eye(4); R4[:3, :3] = r; m = R4 @ m
        if t is not None:
            T4 = np.eye(4); T4[:3, 3] = t; m = T4 @ m
        return m

    # -- materiales
    def _materials(self, off):
        d = self.d
        tex_pair, pal_pair = struct.unpack_from('<HH', d, off)
        mats = []
        for name, dat in info_block(d, off + 4, 4):
            p = off + struct.unpack_from('<I', dat, 0)[0]
            dif_amb, spe_emi, pattr, pmask, tparam, unk3, pbase, misc = struct.unpack_from('<IIIIIIHH', d, p + 4)
            w, h = struct.unpack_from('<HH', d, p + 4 + 28)
            m = Material()
            m.name = name
            rgb = lambda x: tuple(((x >> (5 * i)) & 31) / 31.0 for i in range(3))
            m.diffuse = rgb(dif_amb & 0x7FFF); m.diffuse_vtx = bool(dif_amb & 0x8000)
            m.ambient = rgb((dif_amb >> 16) & 0x7FFF)
            m.emission = rgb((spe_emi >> 16) & 0x7FFF)
            m.alpha = ((pattr >> 16) & 31) / 31.0
            m.light_mask = pattr & 15
            m.cull_back = ((pattr >> 6) & 1) == 0
            m.cull_front = ((pattr >> 7) & 1) == 0
            params = tparam & pmask if pmask else tparam
            m.rep_s = bool(params & (1 << 16)); m.rep_t = bool(params & (1 << 17))
            m.flip_s = bool(params & (1 << 18)); m.flip_t = bool(params & (1 << 19))
            m.fmt = (params >> 26) & 7
            m.w, m.h = w, h
            q = p + 4 + 28 + 4
            m.sx = m.sy = 1.0
            if misc & 1:
                q2 = q
                q = p + 0x2C
                if not misc & 2:
                    m.sx, m.sy = fx(s32(struct.unpack_from('<I', d, q)[0])), fx(s32(struct.unpack_from('<I', d, q + 4)[0]))
            m.tex = m.pal = None
            mats.append(m)
        for dst, o in (('tex', tex_pair), ('pal', pal_pair)):
            for name, dat in info_block(d, off + o, 4):
                o2, num = struct.unpack_from('<HB', dat, 0)
                for k in range(num):
                    mi = d[off + o2 + k]
                    if mi < len(mats):
                        setattr(mats[mi], dst, name)
        return mats

    def _pieces(self, off):
        d = self.d
        out = []
        for name, dat in info_block(d, off, 4):
            p = off + struct.unpack_from('<I', dat, 0)[0]
            co, cl = struct.unpack_from('<II', d, p + 8)
            out.append(bytes(d[p + co:p + co + cl]))
        return out

    def _inv_binds(self, off):
        out = []
        for i in range(self.num_objects):
            p = off + i * 84
            if p + 84 > len(self.d):
                break
            v = [fx(s32(x)) for x in struct.unpack_from('<12I', self.d, p)]
            m = np.eye(4)
            m[:3, 0] = v[0:3]; m[:3, 1] = v[3:6]; m[:3, 2] = v[6:9]; m[:3, 3] = v[9:12]
            out.append(m)
        return out

    # -- comandos de render
    def _ops(self, p):
        d = self.d
        ops = []
        sizes = {0: 0, 1: 0, 2: 2, 3: 1, 4: 1, 5: 1, 6: 3, 7: 1, 8: 1, 0xb: 0, 0xc: 2, 0xd: 2, 0x24: 1, 0x26: 4,
                 0x2b: 0, 0x40: 0, 0x44: 1, 0x46: 4, 0x47: 2, 0x66: 5, 0x80: 0}
        for _ in range(100000):
            op = d[p]; p += 1
            if op == 9:
                n = d[p + 1]; par = d[p:p + 2 + 3 * n]; p += 2 + 3 * n
            else:
                n = sizes.get(op)
                if n is None:
                    break
                par = d[p:p + n]; p += n
            if op == 1:
                break
            if op == 3:
                ops.append(('load', par[0]))
            elif op in (4, 0x24, 0x44):
                ops.append(('mat', par[0]))
            elif op == 5:
                ops.append(('draw', par[0]))
            elif op in (6, 0x26, 0x46, 0x66):
                store = load = None
                if op == 0x26: store = par[3]
                elif op == 0x46: load = par[3]
                elif op == 0x66: store, load = par[3], par[4]
                if load is not None: ops.append(('load', load))
                ops.append(('obj', par[0]))
                if store is not None: ops.append(('store', store))
            elif op == 9:
                terms = [(par[2 + 3 * i], par[3 + 3 * i], par[4 + 3 * i] / 256.0) for i in range(par[1])]
                ops.append(('skin', terms)); ops.append(('store', par[0]))
            elif op == 0xb:
                ops.append(('scaleup',))
            elif op == 0x2b:
                ops.append(('scaledown',))
        return ops

    # -- geometría
    def object_matrices(self, anim=None, frame=0):
        mats = []
        for i, o in enumerate(self.objects):
            t, r, s = o['t'], o['r'], o['s']
            if anim is not None:
                t, r, s = anim.sample(i, frame, t, r, s)
            mats.append(self.trs_matrix(t, r, s))
        return mats

    def triangles(self, anim=None, frame=0, root=None):
        """-> lista de (material, [v0,v1,v2]) con v = (x,y,z,u,v,(r,g,b),(nx,ny,nz)) en espacio del modelo."""
        objm = self.object_matrices(anim, frame)
        stack = [np.eye(4)] * 32
        cur = np.eye(4) if root is None else root.copy()
        mat = None
        tris = []
        for op in self.ops:
            k = op[0]
            if k == 'load':
                cur = stack[op[1]]
            elif k == 'store':
                stack[op[1]] = cur
            elif k == 'obj':
                cur = cur @ objm[op[1]]
            elif k == 'skin':
                acc = np.zeros((4, 4))
                for sp, ib, w in op[1]:
                    inv = self.inv_binds[ib] if ib < len(self.inv_binds) else np.eye(4)
                    acc += w * (stack[sp] @ inv)
                cur = acc
            elif k == 'scaleup':
                cur = cur @ np.diag([self.up_scale] * 3 + [1.0])
            elif k == 'scaledown':
                cur = cur @ np.diag([self.down_scale] * 3 + [1.0])
            elif k == 'mat':
                mat = op[1]
            elif k == 'draw':
                for tri in run_dl(self.pieces[op[1]], cur, stack):
                    tris.append((mat, tri))
        self.last_stack = stack
        return tris


DL_PARAMS = {0x00: 0, 0x14: 1, 0x1B: 3, 0x20: 1, 0x21: 1, 0x22: 1, 0x23: 2, 0x24: 1, 0x25: 1, 0x26: 1, 0x27: 1,
             0x28: 1, 0x29: 1, 0x2A: 1, 0x2B: 1, 0x30: 1, 0x31: 1, 0x32: 1, 0x33: 1, 0x34: 32, 0x40: 1, 0x41: 0,
             0x50: 1, 0x60: 1, 0x70: 3, 0x71: 2, 0x72: 1, 0x10: 1, 0x11: 0, 0x12: 1, 0x13: 1, 0x15: 0, 0x16: 16,
             0x17: 12, 0x18: 16, 0x19: 12, 0x1A: 9, 0x1C: 3}


def run_dl(dl, base, mstack=None):
    """Interpreta una display list de GPU y devuelve triángulos con vértices transformados por `base`."""
    words = np.frombuffer(dl[:len(dl) // 4 * 4], '<u4').tolist()
    i = 0
    cur = base.copy()
    stack = mstack if mstack is not None else {}
    v = [0.0, 0.0, 0.0]
    st = (0.0, 0.0)
    col = (1.0, 1.0, 1.0)
    nrm = (0.0, 0.0, 1.0)
    prim = 0
    verts = []
    out = []
    n3 = lambda a: a if a < 512 else a - 1024

    def emit():
        p = cur @ np.array([v[0], v[1], v[2], 1.0])
        nn = cur[:3, :3] @ np.array(nrm)
        verts.append((p[0], p[1], p[2], st[0], st[1], col, tuple(nn)))

    def flush():
        n = len(verts)
        if prim == 0:
            for k in range(0, n - 2, 3): out.append(verts[k:k + 3])
        elif prim == 1:
            for k in range(0, n - 3, 4):
                a, b, c, e = verts[k:k + 4]; out.append([a, b, c]); out.append([a, c, e])
        elif prim == 2:
            for k in range(n - 2):
                out.append(verts[k:k + 3] if k % 2 == 0 else [verts[k + 1], verts[k], verts[k + 2]])
        elif prim == 3:
            for k in range(0, n - 3, 2):
                a, b, c, e = verts[k:k + 4]; out.append([a, b, e]); out.append([a, e, c])

    while i < len(words):
        cmds = [(words[i] >> (8 * k)) & 0xFF for k in range(4)]
        i += 1
        for c in cmds:
            n = DL_PARAMS.get(c, 0)
            p = words[i:i + n]; i += n
            if c == 0x40:
                verts.clear(); prim = p[0] & 3
            elif c == 0x41:
                flush(); verts.clear()
            elif c == 0x14:
                cur = stack[p[0] & 31] if not isinstance(stack, dict) else stack.get(p[0] & 31, base)
            elif c == 0x1B:
                cur = cur @ np.diag([fx(s32(p[0])), fx(s32(p[1])), fx(s32(p[2])), 1.0])
            elif c == 0x22:
                st = (s16(p[0] & 0xFFFF) / 16.0, s16(p[0] >> 16) / 16.0)
            elif c == 0x20:
                x = p[0]; col = ((x & 31) / 31.0, ((x >> 5) & 31) / 31.0, ((x >> 10) & 31) / 31.0)
            elif c == 0x21:
                x = p[0]; nrm = (n3(x & 0x3FF) / 512.0, n3((x >> 10) & 0x3FF) / 512.0, n3((x >> 20) & 0x3FF) / 512.0)
            elif c == 0x23:
                v = [s16(p[0] & 0xFFFF) / 4096.0, s16(p[0] >> 16) / 4096.0, s16(p[1] & 0xFFFF) / 4096.0]; emit()
            elif c == 0x24:
                x = p[0]; v = [n3(x & 0x3FF) / 64.0, n3((x >> 10) & 0x3FF) / 64.0, n3((x >> 20) & 0x3FF) / 64.0]; emit()
            elif c == 0x25:
                v = [s16(p[0] & 0xFFFF) / 4096.0, s16(p[0] >> 16) / 4096.0, v[2]]; emit()
            elif c == 0x26:
                v = [s16(p[0] & 0xFFFF) / 4096.0, v[1], s16(p[0] >> 16) / 4096.0]; emit()
            elif c == 0x27:
                v = [v[0], s16(p[0] & 0xFFFF) / 4096.0, s16(p[0] >> 16) / 4096.0]; emit()
            elif c == 0x28:
                x = p[0]
                v = [v[0] + n3(x & 0x3FF) / 4096.0, v[1] + n3((x >> 10) & 0x3FF) / 4096.0, v[2] + n3((x >> 20) & 0x3FF) / 4096.0]; emit()
    return out


# ---------------------------------------------------------------- animaciones

class Anim:
    def __init__(self, d, off, name):
        self.name = name
        stamp = d[off:off + 4]
        nf, no = struct.unpack_from('<HH', d, off + 4)
        pivot_off, basis_off = struct.unpack_from('<II', d, off + 12)
        self.num_frames = nf
        offs = struct.unpack_from(f'<{no}H', d, off + 20)
        self.curves = []

        def rot_of(x):
            mode = (x >> 15) & 1; idx = x & 0x7FFF
            if mode == 1:
                selneg, a, b = struct.unpack_from('<HHH', d, off + pivot_off + idx * 6)
                return pivot_mat(selneg & 15, (selneg >> 4) & 15, fx(s16(a)), fx(s16(b)))
            return basis_mat(struct.unpack_from('<5H', d, off + basis_off + idx * 10))

        def info(x):
            start = x & 0xFFFF; end = (x >> 16) & 0xFFF; width = (x >> 28) & 3; rate = (x >> 30) & 3
            return start, end, rate, width

        for co in offs:
            p = off + co
            flags, _, idx = struct.unpack_from('<HBB', d, p); p += 4
            tc = {'t': [None] * 3, 'r': None, 's': [None] * 3, 'animated': (flags & 1) == 0}
            if tc['animated']:
                if ((flags >> 1) & 3) == 0:
                    for i in range(3):
                        if (flags >> (3 + i)) & 1:
                            tc['t'][i] = ('c', fx(s32(struct.unpack_from('<I', d, p)[0]))); p += 4
                        else:
                            inf, o2 = struct.unpack_from('<II', d, p); p += 8
                            a, b, rate, width = info(inf)
                            n = (b - a) >> rate
                            if width == 0:
                                vals = [fx(s32(x)) for x in struct.unpack_from(f'<{n}I', d, off + o2)]
                            else:
                                vals = [fx(s16(x)) for x in struct.unpack_from(f'<{n}H', d, off + o2)]
                            tc['t'][i] = ('s', a, b, vals)
                if ((flags >> 6) & 3) == 0:
                    if (flags >> 8) & 1:
                        v, _ = struct.unpack_from('<HH', d, p); p += 4
                        tc['r'] = ('c', rot_of(v))
                    else:
                        inf, o2 = struct.unpack_from('<II', d, p); p += 8
                        a, b, rate, width = info(inf)
                        n = (b - a) >> rate
                        vals = [rot_of(x) for x in struct.unpack_from(f'<{n}H', d, off + o2)]
                        tc['r'] = ('s', a, b, vals)
                if ((flags >> 9) & 3) == 0:
                    for i in range(3):
                        if (flags >> (11 + i)) & 1:
                            tc['s'][i] = ('c', fx(s32(struct.unpack_from('<I', d, p)[0]))); p += 8
                        else:
                            inf, o2 = struct.unpack_from('<II', d, p); p += 8
                            a, b, rate, width = info(inf)
                            n = (b - a) >> rate
                            if width == 0:
                                vals = [fx(s32(struct.unpack_from('<I', d, off + o2 + k * 8)[0])) for k in range(n)]
                            else:
                                vals = [fx(s16(struct.unpack_from('<H', d, off + o2 + k * 4)[0])) for k in range(n)]
                            tc['s'][i] = ('s', a, b, vals)
            self.curves.append(tc)

    @staticmethod
    def _samp(c, frame):
        if c is None: return None
        if c[0] == 'c': return c[1]
        _, a, b, vals = c
        if not vals: return None
        if frame <= a: return vals[0]
        if frame >= b - 1: return vals[-1]
        lam = (frame - a) / (b - 1 - a)
        idx = lam * (len(vals) - 1)
        lo, hi = int(np.floor(idx)), int(np.ceil(idx)); g = idx - lo
        return vals[lo] * (1 - g) + vals[hi] * g

    def sample(self, i, frame, t, r, s):
        if i >= len(self.curves) or not self.curves[i]['animated']:
            return t, r, s
        c = self.curves[i]
        if any(x is not None for x in c['t']):
            tt = np.array(t if t is not None else [0.0, 0, 0], float)
            for k in range(3):
                v = self._samp(c['t'][k], frame)
                if v is not None: tt[k] = v
            t = tt
        if c['r'] is not None:
            r = self._samp(c['r'], frame)
        if any(x is not None for x in c['s']):
            ss = np.array(s if s is not None else [1.0, 1, 1], float)
            for k in range(3):
                v = self._samp(c['s'][k], frame)
                if v is not None: ss[k] = v
            s = ss
        return t, r, s


class Pattern:
    def __init__(self, d, off, name):
        self.name = name
        nf, ntex, npal, tex_off, pal_off = struct.unpack_from('<HBBHH', d, off + 4)
        rd = lambda o, n: [bytes(d[o + i * 16:o + i * 16 + 16]).split(b'\0')[0].decode('latin-1') for i in range(n)]
        self.num_frames = nf
        self.tex_names = rd(off + tex_off, ntex)
        self.pal_names = rd(off + pal_off, npal)
        self.tracks = {}
        p = off + 12
        for tname, dat in info_block(d, p, 8):
            nk, _, ko = struct.unpack_from('<IHH', dat, 0)
            keys = [struct.unpack_from('<HBB', d, off + ko + k * 4) for k in range(nk)]
            self.tracks[tname] = keys

    def sample(self, mat_name, frame):
        keys = self.tracks.get(mat_name)
        if not keys: return None
        sel = keys[0]
        for k in keys:
            if k[0] <= frame: sel = k
        return self.tex_names[sel[1]], self.pal_names[sel[2]]


# ---------------------------------------------------------------- contenedor y texturas

class TexBank:
    def __init__(self, sec):
        self.sec = sec
        self.tex_data = struct.unpack_from('<I', sec, 0x14)[0]
        self.comp_data = struct.unpack_from('<I', sec, 0x24)[0]
        self.comp_info = struct.unpack_from('<I', sec, 0x28)[0]
        pal_size = struct.unpack_from('<I', sec, 0x30)[0] << 3
        pal_info = struct.unpack_from('<I', sec, 0x34)[0]
        self.pal_data = struct.unpack_from('<I', sec, 0x38)[0]
        self.texs = {n: dat for n, dat in G._dict3d(sec, struct.unpack_from('<H', sec, 0xE)[0], 8)}
        self.pals = {n: struct.unpack_from('<H', dat, 0)[0] << 3 for n, dat in G._dict3d(sec, pal_info, 4)}
        self.pal_raw = sec[self.pal_data:self.pal_data + pal_size]
        self.cache = {}

    def decode(self, tex, pal):
        key = (tex, pal)
        if key in self.cache: return self.cache[key]
        dat = self.texs.get(tex)
        if dat is None:
            return None
        off = struct.unpack_from('<H', dat, 0)[0] << 3
        params = struct.unpack_from('<H', dat, 2)[0]
        w, h = 8 << ((params >> 4) & 7), 8 << ((params >> 7) & 7)
        fmt = (params >> 10) & 7; c0t = (params >> 13) & 1
        poff = self.pals.get(pal, 0) if pal else 0
        colors = np.frombuffer(bytes(self.pal_raw[poff:]) + b'\0' * 512, dtype='<u2')
        img = G._decode_tex(self.sec, fmt, w, h, self.tex_data + off, self.comp_data + off,
                            self.comp_info + off // 2, colors, c0t)
        arr = np.array(img) if img is not None else None
        self.cache[key] = arr
        return arr


class Nitro:
    def __init__(self, data):
        d = self.d = bytes(data)
        self.magic = d[:4]
        nsec = struct.unpack_from('<H', d, 0xE)[0]
        self.models, self.anims, self.patterns, self.banks = [], [], [], []
        for i in range(nsec):
            so = struct.unpack_from('<I', d, 0x10 + i * 4)[0]
            m = d[so:so + 4]
            if m == b'MDL0':
                for name, dat in info_block(d, so + 8, 4):
                    self.models.append(Model(d, so + struct.unpack_from('<I', dat, 0)[0], name))
            elif m == b'TEX0':
                self.banks.append(TexBank(d[so:so + struct.unpack_from('<I', d, so + 4)[0]]))
            elif m == b'JNT0':
                for name, dat in info_block(d, so + 8, 4):
                    try:
                        self.anims.append(Anim(d, so + struct.unpack_from('<I', dat, 0)[0], name))
                    except Exception:
                        pass
            elif m == b'PAT0':
                for name, dat in info_block(d, so + 8, 4):
                    self.patterns.append(Pattern(d, so + struct.unpack_from('<I', dat, 0)[0], name))


class TexLookup:
    def __init__(self, *nitros):
        self.banks = [b for n in nitros for b in n.banks]

    def get(self, tex, pal):
        for b in self.banks:
            if tex in b.texs:
                p = pal if pal in b.pals else None
                if p is None:
                    for bb in self.banks:
                        if pal in bb.pals:
                            return _decode_with(b, bb, tex, pal)
                return b.decode(tex, p)
        return None


def _decode_with(b, bp, tex, pal):
    """Textura de un banco con la paleta de otro."""
    saved = (b.pal_raw, b.pals)
    b.pal_raw = bp.pal_raw; b.pals = bp.pals
    b.cache = {}
    try:
        return b.decode(tex, pal)
    finally:
        b.pal_raw, b.pals = saved; b.cache = {}


# ---------------------------------------------------------------- rasterizador

def wrap(i, n, rep, flip):
    if not rep: return np.clip(i, 0, n - 1)
    if flip:
        per = i // n; r = i % n
        return np.where(per % 2 == 1, n - 1 - r, r)
    return i % n


DEFAULT_LIGHT = (0.35, -0.45, -0.82)  # dirección hacia donde apunta la luz (x der, y arriba, z hacia cámara)


def render(tris, model, texlook, **kw):
    return render_items([(tris, model, kw.pop('pattern', None), kw.pop('frame', 0))], texlook, **kw)


def render_items(items, texlook, scale=16.0, size=None, origin=None, shade=True,
           light=DEFAULT_LIGHT, ambient=0.62, ortho=lambda x, y, z: (x, -y), flipx=False):
    """Rasteriza triángulos (de Model.triangles) con cámara ortográfica de frente (+x derecha, +y arriba,
    +z hacia la cámara). Devuelve imagen RGBA (np.uint8) y (ox, oy) = píxel del origen del modelo."""
    flat = []   # (modelo, patrón, frame, mat, vértices)
    for tris, model, pattern, frame in items:
        for mi, vs in tris:
            flat.append((model, pattern, frame, mi, vs))
    P = []
    for model, pattern, frame, mi, vs in flat:
        P.append([(ortho(v[0], v[1], v[2])[0] * scale * (-1 if flipx else 1),
                   ortho(v[0], v[1], v[2])[1] * scale, v[2]) for v in vs])
    if not P:
        return None, (0, 0)
    xs = [p[0] for pts in P for p in pts]; ys = [p[1] for pts in P for p in pts]
    if origin is None:
        x0, y0 = int(np.floor(min(xs))) - 1, int(np.floor(min(ys))) - 1
        W, H = int(np.ceil(max(xs))) - x0 + 2, int(np.ceil(max(ys))) - y0 + 2
    else:
        x0, y0 = -origin[0], -origin[1]; W, H = size
    img = np.zeros((H, W, 4), np.float32)
    depth = np.full((H, W), -1e9, np.float32)
    L = np.array(light, float); L /= np.linalg.norm(L)
    order = sorted(range(len(flat)), key=lambda k: (flat[k][0].materials[flat[k][3]].alpha < 1))
    for k in order:
        model, pattern, frame, mi, vs = flat[k]
        m = model.materials[mi]
        texn, paln = m.tex, m.pal
        if pattern is not None:
            r = pattern.sample(m.name, frame)
            if r: texn, paln = r
        tex = texlook.get(texn, paln) if texn else None
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = P[k]
        ax -= x0; bx -= x0; cx -= x0; ay -= y0; by -= y0; cy -= y0
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-9: continue
        area_sign = den  # orientación en pantalla (y hacia abajo)
        if flipx: area_sign = -area_sign
        # culling: en pantalla y-abajo, caras frontales antihorarias en y-arriba => den<0
        front = area_sign < 0
        if front and not m.cull_front: pass
        if (not front) and m.cull_back: continue
        if front and m.cull_front: continue
        minx, maxx = max(int(np.floor(min(ax, bx, cx))), 0), min(int(np.ceil(max(ax, bx, cx))), W)
        miny, maxy = max(int(np.floor(min(ay, by, cy))), 0), min(int(np.ceil(max(ay, by, cy))), H)
        if minx >= maxx or miny >= maxy: continue
        gx, gy = np.meshgrid(np.arange(minx, maxx) + 0.5, np.arange(miny, maxy) + 0.5)
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        eps = -1e-4
        inside = (w0 >= eps) & (w1 >= eps) & (w2 >= eps)
        if not inside.any(): continue
        d = w0 * az + w1 * bz + w2 * cz
        if tex is not None:
            su = w0 * vs[0][3] + w1 * vs[1][3] + w2 * vs[2][3]
            tv = w0 * vs[0][4] + w1 * vs[1][4] + w2 * vs[2][4]
            su = su * m.sx; tv = tv * m.sy
            th, tw = tex.shape[:2]
            ui = wrap(np.floor(su).astype(int), tw, m.rep_s, m.flip_s)
            vi = wrap(np.floor(tv).astype(int), th, m.rep_t, m.flip_t)
            texel = tex[vi, ui].astype(np.float32) / 255.0
        else:
            texel = np.ones(gx.shape + (4,), np.float32)
        # color de vértice / iluminación
        cs = []
        for v in vs:
            if shade and m.light_mask:
                n = np.array(v[6]); nl = np.linalg.norm(n)
                ndl = max(0.0, -float(n @ L) / nl) if nl > 1e-6 else 0.0
                inten = ambient + (1 - ambient) * ndl
                base = np.array(m.diffuse) if not m.diffuse_vtx else np.array(v[5])
                cs.append(np.array([inten] * 3))
            else:
                cs.append(np.array(v[5]) if not shade else np.array([1.0, 1.0, 1.0]))
        col = np.stack([w0 * cs[0][i] + w1 * cs[1][i] + w2 * cs[2][i] for i in range(3)], -1)
        rgb = np.clip(texel[..., :3] * col, 0, 1)
        a = texel[..., 3] * m.alpha
        ok = inside & (a > 0.5) & (d >= depth[miny:maxy, minx:maxx] - 1e-4)
        if not ok.any(): continue
        reg = img[miny:maxy, minx:maxx]
        reg[..., :3] = np.where(ok[..., None], rgb, reg[..., :3])
        reg[..., 3] = np.where(ok, 1.0, reg[..., 3])
        dz = depth[miny:maxy, minx:maxx]
        dz[ok] = d[ok]
    return (img * 255).astype(np.uint8), (-x0, -y0)
