"""Rehace la música del vídeo original con los instrumentos de Pokémon Platino y la mezcla con las voces.

1. demucs ya separó audio/original.wav en voces, batería, bajo y resto (audio/sep/htdemucs/original/).
2. transcribir.py pasó bajo y resto a notas (audio/notas_bass.json, notas_other.json).
3. Aquí: la batería se detecta por golpes (graves = bombo, medios ruidosos = caja, agudos = charles), se
   eligen instrumentos del banco BANK_BGM_FIELD (el de los pueblos y rutas), se sintetiza todo con
   tools/sonido.py y se le da la misma dinámica que tenía la música original segundo a segundo.
4. Resultado: audio/musica_platino.wav y audio/mezcla_final.wav (voces originales + música Platino).

  python musica_platino.py
"""
import glob
import json
import os
import sys

import numpy as np
import soundfile as sf
from scipy import signal

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import valrutas
import sonido  # noqa

SEP = os.path.join(AQUI, 'audio', 'sep', 'htdemucs', 'original')
FS_OUT = 44100
BANCO = 'BANK_BGM_FIELD'
P_BAJO, P_CORTA, P_LARGA, P_BATERIA = 32, 2, 48, 1      # bajo, pulsada (tipo piano), sostenida (cuerdas)
KICK, CAJA, CHARLES, CHARLES_AB = 36, 38, 42, 46


def leer(n):
    a, fs = sf.read(os.path.join(SEP, n + '.wav'), dtype='float32')
    return a, fs


def polifonia(notas, maximo):
    """Deja como mucho 'maximo' notas sonando a la vez (se quedan las más fuertes)."""
    out, sonando = [], []
    for n in sorted(notas, key=lambda n: (n[0], -n[3])):
        sonando = [s for s in sonando if s[1] > n[0]]
        if len(sonando) >= maximo:
            peor = min(sonando, key=lambda s: s[3])
            if peor[3] >= n[3]:
                continue
            peor[1] = n[0]              # corta la más débil
            sonando.remove(peor)
        sonando.append(n)
        out.append(n)
    return out


def notas_melodicas():
    notas = []
    bajo = [list(n) for n in json.load(open(os.path.join(AQUI, 'audio', 'notas_bass.json')))]
    bajo = [n for n in bajo if n[3] >= 30 and n[1] - n[0] >= 0.08]
    for a, b, p, v in polifonia(bajo, 1):
        while p > 55:
            p -= 12
        while p < 28:
            p += 12
        notas.append((a, b - a, p, min(127, 40 + v), P_BAJO, 64, 110))
    otro = [list(n) for n in json.load(open(os.path.join(AQUI, 'audio', 'notas_other.json')))]
    otro = [n for n in otro if n[3] >= 35 and n[1] - n[0] >= 0.09 and 40 <= n[2] <= 96]
    for a, b, p, v in polifonia(otro, 4):
        d = b - a
        if d < 0.35:
            notas.append((a, d, p, min(127, 30 + v), P_CORTA, 52, 100))
        else:
            notas.append((a, d, p, min(127, 20 + v), P_LARGA, 76, 90))
    return notas


def golpes_bateria():
    """Golpes de la batería separada: (t, tecla, velocidad)."""
    a, fs = leer('drums')
    m = a.mean(1)
    f, t, Z = signal.stft(m, fs, nperseg=1024, noverlap=768)
    S = np.abs(Z)
    bandas = {KICK: (30, 150), CAJA: (1000, 5000), CHARLES: (7000, 16000)}
    out = []
    for tecla, (f0, f1) in bandas.items():
        e = S[(f >= f0) & (f < f1)].sum(0)
        e = np.log1p(e / (np.median(e) + 1e-9))
        flujo = np.maximum(0, np.diff(e, prepend=e[0]))
        umbral = np.convolve(flujo, np.ones(40) / 40, 'same') * 1.8 + 0.25
        picos, _ = signal.find_peaks(flujo, height=umbral, distance=int(0.09 * fs / 256))
        for k in picos:
            v = int(np.clip(50 + flujo[k] * 40, 50, 127))
            out.append((float(t[k]), tecla, v))
    return out


def dinamica(original, nuevo, fs, ventana=0.5):
    """Ganancia por ventanas para que 'nuevo' siga el volumen de 'original' (silencio donde no había música)."""
    w = int(fs * ventana)
    n = min(len(original), len(nuevo))
    g = np.zeros(n, np.float32)
    rms = lambda x: np.sqrt((x ** 2).mean() + 1e-12)
    centros, gan = [], []
    for i in range(0, n, w):
        ro, rn = rms(original[i:i + w]), rms(nuevo[i:i + w])
        k = 0.0 if ro < 10 ** (-48 / 20) else min(4.0, ro / max(rn, 1e-4))
        centros.append(i + w / 2)
        gan.append(k)
    gan = np.convolve(gan, np.ones(3) / 3, 'same')
    g = np.interp(np.arange(n), centros, gan).astype(np.float32)
    return g


def main():
    son = sonido.Sonido(valrutas.rom())
    voz, fs = leer('vocals')
    dur = len(voz) / fs
    notas = notas_melodicas()
    for t, tecla, v in golpes_bateria():
        notas.append((t, 0.15, tecla, v, P_BATERIA, 64, 110))
    print(len(notas), 'notas', flush=True)
    a = sonido.tocar_notas(son, BANCO, notas, dur + 1)
    a = signal.resample_poly(a, FS_OUT, sonido.FS, axis=0).astype(np.float32)[:len(voz)]
    if len(a) < len(voz):
        a = np.pad(a, ((0, len(voz) - len(a)), (0, 0)))
    musica_orig = sum(leer(n)[0] for n in ('drums', 'bass', 'other'))
    g = dinamica(musica_orig.mean(1), a.mean(1), fs)
    a = a[:len(g)] * g[:, None]
    sf.write(os.path.join(AQUI, 'audio', 'musica_platino.wav'), a, fs)
    mezcla = voz[:len(a)] + a * 0.9
    pico = np.abs(mezcla).max()
    if pico > 0.98:
        mezcla *= 0.98 / pico
    sf.write(os.path.join(AQUI, 'audio', 'mezcla_final.wav'), mezcla, fs)
    print('->', os.path.join(AQUI, 'audio', 'mezcla_final.wav'))


if __name__ == '__main__':
    main()
