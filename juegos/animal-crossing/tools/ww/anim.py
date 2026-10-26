"""Animaciones de huesos NSBCA (BCA0 / JNT0 / JAC0) de Nintendo DS.

Cada animación da, por nodo, curvas de traslación, rotación (matriz 3x3) y escala.
"""
import struct
import numpy as np

from .nitro3d import sections, read_dict, rot_pivot, sx


def basis_mat(w):
    in0, in1, in2, in3, in4 = w
    inp = [in4, in0, in1, in2, in3]
    out = [0] * 6
    for i in range(5):
        out[i] = inp[i] >> 3
        out[5] = ((out[5] << 3) | (inp[i] & 7)) & 0xFFFF
    f = lambda x: sx(x & 0x1FFF, 13) / 4096.0
    a = np.array([f(out[1]), f(out[2]), f(out[3])])
    b = np.array([f(out[4]), f(out[0]), f(out[5])])
    c = np.cross(a, b)
    return np.stack([a, b, c], 1)


class Curve:
    def __init__(self, kind='none', value=None, start=0, end=0, rate=0, values=None):
        self.kind, self.value, self.start, self.end, self.rate, self.values = kind, value, start, end, rate, values

    def at(self, default, frame):
        if self.kind == 'none':
            return default
        if self.kind == 'const':
            return self.value
        vals = self.values
        if not len(vals):
            return default
        if frame <= self.start:
            return vals[0]
        if frame >= self.end - 1:
            return vals[-1]
        pos = (frame - self.start) / float(1 << self.rate)
        lo = int(np.floor(pos))
        hi = min(lo + 1, len(vals) - 1)
        g = pos - lo
        return vals[lo] * (1 - g) + vals[hi] * g


def _info(x):
    return x & 0xFFFF, (x >> 16) & 0xFFF, (x >> 30) & 3, (x >> 28) & 3


class Animation:
    """Animación JAC0. objs[i] da las curvas del nodo i."""

    def __init__(self, d, off, name):
        self.name = name
        if bytes(d[off:off + 4]) != b'J\0AC':
            raise ValueError('JAC0 inválido')
        self.num_frames, nobj = struct.unpack_from('<HH', d, off + 4)
        pivot_off, basis_off = struct.unpack_from('<II', d, off + 12)
        objoffs = struct.unpack_from('<%dH' % nobj, d, off + 20)
        self.objs = []

        def fetch(x):
            if x & 0x8000:
                sel_neg, a, b = struct.unpack_from('<3H', d, off + pivot_off + (x & 0x7FFF) * 6)
                return rot_pivot(sel_neg & 15, (sel_neg >> 4) & 15, sx(a, 16) / 4096.0, sx(b, 16) / 4096.0).T
            w = struct.unpack_from('<5H', d, off + basis_off + (x & 0x7FFF) * 10)
            return basis_mat(w)

        for o in objoffs:
            p = off + o
            flags = struct.unpack_from('<H', d, p)[0]
            p += 4
            c = {'t': [Curve(), Curve(), Curve()], 'r': Curve(), 's': [Curve(), Curve(), Curve()]}
            self.objs.append(c)
            bit = lambda a, b: (flags >> a) & ((1 << (b - a)) - 1)
            if bit(0, 1) != 0:
                continue
            if bit(1, 3) == 0:
                for i in range(3):
                    if bit(3 + i, 4 + i):
                        c['t'][i] = Curve('const', sx(struct.unpack_from('<I', d, p)[0], 32) / 4096.0)
                        p += 4
                    else:
                        inf, offv = struct.unpack_from('<II', d, p)
                        p += 8
                        st, en, rate, width = _info(inf)
                        n = (en - st) >> rate
                        if width == 0:
                            vals = [sx(v, 32) / 4096.0 for v in struct.unpack_from('<%dI' % n, d, off + offv)]
                        else:
                            vals = [sx(v, 16) / 4096.0 for v in struct.unpack_from('<%dH' % n, d, off + offv)]
                        c['t'][i] = Curve('samples', None, st, en, rate, vals)
            if bit(6, 8) == 0:
                if bit(8, 9):
                    v = struct.unpack_from('<H', d, p)[0]
                    p += 4
                    c['r'] = Curve('const', fetch(v))
                else:
                    inf, offv = struct.unpack_from('<II', d, p)
                    p += 8
                    st, en, rate, width = _info(inf)
                    n = (en - st) >> rate
                    vals = [fetch(v) for v in struct.unpack_from('<%dH' % n, d, off + offv)]
                    c['r'] = Curve('samples', None, st, en, rate, vals)
            if bit(9, 11) == 0:
                for i in range(3):
                    if bit(11 + i, 12 + i):
                        c['s'][i] = Curve('const', sx(struct.unpack_from('<I', d, p)[0], 32) / 4096.0)
                        p += 8
                    else:
                        inf, offv = struct.unpack_from('<II', d, p)
                        p += 8
                        st, en, rate, width = _info(inf)
                        n = (en - st) >> rate
                        if width == 0:
                            vals = [sx(v, 32) / 4096.0 for v in struct.unpack_from('<%dI' % (n * 2), d, off + offv)][::2]
                        else:
                            vals = [sx(v, 16) / 4096.0 for v in struct.unpack_from('<%dH' % (n * 2), d, off + offv)][::2]
                        c['s'][i] = Curve('samples', None, st, en, rate, vals)

    def frame(self, f, model):
        """{nodo: (t, R, S)} para el fotograma f. Los nodos sin curva conservan su pose base."""
        out = {}
        for i, c in enumerate(self.objs):
            if i >= len(model.nodes):
                break
            n = model.nodes[i]
            bt = n.t if n.t is not None else np.zeros(3)
            br = n.r if n.r is not None else np.eye(3)
            bs = n.s if n.s is not None else np.ones(3)
            t = np.array([k.at(bt[j], f) for j, k in enumerate(c['t'])])
            r = c['r'].at(br, f)
            s = np.array([k.at(bs[j], f) for j, k in enumerate(c['s'])])
            out[i] = (t, r, s)
        return out


def load_animations(d):
    """Todas las animaciones de un BCA0: {nombre: Animation}."""
    sec = sections(d)['JNT0']
    anims = {}
    for name, e in read_dict(d, sec + 8):
        o = sec + struct.unpack_from('<I', e, 0)[0]
        try:
            anims[name] = Animation(d, o, name)
        except Exception:
            pass
    return anims
