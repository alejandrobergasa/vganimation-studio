"""Motor de vídeo: compone fotogramas a baja resolución al estilo DS con assets extraídos de la ROM.

Todo se calcula como función pura del tiempo (render(t)), así los fotogramas se pueden renderizar en
paralelo. Resolución base 640x360, ampliada x2 con vecino más cercano a 1280x720.
"""
import os
import struct
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from ww.rom import Rom, rutas               # noqa: E402
from ww.assets import load_model            # noqa: E402
from ww.anim import load_animations         # noqa: E402
from ww.nitro3d import TexBank              # noqa: E402
from ww.raster import Canvas, perspective, look_at  # noqa: E402
from ww.render3d import draw_model, build_mesh  # noqa: E402
from ww import gfx2d                        # noqa: E402

# Formato: apaisado 640x360 (x2 = 1280x720) o, con VIDEO_VERTICAL=1, 360x640 (x3 = 1080x1920) para móvil.
# Hay que fijarlo antes de importar este módulo (los guiones lo hacen con os.environ.setdefault).
if os.environ.get('VIDEO_VERTICAL') == '1':
    W, H, SCALE = 360, 640, 3
else:
    W, H, SCALE = 640, 360, 2
FPS = 30


# ------------------------------------------------------------------ 2D

def blit(dst, src, x, y, alpha=1.0, tint=None):
    """dst: HxWx3 float32 0..1. src: hxwx4 uint8 (RGBA)."""
    x, y = int(round(x)), int(round(y))
    h, w = src.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, dst.shape[1]), min(y + h, dst.shape[0])
    if x0 >= x1 or y0 >= y1:
        return
    s = src[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32) / 255.0
    a = s[..., 3:4] * alpha
    rgb = s[..., :3] if tint is None else np.broadcast_to(np.asarray(tint, np.float32), s[..., :3].shape)   # tint = color plano (las máscaras de texto son negras)
    dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - a) + rgb * a


def fill_rect(dst, x, y, w, h, color, alpha=1.0):
    x0, y0, x1, y1 = max(int(x), 0), max(int(y), 0), min(int(x + w), dst.shape[1]), min(int(y + h), dst.shape[0])
    if x0 < x1 and y0 < y1:
        c = np.asarray(color, np.float32)
        dst[y0:y1, x0:x1] = dst[y0:y1, x0:x1] * (1 - alpha) + c * alpha


class Font:
    """Fuente fontA del juego: glifos 16x16 de 1 bpp, orden Windows-1252, anchos proporcionales."""

    def __init__(self, rom):
        attr = rom.get('font/fontA_attr.bin')
        img = rom.get('font/fontA_img.bin')
        self.glyph = {}
        self.width = {}
        for i in range(len(attr) // 4):
            code, w = struct.unpack_from('<HH', attr, i * 4)
            g = np.zeros((16, 16), np.uint8)
            for y in range(16):
                row = int.from_bytes(img[i * 32 + y * 2:i * 32 + y * 2 + 2], 'big')
                for x in range(16):
                    g[y, x] = (row >> (15 - x)) & 1
            ch = bytes([code]).decode('cp1252', 'replace')
            self.glyph[ch] = g
            self.width[ch] = w

    def advance(self, ch, scale=1):
        return (self.width.get(ch, self.width.get('?', 6)) + 1) * scale

    def measure(self, text, scale=1):
        return sum(self.advance(c, scale) for c in text)

    def draw(self, dst, x, y, text, color=(0.25, 0.12, 0.05), shadow=None, alpha=1.0, scale=1, bold=False):
        """Texto con la fuente del juego. scale: ampliación entera (vecino más cercano); bold: engrosa 1 px."""
        cx = x
        for ch in text:
            g = self.glyph.get(ch)
            if g is not None:
                if scale > 1:
                    g = np.repeat(np.repeat(g, scale, 0), scale, 1)
                rgba = np.zeros(g.shape + (4,), np.uint8)
                rgba[..., 3] = g * 255
                if shadow is not None:
                    blit(dst, rgba, cx + scale, y + scale, alpha, tint=shadow)
                blit(dst, rgba, cx, y, alpha, tint=color)
                if bold:
                    blit(dst, rgba, cx + 1, y, alpha, tint=color)
            cx += self.advance(ch, scale)
        return cx


def make_bubble(rom, extra_cols=8, variant='a_mes0a_bg_nsc', extra_rows=0):
    """Nube de diálogo (tiles a_mes). Devuelve (rgba, (tx, ty) origen del texto, (nx, ny) origen del nombre)."""
    tiles = gfx2d.tiles(rom.get('a_mes/a_mes_bg_ncg.bin'), 4)
    pal = gfx2d.palette(rom.get('a_mes/a_mes_bg_ncl.bin'))
    cells = np.frombuffer(rom.get('a_mes/%s.bin' % variant), '<u2').reshape(32, 32).copy()
    # las celdas 17..152 son los tiles donde el juego escribe el texto: se vacían con el relleno blanco (288)
    for y in range(32):
        for x in range(32):
            t = int(cells[y, x]) & 0x3FF
            if 17 <= t <= 152:
                cells[y, x] = (int(cells[y, x]) & 0xFC00) | 288
    col = 16
    cells = np.concatenate([cells[:, :col + 1]] + [cells[:, col:col + 1]] * extra_cols + [cells[:, col + 1:]], 1)
    n = cells.shape[1]
    img = gfx2d.render_map(tiles, pal, cells.astype('<u2').tobytes(), 4, width=n, height=32)
    ys, xs = np.nonzero(img[..., 3])
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    out = img[y0:y1, x0:x1].copy()
    if extra_rows:      # alarga la nube estirando la fila más ancha (los laterales quedan rectos)
        a = out[..., 3] > 0
        mid = range(out.shape[0] // 2 - 8, out.shape[0] // 2 + 8)
        ext = [(a[y].nonzero()[0].max() - a[y].nonzero()[0].min()) for y in mid]
        y_s = list(mid)[int(np.argmax(ext))]
        out = np.concatenate([out[:y_s + 1]] + [out[y_s:y_s + 1]] * (extra_rows * 8) + [out[y_s + 1:]], 0)
    return out, (6 * 8 - x0, 17 * 8 - y0), (5 * 8 - x0, 14 * 8 - y0)


# ------------------------------------------------------------------ 3D

class Asset:
    """Modelo + bancos de texturas + animaciones."""

    def __init__(self, rom, model_path, tex_paths=(), anims=None):
        self.model, self.banks = load_model(rom, model_path, tex_paths)
        self.anims = anims or {}


def load_clips(rom, files):
    out = {}
    for f in files:
        out.update(load_animations(rom.get(f)))
    return out


def ry(theta):
    c, s = np.cos(theta), np.sin(theta)
    m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c
    return m


def world_matrix(pos, yaw=0.0, scale=1.0):
    m = ry(yaw)
    m[:3, :3] *= scale
    m[:3, 3] = pos
    return m


def yaw_facing(dx, dz):
    """Giro para que el frente del modelo (+Z local) apunte hacia (dx, dz)."""
    return float(np.arctan2(dx, dz))


def draw_textured_quad(canvas, texture, corners, world, view, proj, tint=(1, 1, 1)):
    """Decal 3D RGBA. Esquinas: abajo izq., abajo der., arriba der., arriba izq."""
    h, w = texture.shape[:2]
    points = np.asarray(corners, np.float64)[[0, 1, 2, 0, 2, 3]].reshape(2, 3, 3)
    uv = np.array([(0, h-1), (w-1, h-1), (w-1, 0), (0, h-1), (w-1, 0), (0, 0)], np.float64).reshape(2, 3, 2)
    ph = np.concatenate([points, np.ones((2, 3, 1))], -1)
    canvas.draw(ph @ (proj @ view @ world).T, uv, texture,
                np.broadcast_to(np.asarray(tint), (2, 3, 3)).copy(), 1.0, 0, (False, False, False, False))


def draw_surface_texture(canvas, texture, surfaces, world, view, proj, tint=(1, 1, 1)):
    """Proyecta una textura RGBA en triángulos 3D existentes (P, UV, normales).

    Un sesgo mínimo según la normal evita z-fighting con la superficie original.
    La textura sigue el volumen y la pose de la malla, sin usar un plano frontal.
    """
    vp = proj @ view @ world
    for points, uv, normals in surfaces:
        n = normals / np.maximum(np.linalg.norm(normals, axis=-1, keepdims=True), 1e-8)
        p = points + n * .008
        ph = np.concatenate([p, np.ones(p.shape[:2] + (1,))], -1)
        canvas.draw(ph @ vp.T, uv, texture,
                    np.broadcast_to(np.asarray(tint), p.shape).copy(), 1, 0, (False, False, False, False))


def screen_transition(img, t, cuts, half_duration=.20):
    """Transiciones deterministas: (tiempo, bars|zoom|iris|whip|fade)."""
    yy, xx = np.mgrid[:img.shape[0], :img.shape[1]]
    hh, ww = img.shape[:2]
    navy = np.array([.10,.18,.23],np.float32)
    bands = np.array([[.97,.65,.24],[1,.98,.87],[.33,.69,.43],[.35,.57,.87]],np.float32)
    for tc, kind in cuts:
        if abs(t-tc)>half_duration:
            continue
        u=(t-tc)/half_duration
        a=float(ease(1-abs(u)))
        if kind=='bars':
            pos=(xx+.5*yy)/(ww+.5*hh)
            c=float(ease(u+1 if u<0 else u))
            mask=pos<c if u<0 else pos>=c
            img=np.where(mask[...,None],bands[(pos*6).astype(int)%4],img)
            img[np.abs(pos-c)<.012]=navy
        elif kind=='iris':
            d=np.hypot(xx-ww/2,yy-hh*.43)
            radius=np.hypot(hh,ww)*(1-a)
            img[d>radius]=navy
            img[(d>radius-4)&(d<=radius)]=bands[0]
        elif kind=='zoom':
            z=1+.35*a
            xs=np.clip(((np.arange(ww)-ww/2)/z+ww/2).astype(int),0,ww-1)
            ys=np.clip(((np.arange(hh)-hh*.43)/z+hh*.43).astype(int),0,hh-1)
            img=img[ys][:,xs]*(1-.72*a)+.72*a
        elif kind=='whip':
            dx=int(ww*a)*(-1 if u<0 else 1)
            pad=np.pad(img,((0,0),(ww,ww),(0,0)),mode='edge')
            img=sum(pad[:,ww-int(dx*k):2*ww-int(dx*k)] for k in (.65,.8,1))/3
        elif kind=='fade':
            img=img*(1-a)+navy*a
    return img


def chromatic_shift(img, amount):
    """Separación RGB breve con bordes replicados (impactos y glitches)."""
    amount=int(amount)
    if amount<=0:
        return img
    out=img.copy()
    pad=np.pad(img,((0,0),(amount,amount),(0,0)),mode='edge')
    width=img.shape[1]
    out[...,0]=pad[:,:width,0]
    out[...,2]=pad[:,2*amount:2*amount+width,2]
    return out


def pose_at(asset, clip, t, loop=True, speed=1.0, fps=30.0):
    """Override de nodos para el clip en el tiempo t (segundos). Las animaciones corren a 30 fotogramas/s."""
    if clip is None:
        return None
    an = asset.anims[clip]
    f = t * fps * speed
    if loop:
        f = f % max(an.num_frames, 1)
    else:
        f = min(f, an.num_frames - 1)
    return an.frame(f, asset.model)


def pose_layered(asset, base_clip, base_t, over_clip, over_t, loop_base=True):
    """Pose de base más los nodos *animados* (curvas con muestras) de un clip superpuesto (p. ej. talk1 = boca)."""
    pose = dict(pose_at(asset, base_clip, base_t, loop_base))
    over = asset.anims[over_clip]
    f = (over_t * 30.0) % max(over.num_frames, 1)
    fr = over.frame(f, asset.model)
    for i, c in enumerate(over.objs):
        sampled = any(k.kind == 'samples' for k in c['t']) or c['r'].kind == 'samples' or any(k.kind == 'samples' for k in c['s'])
        if sampled and i in fr:
            pose[i] = fr[i]
    return pose


def lerp(a, b, u):
    return a + (b - a) * np.clip(u, 0, 1)


def ease(u):
    u = np.clip(u, 0, 1)
    return u * u * (3 - 2 * u)


# ------------------------------------------------------------------ vídeo

def write_video(frames_iter, out_path, audio=None, fps=FPS, gif=None):
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W * SCALE, H * SCALE),
           '-r', str(fps), '-i', '-']
    if audio:
        cmd += ['-i', audio]
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '17', '-preset', 'medium']
    if audio:
        cmd += ['-c:a', 'aac', '-b:a', '192k', '-shortest']
    cmd += ['-movflags', '+faststart', out_path]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for fr in frames_iter:
        p.stdin.write(fr.tobytes())
    p.stdin.close()
    p.wait()


def upscale(img_u8):
    return np.repeat(np.repeat(img_u8, SCALE, 0), SCALE, 1)
