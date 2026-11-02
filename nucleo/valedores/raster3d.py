"""Rasterizador por software con búfer de profundidad común a toda la escena.

Dibuja lotes de triángulos ya proyectados: corrección de perspectiva, texturas con repetición y espejo
como la DS, transparencia por texel, mezcla alfa y calcas (triángulos que se pintan sobre otros con la
misma profundidad). numba lo compila la primera vez; sin él una escena de miles de triángulos no es viable.
"""
import numpy as np
from numba import njit


@njit(cache=True, fastmath=True)
def _indice(i, n, repetir, espejo):
    if not repetir:
        return 0 if i < 0 else (n - 1 if i >= n else i)
    r = i % n
    if espejo and (i // n) % 2 != 0:
        return n - 1 - r
    return r


@njit(cache=True, fastmath=True)
def _dibujar(color, zbuf, xy, w_inv, uv, luz, tex_id, alfa_mat, modo, tinte, niebla,
             texeles, tex_off, tex_w, tex_h, tex_flags):
    H, W = zbuf.shape
    for t in range(xy.shape[0]):
        ax, ay, bx, by, cx, cy = xy[t, 0, 0], xy[t, 0, 1], xy[t, 1, 0], xy[t, 1, 1], xy[t, 2, 0], xy[t, 2, 1]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-7:
            continue
        x0 = max(int(np.floor(min(ax, bx, cx))), 0)
        x1 = min(int(np.ceil(max(ax, bx, cx))), W)
        y0 = max(int(np.floor(min(ay, by, cy))), 0)
        y1 = min(int(np.ceil(max(ay, by, cy))), H)
        if x0 >= x1 or y0 >= y1:
            continue
        idn = 1.0 / den
        wa, wb, wc = w_inv[t, 0], w_inv[t, 1], w_inv[t, 2]
        tid = tex_id[t]
        m = modo[t]
        if tid >= 0:
            off, tw, th, fl = tex_off[tid], tex_w[tid], tex_h[tid], tex_flags[tid]
            rs, rt, es, et, suave = (fl & 1) != 0, (fl & 2) != 0, (fl & 4) != 0, (fl & 8) != 0, (fl & 16) != 0
        else:
            off, tw, th, rs, rt, es, et, suave = 0, 1, 1, False, False, False, False, False
        for y in range(y0, y1):
            py = y + 0.5
            for x in range(x0, x1):
                px = x + 0.5
                l0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) * idn
                l1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) * idn
                l2 = 1.0 - l0 - l1
                if l0 < -1e-4 or l1 < -1e-4 or l2 < -1e-4:
                    continue
                w = l0 * wa + l1 * wb + l2 * wc
                if w <= 0:
                    continue
                prof = zbuf[y, x]
                # modo 0: opaco; 1: mezcla sin escribir profundidad; 2: calca, que comparte profundidad.
                if m == 2:
                    if w < prof * 0.995:
                        continue
                elif w < prof:
                    continue
                z = 1.0 / w
                r, g, b, a = 1.0, 1.0, 1.0, 1.0
                if tid >= 0:
                    su = (l0 * uv[t, 0, 0] + l1 * uv[t, 1, 0] + l2 * uv[t, 2, 0]) * z
                    tv = (l0 * uv[t, 0, 1] + l1 * uv[t, 1, 1] + l2 * uv[t, 2, 1]) * z
                    if suave:
                        fu, fv = su - 0.5, tv - 0.5
                        iu, iv = int(np.floor(fu)), int(np.floor(fv))
                        du, dv = fu - iu, fv - iv
                        r = g = b = a = 0.0
                        for k in range(4):
                            ku = iu + (k & 1)
                            kv = iv + (k >> 1)
                            pes = (du if k & 1 else 1 - du) * (dv if k >> 1 else 1 - dv)
                            q = off + 4 * (_indice(kv, th, rt, et) * tw + _indice(ku, tw, rs, es))
                            r += pes * texeles[q]
                            g += pes * texeles[q + 1]
                            b += pes * texeles[q + 2]
                            a += pes * texeles[q + 3]
                        r /= 255.0
                        g /= 255.0
                        b /= 255.0
                        a /= 255.0
                    else:
                        iu = int(np.floor(su))
                        iv = int(np.floor(tv))
                        q = off + 4 * (_indice(iv, th, rt, et) * tw + _indice(iu, tw, rs, es))
                        r, g, b, a = texeles[q] / 255.0, texeles[q + 1] / 255.0, texeles[q + 2] / 255.0, texeles[q + 3] / 255.0
                a *= alfa_mat[t]
                if m == 0:
                    if a < 0.5:
                        continue
                elif a <= 0.004:
                    continue
                k = (l0 * luz[t, 0] + l1 * luz[t, 1] + l2 * luz[t, 2]) * z
                r *= k * tinte[t, 0]
                g *= k * tinte[t, 1]
                b *= k * tinte[t, 2]
                if niebla[3] > 0:
                    f = (z - niebla[0]) / max(niebla[1] - niebla[0], 1e-5)
                    f = (0.0 if f < 0 else (1.0 if f > 1 else f)) * niebla[3]
                    r += (niebla[4] - r) * f
                    g += (niebla[5] - g) * f
                    b += (niebla[6] - b) * f
                if m == 0:
                    color[y, x, 0], color[y, x, 1], color[y, x, 2], color[y, x, 3] = r, g, b, 1.0
                    zbuf[y, x] = w
                else:
                    ia = 1.0 - a
                    color[y, x, 0] = r * a + color[y, x, 0] * ia
                    color[y, x, 1] = g * a + color[y, x, 1] * ia
                    color[y, x, 2] = b * a + color[y, x, 2] * ia
                    color[y, x, 3] = a + color[y, x, 3] * ia


class Texturas:
    """Banco de texturas en un único bloque RGBA, tal como lo espera el rasterizador."""

    def __init__(self):
        self._bloques, self._w, self._h, self._flags, self._off = [], [], [], [], []
        self._total = 0
        self._memo = None
        self._ids = {}

    def registrar(self, clave, imagen, repetir_s=False, repetir_t=False, espejo_s=False, espejo_t=False, suave=False):
        """Añade una textura (o devuelve la ya registrada con esa clave)."""
        if clave in self._ids:
            return self._ids[clave]
        im = np.asarray(imagen, np.uint8)
        if im.ndim != 3 or im.shape[2] != 4:
            raise ValueError('La textura debe ser RGBA')
        i = len(self._w)
        self._ids[clave] = i
        self._bloques.append(im.reshape(-1).copy())
        self._off.append(self._total)
        self._total += im.size
        self._h.append(im.shape[0])
        self._w.append(im.shape[1])
        self._flags.append(int(repetir_s) | int(repetir_t) << 1 | int(espejo_s) << 2 | int(espejo_t) << 3 | int(suave) << 4)
        self._memo = None
        return i

    def tablas(self):
        if self._memo is None:
            datos = np.concatenate(self._bloques) if self._bloques else np.zeros(4, np.uint8)
            self._memo = (datos, np.array(self._off or [0], np.int64), np.array(self._w or [1], np.int64),
                          np.array(self._h or [1], np.int64), np.array(self._flags or [0], np.int64))
        return self._memo


def dibujar(color, zbuf, lote, texturas, niebla=None):
    """Pinta un lote (dict de arrays: xy, w_inv, uv, luz, tex, alfa, modo, tinte)."""
    if not len(lote['xy']):
        return
    datos, off, w, h, flags = texturas.tablas()
    n = np.zeros(7, np.float32) if niebla is None else np.asarray(niebla, np.float32)
    _dibujar(color, zbuf, lote['xy'], lote['w_inv'], lote['uv'], lote['luz'], lote['tex'], lote['alfa'],
             lote['modo'], lote['tinte'], n, datos, off, w, h, flags)
