"""Rasterizador por software (numba): perspectiva correcta, z-buffer, texturas DS con mipmaps,
niebla, recorte contra el plano cercano y modos de mezcla (opaco/recorte, alfa, aditivo).
Todo en float32 [0,1] para que el postproceso (bloom, etc.) trabaje sin pérdidas."""
import math
import numpy as np
from numba import njit

MAXTEX = 256
NIVELES = 6            # mipmaps: 256, 128, ..., 8

# modos de mezcla por material
OPACO, RECORTE, ALFA, ADITIVO = 0, 1, 2, 3


def construir_mips(arr):
    """arr (h,w,4) uint8 -> ((NIVELES,256,256,4) float32 [0,1], tamaños por nivel (NIVELES,2))."""
    a = arr.astype(np.float32) / 255.0
    out = np.zeros((NIVELES, MAXTEX, MAXTEX, 4), np.float32)
    tam = []
    for n in range(NIVELES):
        out[n, :a.shape[0], :a.shape[1]] = a
        tam.append((a.shape[1], a.shape[0]))
        hh, ww = max(1, a.shape[0] // 2), max(1, a.shape[1] // 2)
        if a.shape[0] <= 1 and a.shape[1] <= 1:
            continue
        if a.shape[0] == 1 or a.shape[1] == 1:
            b = a[:hh * (2 if a.shape[0] > 1 else 1)]
        pm = a.copy(); pm[:, :, :3] *= pm[:, :, 3:4]
        ys = 2 if a.shape[0] > 1 else 1
        xs = 2 if a.shape[1] > 1 else 1
        pm = pm[:hh * ys, :ww * xs].reshape(hh, ys, ww, xs, 4).mean((1, 3))
        al = pm[:, :, 3:4]
        pm[:, :, :3] = np.where(al > 1e-4, pm[:, :, :3] / np.maximum(al, 1e-4), 0)
        a = pm
    return out, np.array(tam, np.int32)


@njit(cache=True)
def _texel(tex, lvl, u, v, tw, th, rs, rt, fs, ft):
    if rs:
        per = u // tw
        u = u - per * tw
        if fs and per % 2 != 0: u = tw - 1 - u
    else:
        u = min(tw - 1, max(0, u))
    if rt:
        per = v // th
        v = v - per * th
        if ft and per % 2 != 0: v = th - 1 - v
    else:
        v = min(th - 1, max(0, v))
    return tex[lvl, v, u]


@njit(cache=True)
def proyectar(pc, uv, col, mat, foco, cx, cy, near):
    """Triángulos en espacio cámara (n,3,3) -> pantalla; recorta contra near.
    Devuelve (scr[x,y,1/z], uv, col rgba, mat, z medio)."""
    n = len(pc)
    sc = np.zeros((n * 2, 3, 3), np.float32)
    ou = np.zeros((n * 2, 3, 2), np.float32)
    oc = np.zeros((n * 2, 3, 4), np.float32)
    om = np.zeros(n * 2, np.int32)
    oz = np.zeros(n * 2, np.float32)
    used = 0
    for k in range(n):
        src = np.zeros((3, 9), np.float32)
        src[:, :3] = pc[k]; src[:, 3:5] = uv[k]; src[:, 5:9] = col[k]
        poly = np.zeros((5, 9), np.float32)
        m = 0
        for j in range(3):
            cur = src[j]; prev = src[(j + 2) % 3]
            ci = cur[2] >= near; pi = prev[2] >= near
            if ci != pi:
                q = (near - prev[2]) / (cur[2] - prev[2])
                poly[m] = prev + (cur - prev) * q; m += 1
            if ci:
                poly[m] = cur; m += 1
        if m < 3: continue
        for j in range(1, m - 1):
            zs = 0.0
            for c in range(3):
                idx = 0 if c == 0 else (j if c == 1 else j + 1)
                iz = 1.0 / poly[idx, 2]
                sc[used, c, 0] = cx + poly[idx, 0] * foco * iz
                sc[used, c, 1] = cy - poly[idx, 1] * foco * iz
                sc[used, c, 2] = iz
                ou[used, c, 0] = poly[idx, 3]; ou[used, c, 1] = poly[idx, 4]
                for t in range(4): oc[used, c, t] = poly[idx, 5 + t]
                zs += poly[idx, 2]
            om[used] = mat[k]; oz[used] = zs / 3.0
            used += 1
    return sc[:used], ou[:used], oc[:used], om[:used], oz[:used]


@njit(cache=True)
def _uv_en(w0, w1, w2, a, b, c, uv, k):
    iz = w0 * a[2] + w1 * b[2] + w2 * c[2]
    p0 = w0 * a[2] / iz; p1 = w1 * b[2] / iz; p2 = w2 * c[2] / iz
    u = p0 * uv[k, 0, 0] + p1 * uv[k, 1, 0] + p2 * uv[k, 2, 0]
    v = p0 * uv[k, 0, 1] + p1 * uv[k, 1, 1] + p2 * uv[k, 2, 1]
    return u, v


@njit(cache=True)
def dibujar(img, depth, sc, uv, col, mat, tex, tsz, flags, modo, filtro, niebla, fogc, fog0, fog1, pasada):
    """Rasteriza en img (H,W,3) float32 y depth (H,W) = 1/z.
    flags[mat] = (rep_s, rep_t, flip_s, flip_t, cull_front, cull_back)
    pasada: 0 = opacos y recortes (escriben z), 1 = alfa/aditivo (prueban z, no escriben)."""
    H, W = depth.shape
    r = np.zeros(4, np.float32)
    for k in range(len(sc)):
        mi = mat[k]
        md = modo[mi]
        if pasada == 0 and md >= 2: continue
        if pasada == 1 and md < 2: continue
        a = sc[k, 0]; b = sc[k, 1]; c = sc[k, 2]
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-4: continue
        front = den < 0
        if front and flags[mi, 4]: continue
        if (not front) and flags[mi, 5]: continue
        minx = max(0, int(math.floor(min(a[0], min(b[0], c[0])))))
        maxx = min(W - 1, int(math.ceil(max(a[0], max(b[0], c[0])))))
        miny = max(0, int(math.floor(min(a[1], min(b[1], c[1])))))
        maxy = min(H - 1, int(math.ceil(max(a[1], max(b[1], c[1])))))
        if minx > maxx or miny > maxy: continue
        tm = tex[mi]
        tw = tsz[mi, 0, 0]; th = tsz[mi, 0, 1]
        rs = flags[mi, 0]; rt = flags[mi, 1]; fs = flags[mi, 2]; ft = flags[mi, 3]
        dw0x = (b[1] - c[1]) / den; dw1x = (c[1] - a[1]) / den
        dw0y = (c[0] - b[0]) / den; dw1y = (a[0] - c[0]) / den
        for y in range(miny, maxy + 1):
            for x in range(minx, maxx + 1):
                px = x + 0.5; py = y + 0.5
                w0 = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / den
                w1 = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / den
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6: continue
                iz = w0 * a[2] + w1 * b[2] + w2 * c[2]
                if iz <= depth[y, x]: continue
                p0 = w0 * a[2] / iz; p1 = w1 * b[2] / iz; p2 = w2 * c[2] / iz
                u = p0 * uv[k, 0, 0] + p1 * uv[k, 1, 0] + p2 * uv[k, 2, 0]
                v = p0 * uv[k, 0, 1] + p1 * uv[k, 1, 1] + p2 * uv[k, 2, 1]
                if filtro == 0:
                    t = _texel(tm, 0, int(math.floor(u)), int(math.floor(v)), tw, th, rs, rt, fs, ft)
                    for ch in range(4): r[ch] = t[ch]
                else:
                    lvl = 0.0
                    if tw > 8 or th > 8:
                        w0x = w0 + dw0x; w1x = w1 + dw1x
                        w0y = w0 + dw0y; w1y = w1 + dw1y
                        izx = w0x * a[2] + w1x * b[2] + (1 - w0x - w1x) * c[2]
                        izy = w0y * a[2] + w1y * b[2] + (1 - w0y - w1y) * c[2]
                        if izx > 1e-9 and izy > 1e-9:
                            ux, vx = _uv_en(w0x, w1x, 1 - w0x - w1x, a, b, c, uv, k)
                            uy, vy = _uv_en(w0y, w1y, 1 - w0y - w1y, a, b, c, uv, k)
                            rho = max(max(abs(ux - u), abs(vx - v)), max(abs(uy - u), abs(vy - v)))
                            if rho > 1.0: lvl = min(NIVELES - 1.001, math.log2(rho))
                    l0 = int(lvl); fl = lvl - l0
                    for ch in range(4): r[ch] = 0.0
                    for li in range(2):
                        lv = l0 + li
                        wl = (1.0 - fl) if li == 0 else fl
                        if wl < 1e-3: continue
                        tw0 = tsz[mi, lv, 0]; th0 = tsz[mi, lv, 1]
                        sf = 1.0 / (1 << lv)
                        uu = u * sf - 0.5; vv = v * sf - 0.5
                        iu = int(math.floor(uu)); iv = int(math.floor(vv))
                        fu = uu - iu; fv = vv - iv
                        t00 = _texel(tm, lv, iu, iv, tw0, th0, rs, rt, fs, ft)
                        t10 = _texel(tm, lv, iu + 1, iv, tw0, th0, rs, rt, fs, ft)
                        t01 = _texel(tm, lv, iu, iv + 1, tw0, th0, rs, rt, fs, ft)
                        t11 = _texel(tm, lv, iu + 1, iv + 1, tw0, th0, rs, rt, fs, ft)
                        for ch in range(4):
                            r[ch] += wl * ((t00[ch] * (1 - fu) + t10[ch] * fu) * (1 - fv)
                                           + (t01[ch] * (1 - fu) + t11[ch] * fu) * fv)
                al = r[3] * (p0 * col[k, 0, 3] + p1 * col[k, 1, 3] + p2 * col[k, 2, 3])
                if md == 1 and al < 0.5: continue
                if md >= 2 and al < 0.004: continue
                cr = r[0] * (p0 * col[k, 0, 0] + p1 * col[k, 1, 0] + p2 * col[k, 2, 0])
                cg = r[1] * (p0 * col[k, 0, 1] + p1 * col[k, 1, 1] + p2 * col[k, 2, 1])
                cb = r[2] * (p0 * col[k, 0, 2] + p1 * col[k, 1, 2] + p2 * col[k, 2, 2])
                if niebla > 0:
                    f = (1.0 / iz - fog0) / (fog1 - fog0)
                    f = min(1.0, max(0.0, f)) * niebla
                    if md == 3:
                        cr *= (1 - f); cg *= (1 - f); cb *= (1 - f)
                    else:
                        cr = cr * (1 - f) + fogc[0] * f
                        cg = cg * (1 - f) + fogc[1] * f
                        cb = cb * (1 - f) + fogc[2] * f
                if md == 3:
                    img[y, x, 0] += cr * al; img[y, x, 1] += cg * al; img[y, x, 2] += cb * al
                elif md == 2:
                    img[y, x, 0] = img[y, x, 0] * (1 - al) + cr * al
                    img[y, x, 1] = img[y, x, 1] * (1 - al) + cg * al
                    img[y, x, 2] = img[y, x, 2] * (1 - al) + cb * al
                else:
                    img[y, x, 0] = cr; img[y, x, 1] = cg; img[y, x, 2] = cb
                    depth[y, x] = iz
