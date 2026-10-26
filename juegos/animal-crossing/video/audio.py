"""Audio del vídeo: música (SSEQ sintetizado) + voces de personajes a partir de las sílabas del SDAT."""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
from ww.rom import Rom          # noqa: E402
from ww.synth import Sonido     # noqa: E402
import ww.synth as synth        # noqa: E402

SR = 44100


def resample(x, sr_in, sr_out=SR):
    n = int(round(len(x) * sr_out / sr_in))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


class AudioBank:
    def __init__(self, rom):
        self.S = Sonido(rom.raw('sound_dataEUR.sdat'))

    def music(self, seq, seconds):
        a = self.S.renderizar(seq, segundos=seconds)
        L = resample(a[:, 0], synth.FS)
        R = resample(a[:, 1], synth.FS)
        return np.stack([L, R], 1)

    def notes(self, notas, seconds, banco):
        """Música a partir de notas sueltas tocadas con los instrumentos de un banco del SDAT (ver synth.tocar_notas)."""
        a = synth.tocar_notas(self.S, banco, notas, seconds)
        return np.stack([resample(a[:, 0], synth.FS), resample(a[:, 1], synth.FS)], 1)

    def voice_set(self, swar):
        n = len(self.S.sdat.waveArchives[swar][1].waves)
        out = []
        for i in range(n):
            s, rate, _ = self.S.banco.muestra(swar, i)
            out.append(resample(s, rate))
        return out


class Mixer:
    def __init__(self, seconds):
        self.buf = np.zeros((int(seconds * SR) + SR, 2), np.float32)

    def add(self, t, x, gain=1.0, pan=0.0):
        i = int(t * SR)
        if x.ndim == 1:
            x = np.stack([x * (1 - max(pan, 0)), x * (1 + min(pan, 0))], 1)
        n = min(len(x), len(self.buf) - i)
        if n > 0:
            self.buf[i:i + n] += x[:n] * gain

    def fade_out(self, t0, t1):
        i0, i1 = int(t0 * SR), int(t1 * SR)
        self.buf[i0:i1] *= np.linspace(1, 0, i1 - i0)[:, None]
        self.buf[i1:] = 0

    def save(self, path, seconds, peak=0.89):
        x = self.buf[:int(seconds * SR)]
        m = np.abs(x).max()
        if m > 0:
            x = x * (peak / m)
        pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
        with wave.open(path, 'wb') as w:
            w.setnchannels(2)
            w.setsampwidth(2)
            w.setframerate(SR)
            w.writeframes(pcm.tobytes())


def speech_blips(text, voice, pitch, rng, cps=22.0):
    """Lista de (t_relativo, onda) para un texto: una sílaba por letra, ritmo fijo como el texto tecleado."""
    out = []
    for k, ch in enumerate(text):
        if not ch.isalpha():
            continue
        if k % 2:                       # una sílaba cada dos letras, como el balbuceo del juego
            continue
        w = voice[(ord(ch.lower()) * 7 + k * 3) % len(voice)]
        f = pitch * rng.uniform(0.93, 1.1)
        n = max(8, int(len(w) / f))
        w2 = np.interp(np.linspace(0, len(w) - 1, n), np.arange(len(w)), w).astype(np.float32)
        out.append((k / cps, w2))
    return out
