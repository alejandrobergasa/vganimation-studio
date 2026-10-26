"""Monta formigal_v2.mp4: la canción de fiestaformigal (tocada con el banco de Platino) bajo la fiesta, sobre el
render sin música de fiesta. Uso: FORMIGAL_V2=1 python cinematicas/escenas/formigal.py; python montaje.py"""
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

T = json.load(open(os.path.join(valrutas.CACHE, 'formigal_marcas.json')))['fiesta'] / 30
SIN = os.path.join(valrutas.SALIDA, 'formigal_v2_sinmusica.mp4')
dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of',
                                     'default=nw=1:nk=1', SIN]).decode())
m, fs = sf.read(os.path.join(AQUI, 'audio', 'musica_platino.wav'), dtype='float32')
resto = dur - T
x = m[int(1.0 * fs):int((1.0 + resto) * fs)].copy()
x[:int(0.4 * fs)] *= np.linspace(0, 1, int(0.4 * fs))[:, None]
x[-int(2.5 * fs):] *= np.linspace(1, 0, int(2.5 * fs))[:, None]
out = np.zeros((int((dur + 1) * fs), 2), np.float32)
i = int(T * fs)
out[i:i + len(x)] += x[:len(out) - i]
out = limitar(out, 0.8, fs)
wav = os.path.join(AQUI, 'audio', 'musica_formigal_v2.wav')
sf.write(wav, out[:int(dur * fs)], fs, subtype='FLOAT')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', SIN, '-i', wav, '-filter_complex',
                '[1:a]volume=0.9[m];[0:a][m]amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.93[a]',
                '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                os.path.join(valrutas.SALIDA, 'formigal_v2.mp4')], check=True)
print('fiesta en %.1f s, duración %.1f s -> salida/formigal_v2.mp4' % (T, dur))
