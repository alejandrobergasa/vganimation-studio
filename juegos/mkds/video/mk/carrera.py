"""Simulación determinista de una carrera sobre una Pista (línea de carrera del circuito).

Cada corredor avanza por distancia `s` a lo largo de la línea con desplazamiento lateral; se tabula a 120 Hz y
`estado(i, t)` interpola, así que cualquier fotograma se evalúa sin estado previo (válido para render paralelo).
Eventos: salida, turbos (setas), golpes (giro del kart), derrapes automáticos en curvas cerradas."""
import math
import numpy as np

from . import camaras as CM


class Corredor:
    def __init__(self, nombre, s0, lat0=0.0, v=44.0, tipo='b', lat_fn=None, turbos=(), golpes=(), freno_curva=2.5):
        self.nombre, self.s0, self.lat0, self.v, self.tipo = nombre, s0, lat0, v, tipo
        self.lat_fn = lat_fn            # t -> lateral objetivo
        self.turbos = list(turbos)      # [(t, duración, multiplicador)]
        self.golpes = list(golpes)      # [t]  (giro de 720°, frena)
        self.freno_curva = freno_curva
        self.stop_en = None             # (t, s): a partir de t frena hasta parar en s
        self.v_mult = None


class Carrera:
    def __init__(self, pista, corredores, duracion, t_salida, dt=1 / 120.0, umbral_deriva=0.022):
        self.pista, self.c, self.T, self.t_go, self.dt = pista, corredores, duracion, t_salida, dt
        self.umbral = umbral_deriva
        self.n = int(duracion / dt) + 2
        self.tab = [self._simular(c) for c in corredores]

    def _simular(self, c):
        n, dt, p = self.n, self.dt, self.pista
        s = np.zeros(n); v = np.zeros(n); lat = np.zeros(n); der = np.zeros(n); dt_d = np.zeros(n); turbo = np.zeros(n)
        s[0] = c.s0; lat[0] = c.lat0
        vel = 0.0; l = c.lat0; drift_dir = 0; drift_t = 0.0
        for i in range(1, n):
            t = i * dt
            if t < self.t_go:
                s[i] = s[i - 1]; lat[i] = l; continue
            m = p.muestra(s[i - 1])
            cu = m['curv']
            objetivo = c.v * max(0.55, 1 / (1 + c.freno_curva * abs(cu) * 5))
            tb = 1.0
            for (t0, d, mu) in c.turbos:
                if t0 <= t < t0 + d: tb = max(tb, mu)
                turbo[i] = max(turbo[i], 1.0 if t0 <= t < t0 + d else 0.0)
            objetivo *= tb
            for th in c.golpes:
                if th <= t < th + 1.5: objetivo *= 0.12
            if c.stop_en is not None and t >= c.stop_en[0]:
                restante = max(0.0, c.stop_en[1] - s[i - 1])
                objetivo = min(objetivo, math.sqrt(2 * 22.0 * restante))
            k = 1.8 if tb > 1.0 else 2.6
            vel += (objetivo - vel) * min(1.0, dt * k)
            s[i] = s[i - 1] + vel * dt; v[i] = vel
            if c.lat_fn is not None:
                l += (c.lat_fn(t) - l) * min(1.0, dt * 2.5)
            lat[i] = l
            if abs(cu) > self.umbral and vel > 18:
                d = 1 if cu > 0 else -1
                if d != drift_dir: drift_dir = d; drift_t = 0.0
                drift_t += dt
            else:
                drift_dir = 0; drift_t = 0.0
            der[i] = drift_dir; dt_d[i] = drift_t
        return {'s': s, 'v': v, 'lat': lat, 'der': der, 'dt': dt_d, 'turbo': turbo}

    def _i(self, t):
        f = min(max(t, 0.0), self.T) / self.dt
        i = int(f); return min(i, self.n - 2), f - int(f)

    def estado(self, k, t):
        c = self.c[k]; tb = self.tab[k]
        i, f = self._i(t)
        g = lambda a: tb[a][i] * (1 - f) + tb[a][i + 1] * f
        s = g('s'); lat = g('lat'); v = g('v')
        m = self.pista.muestra(s, lat)
        # derrape: ángulo suavizado según el tiempo que lleva derrapando; el signo es el del giro
        dd = tb['der'][i]; dtd = tb['dt'][i]
        deriva = dd * 24.0 * CM.suave(dtd / 0.22)
        volante = float(np.clip(m['curv'] * 22.0, -1, 1)) if dd == 0 else dd * (0.75 + 0.25 * CM.suave(dtd / 0.4))
        if dd != 0: volante = dd * 0.55            # en derrape se gira hacia dentro con menos amplitud
        alto = 0.0; spin = 0.0
        for th in c.golpes:
            u = (t - th) / 1.4
            if 0 <= u <= 1:
                spin = 720.0 * CM.suave(u); alto = 2.6 * math.sin(math.pi * min(1, u * 1.6)) ** 2 * (1 - u * .4)
        # saltito al empezar a derrapar
        if dd != 0 and dtd < 0.28: alto += 0.9 * math.sin(math.pi * dtd / 0.28)
        giro = s / 1.0 * 57.2958 / max(0.4, 0.85)       # rodadura aproximada: ángulo = s / radio (radio ≈ 0,85 u)
        return {'pos': m['pos'] + np.array([0, alto, 0]), 'yaw': m['yaw'] + spin, 'yaw_pista': m['yaw'], 'pitch': -m['pitch'],
                'deriva': deriva, 'volante': volante, 'giro': giro, 'v': v, 's': s, 'lat': lat, 'drift': dd, 'drift_t': dtd,
                'turbo': tb['turbo'][i] > 0, 'alto': alto, 'curv': m['curv'], 'centro': m['centro'], 'normal': m['normal'],
                'roll': -volante * 3.5 + (0 if dd == 0 else -dd * 2.0)}

    def tiempo_en(self, k, s_objetivo):
        """Primer instante en que el corredor k alcanza s_objetivo (o None)."""
        s = self.tab[k]['s']
        idx = np.nonzero(s >= s_objetivo)[0]
        return None if len(idx) == 0 else idx[0] * self.dt
