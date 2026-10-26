"""Síntesis sencilla para efectos y voces de los vídeos de Mario Kart DS (compartida por los ejemplos y los proyectos): ruido filtrado,
golpes, chasquidos, bocinas, pitidos, sirena, motor por velocidad y «voces» tipo máquina de escribir tocadas con el banco 50 de la ROM."""
import numpy as np
from scipy.signal import butter, lfilter

import sonido
from . import audio as A
from .musica import BANCO

FS = A.FS


def _lp(x, fc, orden=2):
    b, a = butter(orden, fc / (FS / 2), 'low'); return lfilter(b, a, x)


def _hp(x, fc, orden=2):
    b, a = butter(orden, fc / (FS / 2), 'high'); return lfilter(b, a, x)


def _est(x, pan=0.0, g=1.0):
    x = np.asarray(x, np.float32) * g
    return np.stack([x * min(1, 1 - pan), x * min(1, 1 + pan)], 1).astype(np.float32)


def ruido(dur, semilla=0):
    return np.random.default_rng(semilla).normal(size=int(dur * FS)).astype(np.float32)


def golpe(dur=0.35, f0=95.0, f1=38.0, semilla=1, g=1.0, ruido_g=0.6):
    n = int(dur * FS); t = np.arange(n) / FS
    f = f1 + (f0 - f1) * np.exp(-t * 14)
    ph = 2 * np.pi * np.cumsum(f) / FS
    env = np.exp(-t * 11)
    r = _lp(ruido(dur, semilla), 1800) * np.exp(-t * 18) * ruido_g
    return _est((np.sin(ph) * env + r) * g)


def chasquido(dur=0.05, g=0.8, semilla=2):
    n = int(dur * FS); t = np.arange(n) / FS
    return _est(_hp(ruido(dur, semilla), 2500) * np.exp(-t * 90) * g)


def impacto_fuerte(semilla=3):
    n = int(1.4 * FS); t = np.arange(n) / FS
    r = _lp(ruido(1.4, semilla), 3500) * np.exp(-t * 3.2)
    f = 60 * np.exp(-t * 2.0)
    s = np.sin(2 * np.pi * np.cumsum(f) / FS) * np.exp(-t * 3.0)
    return _est((r * 0.9 + s * 1.1) * 0.8)


def bocina(f0=420.0, dur=0.4, g=0.5, doppler=0.0, tipo='coche'):
    n = int(dur * FS); t = np.arange(n) / FS
    f = f0 * (1 - doppler * t / dur)
    ph = 2 * np.pi * np.cumsum(f) / FS
    x = np.sign(np.sin(ph)) * 0.5 + np.sign(np.sin(ph * 1.26)) * 0.5
    x = _lp(x, 3200)
    env = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.03)
    return _est(x * env * g)


def pitido(f=1000.0, dur=0.08, g=0.35):
    n = int(dur * FS); t = np.arange(n) / FS
    x = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6
    return _est(x * np.minimum(1, t / 0.004) * np.minimum(1, (dur - t) / 0.01) * g)


def sirena_audio(t0, t1, ganancia):
    """Sirena de dos tonos con barrido (wail). Devuelve (inicio, audio)."""
    n = int((t1 - t0) * FS); t = np.arange(n) / FS
    f = 820 + 330 * np.sign(np.sin(2 * np.pi * t * 1.4)) * 0.0 + 330 * np.sin(2 * np.pi * t * 0.9) ** 3
    ph = 2 * np.pi * np.cumsum(f) / FS
    x = np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph)
    return _est(x * 0.5 * ganancia(t0 + t))


def motor(t0, t1, v_fn, gan, base=26.0, k=1.6):
    n = int((t1 - t0) * FS); tt = t0 + np.arange(n) / FS
    v = v_fn(tt)
    f = base + v * k
    ph = np.cumsum(f) / FS
    saw = 2 * (ph % 1.0) - 1
    saw2 = 2 * ((ph * 2.003) % 1.0) - 1
    x = _lp(saw * 0.6 + saw2 * 0.25, 1300, 2)
    ru = _lp(ruido((t1 - t0), 7), 2200) * (0.05 + v / 140.0)
    amp = 0.18 + 0.82 * np.clip(v / 70.0, 0, 1) ** 0.7
    return _est((x + ru) * amp * gan(tt))


def crepitar(t0, t1, gan, semilla=11):
    rng = np.random.default_rng(semilla)
    n = int((t1 - t0) * FS)
    out = np.zeros((n, 2), np.float32)
    N = int((t1 - t0) * 28)
    for t in np.sort(rng.uniform(0, t1 - t0, N)):
        c = chasquido(rng.uniform(.008, .03), rng.uniform(.15, .7), int(rng.integers(0, 1 << 30)))
        i = int(t * FS); m = min(len(c), n - i)
        if m > 0: out[i:i + m] += c[:m] * float(gan(t0 + t))
    base = _lp(ruido(t1 - t0, 5), 400) * 0.25
    out += _est(base * gan(t0 + np.arange(n) / FS))
    return out


def voces(dialogo, VOZ, cps=18.0):
    """Un «blip» por vocal (y cada tercera letra) sincronizado con el rótulo de cada diálogo (t0, t1, quién, texto). Devuelve {quién: audio}.
    VOZ[quién] = dict(prog, base, rango, vel, pan): instrumento del banco, tecla base, intervalos que se recorren, velocidad y paneo."""
    por = {k: [] for k in VOZ}
    for (t0, t1, quien, txt) in dialogo:
        v = VOZ[quien]
        k = 0
        for i, c in enumerate(txt):
            if c.isalpha() and (c.lower() in 'aeiouáéíóú' or i % 3 == 0):
                t = t0 + i / cps
                if t < t1:
                    key = v['base'] + v['rango'][(k * 5 + ord(c)) % len(v['rango'])] + (2 if txt.rstrip().endswith('?') and i > len(txt) * .8 else 0)
                    por[quien].append((t, 0.075, key, v['vel'], v['prog'], v['pan'], 100))
                    k += 1
    out = {}
    for q, nn in por.items():
        if nn:
            out[q] = sonido.tocar_notas(A.son(), BANCO, nn, max(n[0] for n in nn) + 1.0)
    return out
