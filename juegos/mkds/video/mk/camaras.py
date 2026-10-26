"""Cámaras y curvas: rutas con keyframes, órbitas, persecución, temblor y funciones de suavizado."""
import math
import numpy as np

from . import escena as E


def clamp(x, a=0.0, b=1.0):
    return a if x < a else (b if x > b else x)


def suave(x):
    x = clamp(x); return x * x * (3 - 2 * x)


def suavisimo(x):
    x = clamp(x); return x * x * x * (x * (x * 6 - 15) + 10)


def salida(x):
    x = clamp(x); return 1 - (1 - x) ** 3


def entrada(x):
    x = clamp(x); return x ** 3


def elastico(x):
    x = clamp(x)
    return 0.0 if x == 0 else 1.0 if x == 1 else 1 - math.exp(-7 * x) * math.cos(2 * math.pi * 1.5 * x)


def mezcla(a, b, t):
    return np.asarray(a) * (1 - t) + np.asarray(b) * t


class Ruta:
    """Interpola (t, valor) con Catmull-Rom; valores escalares o vectores. Fuera del rango se mantiene el extremo.
    `suavizar` aplica easing a cada tramo (parada y arranque suaves en cada clave)."""
    def __init__(self, claves, suavizar=False):
        self.t = np.array([c[0] for c in claves], np.float64)
        self.v = np.array([c[1] for c in claves], np.float64)
        if self.v.ndim == 1: self.v = self.v[:, None]
        self.suavizar = suavizar

    def __call__(self, t):
        if t <= self.t[0]: r = self.v[0]
        elif t >= self.t[-1]: r = self.v[-1]
        else:
            i = int(np.searchsorted(self.t, t) - 1)
            u = (t - self.t[i]) / (self.t[i + 1] - self.t[i])
            if self.suavizar: u = suave(u)
            p0 = self.v[max(i - 1, 0)]; p1 = self.v[i]; p2 = self.v[i + 1]; p3 = self.v[min(i + 2, len(self.v) - 1)]
            r = 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u ** 2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)
        return r if len(r) > 1 else float(r[0])


def temblor(t, amp=1.0, frec=11.0, semilla=0):
    """Vector de ruido suave (3,) en [-amp, amp] para sacudidas de cámara."""
    ph = np.array([1.0, 1.7, 2.3]) * (semilla + 1) * 1.618
    return amp * np.array([math.sin(t * frec * 1.0 + ph[0]) * 0.6 + math.sin(t * frec * 2.3 + ph[1]) * 0.4,
                           math.sin(t * frec * 1.4 + ph[1]) * 0.6 + math.sin(t * frec * 2.9 + ph[2]) * 0.4,
                           math.sin(t * frec * 0.8 + ph[2]) * 0.5])


def vec_yaw(yaw):
    r = math.radians(yaw); return np.array([math.sin(r), 0.0, math.cos(r)])


def persecucion(estado, dist=22.0, alto=8.0, adelante=10.0, altura_mira=2.5, lateral=0.0, fov=58.0, roll=0.0):
    """Cámara detrás del kart. estado = dict con pos y yaw."""
    f = vec_yaw(estado['yaw']); der = np.array([f[2], 0, -f[0]])
    pos = np.asarray(estado['pos'])
    return E.Camara(pos - f * dist + [0, alto, 0] + der * lateral, pos + f * adelante + [0, altura_mira, 0], fov=fov, roll=roll)


def orbita(centro, radio, alto, ang_grados, mira_alto=0.0, fov=45.0, roll=0.0):
    a = math.radians(ang_grados); c = np.asarray(centro)
    return E.Camara(c + [math.sin(a) * radio, alto, math.cos(a) * radio], c + [0, mira_alto, 0], fov=fov, roll=roll)
