"""Cinemática vertical «ABALOS KART» (Mario Kart DS), 1080x1920, 30 fps. Guion en video/storyboard_abalos.md.

Todo procede de la ROM de Mario Kart DS (modelos, texturas, animaciones, circuito, fuente y sonido) salvo la cara de Ábalos,
que es la textura que se genera a partir de abalos.jpg (video/mk/extra.py). Los efectos (partículas, bloom, líneas de velocidad...) son de código propio.
    python -I video/mk_abalos.py --rapido --hoja 16        # previsualizar
    python -I video/mk_abalos.py                           # render final -> salida/mk_abalos_kart.mp4"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import mk
from mk import escena as E, circuito as C, kart as K, fx as FX, post as P, camaras as CM
from mk import texto as T, audio as A, director as D, extra as X
import modelos as M
from mk_abalos_plan import *            # tiempos del guion y utilidades
from mk_abalos_escena import EscenaMixin
from mk_abalos_plano import PlanoMixin

from mk_abalos_escena import SEP, ESC


class Guion:
    """Trayectorias y eventos (sin cargar texturas): sirve a la imagen y al audio."""
    def __init__(self, mundo):
        self.mundo = mundo
        pista, suelo = mundo.pista, mundo.suelo
        self.pista, self.suelo = pista, suelo
        # ---- Ábalos
        vH = [(0, 56), (T_FRENA, 56), (T_PARA, 0), (T_ARRANCA, 0), (24.0, 44), (30, 46), (32.4, 38), (T_H_PARA2, 0),
              (T_HUYE - 0.1, 0), (T_HUYE + 1.2, 80), (90, 80)]
        # tráfico: (tipo, t de cruce, lateral del coche, velocidad, lado por el que pasa Ábalos)
        self.trafico = [('taxi', 54.3, 1.5, 24.0, +1), ('camion', 56.0, -1.5, 20.0, -1), ('bus', 57.9, 2.0, 22.0, -1),
                        ('taxi', 59.6, -2.0, 18.0, +1), ('camion', 61.0, 1.0, 20.0, -1)]
        self.peatones = [(55.1, +1), (58.9, -1), (60.4, +1)]            # (t de cruce, sentido)
        latH = [(0, -3.0), (2.5, 2.0), (5.0, -2.5), (T_FRENA, 0.5), (T_PARA, 2.0), (T_ARRANCA, 2.0), (22.0, 3.5), (T_H_PARA2, 3.5),
                (T_HUYE - 0.1, 3.5), (T_HUYE + 0.8, 5.5)]
        # lateral de Ábalos en cada cruce: esquiva a 4,6 u del coche
        claves = []
        for _, tp, lc, vc, lado in self.trafico:
            claves += [(tp - 0.9, None), (tp, float(np.clip(lc + lado * 4.8, -6.2, 6.2))), (tp + 0.8, None)]
        for tp, sen in self.peatones:
            claves += [(tp, None)]
        self.cl_obs = claves
        self.H = Camino(pista, vH, latH, dur=DUR + 1)
        self.H.anclar(T_PARA, 1090.0)
        # claves de lateral dependientes del tráfico (se resuelven ahora que se conoce s(t))
        lat_extra = [(tp, float(np.clip(lc + lado * 4.8, -6.2, 6.2))) for _, tp, lc, vc, lado in self.trafico]
        lat_ped = []
        for tp, sen in self.peatones:
            lat_ped.append((tp, 0.0))
        latH2 = sorted([k for k in latH if k[0] < T_HUYE + 0.8] + lat_extra + [(T_HUYE + 1.5, 0.0), (53.0, 0.0), (T_PIERDE - 0.8, 1.5)],
                       key=lambda k: k[0])
        # el lateral entre cruces vuelve al centro
        ex = []
        for _, tp, lc, vc, lado in self.trafico:
            ex += [(tp - 1.1, 0.0), (tp + 1.0, 0.0)]
        latH2 = sorted(latH2 + [k for k in ex if all(abs(k[0] - q[0]) > 0.45 for q in lat_extra)], key=lambda k: k[0])
        # derrape automático de Ábalos al esquivar
        self.H = Camino(pista, vH, latH2, dur=DUR + 1, suav_lat=0.28)
        self.H.anclar(T_PARA, 1090.0)
        # ---- Policía
        sH_para2 = float(self.H.s(T_H_PARA2))
        self.s_poli_para = sH_para2 + 9.5
        vP = [(0, 76), (T_POLI_PARA - 1.9, 76), (T_POLI_PARA, 0), (T_POLI_ARRANCA - 0.1, 0), (T_POLI_ARRANCA + 1.2, 125), (T_PIERDE, 125),
              (T_PIERDE + 0.9, 0), (120, 0)]
        latP = [(0, -4.0), (T_POLI_PARA - 3.0, -4.0), (T_POLI_PARA, -4.8), (T_POLI_ARRANCA, -4.8), (T_POLI_ARRANCA + 1.5, -2.0), (90, -2.0)]
        self.P0 = Camino(pista, vP, latP, dur=DUR + 1, deriva_claves=[(0, 0), (T_POLI_PARA - 1.5, 0), (T_POLI_PARA - 0.2, 14), (T_POLI_ARRANCA, 14),
                                                                      (T_POLI_ARRANCA + 1, 0), (T_PIERDE + 0.1, 0), (T_PIERDE + 1.0, -52 * (1 if self.H.estado(T_PIERDE)['curv'] > 0 else -1)), (200, -52 * (1 if self.H.estado(T_PIERDE)['curv'] > 0 else -1))])
        self.P0.anclar(T_POLI_PARA, self.s_poli_para)
        self._poli_tabla()
        # ---- tramo final: choque
        eL = self.H.estado(T_PIERDE)
        cur = eL['curv']
        self.exterior = np.array(eL['normal']) * (1 if cur > 0 else -1)
        self.e_loss = eL
        self.choque = Choque(suelo, pista, eL, T_PIERDE, self.exterior)
        self.dist_arbol = 15.5
        self.t_hit = self.choque.instante_impacto(self.dist_arbol)
        self.pos_hit, self.yaw_hit, self.v_hit = self.choque.estado(self.t_hit)
        u = self.pos_hit - np.array(eL['centro'])
        u[1] = 0
        self.dir_hit = u / (np.linalg.norm(u) + 1e-9)
        self.pos_arbol = self.pos_hit + self.dir_hit * 3.4
        # altura del árbol sobre el suelo
        ha = suelo.altura(self.pos_arbol[0], self.pos_arbol[2], self.pos_hit[1] + 4)
        self.pos_arbol[1] = self.pos_hit[1] if np.isnan(ha) else ha
        # cuerpos despedidos: Ábalos (izq) y Peach (der)
        R = E.rotacion(self.yaw_hit, 0, 0)
        izqv = izq(self.yaw_hit)
        fw = vec_yaw(self.yaw_hit)
        self.cuerpos = {}
        for quien, lado, sp, semilla in (('abalos', +1, 1.0, 3), ('peach', -1, 1.15, 8)):
            p0 = self.pos_hit + [0, 3.2, 0] + izqv * lado * 1.1
            vel = self.dir_hit * 15.0 + fw * 10.0 + izqv * lado * 5.0 + [0, 21.0 * sp, 0]
            rv = np.array([620.0 * lado, 180.0, -480.0 * lado]) * (0.9 if quien == 'abalos' else 1.1)
            self.cuerpos[quien] = Cuerpo(suelo, self.t_hit + 0.02, p0, vel, rv, 9.0, semilla=semilla)
        self.t_reposo = max(c.t_reposo for c in self.cuerpos.values())
        # ruedas sueltas
        self.ruedas = []
        for k, (lado, delante) in enumerate(((+1, True), (-1, True))):
            vel = self.dir_hit * (18 + 6 * k) + fw * 10 + izq(self.yaw_hit) * lado * 9 + [0, 15 + 4 * k, 0]
            self.ruedas.append(Cuerpo(suelo, self.t_hit + 0.02, self.pos_hit + [0, 1.4, 0] + izq(self.yaw_hit) * lado * 1.6, vel,
                                      [500 * lado, 80, 700], 9.0, rest=0.55, fric=9.0, semilla=20 + k, radio=0.8))
        # parada de la policía junto a la escena
        self.eventos = {'t_hit': self.t_hit, 't_reposo': self.t_reposo}

    # la policía no puede adelantar a Ábalos durante la persecución: integra con tope
    def _poli_tabla(self):
        P0, H = self.P0, self.H
        dt = P0.dt; n = len(P0.t)
        s = np.zeros(n); s[0] = P0.s(0)
        lag = 0.9
        for i in range(1, n):
            t = P0.t[i]
            s[i] = s[i - 1] + P0.v[i - 1] * dt
            if T_POLI_ARRANCA + 0.5 < t < T_PIERDE + 0.4:
                tope = float(H.s(t)) - 15.0
                if s[i] > tope: s[i] = max(s[i - 1], tope)
        lat = P0.lat.copy()
        for i, t in enumerate(P0.t):
            w = CM.suave((t - 55.0) / 1.5) * (1.0 if t < T_PIERDE + 0.3 else max(0.0, 1.0 - (t - T_PIERDE - 0.3) / 0.6))
            if w > 0: lat[i] = lat[i] * (1 - w) + float(np.interp(t - 0.35, H.t, H.lat)) * 0.85 * w
        self.P = CaminoTab(self.pista, P0, s, lat)

    def trafico_estado(self, i, t):
        kind, tp, lc, vc, lado = self.trafico[i]
        s = float(self.H.s(tp)) + vc * (t - tp)
        m = self.pista.muestra(s, lc)
        return {'pos': m['pos'], 'yaw': m['yaw'], 'pitch': -m['pitch'], 'kind': kind, 's': s}

    def peaton_estado(self, i, t):
        tp, sen = self.peatones[i]
        s = float(self.H.s(tp)) + 1.0
        latH = float(np.interp(tp, self.H.t, self.H.lat))
        ancla = np.clip(latH + 3.9 * (-sen) * -1, -7.0, 7.0) if False else latH + sen * 3.9
        lat = ancla - sen * 8.5 * (t - tp)             # cruza acercándose a la trayectoria de Ábalos
        m = self.pista.muestra(s, lat)
        return {'pos': m['pos'], 'yaw': m['yaw'] + (90 if -sen > 0 else -90), 'v': 8.5, 'lat': lat, 'sen': sen, 'dist': abs(lat - latH)}


class CaminoTab(Camino):
    """Camino con distancia tabulada a mano (la policía)."""
    def __init__(self, pista, base, s, lat):
        self.pista, self.dt, self.dur, self.t = pista, base.dt, base.dur, base.t
        self.I = s; self.s0 = 0.0
        self.v = np.gradient(s, base.dt)
        self.lat, self.der, self.alt = lat, base.der, base.alt
        self.dlat = np.gradient(lat, base.dt)


def _color(c): return np.array(c, np.float64)


# ===================================================================== imagen

class AbalosKart(EscenaMixin, PlanoMixin):
    fps = 30
    duracion = DUR
    ancho, alto = 1080, 1920
    ss = 1.5

    def __init__(self, ancho, alto, ss):
        self.w, self.h = ancho, alto
        self.m = E.Motor(ancho, alto, ss=ss)
        X.parchear_cielo()
        self.mundo = C.Mundo(self.m, 'mario_course')
        self.sp = FX.Sprites(self.m)
        self.g = Guion(self.mundo)
        self._modelos()
        self._particulas()
        self._textos = {}

    # ------------------------------------------------------------ recursos
    def _modelos(self):
        m = self.m
        self.kH = K.Kart(m, 'waluigi', 'c')
        self.kP = K.Kart(m, 'donkey', 'b')
        self.abalos = X.Pasajero(m, 'mario', abalos=True)
        self.peach = X.Pasajero(m, 'peach')
        self.dk_s = X.Pasajero(m, 'donkey')
        self.daisy = X.Peaton(m, 'daisy', piel=(0.98, 0.82, 0.68), zapato=(0.95, 0.65, 0.1))
        self.dk_p = X.Peaton(m, 'donkey', piel=(0.45, 0.25, 0.12), zapato=(0.3, 0.15, 0.07), largo=1.9, escala=4.0)
        self.toad = X.Peaton(m, 'kinopio', piel=(0.98, 0.84, 0.7), zapato=(0.45, 0.25, 0.1), largo=1.1)
        rc = M.Circuito('ridge_course')
        self.taxi = m.malla(rc.objeto('car_a')); self.bus = m.malla(rc.objeto('bus_a')); self.camion = m.malla(rc.objeto('truck_a'))
        self.sombra = m.malla(M.objeto('MapObj/obj_shadow.nsbmd'))
        self.arbol = m.malla(M.Circuito('mario_course').objeto('MarioTree3'))
        self.bomba = m.malla(M.objeto('effect/bombcore/bombcore.nsbmd'))
        # materiales sólidos y mallas propias
        s = m.solido
        self.mat_blanco = s((0.96, 0.94, 0.86)); self.mat_rojo = s((0.62, 0.02, 0.03)); self.mat_gris = s((0.2, 0.2, 0.22))
        self.mat_naranja = s((1.0, 0.45, 0.05)); self.mat_azul = s((0.1, 0.25, 1.0)); self.mat_rojoL = s((1.0, 0.05, 0.05))
        self.mat_piel = s((0.43, 0.24, 0.12)); self.mat_negro = s((0.04, 0.04, 0.05)); self.mat_marca = s((0.05, 0.05, 0.06))
        self.cigarro = E.Malla.une([X.caja(self.mat_blanco, 0.03, 0.03, 0.16, centro=(0, 0, 0.08)),
                                    X.caja(self.mat_naranja, 0.032, 0.032, 0.035, centro=(0, 0, 0.17))])
        self.hueso = E.Malla.une([X.caja(self.mat_blanco, 0.24, 0.24, 1.9), X.caja(self.mat_blanco, 0.5, 0.4, 0.4, centro=(0.12, 0, 1.0)),
                                  X.caja(self.mat_blanco, 0.5, 0.4, 0.4, centro=(-0.12, 0, 1.0)), X.caja(self.mat_blanco, 0.5, 0.4, 0.4, centro=(0.12, 0, -1.0)),
                                  X.caja(self.mat_blanco, 0.5, 0.4, 0.4, centro=(-0.12, 0, -1.0))])
        self.charco = X.disco(self.mat_rojo, 1.0, 16)
        self.barra_luz = {c: E.Malla.une([X.caja(self.mat_negro, 2.6, 0.25, 0.7, centro=(0, 0, 0)),
                                          X.caja(mat, 1.0, 0.45, 0.6, centro=(-0.7, 0.3, 0)), X.caja(self.mat_gris, 1.0, 0.45, 0.6, centro=(0.7, 0.3, 0))])
                          for c, mat in (('rojo', self.mat_rojoL), ('azul', self.mat_azul))}
        self.brazo = X.caja(self.mat_piel, 0.55, 0.55, 1.0, centro=(0, 0, 0.5))
        self.poste = X.caja(self.mat_negro, 0.3, 2.2, 0.3)
        self._aparato()
        self.marca = None

    def _aparato(self):
        """Alcoholímetro: cuerpo gris, boquilla y pantalla con texturas de estados (carga 0..20, resultado A/B)."""
        m = self.m
        W, H = 256, 160
        def pantalla(frac, modo):
            img = np.zeros((H, W, 4), np.float32); img[..., 3] = 1
            img[..., :3] = (0.05, 0.12, 0.06) if modo != 'res' else (0.55, 0.02, 0.03)
            if modo == 'res2': img[..., :3] = (0.95, 0.85, 0.1)
            if modo == 'idle':
                t1 = T.render('SOPLE', 40, relleno=((.6, 1, .6), (.2, .8, .3)), borde=(0.0, .15, .0)); img = self._pegar(img, t1, W / 2, H / 2)
            elif modo == 'carga':
                t1 = T.render('ANALIZANDO', 24, relleno=((.7, 1, .7), (.3, .9, .4)), borde=(0.0, .15, .0)); img = self._pegar(img, t1, W / 2, 34)
                img[104:132, 20:W - 20, :3] = (0.02, 0.06, 0.03)
                n = int((W - 44) * frac)
                img[108:128, 22:22 + n, :3] = (0.35, 1.0, 0.4)
                t2 = T.render('%d%%' % int(frac * 100), 28, relleno=((.8, 1, .8), (.4, 1, .5)), borde=(0.0, .15, .0)); img = self._pegar(img, t2, W / 2, 80)
            else:
                col_b = ((1, 1, 1), (1, .85, .8)) if modo == 'res' else ((.2, 0, 0), (.45, 0, 0))
                bd = (.25, 0, 0) if modo == 'res' else (.9, .6, .0)
                t1 = T.render('BORRACHO 100%', 22, relleno=col_b, borde=bd); t2 = T.render('- MULTÓN', 26, relleno=col_b, borde=bd)
                img = self._pegar(img, t1, W / 2, 55); img = self._pegar(img, t2, W / 2, 105)
            return (np.clip(img, 0, 1) * 255).astype(np.uint8)
        self.pant = {}
        for k in range(0, 21):
            self.pant[('carga', k)] = m.material(pantalla(k / 20.0, 'carga'), 0)
        self.pant[('idle', 0)] = m.material(pantalla(0, 'idle'), 0)
        self.pant[('res', 0)] = m.material(pantalla(0, 'res'), 0)
        self.pant[('res2', 0)] = m.material(pantalla(0, 'res2'), 0)
        cuerpo = E.Malla.une([X.caja(self.mat_gris, 1.7, 3.0, 0.8), X.caja(self.mat_negro, 0.6, 0.6, 1.4, centro=(0, -1.35, 0.9)),
                              X.caja(self.mat_rojoL, 0.25, 0.25, 0.1, centro=(0.6, 1.25, 0.44))])
        self.aparato = cuerpo
        self.aparato_pant = {k: X.caja(mat, 1.4, 0.95, 0.04, centro=(0, 0.35, -0.42), tam_tex=(256, 160),
                                       uv_caras={1: (0, 0, 256, 160)}) for k, mat in self.pant.items()}

    @staticmethod
    def _pegar(img, rgba, cx, cy):
        h, w = rgba.shape[:2]
        x0, y0 = int(cx - w / 2), int(cy - h / 2)
        x0c, y0c = max(0, x0), max(0, y0)
        x1, y1 = min(img.shape[1], x0 + w), min(img.shape[0], y0 + h)
        if x1 > x0c and y1 > y0c:
            s = rgba[y0c - y0:y1 - y0, x0c - x0:x1 - x0]
            a = s[..., 3:4]
            img[y0c:y1, x0c:x1, :3] = img[y0c:y1, x0c:x1, :3] * (1 - a) + s[..., :3] * a
        return img

    # ------------------------------------------------------------ partículas (sin estado: cualquier t se evalúa solo)
    def _particulas(self):
        sp, g = self.sp, self.g
        rng = np.random.default_rng(11)
        self.p_ad, self.p_al = FX.Particulas(self.m, 21), FX.Particulas(self.m, 22)
        pa, pal = self.p_ad, self.p_al
        # humo del cigarro (de la punta a la brisa)
        ts = np.arange(0.2, T_ARRANCA + 18, 1 / 22.0)
        pts = []
        for t in ts:
            if T_H_PARA2 < t < T_HUYE - 0.5 and not (T_H_PARA2 + .3 < t < T_H_PARA2 + 14): pass
            e = g.H.estado(t)
            pts.append(self.punta_cigarro(e))
        pts = np.array(pts)
        n = len(ts)
        v = rng.normal(size=(n, 3)) * [0.5, 0.4, 0.5] + [0, 1.6, 0]
        pal.agregar(ts, rng.uniform(.9, 1.6, n), pts, v, rng.uniform(.12, .2, n), rng.uniform(.9, 1.6, n), np.array([.85, .85, .88]), np.array([.7, .7, .75]),
                    sp.humo, g=(0, .3, 0), a0=.55, a1=0.0, arrastre=1.0)
        # humo de frenada y polvo de arranque de Ábalos
        def humo_ruedas(t0, t1, tasa, e_fn, col=(.9, .88, .85), tam=(.8, 2.8), vida=(.8, 1.6), vs=1.0):
            N = int((t1 - t0) * tasa)
            tt = t0 + (np.arange(N) + rng.random(N)) / tasa
            es = [e_fn(t) for t in tt]
            fw = np.array([vec_yaw(e['yaw'] + e['deriva']) for e in es]); iz = np.array([izq(e['yaw'] + e['deriva']) for e in es]); pos = np.array([e['pos'] for e in es])
            for lado in (-1, 1):
                base = pos - fw * 2.6 + iz * lado * 1.9 + [0, .3, 0] + rng.normal(size=(N, 3)) * .25
                vel = -fw * rng.uniform(1, 5, (N, 1)) * vs + rng.normal(size=(N, 3)) * [2.5, 1.2, 2.5] + [0, 2.2, 0]
                pal.agregar(tt, rng.uniform(*vida, N), base, vel, rng.uniform(.5, 1, N) * tam[0], rng.uniform(1, 1.6, N) * tam[1], np.array(col), np.array(col) * .95, sp.humo2,
                            g=(0, .5, 0), a0=.6, a1=0.0, arrastre=1.1)
        humo_ruedas(T_FRENA, T_PARA + 0.5, 60, g.H.estado, vs=2.0)
        humo_ruedas(T_ARRANCA, T_ARRANCA + 2.0, 30, g.H.estado, col=(.8, .75, .65))
        humo_ruedas(T_H_PARA2 - 1.4, T_H_PARA2 + 0.4, 50, g.H.estado, vs=2.0)
        humo_ruedas(T_POLI_PARA - 1.3, T_POLI_PARA + 0.5, 50, g.P.estado, vs=2.0)
        humo_ruedas(T_HUYE - 0.2, T_HUYE + 2.0, 70, g.H.estado, col=(.95, .9, .8), tam=(1.0, 3.5), vs=2.5)
        # polvo continuo de Ábalos y de la policía en la persecución
        for fn in (g.H.estado, g.P.estado):
            humo_ruedas(T_HUYE + 1.0, T_PIERDE, 6, fn, col=(.8, .78, .7), tam=(.5, 1.8), vida=(.5, 1.0))
        # chispas y llamas de turbo en la huida
        for t0, t1 in ((T_HUYE, T_HUYE + 2.4),):
            N = int((t1 - t0) * 120)
            tt = t0 + (np.arange(N) + rng.random(N)) / 120
            es = [g.H.estado(t) for t in tt]
            fw = np.array([vec_yaw(e['yaw']) for e in es]); pos = np.array([e['pos'] for e in es])
            base = pos - fw * 3.2 + [0, 1.0, 0]
            vv = -fw * rng.uniform(14, 28, (N, 1)) + rng.normal(size=(N, 3)) * 1.6
            pa.agregar(tt, rng.uniform(.16, .3, N), base, vv, rng.uniform(.7, 1.1, N), 0.15, np.array([1.0, .75, .25]) * 1.5, np.array([1.0, .25, 0.0]), sp.glow, a0=1.0, a1=0.0)
        # polvo de Daisy corriendo y de las ruedas del choque
        dd = self.daisy_estado
        N = 160
        tt = 15.4 + (np.arange(N) + rng.random(N)) / 45.0
        es = [dd(t) for t in tt]
        pos = np.array([e['pos'] for e in es])
        pal.agregar(tt, rng.uniform(.6, 1.1, N), pos + [0, .2, 0], rng.normal(size=(N, 3)) * [1.2, .6, 1.2] + [0, 1.5, 0], rng.uniform(.4, .8, N), rng.uniform(1.2, 2.0, N),
                    np.array([.85, .82, .7]), np.array([.9, .88, .8]), sp.humo, g=(0, .3, 0), a0=.4, a1=0, arrastre=1.2)
        # luces de la sirena: destellos aditivos a lo largo de la policía
        # (se dibujan como billboards en cuadro(), porque dependen de la fase del parpadeo)
        # ---------------- choque
        th = g.t_hit
        ph = g.pos_hit
        ch = g.choque
        # chispas y humo mientras derrapa fuera de la pista
        N = int((th - T_PIERDE) * 90)
        tt = T_PIERDE + (np.arange(N) + rng.random(N)) / 90.0
        pp = np.array([ch.estado(t)[0] for t in tt])
        pal.agregar(tt, rng.uniform(.9, 1.6, N), pp + [0, .4, 0], rng.normal(size=(N, 3)) * [3, 1, 3] + [0, 2, 0], rng.uniform(.9, 1.5, N), rng.uniform(2.2, 4.0, N),
                    np.array([.72, .66, .5]), np.array([.8, .76, .65]), sp.humo, g=(0, .5, 0), a0=.7, a1=0.0, arrastre=1.0)
        pa.agregar(tt, rng.uniform(.25, .5, N), pp + [0, .5, 0], rng.normal(size=(N, 3)) * [6, 4, 6] + [0, 5, 0], rng.uniform(.2, .35, N), .05,
                   np.array([1, .8, .4]) * 1.5, np.array([1, .3, .0]), sp.estrella, g=(0, -30, 0))
        # impacto: hojas, polvo, fogonazo, estrellas
        pa.rafaga(th, ph + [0, 2.5, 0], 90, (0, 6, 0), 22, 0.8, 1.0, (1.0, .8, .3), sp.glow, tam1=0.1, color_fin=(1.0, .25, .0), g=(0, -9, 0))
        pa.rafaga(th, ph + [0, 2.5, 0], 60, (0, 5, 0), 30, 0.7, 0.8, (1.0, 1.0, .85), sp.estela, tam1=0.1, color_fin=(1.0, .6, .1), g=(0, -18, 0), estela=1.0)
        pa.rafaga(th, ph + [0, 2.5, 0], 20, (0, 2, 0), 10, 0.7, 1.1, (1.0, .9, .5), sp.estrella8, tam1=2.2, color_fin=(1, .4, .1))
        pa.agregar(np.array([th]), np.array([.55]), (ph + [0, 2.5, 0])[None], np.zeros((1, 3)), 1.0, 16.0, np.array([1.0, .85, .5]), np.array([1.0, .3, .0]), sp.anillo, a0=1.0, a1=0.0)
        pal.rafaga(th, ph + [0, 2.5, 0], 60, (0, 4, 0), 14, 2.5, 1.4, (.62, .55, .4), sp.humo, tam1=7.0, color_fin=(.3, .28, .25), a0=.8, a1=0, g=(0, 2.0, 0), arrastre=.8)
        hojas = np.array([(.25, .7, .15), (.4, .85, .2), (.15, .55, .1)])
        nn = 70
        col = hojas[rng.integers(0, 3, nn)]
        pal.agregar(np.full(nn, th + .02) + rng.uniform(0, .25, nn), rng.uniform(1.4, 2.4, nn), np.array(g.pos_arbol) + [0, 9, 0] + rng.normal(size=(nn, 3)) * [3, 3, 3],
                    rng.normal(size=(nn, 3)) * [5, 4, 5] + [0, 2, 0], rng.uniform(.5, .9, nn), rng.uniform(.5, .9, nn), col, col * .8, sp.confeti, g=(0, -9, 0), a0=1, a1=1,
                    giro=rng.uniform(0, 6.28, nn), arrastre=.6)
        # sangre en el choque y en cada rebote; llamas y humo negro del coche
        sangre = np.array([.75, .02, .04])
        for cuerpo, k in ((g.cuerpos['abalos'], 0), (g.cuerpos['peach'], 1)):
            evs = [cuerpo.t0] + list(cuerpo.t0 + np.array(cuerpo.golpes))
            for te in evs:
                e = cuerpo.estado(te)
                nn = 55 if te != cuerpo.t0 else 30
                pal.rafaga(te, e['pos'] + [0, 1, 0], nn, (0, 6, 0), 16, 0.9, 0.17, sangre, sp.disco, tam1=0.05, color_fin=sangre * .7, g=(0, -34, 0), a0=1, a1=0.85)
        # rastro de sangre durante el vuelo y el rodar
        for cuerpo in g.cuerpos.values():
            tt = np.arange(cuerpo.t0 + .15, cuerpo.t_reposo, 1 / 40.0)
            pp = np.array([cuerpo.estado(t)['pos'] for t in tt])
            nn = len(tt)
            pal.agregar(tt, rng.uniform(.4, .8, nn), pp + [0, 1, 0], rng.normal(size=(nn, 3)) * [2, 1.5, 2], rng.uniform(.12, .22, nn), .05, sangre, sangre * .7, sp.disco,
                        g=(0, -26, 0), a0=1, a1=.8)
        # fuego del coche destrozado
        t_f = th + 0.25
        wp = ph + g.dir_hit * -1.0 + [0, 1.3, 0]
        N = int((DUR - t_f) * 55)
        tt = t_f + (np.arange(N) + rng.random(N)) / 55.0
        base = wp + rng.normal(size=(N, 3)) * [1.4, .3, 1.4]
        pa.agregar(tt, rng.uniform(.5, .9, N), base, rng.normal(size=(N, 3)) * [.8, .5, .8] + [0, 6, 0], rng.uniform(1.4, 2.4, N), 0.2,
                   np.array([1.0, .7, .2]) * 1.4, np.array([1.0, .15, 0.0]), sp.glow, a0=1.0, a1=0.0)
        pa.agregar(tt, rng.uniform(.4, .7, N), base + [0, .5, 0], rng.normal(size=(N, 3)) * [1, .6, 1] + [0, 9, 0], rng.uniform(.7, 1.2, N), .1,
                   np.array([1.2, 1.0, .5]), np.array([1.0, .3, 0.0]), sp.estela, a0=1.0, a1=0.0, estela=0.45)
        M2 = int((DUR - t_f) * 18)
        t2 = t_f + 0.2 + (np.arange(M2) + rng.random(M2)) / 18.0
        pal.agregar(t2, rng.uniform(2.2, 3.6, M2), wp + [0, 2, 0] + rng.normal(size=(M2, 3)) * [1, .5, 1], rng.normal(size=(M2, 3)) * [1.2, .6, 1.2] + [0, 5.5, 0],
                    rng.uniform(1.4, 2.2, M2), rng.uniform(4.5, 7.0, M2), np.array([.12, .11, .1]), np.array([.2, .19, .18]), sp.humo, g=(0, .4, 0), a0=.85, a1=0.0, arrastre=.4)
        # cuerpos: polvo al deslizar
        for cuerpo in g.cuerpos.values():
            for te in cuerpo.golpes[:3]:
                e = cuerpo.estado(cuerpo.t0 + te - cuerpo.t0)
                pal.rafaga(te + 0.0, e['pos'] + [0, .3, 0], 14, (0, 3, 0), 6, 1.0, 1.2, (.7, .65, .5), sp.humo, tam1=3.2, color_fin=(.8, .75, .6), a0=.7, a1=0)
        # estrellitas sobre el cuerpo de Ábalos tendido (aturdido), y huesos que asoman
        self.huesos = []
        for k, quien in enumerate(('abalos', 'peach')):
            cuerpo = g.cuerpos[quien]
            r = np.random.default_rng(40 + k)
            e = cuerpo.estado(cuerpo.t_reposo + 1)
            for j in range(3):
                off = np.array([r.uniform(-1.6, 1.6), 0.15, r.uniform(-1.6, 1.6)])
                rot = E.rotacion(r.uniform(0, 360), r.uniform(-30, 30), r.uniform(-30, 30))
                self.huesos.append((quien, off, rot, 0.55 + 0.1 * j))

    # ------------------------------------------------------------ texto
    def texto(self, s, alto, **kw):
        k = (s, alto, tuple(sorted(kw.items())))
        if k not in self._textos:
            self._textos[k] = T.render(s, alto, **kw)
        return self._textos[k]

    def sp_malla(self, items, cam, mat):
        ps = FX.Particulas(self.m, 0)
        n = len(items)
        ps.agregar(np.zeros(n), np.full(n, 10.0), np.array([i[0] for i in items]), np.zeros((n, 3)), np.array([i[1] for i in items]),
                   np.array([i[1] for i in items]), np.array([i[2] for i in items]), np.array([i[2] for i in items]), mat,
                   g=(0, 0, 0), a0=np.array([i[3] for i in items]), a1=np.array([i[3] for i in items]), giro=np.zeros(n))
        return ps.malla(0.0, cam)


if __name__ == '__main__':
    D.main('mk_abalos', 'AbalosKart', 'mk_abalos_kart.mp4')
