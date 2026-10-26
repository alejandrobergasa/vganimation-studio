"""Dirección de cámara, postproceso, rótulos y banda sonora de «ABALOS KART»."""
import math
import numpy as np

from mk import escena as E, camaras as CM, post as P, texto as T, fx as FX, audio as A
from mk_abalos_plan import *
from mk_abalos_escena import SEP, ESC

UP = np.array([0.0, 1.0, 0.0])
COLOR = {'ABALOS': ((1.0, 1.0, 0.8), (1.0, 0.78, 0.2)), 'PEACH': ((1.0, 0.88, 0.96), (1.0, 0.42, 0.72)),
         'DAISY': ((1.0, 1.0, 0.72), (1.0, 0.72, 0.1)), 'DK': ((1.0, 0.85, 0.6), (0.8, 0.42, 0.1))}
NOMBRE = {'ABALOS': 'ÁBALOS', 'PEACH': 'PEACH', 'DAISY': 'DAISY', 'DK': 'DONKEY KONG'}


def partir(txt, maxc=19):
    pal, lin, act = txt.split(), [], ''
    for p in pal:
        if act and len(act) + 1 + len(p) > maxc:
            lin.append(act); act = p
        else:
            act = (act + ' ' + p).strip()
    if act: lin.append(act)
    return lin


class PlanoMixin:
    # ------------------------------------------------------------ estados para cámara
    def eH(self, t):
        g = self.g
        if t < T_PIERDE: return g.H.estado(t)
        if t < g.t_hit:
            pos, yaw, v = g.choque.estado(t)
            return {'pos': pos, 'yaw': yaw, 'pitch': 0.0, 'roll': 0.0, 'volante': 0.0, 'deriva': 0.0, 'v': v}
        return {'pos': g.pos_hit, 'yaw': g.yaw_hit, 'pitch': 0.0, 'roll': 0.0, 'volante': 0.0, 'deriva': 0.0, 'v': 0.0}

    def medio_cabezas(self, e):
        return (self.cabeza(e, 'abalos') + self.cabeza(e, 'peach')) / 2

    def cam_orbita_kart(self, e, ang, dist, alto, mira, fov, roll=0.0):
        pos = np.asarray(e['pos']) + vec_yaw(e['yaw'] + ang) * dist + [0, alto, 0]
        return E.Camara(pos, mira, fov=fov, roll=roll)

    # ------------------------------------------------------------ cámara y postproceso por plano
    def plano(self, t):
        g = self.g
        post = {'bloom': 0.32, 'radial': 0.0, 'aber': 1.2, 'lineas': 0.0, 'flash': 0.0, 'tinte': (1.0, 1.0, 1.0), 'sac': 0.0}
        e = self.eH(t)
        fw, lf = vec_yaw(e['yaw']), izq(e['yaw'])
        mid = self.medio_cabezas(e)
        ha = self.cabeza(e, 'abalos')
        hp = self.cabeza(e, 'peach')

        # ---- 1. presentación en marcha
        if t < 2.6:
            u = t / 2.6
            cam = self.cam_orbita_kart(e, CM.mezcla(32, -12, CM.suave(u)), CM.mezcla(13.5, 10.5, u), CM.mezcla(2.4, 3.8, u), mid + [0, -0.4, 0], 46)
            post['radial'] = 0.05; post['lineas'] = 0.55; post['bloom'] = 0.4
            return cam, post
        if t < 5.0:
            u = (t - 2.6) / 2.4
            cam = self.cam_orbita_kart(e, CM.mezcla(-44, -22, CM.suave(u)), CM.mezcla(10.5, 9.2, u), 4.8, mid + [0, -0.1, 0], 38)
            post['radial'] = 0.03; post['lineas'] = 0.3
            return cam, post
        # ---- Daisy aparece; el kart frena
        d = self.daisy_estado(t)
        if t < 8.4:
            fwr = vec_yaw(g.pista.muestra(g.H.s(T_PARA), 0)['yaw'])
            dd = self.daisy_estado(7.0)
            rd = np.array([fwr[2], 0, -fwr[0]])
            pos = dd['pos'] - fwr * 7.0 + rd * 3.8 + [0, 2.3, 0]
            if t < 6.9:
                tgt = d['pos'] + [0, 3.2, 0]
            else:
                u = CM.suave((t - 6.9) / 1.0)
                tgt = (d['pos'] + [0, 3.4, 0]) * (1 - u) + (e['pos'] + [0, 2.8, 0]) * u
            cam = E.Camara(pos, tgt, fov=42)
            if t > T_FRENA: post['aber'] = 2.5 + 4.0 * math.exp(-(t - T_FRENA) * 1.2)
            if 5.0 <= t < 5.18: post['flash'] = 0.5 * (1 - (t - 5.0) / 0.18)
            return cam, post
        # ---- discusión con Daisy
        if t < 10.8:
            u = (t - 8.4) / 2.4
            cam = self.cam_orbita_kart(e, CM.mezcla(52, 30, CM.suave(u)), CM.mezcla(8.0, 6.6, u), 4.6, ha + [0, 0.15, 0], 30)
            return cam, post
        if t < 12.45:
            dd = d
            f = vec_yaw(dd['yaw'])
            cam = E.Camara(dd['pos'] + f * 6.8 + [0, 4.7, 0], dd['pos'] + [0, 4.2, 0], fov=28)
            post['bloom'] = 0.4
            return cam, post
        if t < 15.4:
            u = (t - 12.45) / 2.95
            cam = E.Camara(e['pos'] + lf * CM.mezcla(13.0, 10.5, u) + fw * CM.mezcla(-3.0, 2.5, u) + [0, 4.6, 0], ha + [0, 0.15, 0], fov=34)
            return cam, post
        if t < 16.6:
            pos = e['pos'] - fw * 5.5 + [0, 3.6, 0] + lf * (-1.5)
            cam = E.Camara(pos, d['pos'] + [0, 3.0, 0], fov=48)
            post['radial'] = 0.015
            return cam, post
        if t < 19.6:
            u = (t - 16.6) / 3.0
            cam = self.cam_orbita_kart(e, CM.mezcla(-30, -14, CM.suave(u)), CM.mezcla(10.4, 9.0, u), 4.2, mid + [0, 0.0, 0], 36)
            return cam, post
        # ---- sigue conduciendo
        if t < 22.0:
            cam = CM.persecucion(e, dist=11.5, alto=3.4, adelante=9, fov=62)
            post['radial'] = 0.04; post['lineas'] = 0.4
            return cam, post
        if t < T_SIRENA:
            u = (t - 22.0) / (T_SIRENA - 22.0)
            cam = self.cam_orbita_kart(e, CM.mezcla(-22, 18, CM.suave(u)), 8.6, CM.mezcla(2.2, 3.4, u), mid + [0, 0.0, 0], 42)
            post['radial'] = 0.04; post['lineas'] = 0.35
            return cam, post
        # ---- policía
        ep = g.P.estado(t)
        if t < T_POLI_PASA:
            cam = E.Camara(e['pos'] + fw * 12.0 + lf * (-2.0) + [0, 2.8, 0], e['pos'] - fw * 6 + [0, 3.4, 0], fov=50)
            post['radial'] = 0.04; post['lineas'] = 0.3
            return cam, post
        if t < 32.2:
            s0 = g.H.s(31.0)
            m = g.pista.muestra(s0, 12.5)
            cam = E.Camara(m['pos'] + [0, 2.0, 0], ep['pos'] * 0.6 + e['pos'] * 0.4 + [0, 2.6, 0], fov=42)
            post['radial'] = 0.02
            return cam, post
        if t < T_DK_BAJA:
            cam = CM.persecucion(e, dist=13.0, alto=6.4, adelante=18, fov=60)
            return cam, post
        dk = self.dk_estado(t)
        if t < 35.0:
            pie, yawp = self.dk_pie()
            cam = E.Camara(ep['pos'] + vec_yaw(ep['yaw']) * 9.0 + izq(ep['yaw']) * 7.0 + [0, 2.4, 0], dk['pos'] + [0, 3.0, 0], fov=48)
            return cam, post
        pie, yawp = self.dk_pie()
        boca_ = self.boca_abalos(g.H.estado(T_H_PARA2))
        if t < 38.8:
            u = (t - 35.0) / 3.8
            pos = pie - lf * 9.0 + fw * CM.mezcla(7.0, 5.0, u) + [0, 2.8, 0]
            cam = E.Camara(pos, pie + [0, 4.0, 0], fov=36)
            return cam, post
        if t < T_SOPLA:
            u = (t - 38.8) / 2.2
            pos = pie + lf * 8.0 + fw * CM.mezcla(-5.0, -3.0, u) + [0, 6.5, 0]
            cam = E.Camara(pos, boca_ + [0, 1.0, 0], fov=44)
            return cam, post
        eS = g.H.estado(T_H_PARA2)
        boca = self.boca_abalos(eS)
        if t < T_APARATO:
            u = (t - T_SOPLA) / (T_APARATO - T_SOPLA)
            f2 = vec_yaw(eS['yaw']); l2 = izq(eS['yaw'])
            pos = boca + f2 * CM.mezcla(5.6, 4.4, u) + l2 * CM.mezcla(2.4, 1.4, u) + [0, 0.5, 0]
            cam = E.Camara(pos, boca + [0, 0.0, 0] + l2 * 0.4, fov=26)
            if u > 0.25: post['sac'] = 0.12
            return cam, post
        dev = self.pos_aparato(t) or self.pos_aparato(T_APARATO)
        if t < T_RESULTADO + 1.8:
            u = (t - T_APARATO) / (T_RESULTADO + 1.8 - T_APARATO)
            pos = dev['pos'] - dev['dir'] * CM.mezcla(5.2, 4.0, CM.suave(u)) + [0, 0.35, 0]
            cam = E.Camara(pos, dev['pos'] + [0, 0.3, 0], fov=34)
            post['bloom'] = 0.55
            if t >= T_RESULTADO:
                dd = t - T_RESULTADO
                post['sac'] = 0.25 * math.exp(-dd * 2.0)
                post['tinte'] = (1.0, 1.0 - 0.25 * (int(dd * 5) % 2 == 0), 1.0 - 0.25 * (int(dd * 5) % 2 == 0))
                post['flash'] = 0.35 * max(0, 1 - dd * 7)
            return cam, post
        if t < 50.7:
            u = (t - T_RESULTADO - 1.8) / 1.9
            pos = pie - lf * 9.0 + fw * CM.mezcla(5.0, 7.0, u) + [0, 2.6, 0]
            dk2 = self.dk_estado(t)
            cam = E.Camara(pos, dk2['pos'] + [0, 4.0, 0], fov=36)
            return cam, post
        if t < T_HUYE:
            u = (t - 50.7) / 0.7
            cam = self.cam_orbita_kart(e, CM.mezcla(36, 24, u), CM.mezcla(5.0, 4.1, u), 4.5, ha + [0, 0.1, 0], 26)
            post['sac'] = 0.2
            return cam, post
        if t < T_HUYE + 1.6:
            s0 = g.H.s(T_HUYE + 0.5)
            m = g.pista.muestra(s0 + 4, 11.0)
            cam = E.Camara(m['pos'] + [0, 1.6, 0], e['pos'] + [0, 2.0, 0], fov=44)
            post['radial'] = 0.07; post['lineas'] = 0.9
            if t < T_HUYE + 0.2: post['flash'] = 0.5 * (1 - (t - T_HUYE) / 0.2)
            return cam, post
        if t < 54.4:
            cam = CM.persecucion(ep, dist=10.5, alto=3.2, adelante=14, fov=68)
            post['radial'] = 0.04; post['lineas'] = 0.4
            return cam, post
        # ---- persecución
        if t < T_PIERDE:
            cortes = [54.4, 56.1, 57.8, 59.3, 60.9, T_PIERDE]
            k = max(i for i, c in enumerate(cortes) if t >= c) if t < cortes[-1] else len(cortes) - 2
            u = (t - cortes[k]) / (cortes[k + 1] - cortes[k])
            post['radial'] = 0.06; post['lineas'] = 0.75; post['bloom'] = 0.34
            if k == 0:
                cam = self.cam_orbita_kart(e, CM.mezcla(10, -14, u), 10.5, CM.mezcla(2.2, 3.0, u), mid + [0, 0, 0], 52)
            elif k == 1:
                cam = CM.persecucion(e, dist=12.0, alto=6.2, adelante=18, lateral=CM.mezcla(2.5, -2.5, u), fov=66)
            elif k == 2:
                cam = E.Camara(e['pos'] + lf * 9.5 + fw * CM.mezcla(5.0, -4.0, u) + [0, 2.0, 0], mid + [0, 0, 0], fov=50)
            elif k == 3:
                cam = E.Camara(e['pos'] + fw * 7.0 + lf * CM.mezcla(2.5, -3.0, u) + [0, 1.1, 0], e['pos'] + [0, 1.6, 0], fov=64)
            elif k == 4:
                cam = CM.persecucion(e, dist=CM.mezcla(14, 10, u), alto=CM.mezcla(5.5, 3.2, u), adelante=14, lateral=3.0, fov=70)
            else:
                cam = self.cam_orbita_kart(e, CM.mezcla(-35, -8, u), 8.8, 2.8, mid + [0, 0, 0], 55)
            post['aber'] = 2.2
            return cam, post
        # ---- pérdida de control, árbol, vuelo y rodar
        th = g.t_hit
        if t < th + 0.12:
            ar = g.pos_arbol
            cam = E.Camara(ar - g.dir_hit * 0.0 + izq(g.yaw_hit) * -10.0 + vec_yaw(g.yaw_hit) * 6.0 + [0, 2.4, 0], e['pos'] + [0, 2.4, 0], fov=48)
            post['radial'] = 0.05; post['lineas'] = 0.5
            if t > th - 0.1: post['flash'] = 0.4
            return cam, post
        cp = g.cuerpos['abalos'].estado(t)
        if t < th + 2.1:
            u = (t - th) / 2.1
            c0 = cp['pos']
            cam = E.Camara(c0 + vec_yaw(g.yaw_hit + 160 + 60 * u) * CM.mezcla(11, 16, u) + [0, CM.mezcla(3.5, 6, u), 0], c0 + [0, 1.5, 0], fov=54)
            d_ = t - th
            post['sac'] = 0.7 * math.exp(-d_ * 4.0)
            if d_ < 0.18: post['flash'] = 0.85 * (1 - d_ / 0.18)
            post['aber'] = 3 + 7 * math.exp(-d_ * 3)
            post['bloom'] = 0.5
            return cam, post
        if t < th + 5.0:
            u = (t - th - 2.1) / 2.9
            centro = (g.cuerpos['abalos'].estado(g.t_reposo)['pos'] + g.cuerpos['peach'].estado(g.t_reposo)['pos']) / 2
            cam = E.Camara(centro + vec_yaw(g.yaw_hit + 120 - 40 * u) * CM.mezcla(17, 11, CM.suave(u)) + [0, CM.mezcla(7, 3.2, CM.suave(u)), 0],
                           centro + [0, 1.0, 0], fov=48)
            return cam, post
        return self.plano_final(t, post)

    def plano_final(self, t, post):
        g = self.g
        ep = g.P.estado(t)
        W = np.array(g.pos_hit)
        cb = [g.cuerpos[k].estado(g.t_reposo)['pos'] for k in ('abalos', 'peach')]
        M = (W + cb[0] + cb[1]) / 3
        if t < 67.2:
            u = (t - (g.t_hit + 5.0)) / (67.2 - g.t_hit - 5.0)
            cam = E.Camara(M + g.dir_hit * CM.mezcla(34, 28, u) + [0, CM.mezcla(10, 8, u), 0], M + [0, 2.0, 0], fov=48)
            post['bloom'] = 0.45
            return cam, post
        if t < 69.0:
            u = (t - 67.2) / 1.8
            cam = E.Camara(W - g.dir_hit * CM.mezcla(26, 20, u) + vec_yaw(g.yaw_hit) * -6 + [0, 4.0, 0], W + [0, 3.6, 0], fov=44)
            post['bloom'] = 0.5
            return cam, post
        if t < 72.2:
            cabeza = self.asiento(self.kP, ep, 0.0, 0.72, 0.55)
            u = (t - 69.0) / 3.2
            pos = cabeza + vec_yaw(ep['yaw'] - 22) * CM.mezcla(12.5, 10.5, u) + [0, 0.8, 0]
            cam = E.Camara(pos, cabeza + [0, 0.1, 0], fov=34)
            post['bloom'] = 0.45
            return cam, post
        u = (t - 72.2) / (DUR - 72.2)
        ang = math.degrees(math.atan2(-g.dir_hit[0], -g.dir_hit[2])) + 35 - 70 * u
        cam = E.Camara(W * 0.6 + M * 0.4 + vec_yaw(ang) * CM.mezcla(30, 42, u) + [0, CM.mezcla(10, 19, u), 0], W * 0.6 + M * 0.4 + [0, 2.5, 0], fov=46)
        post['bloom'] = 0.5
        return cam, post

    # ------------------------------------------------------------ fotograma
    def cuadro(self, t):
        cam, post = self.plano(t)
        g = self.g
        if post['sac'] > 0:
            cam.ojo = cam.ojo + CM.temblor(t, post['sac'], 26)
        elif t > T_HUYE and t < T_PIERDE:
            cam.ojo = cam.ojo + CM.temblor(t, 0.07, 18)
        ins = list(self.mundo.instancias())
        ins += self.escena(t, cam)
        ins.append(E.Instancia(self.p_al.malla(t, cam), luz='baked'))
        ins.append(E.Instancia(self.p_ad.malla(t, cam), luz='baked'))
        # destellos de la sirena
        if T_SIRENA - 2.0 <= t:
            ep = g.P.estado(t)
            fase = int(t * 6) % 2
            R = self.R_kart(ep)
            c = np.asarray(ep['pos']) + R @ np.array([0.7 * (1 if fase == 0 else -1), 5.5, -3.0])
            col = (1.6, 0.15, 0.1) if fase == 0 else (0.15, 0.4, 1.8)
            ins.append(E.Instancia(self.sp_malla([(c, 4.2, col, 0.95)], cam, self.sp.glow), luz='plana'))
            # el escenario se tiñe levemente cerca de la policía
            dist = np.linalg.norm(np.asarray(ep['pos']) - np.asarray(cam.ojo))
            if dist < 60 and (T_SIRENA <= t < T_PIERDE + 4):
                k = 0.12 * (1 - dist / 60)
                post['tinte'] = (1 + (k * 2 if fase == 0 else -k), 1 - k * .8, 1 + (k * 2 if fase else -k))
        # fogonazo del encendedor/colilla al principio: nada. Fuego del coche: luz cálida sobre el entorno
        img = self.m.render(ins, cam, self.mundo.entorno)
        img = P.bloom(img, 0.72, post['bloom'], 18 * self.h / 1920 + 2)
        if post['radial'] > 0: img = P.desenfoque_radial(img, post['radial'], 7)
        img = P.aberracion(img, post['aber'] * self.h / 960)
        if post['lineas'] > 0: img = P.lineas_velocidad(img, t, post['lineas'])
        tinte = post['tinte']
        if t > g.t_hit + 0.3 and t < DUR:
            tinte = (tinte[0] * 1.03, tinte[1] * .98, tinte[2] * .94)
        img = P.gradacion(img, 1.08, 1.14, tinte)
        img = P.vineta(img, 0.34)
        img = self.overlays(img, t)
        img = P.destello(img, post['flash'])
        # cortes con destello
        for tc in (2.6, 5.0, 8.4, 25.0):
            d = t - tc
            if 0 <= d < 0.12: img = P.destello(img, 0.35 * (1 - d / 0.12))
        if t < 0.5: img = img * CM.suave(t / 0.5)
        if t > DUR - 1.2: img = P.iris(img, CM.suavisimo((t - (DUR - 1.2)) / 1.2), (0.5, 0.45))
        return img

    # ------------------------------------------------------------ rótulos
    def overlays(self, img, t):
        h, w = img.shape[:2]; k = h / 1920.0
        def pop(t0, dur, rebote=0.5, salida=0.35):
            d = t - t0
            if d < 0 or d > dur: return 0.0, 0.0
            return T.rebote(d, rebote), min(1.0, (dur - d) / salida)
        esc, a = pop(0.35, 2.9)
        if a > 0:
            img = T.componer(img, self.texto('ABALOS', int(200 * k), relleno=((1, 1, .85), (1, .62, .1)), borde=(.35, .04, .04)), w / 2, h * 0.24, a, esc)
            img = T.componer(img, self.texto('KART', int(300 * k), relleno=((.75, 1, .8), (.15, .8, .3)), borde=(.02, .2, .05)), w / 2, h * 0.34,
                             a, esc * (1 if t > 0.5 else 0))
        # diálogos
        for (t0, t1, quien, txt) in DIALOGO:
            if not (t0 <= t < t1 + 0.35): continue
            d = t - t0
            fade = min(1.0, (t1 + 0.35 - t) / 0.3)
            lin = partir(txt)
            alto_l = int(76 * k)
            rects = [self.texto(l, alto_l, relleno=COLOR[quien], borde=(.08, .04, .15)) for l in lin]
            cps = 18.0
            total = sum(len(l) for l in lin)
            n = min(total, int(d * cps) + 1)
            y0 = h * 0.795 - (len(lin) - 1) * alto_l * 0.55
            # panel
            wmax = max(r.shape[1] for r in rects)
            ph = int(len(lin) * alto_l * 1.15 + 120 * k)
            y1 = int(y0 - 100 * k); y2 = min(h - 1, y1 + ph + int(30 * k))
            x1 = int(w * 0.5 - max(wmax, 560 * k) / 2 - 36 * k); x2 = int(w * 0.5 + max(wmax, 560 * k) / 2 + 36 * k)
            x1, x2 = max(int(w * .03), x1), min(int(w * .97), x2)
            ys = np.clip(np.minimum(np.arange(y1, y2) - y1, y2 - 1 - np.arange(y1, y2)) / (26 * k), 0, 1)[:, None]
            xs = np.clip(np.minimum(np.arange(x1, x2) - x1, x2 - 1 - np.arange(x1, x2)) / (40 * k), 0, 1)[None, :]
            m = (0.34 * fade * ys * xs)[..., None]
            img[y1:y2, x1:x2] = img[y1:y2, x1:x2] * (1 - m) + np.array([0.02, 0.03, 0.1], np.float32) * m
            tag = self.texto(NOMBRE[quien], int(52 * k), relleno=((1, 1, 1), COLOR[quien][1]), borde=(.05, .05, .2))
            img = T.componer(img, tag, x1 + tag.shape[1] / 2 + 14 * k, y1 + 4 * k, fade, 1.0, anclaje=(0.5, 0.5))
            gastado = 0
            for i, (l, r) in enumerate(zip(lin, rects)):
                vis = max(0, min(len(l), n - gastado)); gastado += len(l)
                if vis <= 0: continue
                frac = vis / len(l)
                rr = r[:, :max(1, int(r.shape[1] * frac))]
                cx = w / 2 - r.shape[1] / 2 + rr.shape[1] / 2
                img = T.componer(img, rr, cx, y0 + i * alto_l * 1.1, fade, 1.0, ajustar=0)
        # BORRACHO: golpe de rótulo grande al llegar el resultado
        d = t - T_RESULTADO
        if 0 <= d < 1.9:
            img = T.componer(img, self.texto('¡MULTÓN!', int(210 * k), relleno=((1, .9, .9), (1, .1, .1)), borde=(.25, 0, 0)), w / 2, h * 0.2, min(1, (1.9 - d) / .3),
                             T.rebote(d, 0.4))
        # FIN
        d = t - 73.4
        if d > 0:
            img = T.componer(img, self.texto('FIN', int(330 * k), relleno=((1, 1, .85), (1, .5, .05)), borde=(.35, .04, .04)), w / 2, h * 0.3, min(1, (DUR - 1.0 - t) / .5), T.rebote(d, .6))
        return img

    # ------------------------------------------------------------ audio (sin cargar modelos)
    @classmethod
    def tiempos(cls):
        from mk import escena as E2, circuito as C2
        from mk_abalos import Guion
        m = E2.Motor(16, 16, ss=1)
        mundo = C2.Mundo(m, 'mario_course')
        return Guion(mundo)

    @staticmethod
    def audio():
        import mk_abalos_audio as AU
        return AU.componer(PlanoMixin.tiempos())
