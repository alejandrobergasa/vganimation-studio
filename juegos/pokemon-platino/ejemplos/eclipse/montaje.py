"""Monta la pista de música de ECLIPSE v2 sobre la escena y la mezcla con los efectos del MP4.
Intro de la canción 1 -> subida (orig 1:20-1:40) justo antes del anillo del eclipse -> canción 2 (orig 1:40-) desde
el anillo. Uso:  python montaje.py   (tras ECLIPSE_V2=1 python cinematicas/escenas/eclipse.py)"""
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import valrutas  # noqa: E402
import subprocess
import sys

import numpy as np
import soundfile as sf

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(AQUI, '..', 'rewindlimbo2'))
from musica_platino2 import limitar  # noqa

FPS = 30
marcas = json.load(open(os.path.join(valrutas.CACHE, 'eclipse_marcas.json')))
T = marcas['anillo'] / FPS
SIN = os.path.join(valrutas.SALIDA, 'eclipse_v2_sinmusica.mp4')
dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                     'default=nw=1:nk=1', SIN]).decode())

m, fs = sf.read(os.path.join(AQUI, 'audio', 'musica_platino.wav'), dtype='float32')
db = lambda x: 10 ** (x / 20)
S = lambda a, b: m[int(a * fs):int(b * fs)]
BUILD = 20.0
xf = int(1.5 * fs)
pre = S(2.0, 2.0 + T - BUILD + 1.5) * db(12)
build = S(80.0, 100.0) * db(12)
song2 = S(100.0, 186.0) * db(-2)
out = np.zeros((int((dur + 1) * fs), 2), np.float32)


def poner(x, t, fade_in=0, fade_out=0):
    x = x.copy()
    if fade_in:
        x[:fade_in] *= np.sin(np.linspace(0, np.pi / 2, fade_in))[:, None]
    if fade_out:
        x[-fade_out:] *= np.cos(np.linspace(0, np.pi / 2, fade_out))[:, None]
    i = int(t * fs)
    n = min(len(x), len(out) - i)
    out[i:i + n] += x[:n]


poner(pre, 0, int(0.5 * fs), xf)
poner(build, T - BUILD, xf, 0)                      # se funde con el final de pre
poner(song2, T, 0, int(2.5 * fs))
out = limitar(out, 0.8, fs)
sf.write(os.path.join(AQUI, 'audio', 'musica_eclipse_v2.wav'), out[:int(dur * fs)], fs, subtype='FLOAT')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SIN, '-i', os.path.join(AQUI, 'audio', 'musica_eclipse_v2.wav'),
                '-filter_complex', '[1:a]volume=0.9[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.93[a]',
                '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                os.path.join(valrutas.SALIDA, 'eclipse_v2.mp4')], check=True)
print('T anillo %.2f s, duración %.1f s -> salida/eclipse_v2.mp4' % (T, dur))
