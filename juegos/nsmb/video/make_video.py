"""Genera el vídeo 'Un paseo por el Mundo 1-1' (256x192, 30 fps, escalado x3) a salida/."""
import sys, os, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from PIL import Image
import world, sim, engine, text, audio
from rom import rutas

FPS, SCALE = 30, 3
INTRO, OUTRO = 3.5, 6.0
OUT = rutas.salida('nsmb')
TMP = rutas.cache('nsmb')


def title_card(img, k, lines):
    """Pinta líneas centradas con alfa k (0..1)."""
    for (s, y, big) in lines:
        t = text.render(s)
        if big: t = t.resize((t.width * 2, t.height * 2), Image.NEAREST)
        a = np.asarray(t).copy(); a[..., 3] = (a[..., 3] * k).astype(np.uint8)
        img.alpha_composite(Image.fromarray(a, 'RGBA'), ((engine.SW - t.width) // 2, y))


def plan():
    w = world.get(); fr, ev = sim.run(w)
    assert not [e for e in ev if e[1].startswith(('HIT', 'FALL'))], ev
    sc = engine.Scene(w)
    return w, fr, sc


def render(path_video, w, fr, sc, only=None):
    n_intro = int(INTRO * FPS); n_run = len(fr) // 2; n_out = int(OUTRO * FPS)
    total = n_intro + n_run + n_out
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{engine.SW*SCALE}x{engine.SH*SCALE}',
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '14', '-preset', 'slow', path_video]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE) if path_video else None
    stills = {}
    f0 = fr[0]
    end_f = fr[-1]
    for k in range(total):
        if k < n_intro:
            f = dict(f0, cam=0); t60 = k * 2
            im = sc.frame(f, t60, wait=True, time_left=400)
            kk = min(1.0, k / 20.0)
            title_card(im, max(0.0, min(1.0, (n_intro - 5 - k) / 12.0)) * min(1.0, k / 20.0),
                       [('NEW SUPER', 34, True), ('MARIO BROS.', 62, True), ('UN PASEO POR EL MUNDO 1-1', 98, False)])
            im = engine.fade(im, kk)
        elif k < n_intro + n_run:
            i = (k - n_intro) * 2
            f = fr[i]; t60 = i
            tl = 400 - min(i, fr_pole_t(fr)) // 36
            im = sc.frame(f, t60, time_left=tl).convert('RGBA')
            if k == n_intro: pass
        else:
            j = k - n_intro - n_run
            f = dict(end_f, foes=[], coins=[], state='done')
            im = sc.frame(f, end_f['t'] + j * 2, time_left=400 - fr_pole_t(fr) // 36).convert('RGBA')
            # Mario entra en el castillo: se oculta a mitad de puerta
            a = min(1.0, j / 20.0)
            im = _hide_mario(sc, f, end_f, j, w)
            title_card(im, min(1.0, max(0.0, (j - 24) / 15.0)), [('¡MUNDO 1-1', 40, True), ('SUPERADO!', 68, True), ('Monedas: %d' % end_f['ncoin'], 106, False)])
            im = engine.fade(im, 1.0 if j < n_out - 20 else max(0.0, (n_out - j) / 20.0))
        rgb = im.convert('RGB')
        if only is not None and k in only: stills[k] = rgb.copy()
        if pr: pr.stdin.write(rgb.resize((engine.SW * SCALE, engine.SH * SCALE), Image.NEAREST).tobytes())
    if pr: pr.stdin.close(); pr.wait()
    return stills, total


def fr_pole_t(fr):
    return next(f['t'] for f in fr if f['state'] == 'pole')


def _hide_mario(sc, f, end_f, j, w):
    """Mario ya está en la puerta: se pinta la escena sin él (entra en el castillo)."""
    saved = sc.mario_pose
    img = sc.frame(dict(f, y=10000), end_f['t'], time_left=400 - fr_pole_t_cached(sc) // 36)
    return img


_pole_t = {}


def fr_pole_t_cached(sc): return _pole_t.get('t', 0)


def audio_mix(fr, total_s):
    pole_t = fr_pole_t(fr)
    ev = []
    for f in fr:
        for e in f['ev']:
            ev.append((INTRO + f['t'] / 60.0, e))
    flag_t = INTRO + pole_t / 60.0
    clear_t = next(INTRO + f['t'] / 60.0 for f in fr if 'fanfare' in f['ev'])
    return audio.build(ev, total_s, flag_t, clear_t)


def main():
    os.makedirs(OUT, exist_ok=True)
    w, fr, sc = plan()
    _pole_t['t'] = fr_pole_t(fr)
    tmp = os.path.join(TMP, 'video_sin_audio.mp4')
    stills, total = render(tmp, w, fr, sc)
    total_s = total / FPS
    mix = audio_mix(fr, total_s)
    wav = os.path.join(TMP, 'mezcla.wav'); audio.write_wav(wav, mix)
    final = os.path.join(OUT, 'nsmb_paseo_mundo_1-1.mp4')
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp, '-i', wav, '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                           '-ar', '44100', '-shortest', '-movflags', '+faststart', final])
    print(final, '%.1f s' % total_s)


if __name__ == '__main__':
    if '--casino' in sys.argv:
        import casino_3d
        casino_3d.main()
    elif '--renfe' in sys.argv:
        import renfe
        renfe.main()
    else:
        main()
