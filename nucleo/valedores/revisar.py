"""Herramientas de revisión de un vídeo, iguales para cualquier agente y cualquier juego.

    python valedores.py revisar info   <video>                      resolución, fps, duración, audio, niveles
    python valedores.py revisar hoja   <video> [paso_s=3] [columnas=5]   hoja de contactos
    python valedores.py revisar frame  <video> <segundo>            un fotograma a tamaño completo
    python valedores.py revisar audio  <video>                      espectrograma + onda y niveles

Las imágenes se guardan en la carpeta de trabajo del proyecto activo (o `.cache/_general/trabajo/revision/`).
Después hay que MIRAR la imagen con la herramienta de lectura de imágenes del agente: generarla no basta.
"""
import json
import math
import os
import re
import shutil
import subprocess

from . import rutas


def _ff(*a):
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', *a])


def _salida():
    d = os.path.join(rutas.trabajo(), 'revision')
    os.makedirs(d, exist_ok=True)
    return d


def _sonda(video):
    r = subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', video])
    return json.loads(r)


def info(video):
    d = _sonda(video)
    v = next((s for s in d['streams'] if s['codec_type'] == 'video'), None)
    a = next((s for s in d['streams'] if s['codec_type'] == 'audio'), None)
    out = {'duracion_s': round(float(d['format']['duration']), 2), 'tamano_mb': round(int(d['format']['size']) / 1e6, 1)}
    if v:
        num, den = (v['avg_frame_rate'].split('/') + ['1'])[:2]
        out.update(resolucion='%dx%d' % (v['width'], v['height']), fps=round(int(num) / max(int(den), 1), 2), video=v['codec_name'])
    out['audio'] = (a['codec_name'] + ' %s Hz' % a['sample_rate']) if a else 'SIN AUDIO'
    if a:
        r = subprocess.run(['ffmpeg', '-hide_banner', '-i', video, '-af', 'volumedetect', '-vn', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        for k in ('mean_volume', 'max_volume'):
            m = re.search(k + r': (-?[\d.]+) dB', r)
            if m:
                out[k] = float(m.group(1))
        r = subprocess.run(['ffmpeg', '-hide_banner', '-i', video, '-af', 'silencedetect=n=-50dB:d=1.5', '-vn', '-f', 'null', '-'],
                           capture_output=True, text=True).stderr
        out['silencios_largos'] = len(re.findall('silence_start', r))
    return out


def hoja(video, paso=3.0, cols=5):
    dur = float(_sonda(video)['format']['duration'])
    filas = max(1, math.ceil(dur / paso / cols))
    v = next(s for s in _sonda(video)['streams'] if s['codec_type'] == 'video')
    vertical = v['height'] > v['width']
    w, h = (216, 384) if vertical else (384, 216)
    p = os.path.join(_salida(), 'hoja.png')
    _ff('-i', video, '-vf', 'fps=1/%s,scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,tile=%dx%d'
        % (paso, w, h, w, h, cols, filas), '-frames:v', '1', p)
    return p


def frame(video, segundo):
    p = os.path.join(_salida(), 'frame_%s.png' % segundo)
    _ff('-ss', str(segundo), '-i', video, '-frames:v', '1', p)
    return p


def audio(video):
    p = os.path.join(_salida(), 'audio.png')
    _ff('-i', video, '-filter_complex', '[0:a]showspectrumpic=s=1200x300:legend=0[s];[0:a]showwavespic=s=1200x150[w];[s][w]vstack',
        '-frames:v', '1', p)
    return p


def principal(argv):
    if not shutil.which('ffmpeg'):
        raise SystemExit('Falta ffmpeg en el PATH.')
    if len(argv) < 2:
        raise SystemExit(__doc__)
    cmd, video, rest = argv[0], argv[1], argv[2:]
    if not os.path.isfile(video):
        raise SystemExit('No existe el vídeo: ' + video)
    if cmd == 'info':
        for k, v in info(video).items():
            print('%-18s %s' % (k, v))
    elif cmd == 'hoja':
        print(hoja(video, float(rest[0]) if rest else 3.0, int(rest[1]) if len(rest) > 1 else 5))
    elif cmd == 'frame':
        if not rest:
            raise SystemExit('Falta el segundo: revisar frame <video> <segundo>')
        print(frame(video, rest[0]))
    elif cmd == 'audio':
        print(audio(video))
        i = info(video)
        print('pico %s dB · media %s dB · silencios largos: %s' % (i.get('max_volume'), i.get('mean_volume'), i.get('silencios_largos')))
    else:
        raise SystemExit(__doc__)
