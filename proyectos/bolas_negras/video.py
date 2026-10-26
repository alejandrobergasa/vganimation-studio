"""«BOLAS NEGRAS» — cinemática vertical (Mario Kart DS), 1080x1920, 30 fps, 36 s. Plan en storyboard.md y guion.md.

Circuito Mario (ROM) para la carretera y el cielo; el cine y los billetes son geometría propia; los personajes son el piloto de Mario de la ROM
con la foto de cada cara; el texto usa la fuente del juego; la imagen final es QUEBUSCA.jpeg (entrada/bolas_negras).
    python valedores.py ejecutar bolas_negras -- python -I proyectos/bolas_negras/video.py --rapido --hoja 16
    python valedores.py ejecutar bolas_negras -- python -I proyectos/bolas_negras/video.py --frame 27.0
    python valedores.py ejecutar bolas_negras -- python -I proyectos/bolas_negras/video.py          # render final"""
import os, sys, math
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'nucleo'))
from valedores import rutas
JUEGO = 'mkds'
sys.path.insert(0, rutas.motor_dir(JUEGO))
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
import numpy as np
from PIL import Image, ImageFilter

import mk
from mk import escena as E, circuito as C, kart as K, fx as FX, post as P, camaras as CM
from mk import texto as T, director as D, extra as X, personas as PE

ENTRADA = os.path.join(REPO, 'entrada', 'bolas_negras')
DUR = 36.0

# ------------------------------------------------------------------ plan (segundos del guion)
T_STOP_A, T_STOP_B = 14.0, 14.0          # los karts se paran
T_SALTA_A, T_SALTA_B = 14.15, 14.4       # bajan de un salto
T_PEDRO, T_PAGA_A, T_PAGA_B, T_PASEN = 16.0, 19.2, 21.0, 22.0
T_ENTRAN = 22.4                          # empiezan a cruzar la puerta
T_SANTOS_GIRA = 25.8
T_BUSCAN, T_FOTO = 32.5, 34.0

COLOR = {'ALEGA': ((.8, 1, .8), (.2, .8, .3)), 'VIVI': ((1, 1, .75), (1, .8, .1)), 'PEDRO': ((1, .85, .85), (.95, .2, .2)),
         'SANTOS': ((.85, .95, 1), (.3, .6, 1))}
NOMBRE = {'ALEGA': 'ALEGA', 'VIVI': 'VIVI', 'PEDRO': 'PEDRO', 'SANTOS': 'SANTOS'}
DIALOGO = [   # (t0, t1, quién, líneas)
    (2.0, 5.0, 'ALEGA', ['¡QUÉ GANAS TENGO DE', 'VER LA BOLA NEGRA!']),
    (5.0, 8.0, 'VIVI', ['¡Y YO! LLEVO UNA', 'SEMANA ESPERANDO.']),
    (8.0, 10.0, 'ALEGA', ['DICEN QUE ES', 'SÚPER NEGRA.']),
    (10.0, 12.0, 'VIVI', ['¡CUANTO MÁS NEGRA,', 'MEJOR!']),
    (16.0, 19.0, 'PEDRO', ['BUENAS. LA ENTRADA', 'SON 10 EUROS.']),
    (19.0, 21.0, 'ALEGA', ['¡TOMA, CON GUSTO!']),
    (21.0, 22.0, 'VIVI', ['¡Y LOS MÍOS!']),
    (22.0, 24.0, 'PEDRO', ['PASEN, PASEN.']),
    (26.0, 28.0, 'SANTOS', ['ESTO ES UNA LOCURA.']),
    (28.0, 31.0, 'SANTOS', ['NO PUEDE SER QUE DOS', 'HOMBRES CRECIDOS']),
    (31.0, 32.5, 'SANTOS', ['PAGUEN POR VER', 'BOLAS NEGRAS.']),
]

# recortes de cara (x0, y0, x1, y1) en píxeles de cada foto

S_C = 108.0          # s del centro del cine sobre la recta (n.º de metro de la línea de carrera)
LAT_FACHADA = -26.0  # la fachada está a la izquierda de la marcha
LAT_PARK = -12.2
Q = 0.72             # escala del cine y sus coordenadas locales respecto al mundo (kart ≈ 6,7 u; persona ≈ 6 u)


def vec_yaw(y):
    return CM.vec_yaw(y)


def suavizar(v, seg, dt):
    k = max(1, int(seg / dt))
    pad = np.pad(v, k, mode='edge')
    return np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), 'same')[k:-k]


class Sitio:
    """Sistema local del cine: origen en el suelo, centro de la fachada; +z hacia la carretera, +x en el sentido de la marcha."""
    def __init__(self, pista):
        q = pista.muestra(S_C)
        self.O = np.asarray(q['centro'] + q['normal'] * LAT_FACHADA, np.float64)
        self.Y = q['yaw'] - 90.0
        self.R = E.rot_y(math.radians(self.Y)).astype(np.float64)
        self.pista = pista

    def w(self, x, y=0.0, z=0.0):
        return self.O + self.R @ (np.array([x, y, z], np.float64) * Q)

    def yaw_hacia(self, dx, dz):
        return self.Y + math.degrees(math.atan2(dx, dz))

    def local(self, p):
        return self.R.T @ (np.asarray(p, np.float64) - self.O) / Q


class Guion:
    """Trayectorias de los karts por la pista y estado de los personajes. Todo es función pura de t."""
    def __init__(self, pista):
        self.pista = pista
        self.sit = Sitio(pista)
        dt = 1 / 120.0
        self.dt = dt
        self.t = np.arange(0, T_STOP_B + 1.0, dt)
        vA = suavizar(np.interp(self.t, *np.array([(0, 30), (10.5, 30), (12.3, 27), (13.0, 17), (13.7, 5), (T_STOP_A, 0), (40, 0)]).T), 0.25, dt)
        IA = np.concatenate([[0], np.cumsum(vA[:-1] * dt)])
        stop_a = S_C + 4.0 + pista.largo
        self.sA = stop_a - np.interp(T_STOP_A, self.t, IA) + IA
        gap = 9.5 * np.array([CM.suave((x - 9.0) / 4.5) for x in self.t])
        sB = self.sA - gap
        self.sB = sB
        self.latA = suavizar(np.interp(self.t, *np.array([(0, -3.5), (11.8, -3.5), (T_STOP_A, LAT_PARK), (40, LAT_PARK)]).T), 0.5, dt)
        self.latB = suavizar(np.interp(self.t, *np.array([(0, 3.5), (9.5, 3.5), (11.4, -3.5), (12.6, -3.5), (T_STOP_B, LAT_PARK), (40, LAT_PARK)]).T), 0.5, dt)
        self.vA = vA
        self.vB = np.gradient(self.sB, dt)
        self.dlatA, self.dlatB = np.gradient(self.latA, dt), np.gradient(self.latB, dt)

    def paseo(self, quien):
        """(inicio, fin) del tramo andando desde el kart hasta esperar ante Pedro (mismos datos que BolasNegras._a_pie)."""
        tsalta = T_SALTA_A if quien == 'A' else T_SALTA_B
        pl = self.sit.local(self.kart(quien, tsalta)['pos'])
        tgt = (2.6, 4.8) if quien == 'A' else (-2.6, 4.8)
        L = math.hypot(tgt[0] - pl[0], tgt[1] - (pl[2] - 4.4))
        return tsalta + 0.35, tsalta + 0.35 + L / (6.0 / Q)

    def kart(self, quien, t):
        """Estado del kart: pos, yaw (grados), giro de ruedas acumulado (grados), volante, v."""
        t = min(max(t, 0.0), self.t[-1])
        g = lambda a: float(np.interp(t, self.t, a))
        s, lat, v, dl = ((g(self.sA), g(self.latA), g(self.vA), g(self.dlatA)) if quien == 'A'
                         else (g(self.sB), g(self.latB), g(self.vB), g(self.dlatB)))
        m = self.pista.muestra(s, lat)
        der = max(-35.0, min(35.0, math.degrees(math.atan2(-dl, max(v, 4.0)))))     # lateral < 0 = hacia la izquierda: yaw +
        if v < 0.2 and t > (T_STOP_A if quien == 'A' else T_STOP_B): der = 0.0
        return {'pos': m['pos'], 'yaw': m['yaw'] + der, 'v': v, 'giro': -math.degrees(s / 1.6), 'volante': max(-1, min(1, der / 25.0)),
                'yaw_via': m['yaw'], 'normal': m['normal']}


def _tex_marquesina(m):
    """Marquesina 512x96: panel negro con bombillas y el rótulo BOLAS NEGRAS con la fuente del juego."""
    W, H = 256, 64
    im = np.zeros((H, W, 3), np.float32); im[:] = (0.05, 0.03, 0.04)
    r = T.render('BOLAS NEGRAS', 40, relleno=((1, 1, .7), (1, .75, .1)), borde=(.45, .05, .05))
    s = min(1.0, (W - 20) / r.shape[1])
    r = np.asarray(Image.fromarray((r * 255).astype(np.uint8)).resize((int(r.shape[1] * s), int(r.shape[0] * s)), Image.LANCZOS), np.float32) / 255
    y0, x0 = (H - r.shape[0]) // 2, (W - r.shape[1]) // 2
    a = r[..., 3:4]; im[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] = im[y0:y0 + r.shape[0], x0:x0 + r.shape[1]] * (1 - a) + r[..., :3] * a
    for x in range(4, W, 12):
        im[2:5, x:x + 4] = (1, .9, .4); im[H - 5:H - 2, x:x + 4] = (1, .9, .4)
    return (np.clip(np.concatenate([im, np.ones((H, W, 1), np.float32)], -1), 0, 1) * 255).astype(np.uint8)


def _tex_cartel():
    """Cartel de película: fondo rojo y una gran bola negra con el 8."""
    W, H = 96, 128
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    im = np.zeros((H, W, 3), np.float32); im[:] = (0.55, 0.05, 0.08) * (1 - 0.35 * (yy / H))[..., None]
    cx, cy, rr = W / 2, H * 0.52, W * 0.36
    d = np.hypot(xx - cx, yy - cy)
    bola = np.clip((rr - d) / 1.2, 0, 1)[..., None]
    sombra = np.clip(1 - d / rr, 0, 1)
    br = np.clip(1 - np.hypot(xx - (cx - rr * .35), yy - (cy - rr * .4)) / (rr * .35), 0, 1)
    col = np.array([0.03, 0.03, 0.04]) + 0.25 * br[..., None]
    im = im * (1 - bola) + col * bola
    disco = np.clip((rr * .42 - np.hypot(xx - cx, yy - (cy + rr * .05))) / 1.0, 0, 1)[..., None]
    im = im * (1 - disco) + np.array([.95, .95, .9]) * disco
    t = T.render('8', 26, relleno=((0, 0, 0), (0, 0, 0)), borde=(0, 0, 0), grosor=0.02)
    y0, x0 = int(cy + rr * .05 - t.shape[0] / 2), int(cx - t.shape[1] / 2)
    a = t[..., 3:4]; im[y0:y0 + t.shape[0], x0:x0 + t.shape[1]] = im[y0:y0 + t.shape[0], x0:x0 + t.shape[1]] * (1 - a) + t[..., :3] * a
    tt = T.render('LA BOLA', 16, relleno=((1, 1, .7), (1, .8, .2)), borde=(.2, 0, 0))
    y0, x0 = 5, int((W - tt.shape[1]) / 2)
    a = tt[..., 3:4]; im[y0:y0 + tt.shape[0], x0:x0 + tt.shape[1]] = im[y0:y0 + tt.shape[0], x0:x0 + tt.shape[1]] * (1 - a) + tt[..., :3] * a
    return (np.clip(np.concatenate([im, np.ones((H, W, 1), np.float32)], -1), 0, 1) * 255).astype(np.uint8)


# ======================================================================= imagen

class BolasNegras:
    fps = 30
    duracion = DUR
    ancho, alto = 1080, 1920
    ss = 1.5

    def __init__(self, ancho, alto, ss):
        self.w, self.h = ancho, alto
        self.m = E.Motor(ancho, alto, ss=ss)
        X.parchear_cielo()
        self.mundo = C.Mundo(self.m, 'mario_course')
        self.g = Guion(self.mundo.pista)
        self.sp = FX.Sprites(self.m)
        self._textos = {}
        self._personajes()
        self._karts()
        self._cine()
        self._particulas()
        self._foto_final()

    # ------------------------------------------------------------ recursos
    def _personajes(self):
        """Cada uno es el piloto de Mario de la ROM con su foto como cara y la ropa de la foto; hitos = (fila de los ojos, fila de la barbilla,
        columna del centro de la cara) en píxeles de la foto."""
        m = self.m
        f = lambda n: os.path.join(ENTRADA, n)
        neg, gris, traje = (0.13, 0.13, 0.15), (0.55, 0.57, 0.6), (0.1, 0.11, 0.17)
        self.alega = PE.Personaje(m, 'ALEGA', f('alega.jpeg'), (176, 306, 146), None, neg, neg, neg, neg, (0.12, 0.13, 0.2), ancho=0.86)
        self.vivi = PE.Personaje(m, 'VIVI', f('vivi.jpg'), (118, 199, 102), (0.09, 0.07, 0.07), neg, neg, neg, neg, (0.2, 0.22, 0.3), ancho=0.86)
        self.santos = PE.Personaje(m, 'SANTOS', f('santos.jpeg'), (342, 585, 255), (0.28, 0.16, 0.1), gris, gris, gris, gris, (0.15, 0.17, 0.25))
        self.pedro = PE.Personaje(m, 'PEDRO', f('pedrosanchez.jpg'), (193, 362, 162), (0.42, 0.42, 0.45), (0.95, 0.95, 0.97), traje, traje,
                                  (0.1, 0.2, 0.6), traje, escala=5.4, largo=1.65, ancho=0.66)

    def _karts(self):
        m = self.m
        self.kA = K.Kart(m, 'luigi', 'b')
        self.kB = K.Kart(m, 'wario', 'b')

    def _cine(self):
        m = self.m
        s = m.solido
        pared, crema, rojo, negro = s((0.5, 0.07, 0.1)), s((0.95, 0.88, 0.7)), s((0.8, 0.1, 0.1)), s((0.02, 0.02, 0.03))
        asfalto, acera, linea, oro = s((0.22, 0.22, 0.25)), s((0.62, 0.6, 0.55)), s((0.95, 0.95, 0.95)), s((1.0, 0.85, 0.3))
        mar = m.material(_tex_marquesina(m), 0)
        car = m.material(_tex_cartel(), 0)
        c = X.caja
        partes = [
            c(pared, 12.3, 14.0, 10.0, centro=(-8.85, 7.0, -5.5)), c(pared, 12.3, 14.0, 10.0, centro=(8.85, 7.0, -5.5)),   # cuerpo a ambos lados de la puerta (5,4 u)
            c(pared, 5.4, 3.5, 10.0, centro=(0, 12.25, -5.5)),                                                           # sobre la puerta (puerta de 10,5 u)
            c(pared, 5.4, 10.5, 7.3, centro=(0, 5.25, -6.85)),                                                           # fondo del cine tras el vestíbulo
            c(crema, 30.8, 1.0, 10.8, centro=(0, 14.5, -5.5)),                                                           # cornisa
            c(crema, 0.7, 10.5, 0.7, centro=(-2.9, 5.25, 0.3)), c(crema, 0.7, 10.5, 0.7, centro=(2.9, 5.25, 0.3)),        # jambas
            c(negro, 0.05, 10.5, 3.2, centro=(-2.66, 5.25, -1.6)), c(negro, 0.05, 10.5, 3.2, centro=(2.66, 5.25, -1.6)),  # forro oscuro del vestíbulo
            c(negro, 5.4, 10.5, 0.05, centro=(0, 5.25, -3.22)), c(negro, 5.4, 0.05, 3.2, centro=(0, 0.2, -1.6)),
            c(crema, 24.0, 0.6, 1.8, centro=(0, 15.3, 0.9)),                                                             # base del letrero
            c(rojo, 6.0, 0.3, 4.0, centro=(0, 10.7, 2.0)),                                                               # toldo
            c(acera, 36.0, 0.25, 8.0, centro=(0, 0.12, 4.0)),                                                            # acera
            c(asfalto, 36.0, 0.12, 14.0, centro=(0, 0.06, 15.0)),                                                        # aparcamiento
        ]
        for x in (-12, -9, -6, -3, 3, 6, 9, 12):
            partes.append(c(linea, 0.25, 0.05, 6.0, centro=(x + 0.0, 0.15, 17.2)))
        self.cine = E.Malla.une(partes)
        self.letrero = c(mar, 24.0, 5.0, 0.8, centro=(0, 17.5, 0.5), tam_tex=(256, 64))
        self.carteles = E.Malla.une([c(car, 5.2, 7.0, 0.2, centro=(-10.0, 6.5, 0.1), tam_tex=(96, 128)),
                                     c(car, 5.2, 7.0, 0.2, centro=(10.0, 6.5, 0.1), tam_tex=(96, 128))])
        self.muro = E.Malla.une([c(crema, 3.0, 14.0, 13.0, centro=(0, 7.0, 0)), c(rojo, 3.4, 1.0, 13.4, centro=(0, 14.5, 0))])
        self.billete = c(m.solido((0.3, 0.8, 0.35)), 1.6, 0.06, 0.8)
        self.mat_oro = oro

    def _particulas(self):
        sp, g = self.sp, self.g
        pa = FX.Particulas(self.m, 5)
        sit = g.sit
        # humo de las frenadas al aparcar
        for quien, t0, t1 in (('A', 12.6, T_STOP_A + 0.3), ('B', 12.9, T_STOP_B + 0.3)):
            ts = np.arange(t0, t1, 1 / 40.0)
            if len(ts) == 0: continue
            pos = np.array([g.kart(quien, t)['pos'] for t in ts]) + [0, 0.4, 0]
            n = len(ts)
            pa.agregar(ts, pa.rng.uniform(.5, .9, n), pos, pa.rng.normal(size=(n, 3)) * [1.5, 1, 1.5] + [0, 1.8, 0], pa.rng.uniform(.8, 1.3, n), 3.0,
                       np.array([.85, .82, .75]), np.array([.9, .88, .8]), sp.humo, g=(0, .5, 0), a0=.7, a1=0.0)
        self.p_humo = pa
        # destellos del letrero (las bombillas)
        self.p_glow = FX.Particulas(self.m, 6)

    def _foto_final(self):
        im = Image.open(os.path.join(ENTRADA, 'QUEBUSCA.jpeg')).convert('RGB')
        W, H = self.w, self.h
        fondo = im.resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(25 * W / 1080))
        self.foto_fondo = np.asarray(fondo, np.float32) / 255 * 0.35
        self.foto = im
        self._cache_foto = {}

    # ------------------------------------------------------------ texto
    def texto(self, s, alto, **kw):
        k = (s, alto, tuple(sorted(kw.items())))
        if k not in self._textos:
            self._textos[k] = T.render(s, alto, **kw)
        return self._textos[k]

    # ------------------------------------------------------------ estado de personajes
    def _asiento(self, kart, quien, t):
        e = self.g.kart(quien, t)
        R = E.rotacion(e['yaw'])
        a, z = kart.asiento
        return e, np.asarray(e['pos']) + R @ (np.array([0, a, z]) * kart.escala)         # como Kart.instancias: el origen del piloto es el asiento

    def x_pedro(self, t):
        """Pedro en la puerta: centrado; se corre a un lado en los planos de pago (cortes) para no tapar al cliente; al final deja pasar."""
        if t < 19.0: return 0.0
        if t < 20.9: return -1.9
        if t < T_PASEN: return 1.9
        return 1.9 + 1.4 * CM.suave((t - T_PASEN) / 0.5)

    def personas(self, t):
        g, sit = self.g, self.g.sit
        ins = []
        def andar(p0, p1, ta, v=6.0 / Q):
            """Posición local entre p0 y p1 desde ta a velocidad v: devuelve (x, z, caminando, dx, dz)."""
            d = np.array(p1) - np.array(p0); L = float(np.hypot(*d)); dur = L / v
            u = min(max((t - ta) / dur, 0.0), 1.0)
            p = np.array(p0) + d * u
            return p, (0 < u < 1), d / max(L, 1e-6), ta + dur
        # ---- Alega y Vivi: en el kart hasta que bajan
        for quien, per, kart, tsalta in (('A', self.alega, self.kA, T_SALTA_A), ('B', self.vivi, self.kB, T_SALTA_B)):
            if t < tsalta:
                e, pos = self._asiento(kart, quien, t)
                pos = pos + [0, 0.10 * math.sin(t * 9 + (0 if quien == 'A' else 2)) * (1 if e['v'] > 3 else 0), 0]
                anim, frame = 'drive', 14 + 14 * (-e['volante'])
                if quien == 'B' and 10.1 <= t < 11.9: anim, frame = 'win', 20          # Vivi: puño al aire
                ins += per.sentado(pos, yaw=e['yaw'], anim=anim, frame=frame)
            else:
                ins += self._a_pie(quien, per, t, andar)
        # ---- Pedro
        x_p = self.x_pedro(t)
        anim, frame = 'drive', 14
        if T_PEDRO + 2.6 <= t < T_PAGA_B + 1.8: anim, frame = 'win', 20                 # mano extendida a por el dinero
        ins += self.pedro.de_pie(sit.w(x_p, 0, 1.1), yaw=sit.yaw_hacia(0, 1), anim=anim, frame=frame, bote=0.04 * math.sin(t * 2.2))
        # ---- Santos
        ins += self._santos(t)
        return ins

    def _a_pie(self, quien, per, t, andar):
        sit = self.g.sit
        kart = self.kA if quien == 'A' else self.kB
        tsalta = T_SALTA_A if quien == 'A' else T_SALTA_B
        e = self.g.kart(quien, tsalta)
        pl = sit.local(e['pos'])
        x0, z0 = pl[0], pl[2]
        z_suelo = z0 - 4.4                       # baja por el lado del cine (izquierda del kart)
        tgt = (2.6, 4.8) if quien == 'A' else (-2.6, 4.8)
        pago = T_PAGA_A if quien == 'A' else T_PAGA_B
        # tramo 1: salto desde el asiento al suelo (0,35 s), con los brazos arriba
        if t < tsalta + 0.35:
            u = (t - tsalta) / 0.35
            _, cad = self._asiento(kart, quien, tsalta)
            ini = sit.local(cad); fin = np.array([x0, 0.0, z_suelo])
            p = ini * (1 - u) + fin * u
            p[1] = max(ini[1] - 2.0, 0.0) * (1 - u) + 3.0 * math.sin(math.pi * u)      # de la cadera (asiento) a los pies
            return per.de_pie(sit.w(*p), yaw=sit.yaw_hacia(0, -1), anim='win', frame=30)
        # tramo 2: caminar hacia la puerta
        ta = tsalta + 0.35
        p, caminando, d, t_fin = andar((x0, z_suelo), tgt, ta)
        entra = t >= T_ENTRAN
        x, z = float(p[0]), float(p[1])
        yaw = sit.yaw_hacia(d[0], d[1])
        anim, frame = 'drive', 14
        if not caminando and not entra:
            yaw = sit.yaw_hacia(0, -1)               # esperando ante Pedro
            if pago - 0.4 <= t < pago + 1.0: anim, frame = 'win', 20          # entrega el billete
        fase = (t - ta) * 11.0 if caminando else None
        tinte = (1, 1, 1)
        if entra:
            tx, tz = (1.3 if quien == 'A' else -1.3), -2.8
            u = min(max((t - T_ENTRAN - (0.0 if quien == 'A' else 0.25)) / 1.3, 0.0), 1.0)
            # primero se acercan a la puerta en línea recta y luego cruzan
            x = (tgt[0] * (1 - min(1, u * 1.8)) + tx * min(1, u * 1.8))
            z = tgt[1] * (1 - u) + tz * u
            yaw = sit.yaw_hacia(0, -1)
            fase = (t - T_ENTRAN) * 11.0 if 0 < u < 1 else None
            osc = max(0.0, min(1.0, (0.3 - z) / 2.2)) if z < 0.3 else 0.0
            f = 1.0 - osc
            tinte = (f, f, f)
            if u >= 1.0: return []
        return per.de_pie(sit.w(x, 0, z), yaw=yaw, fase=fase, anim=anim, frame=frame, tinte=tinte)

    def _santos(self, t):
        sit = self.g.sit
        gira = CM.suave((t - T_SANTOS_GIRA) / 0.5)
        yaw = (sit.Y - 90) * (1 - gira) + sit.Y * gira                      # de mirar la puerta (−x) a mirar a cámara (+z)
        anim, frame = 'drive', 14
        if 26.45 <= t < 27.35: anim, frame = 'lose', 30                       # «esto es una locura»
        return self.santos.de_pie(sit.w(21.8, 0, 13.4), yaw=yaw, anim=anim, frame=frame, bote=0.04 * math.sin(t * 1.7))

    def billetes(self, t):
        sit = self.g.sit
        ins = []
        for t0, x0 in ((T_PAGA_A, 2.6), (T_PAGA_B, -2.6)):
            d = t - t0
            if 0 <= d < 0.9:
                u = min(1.0, d / 0.5)
                p = np.array([x0 * (1 - u) + self.x_pedro(t0) * 0.5 * u + x0 * 0.5 * u, 5.4 + 1.5 * math.sin(math.pi * u), 4.8 * (1 - u) + 3.0 * u])
                ins.append(E.Instancia(self.billete, pos=sit.w(*p), rot=sit.R @ E.rotacion(30 * u, 0, 20 * u), escala=Q, luz='plana'))
        return ins

    # ------------------------------------------------------------ cámaras
    def cam(self, t):
        g, sit = self.g, self.g.sit
        post = {'bloom': 0.22, 'radial': 0.0, 'lineas': 0.0, 'flash': 0.0, 'vineta': 0.30, 'frio': 0.0, 'sac': 0.0}
        eA, eB = g.kart('A', t), g.kart('B', t)
        mid = (np.asarray(eA['pos']) + np.asarray(eB['pos'])) / 2
        yaw_v = (eA['yaw_via'] + eB['yaw_via']) / 2
        f = vec_yaw(yaw_v); n = eA['normal']                                        # n = derecha del avance
        if t < 2.0:                                                                 # 1. persecución alta
            u = t / 2.0
            cam = E.Camara(mid - f * CM.mezcla(18, 14, u) + [0, CM.mezcla(9.0, 7.0, u), 0] + n * 0.5, mid + f * 10 + [0, 1.5, 0], fov=60)
            post['lineas'] = 0.5
        elif t < 5.0:                                                               # 2. frontal baja
            u = (t - 2.0) / 3.0
            ang = CM.mezcla(-14, 14, u)
            cam = E.Camara(mid + f * CM.mezcla(21, 18, u) + n * (CM.mezcla(-3, 3, u)) + [0, 4.6, 0], mid + [0, 3.8, 0] + f * 1.0, fov=56)
            post['lineas'] = 0.18
        elif t < 8.0:                                                               # 3. primer plano de Vivi (kart B, carril derecho)
            u = (t - 5.0) / 3.0
            pos = np.asarray(eB['pos'])
            cam = E.Camara(pos + f * CM.mezcla(7.5, 6.4, u) + n * CM.mezcla(2.8, 1.6, u) + [0, 3.8, 0], pos + [0, 3.3, 0], fov=34)
        elif t < 10.0:                                                              # 4. primer plano de Alega (kart A)
            u = (t - 8.0) / 2.0
            pos = np.asarray(eA['pos'])
            cam = E.Camara(pos + f * CM.mezcla(7.5, 6.4, u) - n * CM.mezcla(2.8, 1.6, u) + [0, 3.8, 0], pos + [0, 3.3, 0], fov=34)
        elif t < 12.0:                                                              # 5. persecución que descubre el cine al salir de la curva
            u = (t - 10.0) / 2.0
            su = CM.suave(u)
            pos = mid - f * CM.mezcla(13, 16, u) + [0, CM.mezcla(5.5, 11.0, su), 0] + n * CM.mezcla(2.0, -4.0, su)
            objetivo = (mid + f * 14 + [0, CM.mezcla(2.0, 3.0, u), 0]) * (1 - 0.5 * su) + sit.w(0, 5.0, 0) * (0.5 * su)
            cam = E.Camara(pos, objetivo, fov=CM.mezcla(52, 56, u))
            post['radial'] = 0.012 + 0.03 * CM.suave(max(0, u - 0.7) / 0.3)
        elif t < 16.0:                                                              # 6. dron alto 3/4 trasero
            u = (t - 12.0) / 4.0
            cm = (np.asarray(eA['pos']) + np.asarray(eB['pos'])) / 2
            pos = cm - f * CM.mezcla(22, 14, u) + n * CM.mezcla(16, 12, u) + [0, CM.mezcla(13, 9, u), 0]
            cam = E.Camara(pos, sit.w(2, 3.0, 8) * (0.4) + cm * 0.6 + [0, 1.0, 0], fov=54)
            if t < 12.12: post['flash'] = 0.35 * (1 - (t - 12.0) / 0.12)
            post['radial'] = max(0.0, 0.03 * (1 - (t - 12.0) / 0.6))
        elif t < 19.0:                                                              # 7. contraplano a Pedro
            u = (t - 16.0) / 3.0
            cam = E.Camara(sit.w(0.2, 6.0, CM.mezcla(21.0, 17.0, u)), sit.w(0.0, 5.8, 0), fov=46)
        elif t < 22.0:                                                              # 8. dos planos desde el hueco de la puerta (se ven sus caras)
            if t < 20.9:
                u = (t - 19.0) / 1.9
                cam = E.Camara(sit.w(CM.mezcla(0.6, 0.9, u), 6.0, -2.9), sit.w(2.6, CM.mezcla(5.3, 5.5, u), 4.8), fov=62)
            else:
                u = (t - 20.9) / 1.1
                cam = E.Camara(sit.w(CM.mezcla(-0.6, -0.9, u), 6.0, -2.9), sit.w(-2.6, CM.mezcla(5.3, 5.5, u), 4.8), fov=62)
        elif t < 24.0:                                                              # 9. plano medio de Pedro con dolly-in
            u = (t - 22.0) / 2.0
            cam = E.Camara(sit.w(1.2, 5.8, CM.mezcla(17.5, 15.5, u)), sit.w(1.2, 5.6, 0.8), fov=46)
        elif t < 26.0:                                                              # 10. deslizamiento hacia la esquina de Santos
            u = CM.suavisimo((t - 24.0) / 2.0)
            ox = CM.mezcla(2.0, 17.5, u)
            cam = E.Camara(sit.w(ox, 6.0, CM.mezcla(26.0, 24.0, u)), sit.w(CM.mezcla(0.0, 21.5, u), 6.0, CM.mezcla(0.5, 13.0, u)), fov=CM.mezcla(50, 40, u))
            post['frio'] = CM.suave((t - 24.0) / 1.0)
        elif t < 28.0:                                                              # 11. plano medio frontal de Santos
            cam = E.Camara(sit.w(21.8, 6.3, 13.4 + 17.0), sit.w(21.8, 5.8, 13.4), fov=42)
            post['frio'] = 1.0
        elif t < 32.5:                                                              # 12. dolly-in a su cara
            u = CM.suave((t - 28.0) / 4.5)
            cam = E.Camara(sit.w(21.8, CM.mezcla(6.3, 5.9, u), 13.4 + CM.mezcla(17.0, 10.0, u)), sit.w(21.8, CM.mezcla(5.8, 5.5, u), 13.4), fov=CM.mezcla(42, 30, u))
            post['frio'] = 1.0
            post['vineta'] = 0.30 + 0.30 * u
        else:                                                                       # 13. golpe de zoom
            u = CM.salida((t - 32.5) / 0.35)
            cam = E.Camara(sit.w(21.8, 5.9, 13.4 + 10.0 - 0.8 * u), sit.w(21.8, 5.6, 13.4), fov=CM.mezcla(30, 25, u))
            post['frio'] = 1.0; post['vineta'] = 0.6
            if t < 32.62: post['flash'] = 0.8 * (1 - (t - 32.5) / 0.12)
            post['sac'] = 0.12 * max(0.0, 1 - (t - 32.5) / 0.5)
        return cam, post

    # ------------------------------------------------------------ fotograma
    def cuadro(self, t):
        if t >= T_FOTO:
            return self.foto_final(t)
        cam, post = self.cam(t)
        if post['sac'] > 0: cam.ojo = cam.ojo + CM.temblor(t, post['sac'], 26)
        elif t < 12.0: cam.ojo = cam.ojo + CM.temblor(t, 0.035, 9)
        ins = list(self.mundo.instancias())
        ins += self.escena(t, cam)
        img = self.m.render(ins, cam, self.mundo.entorno)
        img = P.bloom(img, 0.74, post['bloom'], 16 * self.h / 1920 + 2)
        if post['radial'] > 0: img = P.desenfoque_radial(img, post['radial'], 7)
        if post['lineas'] > 0: img = P.lineas_velocidad(img, t, post['lineas'])
        fr = post['frio']
        img = P.gradacion(img, 1.08 - 0.0 * fr, 1.14 - 0.5 * fr, (1.04 - 0.22 * fr, 1.0 - 0.06 * fr, 0.94 + 0.2 * fr), 1.0, 1.0 - 0.14 * fr)
        img = P.vineta(img, post['vineta'])
        img = self.overlays(img, t)
        img = P.destello(img, post['flash'])
        for tc in (2.0, 5.0, 8.0, 10.0, 16.0, 19.0, 21.0, 22.0, 24.0, 26.0):
            d = t - tc
            if 0 <= d < 0.1: img = P.destello(img, 0.22 * (1 - d / 0.1))
        if t < 0.5: img = img * CM.suave(t / 0.5)
        return img

    def escena(self, t, cam):
        sit, g = self.g.sit, self.g
        ins = []
        ins.append(E.Instancia(self.cine, pos=sit.O, rot=sit.R, escala=Q, luz='normal'))
        ins.append(E.Instancia(self.carteles, pos=sit.O, rot=sit.R, escala=Q, luz='normal'))
        ins.append(E.Instancia(self.muro, pos=sit.w(18.0, 0, 6.5), rot=sit.R, escala=Q, luz='normal'))
        ins.append(E.Instancia(self.letrero, pos=sit.O, rot=sit.R, escala=Q, luz='plana', brillo=1.0))
        for quien, kart in (('A', self.kA), ('B', self.kB)):
            e = g.kart(quien, t)
            ins += X.cuerpo_kart(kart, e['pos'], yaw=e['yaw'], giro=e['giro'] if e['v'] > 0.1 or t < T_STOP_B else e['giro'], volante=e['volante'])
        ins += self.personas(t)
        ins += self.billetes(t)
        ins.append(E.Instancia(self.p_humo.malla(t, cam), luz='baked'))
        return ins

    # ------------------------------------------------------------ rótulos
    def overlays(self, img, t):
        h, w = img.shape[:2]; k = h / 1920.0
        # título
        d = t - 0.15
        if 0 <= d < 2.1:
            a = min(1.0, (2.1 - d) / 0.3)
            esc = T.rebote(d, 0.6)
            img = T.componer(img, self.texto('BOLAS', int(230 * k), relleno=((1, 1, .75), (1, .62, .08)), borde=(.35, .04, .04)), w / 2, h * 0.22, a, esc)
            img = T.componer(img, self.texto('NEGRAS', int(250 * k), relleno=((.55, .55, .6), (.08, .08, .12)), borde=(1, 1, .8), grosor=.1), w / 2, h * 0.33, a, T.rebote(d - 0.1, 0.6))
        for (t0, t1, quien, lin) in DIALOGO:
            if not (t0 <= t < t1 + 0.2): continue
            d = t - t0
            fade = min(1.0, (t1 + 0.2 - t) / 0.2) * min(1.0, d / 0.1 + 0.2)
            alto_l = int(96 * k)
            rects = [self.texto(l, alto_l, relleno=COLOR[quien], borde=(.08, .04, .15)) for l in lin]
            n = min(sum(len(l) for l in lin), int(d * 22.0) + 1)
            y0 = h * 0.745 - (len(lin) - 1) * alto_l * 0.55
            wmax = max(r.shape[1] for r in rects)
            ph = int(len(lin) * alto_l * 1.15 + 110 * k)
            y1 = int(y0 - 95 * k); y2 = min(h - 1, y1 + ph + int(30 * k))
            x1 = max(int(w * .03), int(w * 0.5 - max(wmax, 520 * k) / 2 - 36 * k)); x2 = min(int(w * .97), int(w * 0.5 + max(wmax, 520 * k) / 2 + 36 * k))
            ys = np.clip(np.minimum(np.arange(y1, y2) - y1, y2 - 1 - np.arange(y1, y2)) / (26 * k), 0, 1)[:, None]
            xs = np.clip(np.minimum(np.arange(x1, x2) - x1, x2 - 1 - np.arange(x1, x2)) / (40 * k), 0, 1)[None, :]
            msk = (0.45 * fade * ys * xs)[..., None]
            img[y1:y2, x1:x2] = img[y1:y2, x1:x2] * (1 - msk) + np.array([0.02, 0.03, 0.1], np.float32) * msk
            tag = self.texto(NOMBRE[quien], int(62 * k), relleno=((1, 1, 1), COLOR[quien][1]), borde=(.05, .05, .2))
            img = T.componer(img, tag, x1 + tag.shape[1] / 2 + 14 * k, y1 + 4 * k, fade, 1.0, ajustar=0)
            gastado = 0
            for i, (l, r) in enumerate(zip(lin, rects)):
                vis = max(0, min(len(l), n - gastado)); gastado += len(l)
                if vis <= 0: continue
                rr = r[:, :max(1, int(r.shape[1] * vis / len(l)))]
                cx = w / 2 - r.shape[1] / 2 + rr.shape[1] / 2
                img = T.componer(img, rr, cx, y0 + i * alto_l * 1.1, fade, 1.0, ajustar=0)
        d = t - T_BUSCAN
        if 0 <= d < T_FOTO - T_BUSCAN:
            img = T.componer(img, self.texto('¿QUÉ BUSCAN?', int(200 * k), relleno=((1, 1, .8), (1, .75, .1)), borde=(.3, .02, .02)), w / 2, h * 0.3,
                             1.0, T.rebote(d, 0.45))
        return img

    def foto_final(self, t):
        """QUEBUSCA a pantalla completa (la foto entera, con el fondo desenfocado) y zoom lento 100 → 106 %."""
        h, w = self.h, self.w
        u = (t - T_FOTO) / (DUR - T_FOTO)
        z = 1.0 + 0.06 * u + 0.025 * max(0.0, 1 - (t - T_FOTO) / 0.25)
        W0, H0 = self.foto.size
        esc = w / W0 * z
        key = round(esc, 4)
        if key not in self._cache_foto:
            if len(self._cache_foto) > 8: self._cache_foto.clear()
            self._cache_foto[key] = np.asarray(self.foto.resize((int(W0 * esc), int(H0 * esc)), Image.LANCZOS), np.float32) / 255
        a = self._cache_foto[key]
        img = self.foto_fondo.copy()
        fh, fw = a.shape[:2]
        x0, y0 = (w - fw) // 2, (h - fh) // 2
        xa, ya = max(0, x0), max(0, y0); xb, yb = min(w, x0 + fw), min(h, y0 + fh)
        img[ya:yb, xa:xb] = a[ya - y0:yb - y0, xa - x0:xb - x0]
        if t - T_FOTO < 0.08: img = P.destello(img, 0.6 * (1 - (t - T_FOTO) / 0.08))
        return img

    # ------------------------------------------------------------ audio
    @staticmethod
    def audio():
        """Música + voces + efectos. Necesita la pista (trayectorias de los karts), no el render 3D: motor mínimo."""
        import audio_bn
        X.parchear_cielo()
        g = Guion(C.Mundo(E.Motor(64, 64, ss=1), 'mario_course').pista)
        plan = dict(T_STOP=T_STOP_B, T_SALTA_A=T_SALTA_A, T_SALTA_B=T_SALTA_B, T_ENTRAN=T_ENTRAN, T_PAGA_A=T_PAGA_A, T_PAGA_B=T_PAGA_B,
                    T_BUSCAN=T_BUSCAN, T_FOTO=T_FOTO)
        return audio_bn.componer(DIALOGO, g, plan)


CLAVES = (1.0, 3.5, 6.5, 9.0, 11.6, 14.0, 15.4, 17.5, 20.0, 21.5, 23.0, 25.0, 26.4, 29.0, 32.0, 33.2, 35.0)


def claves():
    """Fotogramas clave a tamaño real en proyectos/bolas_negras/previsualizacion/ y su hoja de contactos."""
    import time
    out = os.path.join(AQUI, 'previsualizacion'); os.makedirs(out, exist_ok=True)
    t0 = time.time()
    cine = BolasNegras(BolasNegras.ancho, BolasNegras.alto, BolasNegras.ss)
    for t in CLAVES:
        D.guardar_frame(cine.cuadro(t), os.path.join(out, 'f_%05.2fs.png' % t))
    print('%d fotogramas en %.0fs' % (len(CLAVES), time.time() - t0))
    print(D.hoja(cine, CLAVES, os.path.join(out, 'hoja.png'), escala=0.25))


if __name__ == '__main__':
    if '--claves' in sys.argv: claves()
    else: D.main('video', 'BolasNegras', 'bolas_negras.mp4')
