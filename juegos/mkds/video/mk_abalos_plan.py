"""Plan de la cinemática «ABALOS KART»: guion en tiempos, trayectorias deterministas (funciones puras de t) y eventos.

Todo lo que se mueve se tabula a 120 Hz sobre la línea de carrera del circuito (`Pista`) o con integración balística
(choque, cuerpos despedidos); `estado(t)` interpola, así cada fotograma se evalúa sin estado previo (render paralelo)."""
import math
import numpy as np

from mk import camaras as CM

# ------------------------------------------------------------------ guion (segundos)
DUR = 76.5
T_PEACH1 = 2.6          # «¡ERES EL PUTO AMO!»
T_FRENA = 6.2
T_PARA = 8.0
T_ARRANCA = 19.4
T_SIRENA = 26.0
T_POLI_PASA = 30.0
T_POLI_PARA = 33.2
T_H_PARA2 = 33.6
T_DK_BAJA = 33.8
T_SOPLA = 41.0
T_APARATO = 44.0
T_RESULTADO = 47.0
T_HUYE = 51.4
T_DK_SUBE = 52.0
T_POLI_ARRANCA = 53.0
T_PIERDE = 62.6         # empieza a perder el control
FIN_PERSEC = 70.0

# diálogos: (t0, t1, quién, texto)
DIALOGO = [
    (T_PEACH1, T_PEACH1 + 2.0, 'PEACH', '¡ERES EL PUTO AMO!'),
    (8.4, 10.8, 'ABALOS', 'EH GUARRILLA, SÚBETE ANDA.'),
    (10.95, 12.3, 'DAISY', 'NO.'),
    (12.45, 15.3, 'ABALOS', 'VENGA ZORRA, NO TE HAGAS LA ESTRECHA.'),
    (16.6, 19.6, 'ABALOS', 'LAS ZORRAS COMO ESA NUNCA LLEGARÁN A NADA.'),
    (19.8, 25.4, 'ABALOS', 'LAS MEJORES SON COMO TÚ, QUE POR 20 DUROS SE PONEN A BAILARME.'),
    (35.0, 38.6, 'DK', '¡ALTO AHÍ! ESTO ES UN CONTROL DE ALCOHOLEMIA.'),
    (38.8, 40.9, 'DK', 'SOPLE EN EL APARATO.'),
    (48.8, 50.6, 'DK', '¡BÁJESE DEL COCHE!'),
    (50.8, 52.1, 'ABALOS', '¡UNA POLLA!'),
    (69.0, 72.0, 'DK', 'VAYA MOVIE, MANO.'),
]

# ------------------------------------------------------------------ utilidades

def suave_serie(v, seg, dt):
    k = max(1, int(seg / dt))
    pad = np.pad(v, k, mode='edge')
    return np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), 'same')[k:-k]


class Camino:
    """Trayectoria sobre la pista: velocidad y lateral por claves. `anclar(t, s)` fija la distancia en un instante."""
    def __init__(self, pista, v_claves, lat_claves=((0, 0.0),), dur=80.0, dt=1 / 120.0, deriva_claves=None, alto_claves=None,
                 suav_v=0.3, suav_lat=0.5):
        self.pista, self.dt, self.dur = pista, dt, dur
        self.t = np.arange(0, dur + 0.5, dt)
        kv = np.array(v_claves, float); kl = np.array(lat_claves, float)
        v = suave_serie(np.interp(self.t, kv[:, 0], kv[:, 1]), suav_v, dt)
        self.v = np.maximum(v, 0)
        self.I = np.concatenate([[0], np.cumsum(self.v[:-1] * dt)])
        self.lat = suave_serie(np.interp(self.t, kl[:, 0], kl[:, 1]), suav_lat, dt)
        self.dlat = np.gradient(self.lat, dt)
        self.der = np.zeros_like(self.t) if deriva_claves is None else suave_serie(np.interp(self.t, *np.array(deriva_claves, float).T), 0.15, dt)
        self.alt = np.zeros_like(self.t) if alto_claves is None else np.interp(self.t, *np.array(alto_claves, float).T)
        self.s0 = 0.0

    def anclar(self, t, s):
        self.s0 = s - np.interp(t, self.t, self.I)
        return self

    def s(self, t):
        return self.s0 + np.interp(t, self.t, self.I)

    def estado(self, t, volante_extra=0.0):
        P = self.pista
        g = lambda a: float(np.interp(t, self.t, a))
        s = self.s0 + g(self.I); lat = g(self.lat); v = g(self.v); dl = g(self.dlat)
        m = P.muestra(s, lat)
        cur = m['curv']
        yaw_l = -math.degrees(math.atan2(dl, max(v, 8.0))) if v > 1 else 0.0
        volante = float(np.clip(cur * 22.0 - dl * 0.22 + volante_extra, -1, 1))
        alto = g(self.alt)
        der = g(self.der)
        return {'pos': m['pos'] + np.array([0, alto, 0]), 'yaw': m['yaw'] + yaw_l, 'yaw_pista': m['yaw'], 'pitch': -m['pitch'],
                'roll': -volante * 3.0, 'volante': volante, 'giro': s * 57.2958 / 0.85, 'v': v, 's': s, 'lat': lat,
                'deriva': der, 'alto': alto, 'curv': cur, 'centro': m['centro'], 'normal': m['normal'], 'turbo': False}


def vec_yaw(y):
    return CM.vec_yaw(y)


def izq(yaw):
    f = CM.vec_yaw(yaw)
    return np.array([f[2], 0.0, -f[0]])


def rot_hacia(d, arriba=(0, 1, 0)):
    """Matriz cuyo eje +z apunta a d."""
    z = np.asarray(d, float); z = z / (np.linalg.norm(z) + 1e-12)
    x = np.cross(arriba, z)
    if np.linalg.norm(x) < 1e-6: x = np.cross((1, 0, 0), z)
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z], 1).astype(np.float32)


# ------------------------------------------------------------------ cuerpos balísticos (despedidos, ruedas)

class Cuerpo:
    """Cuerpo que sale despedido: vuelo, rebotes y rodadura hasta quedar tendido. Tabulado a 120 Hz.
    estado(t) -> pos, yaw, pitch, roll (grados), contacto (bool), reposo (bool)."""
    def __init__(self, suelo, t0, pos, vel, rot_vel, dur, g=-40.0, rest=0.36, fric=22.0, semilla=0, dt=1 / 120.0, radio=1.2, y_min=None):
        self.t0, self.dt = t0, dt
        n = int(dur / dt) + 2
        P = np.zeros((n, 3)); A = np.zeros((n, 3)); C = np.zeros(n, bool); GOL = []
        p = np.array(pos, float); v = np.array(vel, float); w = np.array(rot_vel, float); a = np.zeros(3)
        rng = np.random.default_rng(semilla)
        hint = p[1]
        reposo_i = n - 1
        en_suelo = False
        for i in range(n):
            P[i], A[i] = p, a
            C[i] = en_suelo
            h = suelo.altura(p[0], p[2], hint + 4.0)
            if np.isnan(h): h = hint
            hint = h
            v[1] += g * dt
            p = p + v * dt
            a = a + w * dt
            if p[1] - radio * 0.0 <= h + 0.05:
                p[1] = h + 0.05
                if v[1] < -3.0:
                    v[1] = -v[1] * rest
                    v[0] *= 0.7; v[2] *= 0.7
                    w = w * 0.55 + rng.normal(size=3) * 90
                    GOL.append(i * dt)
                else:
                    v[1] = 0.0
                    sp = math.hypot(v[0], v[2])
                    if sp > 1e-3:
                        k = max(0.0, 1 - fric * dt / sp); v[0] *= k; v[2] *= k
                    w = w * (1 - 3.0 * dt)
                    if sp < 0.4 and reposo_i == n - 1:
                        reposo_i = i
                en_suelo = True
            else:
                en_suelo = False
        self.P, self.A, self.C = P, A, C
        self.golpes = GOL
        self.i_reposo = reposo_i
        self.t_reposo = t0 + reposo_i * dt
        # el ángulo final se asienta hacia la postura tendida más cercana en los últimos 0,35 s antes de parar
        self.n = n

    def estado(self, t):
        f = (t - self.t0) / self.dt
        i = int(min(max(f, 0), self.n - 2)); fr = min(max(f - i, 0), 1) if f < self.n - 1 else 0.0
        if f > self.i_reposo: i, fr = self.i_reposo, 0.0
        p = self.P[i] * (1 - fr) + self.P[i + 1] * fr
        a = self.A[i] * (1 - fr) + self.A[i + 1] * fr
        # asentamiento: cerca del reposo, la inclinación se lleva a un múltiplo de 180 (+90 en cabeceo: boca arriba/abajo)
        u = CM.suave((f - (self.i_reposo - 42)) / 42.0)
        a = a.copy()
        fin = np.array([round(self.A[self.i_reposo][0] / 180.0) * 180.0 + 90.0 * (1 if round(self.A[self.i_reposo][0] / 180.0) % 2 == 0 else -1),
                        self.A[self.i_reposo][1], round(self.A[self.i_reposo][2] / 180.0) * 180.0])
        a = a * (1 - u) + fin * u
        return {'pos': p, 'ang': a, 'reposo': f >= self.i_reposo}


# ------------------------------------------------------------------ choque del kart de Ábalos

class Choque:
    """Pérdida de control: deslizamiento con giro hasta el árbol. Devuelve la posición del impacto (para colocar el árbol)."""
    def __init__(self, suelo, pista, estado0, t0, exterior, v_out=0.4, giro_vel=300.0, dur=2.5, dt=1 / 120.0):
        self.t0, self.dt = t0, dt
        n = int(dur / dt) + 2
        pos = np.array(estado0['pos'], float); v0 = estado0['v']
        f = vec_yaw(estado0['yaw']); fw = np.array([f[0], 0, f[2]])
        vel = (fw * math.cos(math.radians(22)) + exterior * math.sin(math.radians(22))) * v0
        yaw = estado0['yaw']; dp = 0.0
        P = np.zeros((n, 3)); Y = np.zeros(n); R = np.zeros(n); Pi = np.zeros(n); V = np.zeros(n)
        hint = pos[1]
        for i in range(n):
            u = i * dt
            P[i] = pos; Y[i] = yaw; V[i] = np.hypot(vel[0], vel[2])
            Pi[i] = 0.0; R[i] = 0.0
            vel = vel * (1 - 0.35 * dt)
            pos = pos + vel * dt
            yaw += giro_vel * min(1.0, u / 0.35) * dt
            h = suelo.altura(pos[0], pos[2], hint + 3.0)
            if not np.isnan(h):
                hint = h
            pos[1] = hint + 0.0
        self.P, self.Y, self.V, self.n = P, Y, V, n
        # distancia a la calzada (según el lateral con la pista) para elegir el instante del impacto
        self.pista = pista
        d = np.array([np.linalg.norm((p - estado0['centro'])[[0, 2]]) for p in P])
        self.d_centro = d

    def instante_impacto(self, dist):
        i = int(np.argmax(self.d_centro >= dist))
        return self.t0 + i * self.dt

    def estado(self, t):
        f = min(max((t - self.t0) / self.dt, 0), self.n - 2)
        i = int(f); fr = f - i
        pos = self.P[i] * (1 - fr) + self.P[i + 1] * fr
        yaw = self.Y[i] * (1 - fr) + self.Y[i + 1] * fr
        v = self.V[i] * (1 - fr) + self.V[i + 1] * fr
        return pos, yaw, v
