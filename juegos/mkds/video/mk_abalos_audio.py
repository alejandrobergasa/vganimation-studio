"""Banda sonora de «ABALOS KART»: música original tocada con el banco de instrumentos del juego (BANK 50: bajo, acordes, melodía y
batería de la propia ROM), efectos de la ROM y de síntesis sencilla (motor, sirena, bocinas, golpes), y «voces» tipo máquina de escribir
con los mismos instrumentos, sincronizadas con el rótulo de cada diálogo."""
import math
import numpy as np
from scipy.signal import butter, lfilter

import sonido
from mk import audio as A
from mk_abalos_plan import *

from mk.musica import (BANCO, BAJO, ACORDE, METAL, LEAD, LEAD2, CAMP, PAD, TICK,      # noqa: E402
                       BOMBO, CAJA, HAT, HAT_A, PLATO, Partitura)

FS = A.FS
SFX = {'derrape': (0, 465), 'explosion': (0, 566), 'turbo': (0, 546), 'cuenta': (0, 501), 'ya': (0, 251)}


# ------------------------------------------------------------------ música por escena

def _acorde(base, menor=True):
    return [base, base + (3 if menor else 4), base + 7]


def crucero(dur, raiz=45, bpm=126, alegre=False):
    p = Partitura(dur)
    b = 60.0 / bpm
    prog_acordes = [(0, True), (-4, False), (-2, False), (-5, True)] if not alegre else [(0, False), (5, False), (7, False), (5, False)]
    lead = [12, 15, 19, 17, 15, 12, 10, 12, 15, 17, 19, 22, 19, 17, 15, 12]
    for bar in range(int(dur / (4 * b)) + 1):
        off, men = prog_acordes[bar % 4]
        t0 = bar * 4 * b
        root = raiz + off
        patron = [0, 0, 12, 0, 7, 12, 10, 12]
        for i in range(8):
            p.n(t0 + i * b / 2, b * 0.42, root + patron[i], BAJO, 104 if i % 4 == 0 else 88, 58)
        for beat in (1, 3):
            for k in _acorde(root + 24, men):
                p.n(t0 + beat * b + b * 0.5, b * 0.28, k, ACORDE, 84, 78)
        for i in range(8):
            key = root + 24 + lead[(bar * 8 + i) % 16] - 12 + (0 if men else 0)
            if i % 4 != 3 or bar % 2 == 0:
                p.n(t0 + i * b / 2 + (b * 0.08 if i % 2 else 0), b * 0.4, key, LEAD, 86, 70)
        for i in range(4):
            if i in (0, 2): p.bat(t0 + i * b, 'k', 118)
            if i in (1, 3): p.bat(t0 + i * b, 's', 112)
        for i in range(8):
            p.bat(t0 + i * b / 2, 'h', 70 + (14 if i % 2 == 0 else 0))
        if bar % 2 == 1:
            p.bat(t0 + 3.5 * b, 'k', 100)
    return p


def tension(dur, raiz=38, bpm=92, acentos=()):
    p = Partitura(dur)
    b = 60.0 / bpm
    seq = [0, 3, 5, 3, 7, 5, 3, 0]
    for i in range(int(dur / b) + 1):
        t = i * b
        p.n(t, b * 0.8, raiz + seq[i % 8], BAJO, 94, 56)
        if i % 4 == 0:
            for k in _acorde(raiz + 24, True): p.n(t, b * 1.6, k, PAD, 62, 70, 90)
        if i % 2 == 1: p.bat(t + b * 0.5, 'h', 62)
        if i % 4 in (0, 2): p.bat(t, 'k', 90)
        if i % 8 == 4: p.bat(t, 's', 80)
    for (ta, kind) in acentos:
        if kind == 'no':
            for k in (50, 53, 56, 62): p.n(ta, 0.9, k, METAL, 118, 64)
            p.bat(ta, 'c', 110)
        elif kind == 'corre':
            for i in range(int((dur - ta) / (b / 4))):
                p.n(ta + i * b / 4, b * 0.2, raiz + 12 + [0, 3, 5, 3][i % 4], BAJO, 92, 60)
    return p


def sirena(dur, raiz=40, bpm=150):
    p = Partitura(dur)
    b = 60.0 / bpm
    for i in range(int(dur / (b / 2)) + 1):
        t = i * b / 2
        cresc = min(1.0, t / dur)
        p.n(t, b * 0.4, raiz + (0 if i % 8 < 6 else 1), BAJO, int(80 + 30 * cresc), 58)
        if i % 2 == 0: p.bat(t, 'k', int(90 + 25 * cresc))
        p.bat(t, 'h', 66)
        if i % 8 == 4: p.bat(t, 's', 100)
    for i in range(int(dur / (b * 2))):
        t = i * b * 2
        p.n(t, b * 0.9, raiz + 31, LEAD2, 84, 80); p.n(t + b, b * 0.9, raiz + 37, LEAD2, 84, 50)
    # redoble hacia la frenada
    for i in range(24):
        t = dur - 1.6 + i * 0.0666
        if t < dur - 0.05: p.bat(t, 's', int(60 + 3 * i))
    return p


def control(dur, raiz=36, bpm=84):
    """Suspense del control de alcoholemia con ascenso sincronizado con la barra de carga."""
    p = Partitura(dur)
    b = 60.0 / bpm
    for i in range(int(dur / b) + 1):
        t = i * b
        p.n(t, b * 0.9, raiz + [0, 0, 1, 0][i % 4], BAJO, 90, 58)
        p.bat(t, 'k', 82)
        if i % 2 == 1: p.bat(t + b / 2, 'h', 56)
        if i % 8 == 0:
            for k in _acorde(raiz + 24, True): p.n(t, b * 3.5, k, PAD, 54, 70, 80)
    return p


def persecucion(dur, raiz=40, bpm=176):
    p = Partitura(dur)
    b = 60.0 / bpm
    prog_ = [0, 0, -2, -4]
    lead = [19, 22, 24, 22, 19, 17, 19, 15, 17, 19, 22, 19, 17, 15, 14, 15]
    for bar in range(int(dur / (4 * b)) + 1):
        t0 = bar * 4 * b
        root = raiz + prog_[bar % 4]
        for i in range(8):
            p.n(t0 + i * b / 2, b * 0.4, root + (0 if i % 2 == 0 else 12), BAJO, 108, 58)
        for i in range(4):
            p.bat(t0 + i * b, 'k', 122)
            if i % 2 == 1: p.bat(t0 + i * b, 's', 118)
        for i in range(16):
            p.bat(t0 + i * b / 4, 'h', 58 + (22 if i % 4 == 0 else 0))
        for beat in (0.5, 1.5, 2.5, 3.5):
            for k in _acorde(root + 24, True): p.n(t0 + beat * b, b * 0.3, k, METAL, 100, 76)
        for i in range(8):
            p.n(t0 + i * b / 2, b * 0.42, root + 24 + lead[(bar * 8 + i) % 16] - 12, LEAD2, 88, 52 + (i % 3) * 12)
    return p


def lamento(dur, raiz=45, bpm=60):
    p = Partitura(dur)
    b = 60.0 / bpm
    melodia = [(0, 12, 2), (2, 10, 2), (4, 8, 2), (6, 7, 2), (8, 3, 4)]
    for bar in range(int(dur / (4 * b)) + 1):
        t0 = bar * 4 * b
        for k in _acorde(raiz + [0, -4, -2, -5][bar % 4], True): p.n(t0, b * 3.8, k + 12, PAD, 66, 64, 90)
        p.n(t0, b * 3.8, raiz - 12 + [0, -4, -2, -5][bar % 4], BAJO, 80, 60)
    for (tb, k, dd) in melodia:
        p.n(tb * b, dd * b * 0.9, raiz + 24 + k - 12, LEAD, 84, 70)
    return p


def final_wah(dur):
    p = Partitura(dur)
    for i, (t, k, d) in enumerate([(0.0, 62, .55), (0.6, 61, .55), (1.2, 60, .55), (1.8, 59, 1.6)]):
        p.n(t, d, k, METAL, 112, 64)
        p.n(t, d, k - 12, BAJO, 100, 64)
    p.bat(0.0, 'c', 100)
    return p


def sting_fin(dur):
    p = Partitura(dur)
    for k in (60, 64, 67, 72): p.n(0, 1.3, k, METAL, 118)
    p.n(0, 1.3, 48, BAJO, 110)
    p.bat(0, 'c', 118); p.bat(0, 'k', 118)
    return p


from mk import sintesis as S                        # noqa: E402
from mk.sintesis import (_lp, _hp, _est, ruido, golpe, chasquido, impacto_fuerte, bocina, pitido, sirena_audio, motor, crepitar)  # noqa: E402

# ------------------------------------------------------------------ voces tipo máquina de escribir

VOZ = {'ABALOS': dict(prog=LEAD, base=47, rango=(0, 3, 5, 7, 2, 10), vel=96, pan=62),
       'PEACH': dict(prog=LEAD2, base=79, rango=(0, 2, 4, 7, 9, 4), vel=92, pan=72),
       'DAISY': dict(prog=LEAD2, base=76, rango=(0, 4, 7, 5, 2, 9), vel=92, pan=56),
       'DK': dict(prog=BAJO, base=36, rango=(0, 2, 5, 3, 7, 1), vel=112, pan=64)}


def voces(dialogo):
    return S.voces(dialogo, VOZ)


# ------------------------------------------------------------------ composición

def _sfx(clave, dur=4):
    return A.recortar(A.sfx_id(*SFX[clave], dur))


def componer(g):
    mz = A.Mezcla(DUR)
    pitchf = A.pitch
    # ---------------- música
    def pone(p, t0, nivel, dur_fund=0.1, salida=0.15, curva=None, hasta=None):
        a = p.render()
        a = A.normalizar(a, 0.9)
        mz.musica(a, t0, nivel, entrada=dur_fund, salida=salida, hasta=hasta, curva=curva)
    pone(crucero(T_PARA + 0.4), 0.0, 0.50, 0.2, 0.35)
    pone(tension(T_ARRANCA - T_PARA + 0.4, acentos=[(10.95 - T_PARA, 'no'), (15.4 - T_PARA, 'corre')]), T_PARA, 0.42, 0.2, 0.3)
    pone(crucero(T_SIRENA - T_ARRANCA + 0.3, raiz=42, bpm=124, alegre=True), T_ARRANCA, 0.50, 0.2, 0.3)
    pone(sirena(T_H_PARA2 - T_SIRENA), T_SIRENA, 0.48, 0.3, 0.1)
    # control: suspense + ascenso de la barra de carga + aviso
    cp = control(T_HUYE - T_H_PARA2 - 0.2)
    for i in range(20):
        ts = T_APARATO + 0.3 + i * (T_RESULTADO - T_APARATO - 0.5) / 20 - T_H_PARA2
        cp.n(ts, 0.1, 60 + [0, 2, 4, 5, 7, 9, 11, 12][i % 8] + (i // 8) * 12, TICK, 100, 64)
    # resultado: sting y wah-wah de trombón
    tr = T_RESULTADO - T_H_PARA2
    for k in (49, 52, 58): cp.n(tr, 1.0, k, METAL, 118)
    cp.bat(tr, 'c', 118)
    for i, (dt, k, d) in enumerate([(0.9, 55, .35), (1.3, 54, .35), (1.7, 53, .35), (2.1, 52, .7)]):
        cp.n(tr + dt, d, k, METAL, 100); cp.n(tr + dt, d, k - 12, BAJO, 90)
    # redoble antes de huir
    for i in range(22):
        t = T_HUYE - 0.2 - T_H_PARA2 - 1.5 + i * (1.5 / 22) * (1 - 0.01 * i)
        cp.bat(t, 's', int(50 + 3 * i))
    pone(cp, T_H_PARA2, 0.46, 0.3, 0.05)
    pone(persecucion(T_PIERDE + 0.35 - T_HUYE), T_HUYE, 0.50, 0.05, 0.12)
    pone(lamento(T_SIRENA * 0 + 8.5), g.t_reposo + 0.6, 0.42, 0.8, 1.2)
    pone(final_wah(4.0), 72.0, 0.50, 0.05, 1.0)
    pone(sting_fin(2.0), 73.4, 0.45, 0.02, 0.5)
    # ---------------- agacha la música durante los diálogos (antes de añadir efectos)
    for (t0, t1, quien, txt) in DIALOGO:
        mz.sidechain(t0 - 0.05, t1, bajada=0.62, ataque=0.08, suelta=0.3)
    # ---------------- voces
    vv = voces(DIALOGO)
    for q, a in vv.items():
        mz.poner(A.normalizar(a, 0.75), 0.0, 0.5, 0.0)
    # ---------------- efectos
    def sfx(clave, t, gn=0.8, pan=0.0, pitch=1.0, dur=None, norm=0.9):
        a = _sfx(clave)
        if dur: a = A.fundido(a[:int(dur * FS)], 0.0, min(0.2, dur / 2))
        a = A.normalizar(a, norm)
        mz.poner(A.pitch(a, pitch) if pitch != 1.0 else a, t, gn, pan)
    # motor de Ábalos
    def vH(tt): return np.interp(tt, g.H.t, g.H.v)
    def ganH(tt):
        base = np.where(tt < T_PIERDE + 0.3, 1.0, 0.0)
        base = base * np.where(tt > T_PARA + 0.5, np.where(tt < T_ARRANCA, 0.55, 1.0), 1.0)
        return base * np.clip((T_PIERDE + 0.3 - tt) / 0.1, 0, 1) * 0.55
    mz.poner(motor(0.0, T_PIERDE + 0.5, vH, ganH), 0.0, 0.55)
    # motor de la policía
    def vP(tt): return np.interp(tt, g.P.t, g.P.v)
    def ganP(tt):
        a = np.clip((tt - (T_SIRENA - 2.0)) / 3.0, 0, 1)
        b = np.clip((T_PIERDE + 6.0 - tt) / 1.0, 0, 1)
        return a * b * 0.5 * np.where((tt > T_POLI_PARA + 0.4) & (tt < T_POLI_ARRANCA), 0.5, 1.0)
    mz.poner(motor(T_SIRENA - 2.0, T_PIERDE + 6.5, vP, ganP, base=30.0, k=1.5), T_SIRENA - 2.0, 0.5)
    # sirena
    def gsi(tt):
        a = np.clip((tt - T_SIRENA) / 3.5, 0, 1)
        b = np.where(tt < T_DK_BAJA - 0.2, 1.0, np.where(tt < T_POLI_ARRANCA - 0.4, 0.22, 1.0))
        c = np.clip((T_PIERDE + 6.5 - tt) / 1.0, 0, 1)
        return a * b * c * 0.30
    mz.poner(sirena_audio(T_SIRENA, T_PIERDE + 6.6, gsi), T_SIRENA, 0.6)
    # derrapes: de la ROM
    for t0, d, gn in ((T_FRENA - 0.1, 1.9, 0.8), (T_H_PARA2 - 1.5, 1.3, 0.7), (T_POLI_PARA - 1.5, 1.3, 0.7), (T_HUYE - 0.1, 1.0, 0.55),
                      (T_PIERDE, 1.35, 0.9)):
        sfx('derrape', t0, gn, dur=d, pitch=1.0 if t0 != T_PIERDE else 0.85)
    for tp in [x[1] for x in g.trafico]:
        sfx('derrape', tp - 0.7, 0.35, dur=0.55, pitch=1.15, pan=0.2)
    sfx('turbo', T_HUYE, 0.8)
    sfx('turbo', T_ARRANCA, 0.5, pitch=0.9)
    # bocinas en los cruces (taxi: pi-pi, camión: grave y larga, bus: muy grave)
    for kind, tp, lc, vc, lado in g.trafico:
        pan = 0.4 * (1 if lc > 0 else -1)
        if kind == 'taxi':
            mz.poner(bocina(480, 0.16, 0.5, 0.15), tp - 0.9, 1.0, pan); mz.poner(bocina(480, 0.3, 0.5, 0.25), tp - 0.65, 1.0, pan)
        elif kind == 'camion':
            mz.poner(bocina(250, 0.9, 0.55, 0.25), tp - 0.9, 1.0, pan)
        else:
            mz.poner(bocina(190, 1.1, 0.6, 0.3), tp - 1.0, 1.0, pan)
    for tp, sen in g.peatones:
        mz.poner(bocina(520, 0.2, 0.4, 0.1), tp - 0.8, 1.0, 0.1)
        mz.poner(pitido(1200, 0.05, 0.25), tp - 0.3, 1.0)
    # pitidos del aparato
    for i in range(20):
        ts = T_APARATO + 0.3 + i * (T_RESULTADO - T_APARATO - 0.5) / 20
        mz.poner(pitido(660 + i * 38, 0.06, 0.3), ts, 1.0)
    for i in range(8):
        mz.poner(pitido(880 if i % 2 == 0 else 700, 0.14, 0.45), T_RESULTADO + i * 0.2, 1.0)
    mz.poner(pitido(1500, 0.5, 0.35), T_SOPLA + 0.5, 1.0)
    # soplido: ruido filtrado
    n = int(1.6 * FS); t = np.arange(n) / FS
    sopl = _est(_lp(_hp(ruido(1.6, 21), 400), 3000) * np.sin(np.pi * np.clip(t / 1.6, 0, 1)) * 0.45)
    mz.poner(sopl, T_SOPLA + 1.0, 1.0)
    mz.poner(sopl * 0.9, T_SOPLA + 1.7, 0.8)
    # choque
    th = g.t_hit
    sfx('explosion', th, 1.0, norm=0.95)
    mz.poner(impacto_fuerte(), th, 1.0)
    for i in range(6): mz.poner(chasquido(0.04, 0.9, 40 + i), th + 0.02 + i * 0.045, 0.7)
    for k, c in g.cuerpos.items():
        for te in c.golpes[:4]:
            mz.poner(golpe(0.4, 85, 35, int(te * 100) % 999, 0.9), c.t0 + te, 1.0, -0.3 if k == 'abalos' else 0.3)
            mz.poner(chasquido(0.05, 0.9, int(te * 50) % 997), c.t0 + te + 0.01, 0.9)
            mz.poner(chasquido(0.04, 0.8, int(te * 51) % 991), c.t0 + te + 0.08, 0.8)
        mz.poner(golpe(0.6, 55, 28, 5, 0.7), c.t_reposo, 0.9)
        for j in range(3): mz.poner(chasquido(0.03, 0.9, 70 + j), c.t_reposo + 0.35 + j * 0.22, 0.9)
    mz.poner(crepitar(th + 0.3, DUR, lambda tt: np.clip((tt - th - 0.3) / 1.0, 0, 1) * np.clip((DUR - tt) / 1.5, 0, 1) * 0.8), th + 0.3, 1.0)
    # remate: sirena que se apaga y aire
    return mz
