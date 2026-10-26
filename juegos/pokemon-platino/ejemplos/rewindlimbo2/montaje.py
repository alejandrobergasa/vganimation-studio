"""Montaje final de REWINDLIMBO2: concatena el vídeo de los 14 tramos (sin recodificar) y rehace el audio entero
(mezcla_final.wav = voces originales + música resintetizada con Platino, más los efectos _sfx.wav de cada tramo
colocados en su segundo exacto). Así no quedan huecos de AAC en los cortes. También saca un GIF de muestra.

  python trabajo/rewindlimbo2/montaje.py [sufijo]     (p. ej. v3 -> rewindlimbo2_v3.mp4)
"""
import os
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import valrutas  # noqa: E402
import subprocess
import sys
import wave

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from musica_platino2 import limitar

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
SAL = os.path.join(valrutas.SALIDA, 'rewindlimbo2')
FINAL = os.path.join(valrutas.SALIDA, 'rewindlimbo2')
DURACION = 618.624
TRAMOS = [('t1_preparativos', 0.0), ('t2_parque', 70.0), ('t3_busqueda', 150.0), ('t4_robot', 241.0),
          ('t5_caja', 294.0), ('t6_logrono', 315.0), ('t7_angeles', 330.0), ('t8_grupo', 365.0),
          ('t9_ordenador', 422.0), ('t10_obra', 447.0), ('t11_inspector', 491.0), ('t12_bano', 525.6),
          ('t13_maletin', 538.8), ('t14_escondite', 567.6)]


SFX = 0.7                                              # los efectos del juego, por debajo de voces y música


def leer_wav(ruta):
    a, sr = sf.read(ruta, dtype='float32', always_2d=True)
    if a.shape[1] == 1:
        a = np.repeat(a, 2, axis=1)
    return a, sr


def main():
    base, sr = leer_wav(os.path.join(AQUI, 'audio', 'mezcla_final.wav'))
    total = int(DURACION * sr)
    mezcla = np.zeros((total, 2), np.float32)
    mezcla[:min(total, len(base))] = base[:total]
    for nombre, t0 in TRAMOS:
        ruta = os.path.join(SAL, nombre + '_sfx.wav')
        if not os.path.exists(ruta):
            continue
        s, ssr = leer_wav(ruta)
        if ssr != sr:
            s = resample_poly(s, sr, ssr, axis=0).astype(np.float32)
        i = int(round(t0 * sr))
        n = min(len(s), total - i)
        mezcla[i:i + n] += s[:n] * SFX
    mezcla = limitar(mezcla, 0.95, sr)                 # sin tanh: distorsionaba los picos
    wav = os.path.join(AQUI, 'audio', 'montaje_audio.wav')
    with wave.open(wav, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((mezcla * 32767).astype(np.int16).tobytes())

    lista = os.path.join(AQUI, 'tramos.txt')
    with open(lista, 'w') as f:
        for nombre, _ in TRAMOS:
            f.write("file '%s'\n" % os.path.join(SAL, nombre + '.mp4').replace('\\', '/'))
    final = FINAL + ('_' + sys.argv[1] if len(sys.argv) > 1 else '')
    salida = final + '.mp4'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lista, '-i', wav,
                    '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                    '-t', '%.3f' % DURACION, salida], check=True)
    # GIF de muestra (el original dura 10 minutos): el forcejeo con el robot y el lanzamiento, 4:28-4:42
    gif = final + '_muestra.gif'
    paleta = os.path.join(AQUI, 'paleta.png')
    filtro = 'fps=15,scale=512:-1:flags=neighbor'
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '268', '-t', '14', '-i', salida,
                    '-vf', filtro + ',palettegen', paleta], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '268', '-t', '14', '-i', salida, '-i', paleta,
                    '-lavfi', filtro + '[x];[x][1:v]paletteuse', gif], check=True)
    print(salida)
    print(gif)


if __name__ == '__main__':
    main()
