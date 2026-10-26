"""Montaje de la escena de «ABALOS KART»: instancias de karts, personajes, tráfico, aparato y restos del choque (por instante t)."""
import math
import numpy as np

from mk import escena as E, camaras as CM, extra as X
from mk_abalos_plan import *

SEP = 0.21
ESC = 5.0


class EscenaMixin:
    # ------------------------------------------------------------ geometría de apoyo
    def R_kart(self, e):
        return E.rotacion(e['yaw'] + e.get('deriva', 0.0), e['pitch'], e['roll'])

    def asiento(self, kart, e, dx, dy=0.0, dz=0.0):
        """Posición mundo de un punto (dx, dy, dz en unidades del modelo) respecto al asiento del kart."""
        a, z = kart.asiento
        return np.asarray(e['pos']) + self.R_kart(e) @ (np.array([dx, a + dy, z + dz]) * ESC)

    def cabeza(self, e, quien='abalos', kart=None):
        dx = SEP if quien == 'abalos' else -SEP
        return self.asiento(kart or self.kH, e, dx, 0.5, 0.05)

    def boca_abalos(self, e):
        return self.asiento(self.kH, e, SEP, 0.30, 0.19)

    def punta_cigarro(self, e):
        return self.asiento(self.kH, e, SEP - 0.045, 0.30, 0.38)

    def dk_pie(self):
        g = self.g
        e = g.H.estado(T_H_PARA2)
        p = np.array(e['pos']) + izq(e['yaw']) * 7.0 + vec_yaw(e['yaw']) * -0.6
        p[1] = self._suelo(p, e['pos'][1])
        return p, e['yaw'] - 90.0

    def _suelo(self, pos, hint):
        h = self.g.suelo.altura(pos[0], pos[2], hint + 3.0)
        return hint if np.isnan(h) else h

    def daisy_estado(self, t):
        g = self.g
        base = g.pista.muestra(g.H.s(T_PARA) + 10.5, 0.4)
        pos = np.array(base['pos'])
        yaw = base['yaw'] + 180
        corre = max(0.0, t - 15.4)
        if corre > 0:
            fw = vec_yaw(base['yaw'])
            dirv = np.array(base['normal']) * 0.86 + fw * 0.5
            dirv /= np.linalg.norm(dirv)
            u = min(corre, 6.0)
            pos = pos + dirv * 15.0 * u
            yaw = math.degrees(math.atan2(dirv[0], dirv[2]))
            pos[1] = self._suelo(pos, pos[1])
        return {'pos': pos, 'yaw': yaw, 'corre': corre > 0.0, 'fase': corre * 15.5}

    def dk_estado(self, t):
        """Donkey Kong: en el kart, saltando, a pie junto a Ábalos y de vuelta al kart."""
        g = self.g
        ep = g.P.estado(t)
        asiento = self.asiento(self.kP, ep, 0.0)
        if t < T_DK_BAJA or t >= T_DK_SUBE + 0.7:
            return {'modo': 'kart', 'pos': asiento}
        pie, yawp = self.dk_pie()
        ep0 = g.P.estado(T_DK_BAJA)
        sale = self.asiento(self.kP, ep0, 0.0)
        suelo0 = sale + izq(ep0['yaw']) * 2.6
        suelo0[1] = self._suelo(suelo0, ep0['pos'][1])
        if t < T_DK_BAJA + 0.5:
            u = (t - T_DK_BAJA) / 0.5
            p = sale * (1 - u) + suelo0 * u
            p[1] += 6.0 * 4 * u * (1 - u)
            return {'modo': 'salto', 'pos': p, 'yaw': ep0['yaw'] + 90, 'u': u}
        if t < T_HUYE + 0.4:
            u = min(1.0, (t - T_DK_BAJA - 0.5) / 1.3)
            p = suelo0 * (1 - CM.suave(u)) + pie * CM.suave(u)
            d = pie - suelo0
            yaw = math.degrees(math.atan2(d[0], d[2])) if u < 1 else yawp
            return {'modo': 'pie', 'pos': p, 'yaw': yaw, 'fase': (t - T_DK_BAJA) * 10.0, 'camina': u < 1}
        u = min(1.0, (t - T_HUYE - 0.4) / (T_DK_SUBE + 0.7 - T_HUYE - 0.4))
        d = asiento - pie
        yaw = math.degrees(math.atan2(d[0], d[2]))
        if u < 0.7:
            p = pie + d * CM.suave(u / 0.7) * 0.9
            p[1] = pie[1]
            return {'modo': 'pie', 'pos': p, 'yaw': yaw, 'fase': (t - T_HUYE) * 14, 'camina': True}
        w = (u - 0.7) / 0.3
        p0 = pie + d * 0.9; p0[1] = pie[1]
        p = p0 * (1 - w) + asiento * w
        p[1] += 4.0 * 4 * w * (1 - w)
        return {'modo': 'salto', 'pos': p, 'yaw': yaw, 'u': w}

    # ------------------------------------------------------------ karts y pilotos
    def pose_peach(self, t, e):
        if T_PEACH1 - 0.1 <= t < T_PEACH1 + 2.2:
            return 'win', ((t - T_PEACH1 + 0.1) * 30) % 120
        if 21.0 <= t < 25.7:
            return 'win', ((t - 21.0) * 30 + 20) % 140
        return 'drive', 14 + 14 * (-e['volante'])

    def kart_abalos(self, t, e):
        ins = X.cuerpo_kart(self.kH, e['pos'], e['yaw'], e['pitch'], e['roll'], e['giro'], e['volante'], e.get('deriva', 0.0))
        R = self.R_kart(e)
        a, z = self.kH.asiento
        esc = ESC
        if T_SOPLA + 1.0 < t < T_SOPLA + 2.6:
            esc = ESC * (1.0 + 0.11 * (0.5 - 0.5 * math.cos((t - T_SOPLA - 1.0) * 5.2)))
        ins.append(E.Instancia(self.abalos.malla('drive', 14 + 14 * (-e['volante'])), pos=e['pos'] + R @ (np.array([SEP, a, z]) * ESC), rot=R, escala=esc))
        an, fr = self.pose_peach(t, e)
        ins.append(E.Instancia(self.peach.malla(an, fr), pos=e['pos'] + R @ (np.array([-SEP, a, z]) * ESC), rot=R, escala=ESC))
        if t < T_SOPLA - 0.4:
            ins.append(E.Instancia(self.cigarro, pos=self.asiento(self.kH, e, SEP - 0.045, 0.30, 0.20), rot=R, escala=ESC, luz='normal',
                                   emision=(0.05, 0.02, 0.0)))
        return ins

    def sombra_de(self, e, esc=2.6, alfa=0.55):
        if 'centro' in e:
            gp = np.array(e['centro']) + np.array(e['normal']) * e['lat'] + [0, 0.07, 0]
        else:
            gp = np.array(e['pos']) + [0, 0.07, 0]
        return E.Instancia(self.sombra, pos=gp, yaw=e.get('yaw_pista', e['yaw']), escala=esc, luz='plana', alfa=alfa, tinte=(0, 0, 0))

    def kart_policia(self, t, e, dk):
        ins = X.cuerpo_kart(self.kP, e['pos'], e['yaw'], e['pitch'], e['roll'], e['giro'], e['volante'], e.get('deriva', 0.0), tinte=(0.45, 0.55, 1.15))
        R = self.R_kart(e)
        a, z = self.kP.asiento
        if dk['modo'] == 'kart':
            ins.append(E.Instancia(self.dk_s.malla('drive', 14 + 14 * (-e['volante'])), pos=e['pos'] + R @ (np.array([0, a, z]) * ESC), rot=R, escala=ESC))
        fase = int(t * 6) % 2
        base = np.asarray(e['pos']) + R @ np.array([0, 5.2, -3.0])
        ins.append(E.Instancia(self.barra_luz['rojo' if fase == 0 else 'azul'], pos=base, rot=R, escala=1.0, emision=(0.35, 0.35, 0.35)))
        ins.append(E.Instancia(self.poste, pos=np.asarray(e['pos']) + R @ np.array([0, 4.1, -3.0]), rot=R, luz='normal'))
        return ins

    # ------------------------------------------------------------ escena completa
    def escena(self, t, cam):
        g = self.g
        ins = []
        if t < T_PIERDE:
            e = g.H.estado(t)
            ins += self.kart_abalos(t, e); ins.append(self.sombra_de(e))
        elif t < g.t_hit:
            pos, yaw, v = g.choque.estado(t)
            u = t - T_PIERDE
            e0 = g.e_loss
            lado = 1 if np.dot(g.exterior, izq(e0['yaw'])) > 0 else -1
            e = {'pos': pos, 'yaw': yaw, 'pitch': 0.0, 'roll': 10.0 * CM.suave(u / 0.5) * lado, 'volante': math.sin(u * 14) * 0.9,
                 'giro': e0['giro'] + u * v * 67.0, 'deriva': 0.0}
            ins += self.kart_abalos(t, e)
            ins.append(E.Instancia(self.sombra, pos=pos + [0, 0.08, 0], yaw=yaw, escala=2.6, luz='plana', alfa=.5, tinte=(0, 0, 0)))
        else:
            ins += self.restos(t)
        if t >= T_SIRENA - 2.0:
            ep = g.P.estado(t)
            dk = self.dk_estado(t)
            ins += self.kart_policia(t, ep, dk)
            ins.append(self.sombra_de(ep))
            if dk['modo'] in ('salto', 'pie'):
                ins += self.dk_a_pie(t, dk)
        if 4.9 < t < 21.0:
            d = self.daisy_estado(t)
            fase = d['fase']
            corre = d['corre']
            frame = 14 + 11 * math.sin((t - 10.95) * 17) if 10.95 <= t < 12.4 else 14
            ins += self.daisy.instancias(d['pos'], d['yaw'], fase if corre else 0.0, amp=48.0 if corre else 0.0, anim='spin' if corre else 'drive',
                                         frame=(fase * 3) % 27 if corre else frame, inclina=10.0 if corre else 0.0,
                                         rebote=abs(math.sin(fase)) * 0.35 if corre else 0.0)
            ins.append(E.Instancia(self.sombra, pos=d['pos'] + [0, 0.07, 0], yaw=d['yaw'], escala=1.3, luz='plana', alfa=.5, tinte=(0, 0, 0)))
        if T_HUYE - 3.0 < t < T_PIERDE + 0.5:
            for i, (kind, tp, lc, vc, lado) in enumerate(g.trafico):
                if abs(t - tp) < 3.2:
                    s = g.trafico_estado(i, t)
                    mal, esc = {'taxi': (self.taxi, 2.5), 'bus': (self.bus, 2.2), 'camion': (self.camion, 2.4)}[kind]
                    ins.append(E.Instancia(mal, pos=s['pos'], yaw=s['yaw'], pitch=s['pitch'], escala=esc, luz='normal'))
                    ins.append(E.Instancia(self.sombra, pos=np.array(s['pos']) + [0, .08, 0], yaw=s['yaw'], escala=3.0 if kind != 'bus' else 4.2,
                                           luz='plana', alfa=.5, tinte=(0, 0, 0)))
            for i, (tp, sen) in enumerate(g.peatones):
                if abs(t - tp) < 2.2:
                    s = g.peaton_estado(i, t)
                    fase = (t - tp) * 20.0
                    ins += self.toad.instancias(s['pos'], s['yaw'], fase, amp=45.0, anim='drive', frame=14, inclina=8.0, rebote=abs(math.sin(fase)) * 0.3)
        da = np.array(cam.ojo) - g.pos_arbol
        ya = math.degrees(math.atan2(da[0], da[2]))
        sh = 0.0; lean = 0.0
        if t >= g.t_hit:
            u = t - g.t_hit
            sh = 7.0 * math.exp(-u * 3.5) * math.sin(u * 38)
            lean = -6.0 * (1 - math.exp(-u * 5))
        ins.append(E.Instancia(self.arbol, pos=g.pos_arbol, rot=E.rotacion(ya, lean, sh), escala=0.6, luz='plana'))
        if T_DK_BAJA + 4.0 < t < T_HUYE:
            ins += self.aparato_instancias(t)
        return ins

    def dk_a_pie(self, t, dk):
        ins = []
        if dk['modo'] == 'pie':
            fase = dk['fase']; cam = dk.get('camina', False)
            ins += self.dk_p.instancias(dk['pos'], dk['yaw'], fase if cam else 0.0, amp=40.0 if cam else 0.0, anim='drive', frame=14,
                                        inclina=6.0 if cam else 0.0, rebote=abs(math.sin(fase)) * 0.3 if cam else 0.0)
            if not cam and not (T_APARATO - 0.2 <= t < T_RESULTADO + 1.9):
                dev = self.pos_aparato(t)
                if dev is not None:
                    hombro = np.array(dk['pos']) + [0, 4.6, 0]
                    d = dev['pos'] - hombro
                    L = np.linalg.norm(d)
                    ins.append(E.Instancia(self.brazo, pos=hombro, rot=rot_hacia(d), escala=np.array([1, 1, L * 0.98]), luz='normal'))
        else:
            R = E.rotacion(dk['yaw'], -20 * math.sin(math.pi * dk['u']), 0)
            ins.append(E.Instancia(self.dk_s.malla('spin', (dk['u'] * 20) % 27), pos=dk['pos'], rot=R, escala=ESC))
        return ins

    # ------------------------------------------------------------ alcoholímetro
    def pos_aparato(self, t):
        g = self.g
        e = g.H.estado(T_H_PARA2)
        t0 = T_DK_BAJA + 4.9
        if t < t0 or t > T_HUYE: return None
        boca = self.boca_abalos(e)
        dir_a = -izq(e['yaw']) * 0.9 - vec_yaw(e['yaw']) * 0.45
        dir_a = dir_a / np.linalg.norm(dir_a)
        pos_final = boca + izq(e['yaw']) * 1.55 + [0, -0.3, 0]
        pie, _ = self.dk_pie()
        pos_ini = pie + [0, 3.0, 0] + dir_a * 0.5
        u = CM.suave((t - t0) / 0.6)
        if t > T_HUYE - 1.8: u = 1 - CM.suave((t - (T_HUYE - 1.8)) / 0.6)
        pos = pos_ini * (1 - u) + pos_final * u
        if T_SOPLA + 1.0 < t < T_SOPLA + 2.9: pos = pos + dir_a * 0.25 * math.sin((t - T_SOPLA - 1.0) * 6)
        return {'pos': pos, 'dir': dir_a, 'yaw': e['yaw']}

    def pantalla_estado(self, t):
        if t < T_APARATO + 0.3: return ('idle', 0)
        if t < T_RESULTADO: return ('carga', int(min(20, max(0, (t - T_APARATO - 0.3) / (T_RESULTADO - T_APARATO - 0.5) * 20))))
        return ('res', 0) if int((t - T_RESULTADO) * 5) % 2 == 0 else ('res2', 0)

    def aparato_instancias(self, t):
        d = self.pos_aparato(t)
        if d is None: return []
        R = rot_hacia(d['dir'])
        return [E.Instancia(self.aparato, pos=d['pos'], rot=R, escala=1.0, luz='normal'),
                E.Instancia(self.aparato_pant[self.pantalla_estado(t)], pos=d['pos'], rot=R, escala=1.0, luz='plana', brillo=1.15)]

    # ------------------------------------------------------------ después del choque
    def restos(self, t):
        g = self.g
        ins = []
        u = t - g.t_hit
        pos = g.pos_hit - g.dir_hit * (0.9 * (1 - math.exp(-u * 9)))
        quemado = CM.suave((u - 0.4) / 3.0)
        tinte = tuple(np.array([1.0, 1.0, 1.0]) * (1 - 0.72 * quemado))
        lado = 1 if np.dot(g.exterior, izq(g.yaw_hit)) > 0 else -1
        R = E.rotacion(g.yaw_hit + 8, -6 - 6 * (1 - math.exp(-u * 8)), 16 * (1 - math.exp(-u * 6)) * lado)
        sq = np.array([1.0, 0.8, 0.78])
        ins.append(E.Instancia(self.kH.cuerpo, pos=pos, rot=R, escala=sq * ESC, tinte=tinte, emision=(0.18 * quemado, 0.04 * quemado, 0.0)))
        for r in self.kH.ruedas:
            if r['delante']: continue
            ins.append(E.Instancia(r['malla'], pos=pos + R @ (r['centro'] * ESC * sq), rot=R, escala=ESC, tinte=tinte))
        fr = [r for r in self.kH.ruedas if r['delante']]
        for k, w in enumerate(g.ruedas):
            ew = w.estado(t); a = ew['ang']
            ins.append(E.Instancia(fr[k]['malla'], pos=ew['pos'] + [0, .6, 0], rot=E.rotacion(a[2], a[0], a[1]), escala=ESC, tinte=tinte))
        ins.append(E.Instancia(self.sombra, pos=g.pos_hit + [0, 0.1, 0], yaw=g.yaw_hit, escala=3.0, luz='plana', alfa=.6, tinte=(0, 0, 0)))
        for quien, mp in (('abalos', self.abalos), ('peach', self.peach)):
            c = g.cuerpos[quien]
            ec = c.estado(t); a = ec['ang']
            if not ec['reposo']:
                anim, f = 'spin', ((t - c.t0) * 30) % 27
            else:
                anim, f = 'lose', min(118, (t - c.t_reposo) * 30 * 0.6 + 25)
            ins.append(E.Instancia(mp.malla(anim, f), pos=ec['pos'] + [0, 1.5, 0], rot=E.rotacion(a[1], a[0], a[2]), escala=ESC))
            if ec['reposo']:
                tr = t - c.t_reposo
                ins.append(E.Instancia(self.charco, pos=ec['pos'] + [0, 0.12, 0], yaw=30 if quien == 'peach' else 100,
                                       escala=min(1.0, tr / 2.0) * (2.8 if quien == 'abalos' else 2.5), luz='plana', alfa=0.95))
        for (quien, off, rot, tt) in self.huesos:
            c = g.cuerpos[quien]
            if t > c.t_reposo + tt:
                ec = c.estado(t)
                esc = min(1.0, (t - c.t_reposo - tt) / 0.25)
                ins.append(E.Instancia(self.hueso, pos=ec['pos'] + off + [0, 0.5 * esc, 0], rot=rot, escala=0.4 + 0.6 * math.sin(esc * math.pi / 2), luz='normal'))
        return ins
