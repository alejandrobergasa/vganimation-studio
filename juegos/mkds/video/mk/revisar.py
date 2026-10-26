"""Revisión del MP4 entregado: ficha técnica, hoja de fotogramas y nivel de audio por segundo.
Uso:  python -I video/mk/revisar.py salida/mk_demo_carrera.mp4 [n_fotogramas=24]
Genera cache/mkds/revision_hoja.png (mirarla) y cache/mkds/revision_audio.png."""
import os, sys, json, subprocess, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import numpy as np
from PIL import Image, ImageDraw
import mk


def ficha(ruta):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', ruta], capture_output=True, text=True)
    j = json.loads(r.stdout)
    v = next(s for s in j['streams'] if s['codec_type'] == 'video')
    a = next((s for s in j['streams'] if s['codec_type'] == 'audio'), None)
    print('vídeo %s %sx%s %s fps, %.2f s, %.1f MB' % (v['codec_name'], v['width'], v['height'], v['avg_frame_rate'],
                                                   float(j['format']['duration']), int(j['format']['size']) / 1e6))
    print('audio', (a['codec_name'], a.get('sample_rate'), a.get('channels')) if a else 'NO TIENE')
    return float(j['format']['duration']), v


def hoja(ruta, n=24, escala=0.2):
    dur, v = ficha(ruta)
    ims = []
    with tempfile.TemporaryDirectory() as d:
        for i in range(n):
            t = dur * (i + 0.5) / n
            p = os.path.join(d, '%03d.png' % i)
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '%.3f' % t, '-i', ruta, '-frames:v', '1', p], check=True)
            im = Image.open(p).convert('RGB'); im = im.resize((int(im.width * escala), int(im.height * escala)), Image.LANCZOS)
            ims.append((t, im))
    w, h = ims[0][1].size; cols = 8; filas = (n + cols - 1) // cols
    S = Image.new('RGB', (cols * w, filas * (h + 14)), (20, 20, 30)); dr = ImageDraw.Draw(S)
    for k, (t, im) in enumerate(ims):
        x, y = (k % cols) * w, (k // cols) * (h + 14)
        S.paste(im, (x, y + 14)); dr.text((x + 3, y + 1), '%.1fs' % t, fill=(255, 255, 0))
    out = os.path.join(mk.CACHE, 'revision_hoja.png'); S.save(out); print(out)


def audio(ruta):
    r = subprocess.run(['ffmpeg', '-v', 'error', '-i', ruta, '-vn', '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'], capture_output=True)
    x = np.frombuffer(r.stdout, np.float32)
    if len(x) == 0: print('sin audio'); return
    fs = 16000; n = len(x) // fs
    rms = [float(np.sqrt((x[i * fs:(i + 1) * fs] ** 2).mean())) for i in range(n)]
    print('pico %.3f  rms medio %.3f  silencios (<0,005): %s' % (np.abs(x).max(), np.mean(rms), [i for i, r_ in enumerate(rms) if r_ < 0.005]))
    W, H = n * 20, 120
    im = Image.new('RGB', (W, H), (20, 20, 30)); d = ImageDraw.Draw(im)
    for i, r_ in enumerate(rms): d.rectangle([i * 20 + 2, H - min(H, int(r_ * 600)), i * 20 + 18, H], fill=(90, 200, 255))
    out = os.path.join(mk.CACHE, 'revision_audio.png'); im.save(out); print(out)


if __name__ == '__main__':
    ruta = sys.argv[1]
    hoja(ruta, int(sys.argv[2]) if len(sys.argv) > 2 else 24)
    audio(ruta)
