"""Circuitos: geometría + cielo + suelo consultable + línea de carrera suave para conducir karts."""
import math
import numpy as np
from numba import njit

import modelos as M
import nkm as NK
from . import escena as E


@njit(cache=True)
def _alturas(tri, celdas, ini, cuenta, x, z, hint, tol_arriba, minx, minz, cel, nx, nz):
    """Altura del suelo en (x,z): la más alta por debajo de hint+tol_arriba. NaN si no hay."""
    ix = int((x - minx) / cel); iz = int((z - minz) / cel)
    if ix < 0 or iz < 0 or ix >= nx or iz >= nz: return np.nan
    c = iz * nx + ix
    mejor = -1e30; hallado = False
    for q in range(ini[c], ini[c] + cuenta[c]):
        k = celdas[q]
        a = tri[k, 0]; b = tri[k, 1]; cc = tri[k, 2]
        den = (b[2] - cc[2]) * (a[0] - cc[0]) + (cc[0] - b[0]) * (a[2] - cc[2])
        if abs(den) < 1e-9: continue
        w0 = ((b[2] - cc[2]) * (x - cc[0]) + (cc[0] - b[0]) * (z - cc[2])) / den
        w1 = ((cc[2] - a[2]) * (x - cc[0]) + (a[0] - cc[0]) * (z - cc[2])) / den
        w2 = 1.0 - w0 - w1
        if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6: continue
        y = w0 * a[1] + w1 * b[1] + w2 * cc[1]
        if y <= hint + tol_arriba and y > mejor:
            mejor = y; hallado = True
    return mejor if hallado else np.nan


class Suelo:
    """Altura del terreno consultable (cuadrícula de triángulos con normal hacia arriba)."""
    def __init__(self, tris, cel=8.0, ny_min=0.3):
        t = np.asarray(tris, np.float64)
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        ln = np.linalg.norm(n, axis=1)
        ny = np.where(ln > 1e-12, np.abs(n[:, 1]) / np.maximum(ln, 1e-12), 0)
        t = t[ny > ny_min]
        self.tri = np.ascontiguousarray(t)
        self.minx, self.minz = t[:, :, 0].min() - 1, t[:, :, 2].min() - 1
        self.cel = cel
        self.nx = int((t[:, :, 0].max() - self.minx) / cel) + 2
        self.nz = int((t[:, :, 2].max() - self.minz) / cel) + 2
        listas = [[] for _ in range(self.nx * self.nz)]
        for k, tr in enumerate(t):
            x0 = int((tr[:, 0].min() - self.minx) / cel); x1 = int((tr[:, 0].max() - self.minx) / cel)
            z0 = int((tr[:, 2].min() - self.minz) / cel); z1 = int((tr[:, 2].max() - self.minz) / cel)
            for iz in range(z0, z1 + 1):
                for ix in range(x0, x1 + 1):
                    listas[iz * self.nx + ix].append(k)
        self.cuenta = np.array([len(l) for l in listas], np.int32)
        self.ini = np.concatenate([[0], np.cumsum(self.cuenta)[:-1]]).astype(np.int32)
        self.celdas = np.array([k for l in listas for k in l], np.int32)

    def altura(self, x, z, hint=1e4, tol=2.5):
        return _alturas(self.tri, self.celdas, self.ini, self.cuenta, float(x), float(z), float(hint), float(tol),
                        self.minx, self.minz, self.cel, self.nx, self.nz)


def catmull(p, n_por_tramo=24, cerrada=True):
    """Spline Catmull-Rom centrípeta por los puntos p (n,3)."""
    p = np.asarray(p, np.float64); n = len(p)
    out = []
    rango = range(n) if cerrada else range(n - 1)
    for i in rango:
        p0, p1, p2, p3 = p[(i - 1) % n], p[i], p[(i + 1) % n], p[(i + 2) % n]
        t0 = 0.0
        t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-6) ** 0.5
        t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-6) ** 0.5
        t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-6) ** 0.5
        t = np.linspace(t1, t2, n_por_tramo, endpoint=False)[:, None]
        a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
        a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
        a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
        b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
        b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
        out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
    return np.concatenate(out)


class Pista:
    """Línea de carrera continua parametrizada por distancia. muestra(s, lateral) -> dict con pos, yaw, pitch, curvatura."""
    def __init__(self, puntos, suelo=None, paso=0.5, cerrada=True, suavizado=9):
        c = catmull(puntos, 32, cerrada)
        if cerrada: c = np.concatenate([c, c[:1]])
        seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
        s = np.concatenate([[0], np.cumsum(seg)])
        self.largo = s[-1]; self.cerrada = cerrada
        self.s = np.arange(0, self.largo, paso)
        xs = np.stack([np.interp(self.s, s, c[:, k]) for k in range(3)], 1)
        if suelo is not None:
            for i in range(len(xs)):
                h = suelo.altura(xs[i, 0], xs[i, 2], xs[i, 1])
                if not np.isnan(h): xs[i, 1] = h
        # alisar la altura (el suelo tiene escalones de triángulo a triángulo)
        k = suavizado
        if k > 1:
            pad = np.concatenate([xs[-k:, 1], xs[:, 1], xs[:k, 1]]) if cerrada else np.pad(xs[:, 1], k, mode='edge')
            ker = np.ones(2 * k + 1) / (2 * k + 1)
            xs[:, 1] = np.convolve(pad, ker, 'same')[k:-k]
        self.p = xs
        self.paso = paso
        d = np.roll(xs, -1, 0) - np.roll(xs, 1, 0) if cerrada else np.gradient(xs, axis=0)
        self.yaw_d = np.degrees(np.arctan2(d[:, 0], d[:, 2]))
        horiz = np.maximum(np.hypot(d[:, 0], d[:, 2]), 1e-9)
        self.pitch_d = np.degrees(np.arctan2(d[:, 1], horiz))
        dy = np.unwrap(np.radians(self.yaw_d))
        curv = np.gradient(dy) / paso
        k = int(4 / paso)
        self.curv = np.convolve(np.pad(curv, k, mode='wrap' if cerrada else 'edge'), np.ones(2 * k + 1) / (2 * k + 1), 'same')[k:-k]
        self.yaw_u = np.degrees(dy)

    def _i(self, s):
        s = s % self.largo if self.cerrada else min(max(s, 0), self.largo - 1e-6)
        f = s / self.paso; i = int(f); return i % len(self.p), (i + 1) % len(self.p), f - int(f)

    def muestra(self, s, lateral=0.0):
        i, j, f = self._i(s)
        pos = self.p[i] * (1 - f) + self.p[j] * f
        a = math.radians(self.yaw_d[i]); b = math.radians(self.yaw_d[j])
        yaw = math.degrees(math.atan2(math.sin(a) * (1 - f) + math.sin(b) * f, math.cos(a) * (1 - f) + math.cos(b) * f))
        pitch = self.pitch_d[i] * (1 - f) + self.pitch_d[j] * f
        curv = self.curv[i] * (1 - f) + self.curv[j] * f
        r = math.radians(yaw)
        normal = np.array([-math.cos(r), 0.0, math.sin(r)])            # a la derecha del avance (lateral > 0 = derecha)
        return {'pos': pos + normal * lateral, 'yaw': yaw, 'pitch': pitch, 'curv': curv, 'centro': pos, 'normal': normal}


class Mundo:
    """Circuito listo para renderizar: instancias del circuito y del cielo, entorno y pista."""
    def __init__(self, motor, nombre, linea=0):
        self.motor = motor
        self.c = M.Circuito(nombre)
        self.nombre = nombre
        cj = self.c.conjunto()
        self.malla = motor.malla(cj)
        self.suelo = Suelo(self.malla.xyz)
        self.nkm = NK.Nkm(self.c.nkm)
        sk = self.c.conjunto_cielo()
        self.cielo = motor.malla(sk) if sk is not None else None
        pts, esc = self.nkm.linea(linea)
        self.pista = Pista(pts, self.suelo) if len(pts) >= 4 else None      # los circuitos de misión no tienen línea
        self.entorno = self._entorno()

    def _entorno(self):
        env = E.Entorno()
        if self.cielo is not None:
            xyz = self.cielo.xyz.reshape(-1, 3)
            self.escala_cielo = 1.0
            # color de niebla = media de la parte baja del cielo (la textura del cielo cerca del horizonte)
            cam = E.Camara((0, 0, 0), (1, 0.0, 0), fov=40)
            m = E.Motor(64, 96, ss=1, filtro=1); m._mats = self.motor._mats; m._tex = None
            img = m.render([E.Instancia(self.cielo, capa=-1, luz='plana')], cam, E.Entorno(niebla_fuerza=0))
            h = img[int(96 * 0.45):int(96 * 0.55)]
            env.niebla = h.reshape(-1, 3).mean(0).astype(np.float32)
            env.cielo_bajo = env.niebla
            top = img[:10].reshape(-1, 3).mean(0).astype(np.float32)
            env.cielo = top
            env.niebla_ini, env.niebla_fin = 160.0, 760.0
        return env

    def instancias(self):
        ins = [E.Instancia(self.malla, luz='baked')]
        if self.cielo is not None:
            ins.append(E.Instancia(self.cielo, capa=-1, luz='plana'))
        return ins
