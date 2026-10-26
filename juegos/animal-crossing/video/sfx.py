"""Efectos de sonido del vídeo, construidos con las muestras del banco 12 del SDAT (bombo p0, caja de ruido p1, hi-hat p2,
bajo p6, punteo p3, campanilla p13) más filtrado/glissandos propios. Todo sale de sonidos de la ROM; nada se graba ni se descarga.

Cada función devuelve un array mono float32 a 44,1 kHz (normalizado a pico ≈ 0,9 antes de mezclar).
"""
import numpy as np
from scipy.signal import butter, sosfilt

import audio as AU

SR = AU.SR
BANCO = 12
KICK, SNARE, HAT, BAJO, PUNTEO, CAMPANA = 0, 1, 2, 6, 3, 13


def _norm(x, peak=0.9):
    m = np.abs(x).max()
    return (x * (peak / m)).astype(np.float32) if m > 0 else x.astype(np.float32)


def _env(n, a=0.005, d=0.2, curve=3.0):
    """Ataque lineal de a s y caída exponencial."""
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-curve * t / max(d, 1e-3))
    return e.astype(np.float32)


class SFX:
    def __init__(self, audio_bank):
        self.A = audio_bank
        self.rng = np.random.RandomState(21)
        self._c = {}

    # ---------------------------------------------------------------- materia prima
    def nota(self, prog, key, dur=0.4, vel=115):
        """Una nota suelta del banco 12 como mono."""
        k = (prog, key, dur, vel)
        if k not in self._c:
            a = self.A.notes([(0.0, dur, key, vel, prog, 64, 127)], dur + 0.8, BANCO)
            self._c[k] = a.mean(1).astype(np.float32)
        return self._c[k]

    def ruido(self, dur=0.6):
        """Ruido de banda ancha: la caja del banco 12 (muestra de ruido) concatenada con teclas distintas."""
        parts = [self.nota(SNARE, k, 0.5, 120) for k in (40, 46, 52, 58)]
        x = np.concatenate([p[int(0.01 * SR):int(0.25 * SR)] for p in parts])
        while len(x) < dur * SR:
            x = np.concatenate([x, x[::-1]])
        x = x[:int(dur * SR)]
        return x - x.mean()

    @staticmethod
    def _glide(x, r0, r1):
        """Cambia el tono de x con una rampa de velocidad r0 → r1 (remuestreo con fase acumulada)."""
        n = len(x)
        rate = np.linspace(r0, r1, n)
        pos = np.cumsum(rate)
        pos = pos[pos < n - 1]
        return np.interp(pos, np.arange(n), x).astype(np.float32)

    @staticmethod
    def _sweep(x, f0, f1, q=2.5, n_seg=24):
        """Filtro paso banda cuya frecuencia central va de f0 a f1 (por segmentos con solapamiento)."""
        n = len(x)
        out = np.zeros(n, np.float32)
        seg = n // n_seg + 1
        for i in range(n_seg):
            f = f0 * (f1 / f0) ** (i / max(n_seg - 1, 1))
            lo, hi = max(40.0, f / (1 + 1 / q)), min(SR / 2 - 100, f * (1 + 1 / q))
            sos = butter(2, [lo, hi], 'bandpass', fs=SR, output='sos')
            a, b = max(0, (i - 1) * seg // 1), min(n, (i + 1) * seg)
            y = sosfilt(sos, x[a:b])
            w = np.hanning(b - a).astype(np.float32)
            out[a:b] += y * w
        return out

    # ---------------------------------------------------------------- efectos
    def whoosh(self, dur=0.38, up=True, boom=False):
        """Barrido de ruido (transición / lanzar la caña)."""
        x = self.ruido(dur)
        f0, f1 = (500, 5500) if up else (5500, 500)
        y = self._sweep(x, f0, f1)
        n = len(y)
        t = np.linspace(0, 1, n)
        env = np.sin(np.pi * np.clip(t, 0, 1)) ** (1.4 if up else 0.9)
        y = y * env
        if boom:
            k = self.nota(KICK, 36, 0.4, 125)[:int(0.35 * SR)]
            y = y.copy()
            i0 = n // 2
            y[i0:i0 + len(k)] += 0.9 * k[:max(0, n - i0)] if i0 + len(k) <= n else 0
        return _norm(y, 0.85)

    def splash(self, big=1.0):
        """Chapoteo: ruido filtrado que decae + burbujas (campanillas cortas con glissando ascendente)."""
        dur = 0.55 + 0.35 * big
        x = self.ruido(dur)
        sos = butter(2, 3200, 'lowpass', fs=SR, output='sos')
        y = sosfilt(sos, x) * _env(len(x), 0.008, 0.28 * big + 0.1, 3.0)
        y += 0.35 * self._sweep(x, 2500, 900, 1.5) * _env(len(x), 0.002, 0.18, 4.0)
        for i in range(int(4 + 4 * big)):
            t0 = 0.05 + self.rng.uniform(0, 0.4)
            b = self._glide(self.nota(CAMPANA, int(self.rng.choice([64, 67, 71, 74])), 0.12, 85)[:int(0.14 * SR)], 0.8, 1.5)
            b = b * _env(len(b), 0.002, 0.05, 3.0) * 0.28
            i0 = int(t0 * SR)
            y[i0:i0 + len(b)] += b[:max(0, len(y) - i0)]
        return _norm(y, 0.9)

    def plop(self):
        """«Bloop» del flotador al caer."""
        k = self.nota(BAJO, 52, 0.25, 118)[:int(0.22 * SR)]
        y = self._glide(k, 0.7, 1.7)
        y = y * _env(len(y), 0.002, 0.1, 3.0)
        return _norm(y, 0.9)

    def tick(self):
        """Tic seco del flotador cuando pican."""
        h = self.nota(HAT, 60, 0.1, 110)[:int(0.08 * SR)]
        b = self._glide(self.nota(PUNTEO, 84, 0.1, 100)[:int(0.08 * SR)], 1.0, 0.8)
        n = min(len(h), len(b))
        return _norm(h[:n] * 0.6 + b[:n] * 0.6, 0.8)

    def ratchet(self, dur=2.5, rate=14.0):
        """Carrete de la caña: hi-hats rápidos con un toque grave."""
        out = np.zeros(int((dur + 0.2) * SR), np.float32)
        h = self.nota(HAT, 64, 0.1, 100)[:int(0.06 * SR)]
        t = 0.0
        i = 0
        while t < dur:
            a = int(t * SR)
            out[a:a + len(h)] += h * (0.55 if i % 2 else 0.85)
            t += 1.0 / rate
            i += 1
        return _norm(out, 0.6)

    def alerta(self):
        """Sonido de «¡pican!»: dos campanillas rápidas ascendentes + caja."""
        out = np.zeros(int(0.7 * SR), np.float32)
        for t0, k in ((0.0, 72), (0.09, 79), (0.18, 84)):
            n = self.nota(CAMPANA, k - 12, 0.25, 118)[:int(0.35 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(n)] += n * _env(len(n), 0.002, 0.2, 3.0)
        s = self.nota(SNARE, 50, 0.3, 120)[:int(0.2 * SR)]
        out[:len(s)] += 0.5 * s
        return _norm(out, 0.9)

    def pop(self, key=84):
        """Burbuja de cómic: campanilla corta con subida de tono."""
        n = self.nota(CAMPANA, key - 12, 0.2, 118)[:int(0.16 * SR)]
        y = self._glide(n, 0.75, 1.25)
        y = y * _env(len(y), 0.001, 0.07, 3.5)
        return _norm(y, 0.85)

    def bleep(self):
        """«Piiii» de censura (punteo tonal agudo, tono fijo)."""
        n = self.nota(PUNTEO, 96, 0.4, 120)[:int(0.3 * SR)]
        e = np.ones(len(n), np.float32)
        e[:200] = np.linspace(0, 1, 200)
        e[-300:] = np.linspace(1, 0, 300)
        return _norm(n * e, 0.7)

    def ding(self, key=84):
        """Revelado de un dato: campanilla brillante + cola de destellos."""
        out = np.zeros(int(1.0 * SR), np.float32)
        a = self.nota(CAMPANA, key - 12, 0.5, 120)[:int(0.7 * SR)]
        out[:len(a)] += a
        for j, (t0, k) in enumerate(((0.06, key + 7), (0.12, key + 12), (0.18, key + 19))):
            b = self.nota(CAMPANA, k - 12, 0.2, 90)[:int(0.3 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(b)] += 0.45 * b * _env(len(b), 0.001, 0.15, 3.0)
        p = self.nota(KICK, 48, 0.2, 105)[:int(0.12 * SR)]
        out[:len(p)] += 0.5 * p
        return _norm(out, 0.9)

    def fanfarria(self):
        """Salmón capturado: arpegio ascendente de campanillas con acorde final y bombo."""
        out = np.zeros(int(2.0 * SR), np.float32)
        notas = [(0.00, 72), (0.09, 76), (0.18, 79), (0.27, 84), (0.40, 88)]
        for t0, k in notas:
            n = self.nota(CAMPANA, k - 12, 0.6, 122)[:int(0.9 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(n)] += n * 0.8
        for k in (72, 76, 79, 84):
            n = self.nota(PUNTEO, k, 0.7, 110)[:int(1.1 * SR)]
            i0 = int(0.40 * SR)
            out[i0:i0 + len(n)] += 0.35 * n
        for t0 in (0.0, 0.40):
            b = self.nota(KICK, 36, 0.4, 125)[:int(0.3 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(b)] += 0.9 * b
        return _norm(out, 0.95)

    def golpe(self):
        """Impacto grave (tirón de la caña / aparece el salmón rey)."""
        k = self.nota(KICK, 33, 0.5, 127)[:int(0.5 * SR)]
        b = self._glide(self.nota(BAJO, 28, 0.6, 127)[:int(0.55 * SR)], 1.0, 0.7)
        n = min(len(k), len(b))
        return _norm(k[:n] + 0.8 * b[:n], 0.95)

    def sting_rey(self):
        """«Dun dun» del salmón rey."""
        out = np.zeros(int(1.6 * SR), np.float32)
        for t0, key in ((0.0, 31), (0.55, 28)):
            b = self.nota(BAJO, key, 0.7, 127)[:int(0.9 * SR)]
            k = self.nota(KICK, 33, 0.4, 127)[:int(0.3 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(b)] += b
            out[i0:i0 + len(k)] += 0.9 * k
        return _norm(out, 0.95)

    def chiste(self):
        """Redoble de «ba-dum» para el chiste del tamaño: caja doble + campanilla."""
        out = np.zeros(int(0.9 * SR), np.float32)
        for t0 in (0.0, 0.12):
            s = self.nota(SNARE, 54, 0.3, 120)[:int(0.2 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(s)] += s
        c = self.nota(CAMPANA, 74 - 12, 0.5, 118)[:int(0.6 * SR)]
        i0 = int(0.3 * SR)
        out[i0:i0 + len(c)] += 0.8 * c
        return _norm(out, 0.85)

    def trino(self, dur=1.6):
        """Subida de tensión: campanillas rápidas con tono ascendente (antes de saltar el salmón)."""
        out = np.zeros(int((dur + 0.3) * SR), np.float32)
        n_notas = int(dur * 18)
        for i in range(n_notas):
            t0 = i * dur / n_notas
            k = 72 + int(12 * i / n_notas)
            n = self.nota(CAMPANA, k - 12, 0.1, 100)[:int(0.1 * SR)]
            i0 = int(t0 * SR)
            out[i0:i0 + len(n)] += n * (0.4 + 0.6 * i / n_notas)
        return _norm(out, 0.7)
