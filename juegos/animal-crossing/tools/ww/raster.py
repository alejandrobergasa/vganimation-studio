"""Rasterizador por software al estilo DS: texturas con vecino más cercano, sin suavizado,
sin antialiasing, interpolación con perspectiva correcta."""
import numpy as np


def perspective(fovy_deg, aspect, near, far):
    f = 1.0 / np.tan(np.radians(fovy_deg) / 2)
    m = np.zeros((4, 4))
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = 2 * far * near / (near - far)
    m[3, 2] = -1
    return m


def ortho(w, h, near, far):
    m = np.eye(4)
    m[0, 0] = 2.0 / w
    m[1, 1] = 2.0 / h
    m[2, 2] = -2.0 / (far - near)
    m[2, 3] = -(far + near) / (far - near)
    return m


def look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = map(lambda v: np.asarray(v, np.float64), (eye, target, up))
    f = target - eye
    f /= np.linalg.norm(f)
    s = np.cross(f, up)
    s /= np.linalg.norm(s)
    u = np.cross(s, f)
    m = np.eye(4)
    m[0, :3], m[1, :3], m[2, :3] = s, u, -f
    m[:3, 3] = -m[:3, :3] @ eye
    return m


class Canvas:
    def __init__(self, w, h, bg=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.color = np.zeros((h, w, 4), np.float32)
        self.color[:] = np.asarray(bg, np.float32) / 255.0
        self.depth = np.full((h, w), np.inf, np.float32)

    def to_image(self):
        return (np.clip(self.color, 0, 1) * 255 + 0.5).astype(np.uint8)

    def draw(self, clip, uv, tex, shade, alpha=1.0, cull=0, wrap=(True, True, False, False),
             size=None):
        """clip: (T,3,4) coordenadas de recorte. uv: (T,3,2) en texeles. shade: (T,3,3) color por vértice.
        tex: array (h,w,4) uint8 o None. cull: 0 sin descarte (ambas caras), 1 oculta frontales, 2 oculta traseras
        (convención NDS: 1=front, 2=back, 3=none ... aquí 'cull' ya viene resuelto por el llamador)."""
        W, H = self.w, self.h
        w = clip[..., 3]
        okw = (w > 1e-4).all(axis=1)
        clip, uv, shade, w = clip[okw], uv[okw], shade[okw], w[okw]
        if len(clip) == 0:
            return
        ndc = clip[..., :3] / w[..., None]
        sxp = (ndc[..., 0] * 0.5 + 0.5) * W
        syp = (1 - (ndc[..., 1] * 0.5 + 0.5)) * H
        zz = ndc[..., 2]
        invw = 1.0 / w
        th, tw = (tex.shape[:2] if tex is not None else (1, 1))
        for t in range(len(clip)):
            x0, x1, x2 = sxp[t]
            y0, y1, y2 = syp[t]
            area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
            if abs(area) < 1e-9:
                continue
            if cull == 2 and area < 0:      # trasera
                continue
            if cull == 1 and area > 0:      # frontal
                continue
            minx = max(int(np.floor(min(x0, x1, x2))), 0)
            maxx = min(int(np.ceil(max(x0, x1, x2))), W)
            miny = max(int(np.floor(min(y0, y1, y2))), 0)
            maxy = min(int(np.ceil(max(y0, y1, y2))), H)
            if minx >= maxx or miny >= maxy:
                continue
            gx, gy = np.meshgrid(np.arange(minx, maxx) + 0.5, np.arange(miny, maxy) + 0.5)
            b0 = ((x1 - gx) * (y2 - gy) - (x2 - gx) * (y1 - gy)) / area
            b1 = ((x2 - gx) * (y0 - gy) - (x0 - gx) * (y2 - gy)) / area
            b2 = 1 - b0 - b1
            inside = (b0 >= 0) & (b1 >= 0) & (b2 >= 0)
            if not inside.any():
                continue
            z = b0 * zz[t, 0] + b1 * zz[t, 1] + b2 * zz[t, 2]
            dsub = self.depth[miny:maxy, minx:maxx]
            ok = inside & (z <= dsub + 1e-6)
            if not ok.any():
                continue
            iw0, iw1, iw2 = invw[t]
            pw = b0 * iw0 + b1 * iw1 + b2 * iw2
            c0, c1, c2 = b0 * iw0 / pw, b1 * iw1 / pw, b2 * iw2 / pw
            if tex is not None:
                u = c0 * uv[t, 0, 0] + c1 * uv[t, 1, 0] + c2 * uv[t, 2, 0]
                v = c0 * uv[t, 0, 1] + c1 * uv[t, 1, 1] + c2 * uv[t, 2, 1]
                ui = np.floor(u).astype(np.int64)
                vi = np.floor(v).astype(np.int64)
                ui = _wrap(ui, tw, wrap[0], wrap[2])
                vi = _wrap(vi, th, wrap[1], wrap[3])
                texel = tex[vi, ui].astype(np.float32) / 255.0
            else:
                texel = np.ones(gx.shape + (4,), np.float32)
            sh = (c0[..., None] * shade[t, 0] + c1[..., None] * shade[t, 1] + c2[..., None] * shade[t, 2])
            a = texel[..., 3] * alpha
            ok &= a > 0.5 if alpha >= 1 else a > 0.02
            if not ok.any():
                continue
            rgb = texel[..., :3] * sh
            reg = self.color[miny:maxy, minx:maxx]
            if alpha < 1:
                aa = a[..., None]
                new = rgb * aa + reg[..., :3] * (1 - aa)
                reg[..., :3] = np.where(ok[..., None], new, reg[..., :3])
                reg[..., 3] = np.where(ok, np.maximum(reg[..., 3], a), reg[..., 3])
            else:
                reg[..., :3] = np.where(ok[..., None], rgb, reg[..., :3])
                reg[..., 3] = np.where(ok, 1.0, reg[..., 3])
                dsub[ok] = z[ok]


def _wrap(i, n, rep, flip):
    if not rep:
        return np.clip(i, 0, n - 1)
    if flip:
        r = i % n
        return np.where((i // n) % 2 == 1, n - 1 - r, r)
    return i % n
