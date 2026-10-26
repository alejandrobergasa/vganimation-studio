"""Cinemática vertical de demostración: «MARIO KART DS» (Mario Kart DS). 1080x1920, 30 fps, ~38 s.

Guion en video/storyboard_mk.md. Todo sale de la ROM: modelos, texturas, animaciones, circuito, línea de carrera,
fuente y sonido. Efectos propios (partículas, bloom, líneas de velocidad...) en video/mk/.
    python -I video/mk_demo.py --rapido --hoja 16        # previsualizar
    python -I video/mk_demo.py                           # render final -> salida/mk_demo_carrera.mp4"""
import os, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np

import mk
from mk import escena as E, circuito as C, kart as K, fx as FX, post as P, camaras as CM, carrera as CR
from mk import texto as T, audio as A, director as D
import modelos as M

# ------------------------------------------------------------------ guion (tiempos en segundos)
DUR = 38.0
T_TITULO = 0.5
T_CUENTA = (4.6, 5.6, 6.6)          # 3, 2, 1
T_SALIDA = 7.6                      # ¡YA!
T_META = 29.8                       # Mario cruza la línea
T_FIN = 37.0                        # cierre en iris
S0 = 1114.5                         # distancia de la línea de salida en la línea de carrera

# efectos de sonido (SSAR:secuencia) elegidos del catálogo assets_extraidos_mkds/audio/catalogo_audio.csv
# Los ids se eligieron por descriptores acústicos (la SDAT no tiene nombres): confirmar de oído y cambiar aquí si hace falta.
SFX = {'cuenta': (0, 501), 'ya': (0, 251), 'turbo': (0, 546), 'concha': (2, 110), 'explosion': (0, 566),
       'voz': (3, 0), 'derrape': (0, 465)}
MUSICA = {'carrera': 22, 'meta': 9}


def _color_confeti(rng, n):
    paleta = np.array([(1, .2, .2), (.2, .6, 1), (1, .85, .1), (.3, .9, .4), (1, .4, .8), (1, 1, 1)], np.float64)
    return paleta[rng.integers(0, len(paleta), n)]


class DemoMK:
    fps = 30
    duracion = DUR
    ancho, alto = 1080, 1920
    ss = 1.5

    def __init__(self, ancho, alto, ss):
        self.w, self.h = ancho, alto
        self.m = E.Motor(ancho, alto, ss=ss)
        self.mundo = C.Mundo(self.m, 'mario_course')
        self.sp = FX.Sprites(self.m)
        pista = self.mundo.pista
        self.largo = pista.largo
        self.k = {n: K.Kart(self.m, n, 'b') for n in ('mario', 'luigi', 'peach')}
        # modelos de objetos
        self.concha = self.m.malla(M.objeto('Item/it_koura_r.nsbmd'))
        self.bomba = self.m.malla(M.objeto('effect/bombcore/bombcore.nsbmd'))
        self.sombra = self.m.malla(M.objeto('MapObj/obj_shadow.nsbmd'))
        self.estrella_item = self.m.malla(M.objeto('Item/it_star.nsbmd'))
        self.castillo = np.array([74.0, 45.0, 33.0])
        self._carrera()
        self._particulas()
        self._textos = {}

    # ------------------------------------------------------------ simulación
    def _carrera(self):
        p = self.mundo.pista
        def mario(v, tb):
            return CR.Corredor('mario', S0 + 2, -4, v, turbos=tb, lat_fn=lambda t: -3.0 if t < 19 else -5.0)
        # 1ª pasada sin golpe para saber cuándo la concha alcanza a Luigi
        t_lanza = 15.0
        c0 = CR.Carrera(p, [mario(58.5, [(10.0, 1.3, 1.4), (18.4, 1.9, 1.5)]),
                            CR.Corredor('luigi', S0 + 14, 4, 63, tipo='b'),
                            CR.Corredor('peach', S0 - 6, 3, 52.5)], DUR, T_SALIDA)
        sm = c0.estado(0, t_lanza)['s']
        ts = np.arange(t_lanza, t_lanza + 4, 1 / 120.0)
        self.v_concha = 150.0
        sc = sm + 6 + self.v_concha * (ts - t_lanza)
        sl = np.array([c0.estado(1, t)['s'] for t in ts])
        i = int(np.argmax(sc >= sl - 3.0))
        self.t_lanza, self.t_golpe = t_lanza, float(ts[i])
        self.s_lanza = sm + 6
        mario_c = mario(58.5, [(10.0, 1.3, 1.4), (self.t_golpe + 1.0, 1.9, 1.5)])
        mario_c.stop_en = (T_META + 0.3, S0 + self.largo + 38)
        self.car = CR.Carrera(p, [mario_c,
                                  CR.Corredor('luigi', S0 + 14, 4, 63, golpes=[self.t_golpe]),
                                  CR.Corredor('peach', S0 - 6, 3, 52.5)], DUR, T_SALIDA)
        # ajuste fino: Mario debe cruzar la meta en T_META
        t_real = self.car.tiempo_en(0, S0 + self.largo)
        self.t_meta = t_real if t_real else T_META
        self.estados = {}

    def est(self, k, t):
        key = (k, round(t * 120))
        if key not in self.estados:
            if len(self.estados) > 4000: self.estados.clear()
            self.estados[key] = self.car.estado(k, t)
        return self.estados[key]

    # ------------------------------------------------------------ partículas
    def _particulas(self):
        sp, rng = self.sp, np.random.default_rng(7)
        pa = FX.Particulas(self.m, 11)
        self.p_aditivo, self.p_alfa = pa, FX.Particulas(self.m, 12)
        pal = self.p_alfa
        nombres = ['mario', 'luigi', 'peach']
        tt = np.arange(0, DUR, 1 / 60.0)
        for ki, nom in enumerate(nombres):
            est = [self.car.estado(ki, t) for t in tt]
            fw = np.array([CM.vec_yaw(e['yaw'] if e['alto'] == 0 else e['yaw_pista']) for e in est])
            pos = np.array([e['pos'] for e in est])
            der = np.array([e['normal'] for e in est])          # derecha
            vel = np.array([e['v'] for e in est])
            drift = np.array([e['drift'] for e in est]); dtm = np.array([e['drift_t'] for e in est])
            turbo = np.array([e['turbo'] for e in est])
            # chispas de derrape: dos ruedas traseras
            idx = np.nonzero((drift != 0) & (dtm > 0.12))[0]
            if len(idx):
                for lado in (-1, 1):
                    for rep in range(2):
                        base = pos[idx] - fw[idx] * 2.6 + der[idx] * lado * 1.7 + [0, 0.35, 0]
                        n = len(idx)
                        v = (-fw[idx] * rng.uniform(5, 14, (n, 1)) + der[idx] * lado * rng.uniform(1, 7, (n, 1))
                             + rng.normal(size=(n, 3)) * [3, 5, 3] + [0, 7, 0])
                        d_t = dtm[idx]
                        col = np.where((d_t < 0.7)[:, None], np.array([1.0, .95, .75]),
                                       np.where((d_t < 1.5)[:, None], np.array([.35, .65, 1.0]), np.array([1.0, .5, .1])))
                        pa.agregar(tt[idx], rng.uniform(.28, .6, n), base, v, rng.uniform(.22, .42, n), 0.06, col * 1.4, col * .5,
                                   sp.estrella, g=(0, -22.0, 0), a0=1.0, a1=0.0)
            # llamas de turbo
            it = np.nonzero(turbo)[0]
            if len(it):
                n = len(it)
                base = pos[it] - fw[it] * 3.0 + [0, 0.9, 0]
                v = -fw[it] * rng.uniform(14, 26, (n, 1)) + rng.normal(size=(n, 3)) * 1.4
                pa.agregar(tt[it], rng.uniform(.18, .34, n), base, v, rng.uniform(.7, 1.1, n), 0.15,
                           np.array([1.0, .75, .25]) * 1.5, np.array([1.0, .25, .0]), sp.glow, a0=1.0, a1=0.0)
                pa.agregar(tt[it], rng.uniform(.2, .4, n), base, v * 1.3, rng.uniform(.3, .5, n), 0.06,
                           np.array([1.0, 1.0, .8]) * 1.6, np.array([1.0, .5, .1]), sp.estela, a0=1.0, a1=0.0, estela=1.0)
            # polvo bajo las ruedas traseras al avanzar
            idp = np.nonzero(vel > 10)[0][::2]
            if len(idp):
                for lado in (-1, 1):
                    n = len(idp)
                    base = pos[idp] - fw[idp] * 2.4 + der[idp] * lado * 1.6 + [0, 0.2, 0]
                    v = -fw[idp] * rng.uniform(1, 5, (n, 1)) + rng.normal(size=(n, 3)) * [1.5, 0.8, 1.5] + [0, 1.8, 0]
                    pal.agregar(tt[idp], rng.uniform(.7, 1.3, n), base, v, rng.uniform(.4, .8, n), rng.uniform(1.6, 2.6, n),
                                np.array([.85, .8, .7]), np.array([.9, .88, .8]), sp.humo, g=(0, .4, 0), a0=0.22, a1=0.0, arrastre=1.4)
            # humo de motor en la parrilla
            ir = np.nonzero((tt > T_CUENTA[0] - .4) & (tt < T_SALIDA + .5))[0][::2]
            n = len(ir)
            if n:
                base = pos[ir] - fw[ir] * 3.2 + [0, 0.9, 0] + rng.normal(size=(n, 3)) * .2
                v = -fw[ir] * rng.uniform(1.5, 4, (n, 1)) + [0, 1.4, 0] + rng.normal(size=(n, 3)) * .5
                pal.agregar(tt[ir], rng.uniform(.8, 1.4, n), base, v, rng.uniform(.3, .5, n), rng.uniform(1.2, 1.8, n),
                            np.array([.7, .7, .72]), np.array([.85, .85, .9]), sp.humo2, g=(0, 1.0, 0), a0=0.5, a1=0.0, arrastre=1.0)
        # explosión en el impacto de la concha
        eh = self.car.estado(1, self.t_golpe)['pos'] + [0, 2.0, 0]
        tg = self.t_golpe
        pa.rafaga(tg, eh, 90, (0, 6, 0), 26, 0.9, 1.1, (1.0, .8, .3), sp.glow, tam1=0.1, color_fin=(1.0, .25, .0), g=(0, -9, 0))
        pa.rafaga(tg, eh, 60, (0, 5, 0), 34, 0.7, 0.9, (1.0, 1.0, .85), sp.estela, tam1=0.1, color_fin=(1.0, .6, .1), g=(0, -18, 0), estela=1.0)
        pa.rafaga(tg, eh, 24, (0, 2, 0), 12, 0.75, 1.2, (1.0, .9, .5), sp.estrella8, tam1=2.2, color_fin=(1, .4, .1))
        pa.agregar(np.array([tg]), np.array([.55]), eh[None], np.zeros((1, 3)), 1.0, 14.0, np.array([1.0, .85, .5]), np.array([1.0, .3, .0]),
                   sp.anillo, a0=1.0, a1=0.0)
        pal.rafaga(tg, eh, 36, (0, 3, 0), 7, 1.6, 2.2, (.25, .22, .2), sp.humo, tam1=6.0, color_fin=(.1, .1, .1), a0=.8, a1=0, g=(0, 2.2, 0), arrastre=.9)
        # confeti y fuegos artificiales en la meta
        em = self.car.estado(0, self.t_meta)
        n = 420
        pos = em['pos'] + [0, 24, 0] + rng.normal(size=(n, 3)) * [26, 4, 26]
        vel = rng.normal(size=(n, 3)) * [5, 4, 5] + [0, -6, 0]
        col = _color_confeti(rng, n)
        pal.agregar(np.full(n, self.t_meta + 0.1) + rng.uniform(0, 1.6, n), rng.uniform(4, 6.5, n), pos, vel,
                    rng.uniform(.5, .85, n), rng.uniform(.5, .85, n), col, col, sp.confeti, g=(0, -3.2, 0), a0=1.0, a1=1.0,
                    giro=rng.uniform(0, 6.28, n), arrastre=0.6)
        centro = em['pos']
        for j, (dx, dy, dz, col) in enumerate([(-26, 40, 18, (1, .3, .3)), (30, 46, 30, (.3, .6, 1)), (4, 52, 44, (1, .9, .2)),
                                              (-12, 44, 52, (.4, 1, .5)), (26, 38, -6, (1, .5, 1))]):
            tf = self.t_meta + 1.6 + j * 0.55
            c = centro + np.array([dx, dy, dz])
            pa.rafaga(tf, c, 120, (0, 0, 0), 28, 1.5, 1.1, np.array(col) * 1.5, sp.estrella, tam1=0.1, color_fin=np.array(col) * .4, g=(0, -9, 0), arrastre=.8)
            pa.rafaga(tf, c, 40, (0, 0, 0), 14, 1.1, 1.6, (1.4, 1.4, 1.2), sp.glow, tam1=0.1, color_fin=np.array(col), g=(0, -5, 0), arrastre=1.2)

    # ------------------------------------------------------------ utilidades de escena
    def kart_inst(self, nombre, ki, t, **kw):
        e = self.est(ki, t)
        k = self.k[nombre]
        pose, fp = 'drive', None
        if nombre == 'luigi' and self.t_golpe <= t < self.t_golpe + 1.4:
            pose, fp = 'spin', ((t - self.t_golpe) * 20) % 28
        if nombre == 'mario' and t > self.t_meta + 1.6:
            pose, fp = 'win', ((t - self.t_meta - 1.6) * 30) % 99
        ins = k.instancias(e['pos'], yaw=e['yaw'], pitch=e['pitch'], roll=e['roll'], giro=e['giro'], volante=e['volante'],
                           pose=pose, frame_pose=fp, deriva=e['deriva'], **kw)
        # sombra de contacto
        gp = e['centro'] + e['normal'] * e['lat'] + [0, 0.06, 0]
        ins.append(E.Instancia(self.sombra, pos=gp, yaw=e['yaw_pista'], escala=2.6, luz='plana', alfa=0.55, tinte=(0, 0, 0)))
        return ins

    def texto(self, s, alto, **kw):
        k = (s, alto, tuple(sorted(kw.items())))
        if k not in self._textos:
            self._textos[k] = T.render(s, alto, **kw)
        return self._textos[k]

    # ------------------------------------------------------------ planos
    def plano(self, t):
        """-> (cámara, dict de postproceso). Cada tramo del guion define su cámara y sus efectos."""
        e0, e1, e2 = self.est(0, t), self.est(1, t), self.est(2, t)
        sh = np.zeros(3)
        post = {'bloom': 0.32, 'radial': 0.0, 'aber': 1.2, 'lineas': 0.0, 'flash': 0.0, 'tinte': (1.0, 1.0, 1.0)}
        # --- A: sobrevuelo del castillo
        if t < 3.8:
            u = t / 3.8
            cam = E.Camara(CM.Ruta([(0, (-60, 160, 140)), (3.8, (20, 70, 120))], True)(t),
                           CM.Ruta([(0, (70, 40, 20)), (3.8, (74, 42, 30))])(t), fov=CM.mezcla(62, 48, CM.suave(u)))
            post['bloom'] = 0.5
            return cam, post
        # --- B: parrilla de salida (travelling bajo) y cuenta atrás
        if t < T_SALIDA + 0.4:
            f = CM.vec_yaw(90.4); r = np.array([f[2], 0, -f[0]])
            base = e1['pos'] * .4 + e0['pos'] * .35 + e2['pos'] * .25
            u = (t - 3.8) / (T_SALIDA + 0.4 - 3.8)
            ang = CM.mezcla(-52, 10, CM.suave(u))
            # órbita desde delante (los karts miran a +x); empezamos en diagonal frontal y terminamos detrás
            a = math.radians(CM.mezcla(62, 160, CM.suave(u)))
            rad = CM.mezcla(24, 17, CM.suave(u))
            cam = E.Camara(base + [math.sin(a) * rad, CM.mezcla(2.6, 4.6, CM.suave(u)), math.cos(a) * rad],
                           base + [0, 1.8, 0], fov=CM.mezcla(40, 50, CM.suave(u)))
            return cam, post
        # --- C: persecución alta de Mario
        post['aber'] = 1.6
        v_n = min(1.0, e0['v'] / 60.0)
        boost = 1.0 if e0['turbo'] else 0.0
        if t < 11.6:
            cam = CM.persecucion(e0, dist=CM.mezcla(11.5, 14, boost), alto=CM.mezcla(4.6, 5.6, boost), adelante=11, fov=CM.mezcla(66, 82, boost))
            post['radial'] = 0.03 + 0.05 * boost; post['lineas'] = 0.8 * boost
            if T_SALIDA <= t < T_SALIDA + 0.25: post['flash'] = 0.45 * (1 - (t - T_SALIDA) / 0.25)
            return cam, post
        # --- D: travelling lateral bajo
        if t < 15.0:
            k = e0; r = k['normal']
            lado = -1 if int(t * .35) % 2 == 0 else 1
            f = CM.vec_yaw(k['yaw_pista'])
            u = (t - 11.6) / 3.4
            pos = k['pos'] + r * 13.5 * -1 + f * CM.mezcla(5, -6, u) + [0, CM.mezcla(2.0, 3.8, u), 0]
            cam = E.Camara(pos, k['pos'] + f * 2.5 + [0, 1.6, 0], fov=CM.mezcla(44, 54, u), roll=-k['volante'] * 2.5)
            post['radial'] = 0.025
            return cam, post
        # --- E: la concha y el impacto
        if t < self.t_golpe + 2.3:
            ts = max(t, self.t_lanza)
            if t < self.t_golpe + 0.02:
                sc = self.s_lanza + self.v_concha * (t - self.t_lanza)
                m = self.mundo.pista.muestra(sc)
                dist = 12 - 3 * CM.suave((t - self.t_lanza) / 0.8)
                f = CM.vec_yaw(m['yaw'])
                cam = E.Camara(m['pos'] - f * dist + [0, 4.5, 0], e1['pos'] + [0, 1.5, 0], fov=60)
                post['radial'] = 0.06; post['lineas'] = 0.4
            else:
                u = (t - self.t_golpe)
                a = math.radians(210 + 70 * CM.suave(u / 2.3))
                c = e1['pos']
                cam = E.Camara(c + [math.sin(a) * 15, 5.5 - 1.5 * CM.suave(u / 1.5), math.cos(a) * 15], c + [0, 2.4, 0],
                               fov=CM.mezcla(46, 58, CM.suave(u / 2.3)))
                sh = CM.temblor(t, 0.9 * math.exp(-u * 4.0), 26)
                post['flash'] = max(0.0, 0.9 - u * 6) if u < 0.15 else 0.0
                post['aber'] = 3 + 6 * math.exp(-u * 3)
                post['bloom'] = 0.5
            cam.ojo = cam.ojo + sh
            return cam, post
        # --- F: adelantamiento con turbo, vista de dron
        if t < 23.0:
            u = (t - (self.t_golpe + 2.3)) / (23.0 - (self.t_golpe + 2.3))
            f = CM.vec_yaw(e0['yaw_pista']); r = e0['normal']
            cam = E.Camara(e0['pos'] - f * CM.mezcla(10, 12, u) + r * CM.mezcla(-4, 5, u) + [0, CM.mezcla(2.2, 8, CM.suave(u)), 0],
                           e0['pos'] + f * 8 + [0, 1.5, 0], fov=CM.mezcla(70, 62, u), roll=e0['roll'] * .5)
            post['radial'] = 0.07 * boost + 0.02; post['lineas'] = 0.9 * boost
            return cam, post
        # --- G: tramo final, cámara baja frontal y persecución hasta la meta
        if t < self.t_meta - 1.2:
            f = CM.vec_yaw(e0['yaw_pista']); r = e0['normal']
            if t < 26.3:
                cam = E.Camara(e0['pos'] + f * 14 + r * -2.5 + [0, 1.9, 0] , e0['pos'] + [0, 1.9, 0], fov=64, roll=-e0['volante'] * 2)
            else:
                cam = CM.persecucion(e0, dist=11, alto=4.3, adelante=12, lateral=CM.mezcla(0, 3, boost), fov=CM.mezcla(64, 78, boost))
            post['radial'] = 0.04 + .05 * boost; post['lineas'] = 0.7 * boost
            return cam, post
        # --- H: cruce de meta en cámara lenta y victoria
        if t < self.t_meta + 1.8:
            u = (t - (self.t_meta - 1.2)) / 3.0
            f = CM.vec_yaw(e0['yaw_pista']); r = e0['normal']
            cam = E.Camara(e0['pos'] - f * CM.mezcla(10, 6, u) + r * CM.mezcla(5, 3, u) + [0, CM.mezcla(3.4, 1.8, u), 0],
                           e0['pos'] + f * 2 + [0, 1.6, 0], fov=CM.mezcla(60, 46, CM.suave(u)))
            post['flash'] = max(0.0, 0.8 - abs(t - self.t_meta) * 5)
            post['radial'] = .035
            return cam, post
        u = (t - self.t_meta - 1.8) / (T_FIN - self.t_meta - 1.8)
        ang = 160 + 110 * CM.suavisimo(u)
        c = e0['pos']
        cam = CM.orbita(c, CM.mezcla(13, 9, u), CM.mezcla(2.6, 3.2, u), ang + e0['yaw_pista'] * 0, mira_alto=1.9, fov=CM.mezcla(48, 40, u))
        post['bloom'] = 0.42
        return cam, post

    # ------------------------------------------------------------ fotograma
    def cuadro(self, t):
        cam, post = self.plano(t)
        ins = list(self.mundo.instancias())
        for nom, ki in (('mario', 0), ('luigi', 1), ('peach', 2)):
            ins += self.kart_inst(nom, ki, t)
        # concha roja en vuelo
        if self.t_lanza <= t < self.t_golpe:
            s = self.s_lanza + self.v_concha * (t - self.t_lanza)
            m = self.mundo.pista.muestra(s, self.est(1, t)['lat'])
            ins.append(E.Instancia(self.concha, pos=m['pos'] + [0, 1.1, 0], yaw=(t - self.t_lanza) * 900, escala=3.2, luz='plana'))
            ins.append(E.Instancia(self.sp_malla([(m['pos'] + [0, 1.1, 0], 4.5, (1.0, .35, .25), .9)], cam, self.sp.glow), luz='plana'))
        # bola de fuego del impacto (modelo bombcore del juego)
        if self.t_golpe <= t < self.t_golpe + 0.6:
            u = (t - self.t_golpe) / 0.6
            ins.append(E.Instancia(self.bomba, pos=self.est(1, t)['pos'] + [0, 2, 0], escala=0.8 + 3.2 * CM.salida(u), luz='plana',
                                   alfa=max(0.0, 1 - u * u) * 0.9, brillo=1.4, yaw=u * 120))
        # estrellitas girando sobre Luigi mientras gira
        if self.t_golpe + 0.3 <= t < self.t_golpe + 2.0:
            e = self.est(1, t); items = []
            for j in range(5):
                a = (t - self.t_golpe) * 7 + j * 2 * math.pi / 5
                items.append((e['pos'] + [math.cos(a) * 2.4, 4.4 + .3 * math.sin(a * 2), math.sin(a) * 2.4], 1.0, (1.2, 1.0, .3), 1.0))
            ins.append(E.Instancia(self.sp_malla(items, cam, self.sp.estrella), luz='plana'))
        # partículas (alfa y aditivas)
        ins.append(E.Instancia(self.p_alfa.malla(t, cam), luz='plana'))
        ins.append(E.Instancia(self.p_aditivo.malla(t, cam), luz='plana'))
        img = self.m.render(ins, cam, self.mundo.entorno)
        # --- postproceso
        img = P.bloom(img, 0.72, post_v(post, 'bloom'), 18 * self.h / 1920 + 2)
        if post['radial'] > 0: img = P.desenfoque_radial(img, post['radial'], 7)
        img = P.aberracion(img, post['aber'] * self.h / 960)
        if post['lineas'] > 0: img = P.lineas_velocidad(img, t, post['lineas'])
        img = P.gradacion(img, 1.08, 1.14, post['tinte'])
        img = P.vineta(img, 0.34)
        img = self.overlays(img, t)
        img = P.destello(img, post['flash'])
        # transiciones de plano: destello blanco corto en los cortes importantes
        for tc in (3.8, 11.6, 15.0, 23.0):
            d = t - tc
            if 0 <= d < 0.18: img = P.destello(img, 0.55 * (1 - d / 0.18))
        if t < 0.5: img = img * CM.suave(t / 0.5)
        if t > T_FIN - 1.0: img = P.iris(img, CM.suavisimo((t - (T_FIN - 1.0)) / 1.0), (0.5, 0.45))
        return img

    def sp_malla(self, items, cam, mat):
        """Malla de billboards sueltos: items = [(pos, tam, color, alfa)]."""
        ps = FX.Particulas(self.m, 0)
        n = len(items)
        ps.agregar(np.zeros(n), np.full(n, 10.0), np.array([i[0] for i in items]), np.zeros((n, 3)), np.array([i[1] for i in items]),
                   np.array([i[1] for i in items]), np.array([i[2] for i in items]), np.array([i[2] for i in items]), mat,
                   g=(0, 0, 0), a0=np.array([i[3] for i in items]), a1=np.array([i[3] for i in items]), giro=np.zeros(n))
        return ps.malla(0.0, cam)

    # ------------------------------------------------------------ texto en pantalla
    def overlays(self, img, t):
        h, w = img.shape[:2]; k = h / 1920.0
        def pop(t0, dur=3.0, rebote=0.5, salida=0.35):
            d = t - t0
            if d < 0 or d > dur: return 0.0, 0.0
            esc = T.rebote(d, rebote); a = min(1.0, (dur - d) / salida)
            return esc, a
        # título
        esc, a = pop(T_TITULO, 3.0)
        if a > 0:
            img = T.componer(img, self.texto('MARIO KART', int(170 * k)), w / 2, h * 0.26, a, esc)
            img = T.componer(img, self.texto('DS', int(330 * k)), w / 2, h * 0.355, a, esc * (1 if t > T_TITULO + .15 else 0))
            esc2, a2 = pop(T_TITULO + 0.5, 2.5)
            img = T.componer(img, self.texto('¡A LA CARRERA!', int(80 * k), relleno=((1, 1, 1), (.75, .9, 1)), borde=(.05, .1, .35)),
                             w / 2, h * 0.455, a2, esc2)
        # cuenta atrás
        for n, tc in zip(('3', '2', '1'), T_CUENTA):
            d = t - tc
            if 0 <= d < 0.95:
                col = {'3': ((1, .6, .5), (1, .15, .1)), '2': ((1, 1, .6), (1, .7, .0)), '1': ((.7, 1, .6), (.1, .8, .2))}[n]
                img = T.componer(img, self.texto(n, int(420 * k), relleno=col), w / 2, h * 0.38, min(1, (0.95 - d) / .25), T.rebote(d, 0.35) * (1.1 - 0.1 * d))
        d = t - T_SALIDA
        if 0 <= d < 1.5:
            img = T.componer(img, self.texto('¡YA!', int(380 * k), relleno=((1, 1, .8), (1, .55, .05))), w / 2, h * 0.38,
                             min(1, (1.5 - d) / .4), T.rebote(d, 0.4) * (1 + .15 * d))
        # posición: 1.º / 2.º ... (sólo durante la carrera)
        if T_SALIDA + 0.6 < t < self.t_meta + 0.2:
            ss = [self.est(i, t)['s'] for i in range(3)]
            pos = 1 + sum(1 for x in ss[1:] if x > ss[0] + 0.0)
            img = T.componer(img, self.texto(str(pos), int(210 * k), relleno=((1, 1, .8), (1, .8, .1) if pos == 1 else (.8, .9, 1))),
                             w * 0.12, h * 0.085, 1.0, 1.0)
            img = T.componer(img, self.texto('/3', int(80 * k), relleno=((1, 1, 1), (.8, .85, 1))), w * 0.235, h * 0.10, 1.0, 1.0)
        # meta y victoria
        d = t - self.t_meta
        if 0 <= d < 2.2:
            img = T.componer(img, self.texto('¡META!', int(300 * k), relleno=((1, 1, .9), (.3, .85, 1)), borde=(.05, .1, .4)), w / 2, h * 0.30,
                             min(1, (2.2 - d) / .4), T.rebote(d, 0.45))
        d = t - (self.t_meta + 2.2)
        if 0 <= d < (T_FIN - self.t_meta - 2.2 - 0.6):
            img = T.componer(img, self.texto('¡VICTORIA!', int(190 * k), relleno=((1, 1, .7), (1, .6, .0)), borde=(.35, .05, .05)), w / 2, h * 0.22,
                             1.0, T.rebote(d, 0.55) * (1 + 0.02 * math.sin(d * 5)))
            img = T.componer(img, self.texto('MARIO GANA LA CARRERA', int(78 * k), relleno=((1, 1, 1), (.75, .9, 1)), borde=(.05, .1, .35)),
                             w / 2, h * 0.30, min(1, d / .5), T.rebote(d - .3, 0.4))
        return img

    # ------------------------------------------------------------ audio
    @classmethod
    def tiempos(cls):
        """Instantes de los eventos (sin cargar karts ni texturas de karts): salen de la misma simulación que el vídeo."""
        o = object.__new__(cls)
        o.m = E.Motor(16, 16, ss=1); o.mundo = C.Mundo(o.m, 'mario_course'); o.largo = o.mundo.pista.largo
        o._carrera()
        return o

    @staticmethod
    def audio():
        o = DemoMK.tiempos(); car = o.car
        mz = A.Mezcla(DUR)
        # música de carrera con fundidos; se agacha en los eventos fuertes
        mus = A.normalizar(A.bgm(MUSICA['carrera'], 40), 0.9)
        mz.musica(mus, 0.0, 0.5, entrada=1.2, salida=1.2, hasta=o.t_meta + 0.2,
                  curva=lambda t: np.interp(t, [0, T_CUENTA[0] - .2, T_SALIDA - .3, T_SALIDA + .4], [.55, .55, .45, 1.0]))
        fan = A.normalizar(A.bgm(MUSICA['meta'], 14), 0.9)
        mz.musica(fan, o.t_meta + 0.1, 0.55, salida=1.5, hasta=o.t_meta + 11)
        def sfx(clave, t, g=0.8, pan=0.0, pitch=1.0, dur=None, norm=0.9):
            a = A.recortar(A.sfx_id(*SFX[clave], 4))
            if dur: a = A.fundido(a[:int(dur * A.FS)], 0.0, min(0.15, dur / 2))
            a = A.normalizar(a, norm)
            mz.poner(A.pitch(a, pitch) if pitch != 1.0 else a, t, g, pan)
        for n, tc in enumerate(T_CUENTA):
            sfx('cuenta', tc, 0.8, pitch=1.0)
        sfx('ya', T_SALIDA, 0.9, pitch=1.5)
        sfx('turbo', 10.0, 0.7)
        sfx('concha', o.t_lanza, 0.7)
        sfx('explosion', o.t_golpe, 1.0, norm=0.95)
        sfx('turbo', o.t_golpe + 1.0, 0.7)
        sfx('voz', o.t_meta - 0.1, 0.9)
        # derrapes de Mario: un chirrido corto al empezar cada derrape largo
        der = car.tab[0]['der']; dt = car.dt
        ini = [i * dt for i in range(1, len(der)) if der[i] != 0 and der[i - 1] == 0]
        for ti in ini:
            if T_SALIDA < ti < o.t_meta - 0.5:
                sfx('derrape', ti, 0.35, dur=0.7, pan=-0.2 * der[int(ti / dt) + 1])
        return mz


def post_v(post, k):
    return post[k]


if __name__ == '__main__':
    D.main('mk_demo', 'DemoMK', 'mk_demo_carrera.mp4')
