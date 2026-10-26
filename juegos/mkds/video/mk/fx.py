"""Efectos visuales 3D: sprites procedurales y sistema de partículas evaluable en cualquier instante (sin estado).

Las partículas son quads orientados a cámara (o estelas alargadas) que entran al mismo rasterizador que el resto de
la escena, por lo que quedan ocultas tras la geometría y reciben la niebla. Todo es determinista: dada la semilla,
el fotograma t siempre sale igual, así que se puede renderizar en paralelo y en cualquier orden."""
import math
import numpy as np
from scipy.ndimage import gaussian_filter

from . import escena as E
from . import raster as R


# ------------------------------------------------------------------ sprites procedurales

def _grid(n):
    y, x = np.mgrid[0:n, 0:n]
    return (x + .5) / n * 2 - 1, (y + .5) / n * 2 - 1


def sprite_glow(n=64, dureza=2.2):
    x, y = _grid(n); r = np.hypot(x, y)
    a = np.clip(1 - r, 0, 1) ** dureza
    return _rgba(a)


def sprite_disco(n=64):
    x, y = _grid(n); r = np.hypot(x, y)
    return _rgba(np.clip((1 - r) * 6, 0, 1))


def sprite_estrella(n=64, puntas=4, fino=.22):
    x, y = _grid(n); r = np.hypot(x, y) + 1e-6; ang = np.arctan2(y, x)
    f = fino + (1 - fino) * np.abs(np.cos(ang * puntas / 2)) ** 6
    a = np.clip(1 - r / f, 0, 1) ** 1.4
    a = np.maximum(a, np.clip(1 - r * 2.2, 0, 1) ** 2)
    return _rgba(a)


def sprite_humo(n=64, semilla=1):
    rng = np.random.default_rng(semilla)
    x, y = _grid(n); r = np.hypot(x, y)
    ruido = gaussian_filter(rng.random((n, n)), n / 14, mode='wrap')
    ruido = (ruido - ruido.min()) / np.ptp(ruido)
    a = np.clip(1 - r, 0, 1) ** 1.2 * (0.45 + 0.75 * ruido)
    return _rgba(np.clip(a, 0, 1))


def sprite_anillo(n=96, grosor=.12):
    x, y = _grid(n); r = np.hypot(x, y)
    a = np.clip(1 - np.abs(r - (1 - grosor * 1.4)) / grosor, 0, 1) ** 1.5
    return _rgba(a)


def sprite_estela(n=64):
    """Trazo alargado en x: núcleo brillante y extremos que se desvanecen."""
    x, y = _grid(n)
    a = np.clip(1 - np.abs(y) * 1.0, 0, 1) ** 2.2 * np.clip(1 - np.abs(x) ** 3, 0, 1)
    return _rgba(a)


def sprite_confeti(n=16):
    a = np.zeros((n, n)); a[3:13, 4:12] = 1
    return _rgba(a)


def _rgba(a):
    a = np.asarray(a, np.float32)
    out = np.zeros(a.shape + (4,), np.uint8)
    out[..., :3] = 255; out[..., 3] = np.clip(a * 255, 0, 255)
    return out


class Sprites:
    """Materiales de sprite listos (aditivos y con alfa) registrados en un Motor."""
    def __init__(self, motor):
        m = motor
        self.glow = m.material(sprite_glow(), R.ADITIVO)
        self.glow_alfa = m.material(sprite_glow(), R.ALFA)
        self.disco = m.material(sprite_disco(), R.ALFA)
        self.estrella = m.material(sprite_estrella(), R.ADITIVO)
        self.estrella8 = m.material(sprite_estrella(64, 8, .3), R.ADITIVO)
        self.humo = m.material(sprite_humo(64, 3), R.ALFA)
        self.humo2 = m.material(sprite_humo(64, 11), R.ALFA)
        self.anillo = m.material(sprite_anillo(), R.ADITIVO)
        self.anillo_alfa = m.material(sprite_anillo(), R.ALFA)
        self.estela = m.material(sprite_estela(), R.ADITIVO)
        self.confeti = m.material(sprite_confeti(), R.ALFA, (0, 0, 0, 0, 0, 0))


# ------------------------------------------------------------------ partículas

class Particulas:
    """Conjunto de partículas con trayectoria cerrada: pos = p0 + v·a + ½·g·a² (a = edad), con arrastre opcional.
    Los campos son arrays; `agregar` los amplía. `malla(t, camara)` devuelve la Malla de las vivas en t."""
    CAMPOS = ('t0', 'vida', 'p0', 'v', 'g', 'tam0', 'tam1', 'c0', 'c1', 'a0', 'a1', 'mat', 'giro', 'estela', 'arrastre')

    def __init__(self, motor, semilla=1):
        self.motor = motor
        self.rng = np.random.default_rng(semilla)
        self.d = {k: [] for k in self.CAMPOS}

    def agregar(self, t0, vida, p0, v, tam0, tam1, c0, c1, mat, g=(0, -9.0, 0), a0=1.0, a1=0.0, giro=None, estela=0.0, arrastre=0.0):
        n = len(t0)
        def f(x, k):
            x = np.asarray(x, np.float64)
            return np.broadcast_to(x, (n,) + k).copy() if x.ndim <= len(k) else x
        self.d['t0'].append(f(t0, ())); self.d['vida'].append(f(vida, ()))
        self.d['p0'].append(f(p0, (3,))); self.d['v'].append(f(v, (3,))); self.d['g'].append(f(g, (3,)))
        self.d['tam0'].append(f(tam0, ())); self.d['tam1'].append(f(tam1, ()))
        self.d['c0'].append(f(c0, (3,))); self.d['c1'].append(f(c1, (3,)))
        self.d['a0'].append(f(a0, ())); self.d['a1'].append(f(a1, ()))
        self.d['mat'].append(f(mat, ()).astype(np.int32))
        self.d['giro'].append(f(self.rng.uniform(0, 6.28, n) if giro is None else giro, ()))
        self.d['estela'].append(f(estela, ())); self.d['arrastre'].append(f(arrastre, ()))
        self._cat = None

    def _todo(self):
        if self._cat is None:
            self._cat = {k: np.concatenate(v) for k, v in self.d.items()} if self.d['t0'] else None
        return self._cat

    # emisores de comodidad ------------------------------------------------
    def rafaga(self, t, pos, n, vel, dispersion, vida, tam, color, mat, **kw):
        """n partículas a la vez desde pos, con velocidad media `vel` (3) y dispersión esférica."""
        d = self.rng.normal(size=(n, 3)); d /= np.linalg.norm(d, axis=1, keepdims=True)
        v = np.asarray(vel) + d * dispersion * self.rng.uniform(.4, 1.0, (n, 1))
        vd = np.asarray(vida) * self.rng.uniform(.7, 1.15, n)
        tm = np.asarray(tam)
        c = np.asarray(color, np.float64)
        self.agregar(np.full(n, t), vd, np.broadcast_to(np.asarray(pos, np.float64), (n, 3)), v, tm * self.rng.uniform(.7, 1.2, n),
                     kw.pop('tam1', tm * 0.2) * np.ones(n), c, kw.pop('color_fin', c * 0.3), mat, **kw)

    def continuo(self, t_ini, t_fin, tasa, pos_fn, vel_fn, vida, tam, color, mat, dispersion=1.0, **kw):
        """Emite `tasa` partículas/s entre t_ini y t_fin; pos_fn(t) -> (3,), vel_fn(t) -> (3,)."""
        N = int((t_fin - t_ini) * tasa)
        ts = t_ini + (np.arange(N) + self.rng.random(N)) / tasa
        if len(ts) == 0: return
        P = np.array([pos_fn(t) for t in ts]); V = np.array([vel_fn(t) for t in ts])
        d = self.rng.normal(size=(len(ts), 3)) * dispersion
        tm = np.asarray(tam); c = np.asarray(color, np.float64)
        self.agregar(ts, np.asarray(vida) * self.rng.uniform(.7, 1.2, len(ts)), P, V + d, tm * self.rng.uniform(.7, 1.25, len(ts)),
                     kw.pop('tam1', tm * 0.3) * np.ones(len(ts)), c, kw.pop('color_fin', c * 0.3), mat, **kw)

    # evaluación ---------------------------------------------------------
    def malla(self, t, cam):
        c = self._todo()
        if c is None: return E.Malla.une([])
        edad = t - c['t0']
        vivo = (edad >= 0) & (edad < c['vida'])
        if not vivo.any(): return E.Malla.une([])
        i = np.nonzero(vivo)[0]; a = edad[i][:, None]; u = (edad[i] / c['vida'][i])[:, None]
        k = c['arrastre'][i][:, None]
        # con arrastre lineal: x = v·(1-e^{-ka})/k ; sin él, v·a
        va = np.where(k > 1e-6, c['v'][i] * (1 - np.exp(-k * a)) / np.maximum(k, 1e-6), c['v'][i] * a)
        pos = c['p0'][i] + va + 0.5 * c['g'][i] * a * a
        tam = c['tam0'][i][:, None] * (1 - u) + c['tam1'][i][:, None] * u
        col = c['c0'][i] * (1 - u) + c['c1'][i] * u
        alfa = (c['a0'][i][:, None] * (1 - u) + c['a1'][i][:, None] * u)[:, 0]
        # base de cámara
        b = cam.base()
        der, arr, fw = b[0], b[1], b[2]
        giro = c['giro'][i] + (edad[i] * 1.3)
        cs, sn = np.cos(giro)[:, None], np.sin(giro)[:, None]
        ex = der[None] * cs + arr[None] * sn
        ey = -der[None] * sn + arr[None] * cs
        # estelas: alargadas a lo largo de la velocidad proyectada
        est = c['estela'][i] > 0
        if est.any():
            vel = c['v'][i] + c['g'][i] * a
            vel_n = np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6
            dirv = vel / vel_n
            lado = np.cross(dirv, fw[None]); lado /= (np.linalg.norm(lado, axis=1, keepdims=True) + 1e-9)
            ex = np.where(est[:, None], dirv, ex); ey = np.where(est[:, None], lado, ey)
            largo = np.where(est, c['estela'][i] * np.minimum(vel_n[:, 0], 40) / 10, 1.0)[:, None]
        else:
            largo = np.ones((len(i), 1))
        hx = ex * tam * largo; hy = ey * tam
        p = pos
        q = np.stack([p - hx - hy, p + hx - hy, p + hx + hy, p - hx + hy], 1)             # (n,4,3)
        n = len(i)
        xyz = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
        uvs = np.array([[0, 1], [1, 1], [1, 0]], np.float32), np.array([[0, 1], [1, 0], [0, 0]], np.float32)
        uv = np.concatenate([np.broadcast_to(uvs[0], (n, 3, 2)), np.broadcast_to(uvs[1], (n, 3, 2))])
        cc = np.concatenate([col, col])
        colr = np.repeat(cc[:, None, :], 3, 1)
        al = np.repeat(np.concatenate([alfa, alfa])[:, None], 3, 1)
        mat = np.concatenate([c['mat'][i], c['mat'][i]])
        tam_tex = np.array([self.motor._mats[m][1][0] for m in range(len(self.motor._mats))], np.float32)
        uv = uv * tam_tex[mat][:, None, :]          # los uv van en texels
        return E.Malla(xyz, uv, np.zeros_like(xyz), colr, mat, al)
