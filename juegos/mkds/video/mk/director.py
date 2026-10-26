"""Director: renderiza una cinemática (clase con cuadro(t) puro) en paralelo, la codifica con ffmpeg y le mezcla el audio.

Contrato de la cinemática (ver video/mk_demo.py):
    class MiCine:
        fps = 30; duracion = 30.0; ancho = 1080; alto = 1920
        def __init__(self, ancho, alto, ss): ...       # carga assets (se ejecuta en cada proceso)
        def cuadro(self, t) -> float32 (alto, ancho, 3) # imagen final, ya con postproceso; sin estado entre llamadas
        @staticmethod
        def audio() -> audio.Mezcla                     # (sólo en el proceso principal; no necesita assets 3D)
Uso:  python -I video/mk_demo.py [--rapido] [--frame 12.5] [--hoja 0,5,10,...] [--salida ruta.mp4]"""
import os, sys, subprocess, time, argparse, importlib
import numpy as np
from PIL import Image

from . import post, SALIDA, CACHE

_CINE = None


def _init(modulo, clase, ancho, alto, ss):
    global _CINE
    m = importlib.import_module(modulo)
    _CINE = getattr(m, clase)(ancho, alto, ss)


def _frame(args):
    i, fps = args
    return i, post.a_uint8(_CINE.cuadro(i / fps), i)


def guardar_frame(img, ruta):
    Image.fromarray(post.a_uint8(img)).save(ruta)


def hoja(cine, tiempos, ruta, escala=0.25):
    ims = []
    for t in tiempos:
        a = post.a_uint8(cine.cuadro(t)); im = Image.fromarray(a)
        im = im.resize((int(im.width * escala), int(im.height * escala)), Image.LANCZOS)
        ims.append((t, im))
    from PIL import ImageDraw
    w, h = ims[0][1].size
    cols = min(len(ims), 8); filas = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (cols * w, filas * (h + 14)), (20, 20, 30)); d = ImageDraw.Draw(S)
    for k, (t, im) in enumerate(ims):
        x, y = (k % cols) * w, (k // cols) * (h + 14)
        S.paste(im, (x, y + 14)); d.text((x + 3, y + 1), '%.2fs' % t, fill=(255, 255, 0))
    S.save(ruta)
    return ruta


def _frame_png(t):
    return t, post.a_uint8(_CINE.cuadro(t))


def hoja_mp(modulo, clase, ancho, alto, ss, tiempos, ruta, procesos, escala=0.25):
    """Hoja de contactos en paralelo (cada proceso carga la cinemática una vez)."""
    import multiprocessing as mp
    from PIL import ImageDraw
    with mp.get_context('spawn').Pool(procesos, _init, (modulo, clase, ancho, alto, ss)) as pool:
        res = dict(pool.imap_unordered(_frame_png, list(tiempos)))
    ims = []
    for t in tiempos:
        im = Image.fromarray(res[t]); im = im.resize((int(im.width * escala), int(im.height * escala)), Image.LANCZOS); ims.append((t, im))
    w, h = ims[0][1].size
    cols = min(len(ims), 8); filas = (len(ims) + cols - 1) // cols
    S = Image.new('RGB', (cols * w, filas * (h + 14)), (20, 20, 30)); d = ImageDraw.Draw(S)
    for k, (t, im) in enumerate(ims):
        x, y = (k % cols) * w, (k // cols) * (h + 14)
        S.paste(im, (x, y + 14)); d.text((x + 3, y + 1), '%.2fs' % t, fill=(255, 255, 0))
    S.save(ruta)
    return ruta


def main(modulo, clase, defecto_salida, argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--rapido', action='store_true', help='540x960 sin supermuestreo (previsualización)')
    ap.add_argument('--frame', type=float, help='guarda un fotograma (s) en cache/mkds/frame.png')
    ap.add_argument('--hoja', help='lista de segundos separados por comas, o "n" para n fotogramas uniformes')
    ap.add_argument('--salida', default=os.path.join(SALIDA, defecto_salida))
    ap.add_argument('--ss', type=float, default=None, help='supermuestreo (1 = ninguno)')
    ap.add_argument('--procesos', type=int, default=max(1, (os.cpu_count() or 4) - 1))
    ap.add_argument('--sin-audio', action='store_true')
    a = ap.parse_args(argv)
    mod = importlib.import_module(modulo); Clase = getattr(mod, clase)
    ancho, alto = (540, 960) if a.rapido else (Clase.ancho, Clase.alto)
    ss = a.ss if a.ss is not None else (1.0 if a.rapido else getattr(Clase, 'ss', 1.5))
    fps = Clase.fps; dur = Clase.duracion
    os.makedirs(SALIDA, exist_ok=True)
    if a.frame is not None or a.hoja:
        if a.hoja and a.frame is None:
            ts = ([float(x) for x in a.hoja.split(',')] if ',' in a.hoja or '.' in a.hoja
                  else list(np.linspace(0, dur - 1 / fps, int(a.hoja))))
            print(hoja_mp(modulo, clase, ancho, alto, ss, ts, os.path.join(CACHE, 'hoja.png'), a.procesos)); return
        cine = Clase(ancho, alto, ss)
        if a.frame is not None:
            r = os.path.join(CACHE, 'frame.png'); guardar_frame(cine.cuadro(a.frame), r); print(r)
        if a.hoja:
            ts = ([float(x) for x in a.hoja.split(',')] if ',' in a.hoja or '.' in a.hoja
                  else list(np.linspace(0, dur - 1 / fps, int(a.hoja))))
            print(hoja(cine, ts, os.path.join(CACHE, 'hoja.png')))
        return
    n = int(round(dur * fps))
    sin_audio = os.path.join(CACHE, 'video_sin_audio.mp4')
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (ancho, alto),
           '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', sin_audio]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    import multiprocessing as mp
    with mp.get_context('spawn').Pool(a.procesos, _init, (modulo, clase, ancho, alto, ss)) as pool:
        for k, (i, frame) in enumerate(pool.imap(_frame, [(i, fps) for i in range(n)], chunksize=2)):
            ff.stdin.write(frame.tobytes())
            if k % 30 == 0:
                el = time.time() - t0
                print('\r  %d/%d  %.1fs  (~%.0fs restantes)' % (k, n, el, el / max(k, 1) * (n - k)), end='', flush=True)
    ff.stdin.close(); ff.wait()
    print('\n  vídeo: %.1fs' % (time.time() - t0))
    if a.sin_audio:
        os.replace(sin_audio, a.salida); print(a.salida); return
    mezcla = Clase.audio()
    wav = os.path.join(CACHE, 'audio_final.wav'); mezcla.guardar(wav)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', sin_audio, '-i', wav, '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '256k', '-shortest', a.salida], check=True)
    print(a.salida)
