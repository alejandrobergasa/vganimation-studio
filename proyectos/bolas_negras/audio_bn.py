"""Audio completo de «BOLAS NEGRAS»: música (musica_bn.py) + voces tipo máquina de escribir sincronizadas con los rótulos + motores, derrapes
de la ROM, saltos, pasos, billetes y golpe final. Devuelve una `Mezcla`; la usa `BolasNegras.audio()`.
Efectos de la ROM (SSAR 0, ids comprobados en «Ábalos»): derrape 465, turbo 546; el resto es síntesis sencilla de `mk/sintesis.py`."""
import math
import numpy as np

from mk import audio as A
from mk import sintesis as S
from mk.musica import BAJO, LEAD, LEAD2
import musica_bn

FS = A.FS
SFX = {'derrape': (0, 465), 'turbo': (0, 546)}
CPS = 22.0                                  # letras por segundo del rótulo (igual que BolasNegras.overlays)

VOZ = {'ALEGA': dict(prog=LEAD, base=52, rango=(0, 3, 5, 7, 2, 10), vel=96, pan=52),
       'VIVI': dict(prog=LEAD2, base=71, rango=(0, 2, 4, 7, 9, 4), vel=94, pan=76),
       'PEDRO': dict(prog=BAJO, base=38, rango=(0, 2, 0, 3, -2, 0), vel=104, pan=64),
       'SANTOS': dict(prog=LEAD, base=47, rango=(0, -2, -4, -5, -7, -3), vel=92, pan=64)}


def _sfx(clave, dur=4):
    return A.recortar(A.sfx_id(*SFX[clave], dur))


def _paso(semilla, g=0.5):
    """Pisada suave: golpe grave corto con un poco de ruido."""
    return S.golpe(0.09, 150, 80, semilla, g, 0.9)


def _swish(dur=0.3, g=0.35, semilla=4):
    """Billete que pasa de mano en mano: ruido filtrado con envolvente."""
    n = int(dur * FS); t = np.arange(n) / FS
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    return S._est(S._hp(S._lp(S.ruido(dur, semilla), 5500), 1200) * env * g)


def componer(dialogo, g, plan):
    """dialogo = [(t0, t1, quién, [líneas])]; g = Guion (kart(), paseo()); plan = dict con T_* del vídeo."""
    mz = musica_bn.componer()
    dur = mz.dur
    # ---- la música baja mientras hay texto (antes de añadir voces y efectos)
    for (t0, t1, quien, lin) in dialogo:
        mz.sidechain(t0 - 0.05, t1, bajada=0.62, ataque=0.08, suelta=0.3)
    # ---- voces: un blip por letra, al ritmo del rótulo
    vv = S.voces([(t0, t1, q, ''.join(lin)) for (t0, t1, q, lin) in dialogo], VOZ, CPS)
    for q, a in vv.items():
        mz.poner(A.normalizar(a, 0.75), 0.0, 0.5, 0.0)

    def sfx(clave, t, gn=0.8, pan=0.0, pitch=1.0, dur=None, norm=0.9):
        a = _sfx(clave)
        if dur: a = A.fundido(a[:int(dur * FS)], 0.0, min(0.2, dur / 2))
        a = A.normalizar(a, norm)
        mz.poner(A.pitch(a, pitch) if pitch != 1.0 else a, t, gn, pan)

    # ---- motores de los karts (velocidad real de la trayectoria); suenan hasta que se paran
    t_fin = plan['T_STOP'] + 1.0
    for quien, vel, pan, base in (('A', g.vA, -0.3, 26.0), ('B', g.vB, 0.3, 29.0)):
        v_fn = lambda tt, vel=vel: np.interp(tt, g.t, vel)
        gan = lambda tt: np.clip((t_fin - tt) / 0.8, 0, 1) * 0.42
        mz.poner(S.motor(0.0, t_fin, v_fn, gan, base=base, k=2.6), 0.0, 0.6, pan)
    # ---- derrapes al aparcar (los mismos instantes que el humo)
    sfx('derrape', 12.55, 0.7, pan=-0.2, dur=1.5)
    sfx('derrape', 12.85, 0.6, pan=0.2, dur=1.3, pitch=1.06)
    # ---- saltan al suelo
    for q, ts in (('A', plan['T_SALTA_A']), ('B', plan['T_SALTA_B'])):
        mz.poner(S.golpe(0.2, 110, 55, 8 + ord(q), 0.7, 0.6), ts + 0.33, 0.8, -0.2 if q == 'A' else 0.2)
    # ---- pasos: hacia la puerta y al entrar (una pisada cada medio ciclo de la marcha: fase = 11 rad/s)
    paso = math.pi / 11.0
    k = 0
    for q, pan in (('A', 0.2), ('B', -0.2)):
        ta, tf = g.paseo(q)
        for i in range(1, int((tf - ta) / paso) + 1):
            k += 1
            mz.poner(_paso(100 + k), ta + i * paso, 0.55, pan * (1 - 0.0 * i))
    for q, pan, off in (('A', 0.2, 0.0), ('B', -0.2, 0.25)):
        t0 = plan['T_ENTRAN'] + off
        for i in range(1, int(1.3 / paso) + 1):
            k += 1
            mz.poner(_paso(300 + k, 0.45), t0 + i * paso, 0.5 * (1 - 0.35 * i / 8), pan)
    # ---- billetes: swish al entregarlos
    for tp, pan in ((plan['T_PAGA_A'], 0.15), (plan['T_PAGA_B'], -0.15)):
        mz.poner(_swish(0.3, 0.45, int(tp * 10)), tp, 0.9, pan)
        mz.poner(S.chasquido(0.04, 0.6, int(tp * 7)), tp + 0.5, 0.6, pan)
    # ---- remate: golpe de «¿QUÉ BUSCAN?» y corte a la portada
    tb, tf = plan['T_BUSCAN'], plan['T_FOTO']
    mz.poner(S.impacto_fuerte(5), tb, 0.55)
    mz.poner(S.golpe(0.6, 70, 30, 6, 0.8), tb, 0.8)
    sfx('turbo', tf, 0.35, pitch=0.8, dur=0.7)
    mz.poner(S.golpe(0.5, 90, 35, 9, 0.8), tf, 0.7)
    return mz
