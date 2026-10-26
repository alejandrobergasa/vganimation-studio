"""Vídeo de prueba: Tom Nook explica el repositorio a un vecino.

Uso:  python video/prueba.py [--solo-frames t1,t2,...] [--hoja]
Salida: salida/prueba_nook.mp4 (+ .gif de menor tamaño)
"""
import os
import sys
import multiprocessing as mp

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from motor import *             # noqa: E402,F401,F403
from escena import Village      # noqa: E402
import audio as AU              # noqa: E402

DURATION = 60.0
CPS = 22.0                      # caracteres por segundo al teclear
HOLD = 1.0                      # pausa tras acabar una línea

# (quién, texto, emote del oyente, inset)
LINES = [
    ('N', '¡Hola, hola! Soy Tom Nook. Hoy te cuento cómo se hizo este vídeo, sí, sí.', None, None),
    ('V', '¡Genial! ¿Y de dónde salen todos estos dibujos?', 'hatena', None),
    ('N', 'De una única ROM: Animal Crossing: Wild World, de Nintendo DS. Nada más.', None, 'rom'),
    ('N', 'Primero leemos su sistema de ficheros: casi 17.000 archivos.', None, 'ficheros'),
    ('V', '¿Y cómo se abre eso?', 'hatena', None),
    ('N', 'Con lectores propios en Python: LZ77, modelos, texturas y animaciones.', None, 'texturas'),
    ('N', 'La música y las voces salen de un SDAT, que sintetizamos nota a nota.', None, 'onda'),
    ('N', 'Un motor compone cada fotograma y ffmpeg lo codifica. ¡Un comando y listo!', None, 'repo'),
    ('V', '¡Qué bien! ¡Gracias, Tom!', 'happy', None),
    ('N', 'Y ahora, hablemos de tu hipoteca... ¡sí, sí!', 'niko', None),
]
T_START = 5.5
GAP = 0.35


def schedule(font, width_px):
    """Calcula inicio y fin de cada línea y su texto ajustado a líneas."""
    t = T_START
    out = []
    for who, text, emote, inset in LINES:
        words, lines, cur = text.split(' '), [], ''
        for w in words:
            cand = (cur + ' ' + w).strip()
            if font.measure(cand) <= width_px:
                cur = cand
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
        typ = len(text) / CPS
        out.append(dict(who=who, text=text, wrapped=lines, emote=emote, inset=inset, t0=t, t1=t + typ, t_end=t + typ + HOLD))
        t += typ + HOLD + GAP
    return out


# ---------------------------------------------------------------- estado global por proceso
G = {}


def init():
    rom = Rom()
    G['rom'] = rom
    G['v'] = Village(rom)
    clips = {}
    for p in rom.list('anm/'):
        if p.endswith('.nsbca'):
            clips.update(load_clips(rom, [p]))
    G['nook'] = Asset(rom, 'npc_sp/model/rcn.nsbmd', ['npc_sp/model/rcn_tex.nsbtx'], clips)
    G['vil'] = Asset(rom, 'npc/model/16/17.nsbmd', ['npc/model/16/17.nsbtx'], clips)
    from ww.nitro3d import TexBank as TB
    G['vil'].banks.insert(0, TB(rom.get('cloth/0/cloth012.nsbtx')))
    G['font'] = Font(rom)
    img, tpos, npos = make_bubble(rom, 10)
    G['bubble'], G['tpos'], G['npos'] = img, tpos, npos
    G['text_w'] = 160 + 8 * 10
    G['sched'] = schedule(G['font'], G['text_w'])
    G['insets'] = build_insets(rom, G['font'])
    G['wave'] = AU.AudioBank(rom).voice_set(18)[5]


def active(t):
    for s in G['sched']:
        if s['t0'] <= t < s['t_end']:
            return s
    return None


def blink(t, phase):
    k = (t + phase) % 3.1
    return k < 0.14


def emote_clip(kind, t_since):
    if kind is None:
        return 'wait1', True, 0.0
    a, b = 'mr_%s1' % kind, 'mr_%s2' % kind
    n1 = G['nook'].anims[a].num_frames / 30.0
    if t_since < n1 or b not in G['nook'].anims:
        return a, False, t_since            # sin clip de espera: se mantiene el último fotograma
    return b, True, t_since - n1


def actor_state(who, t, s):
    """Devuelve (clip, loop, tiempo_local, tex_override) para el actor 'N' o 'V'."""
    asset = G['nook'] if who == 'N' else G['vil']
    tex = {}
    clip, loop, tl = 'wait1', True, t
    speaking = s is not None and s['who'] == who and t < s['t1']
    if speaking:
        clip, tl = 'talk1', t
    elif s is not None and s['who'] != who and s['emote']:
        clip, loop, tl = emote_clip(s['emote'], t - s['t0'])
    eyes = 'e.0'
    if blink(t, 0.0 if who == 'N' else 1.3):
        eyes = 'e.2'
    if s is not None and s['who'] != who and s['emote'] == 'happy':
        eyes = 'e.5'
    if s is not None and s['who'] != who and s['emote'] == 'hatena':
        eyes = 'e.6' if (t - s['t0']) < 1.2 else 'e.0'
    if s is not None and s['emote'] == 'niko' and s['who'] != who:
        eyes = 'e.5'
    tex['e'] = eyes
    if who == 'V':
        tex['m'] = 'm.%d' % (1 + int(t * 8) % 2) if speaking else 'm.0'
    return asset, clip, loop, tl, tex


def build_insets(rom, font):
    ins = {}
    n_files = len(rom.index)
    ins['rom'] = ['ROM: %s' % rom.title, 'Código de juego: %s' % rom.game_code, 'Región: Europa (EUR)',
                  'Formato: Nintendo DS (NitroFS)']
    sample = ['npc_sp/model/rcn.nsbmd', 'npc/model/16/17.nsbmd', 'anm/0/1.nsbca', 'font/fontA_img.bin',
              'a_mes/a_mes_bg_ncg.bin', 'sound_dataEUR.sdat']
    ins['ficheros'] = ['%d ficheros:' % n_files] + sample
    ins['repo'] = ['tools/ww/   lectores', 'tools/extraer.py', 'video/   motor + guion', 'salida/   el vídeo']
    return ins


# ---------------------------------------------------------------- dibujo
def cam_at(t):
    """(eye, target) con keyframes suaves."""
    keys = [
        (0.0, (-4.0, 4.6, 17.0), (0.0, 1.9, -2.0)),
        (5.5, (0.0, 3.2, 11.5), (0.0, 0.85, 0.0)),
        (30.0, (0.6, 3.0, 10.8), (0.2, 0.85, 0.0)),
        (52.0, (0.0, 3.2, 11.5), (0.0, 0.85, 0.0)),
        (60.0, (0.0, 5.0, 17.5), (0.0, 1.8, -2.0)),
    ]
    for (t0, e0, g0), (t1, e1, g1) in zip(keys, keys[1:]):
        if t0 <= t <= t1:
            u = float(ease((t - t0) / (t1 - t0)))
            return np.array(e0) * (1 - u) + np.array(e1) * u, np.array(g0) * (1 - u) + np.array(g1) * u
    return np.array(keys[-1][1]), np.array(keys[-1][2])


NOOK_POS = np.array([-1.9, 0.0, 1.0])
VIL_POS = np.array([1.9, 0.0, 1.0])


def vil_walk(t):
    """Posición y giro del vecino: entra caminando desde la derecha hasta su sitio."""
    t0, t1 = 0.6, 4.6
    if t < t0:
        return np.array([11.0, 0, 1.0]), yaw_facing(-1, 0.1), 'walk1', t
    if t < t1:
        u = (t - t0) / (t1 - t0)
        p = np.array([11.0 + (VIL_POS[0] - 11.0) * u, 0, 1.0 + (VIL_POS[2] - 1.0) * u])
        return p, yaw_facing(-1, 0.1), 'walk1', t
    # se gira hacia Nook y la cámara
    u = ease((t - t1) / 0.8)
    yaw = (1 - u) * yaw_facing(-1, 0.1) + u * yaw_facing(-1, 1.0)
    return VIL_POS.copy(), yaw, None, t


def panel(dst, x, y, w, h):
    fill_rect(dst, x - 2, y - 2, w + 4, h + 4, (0.95, 0.55, 0.15))
    fill_rect(dst, x, y, w, h, (1.0, 0.99, 0.93))


def draw_inset(dst, kind, t, s):
    font = G['font']
    u = min((t - s['t0']) / 0.35, 1.0, (s['t_end'] - t) / 0.35)
    if u <= 0:
        return
    w, h = 252, 112
    x, y = W - w - 14 + int((1 - ease(u)) * 40), 14
    a = float(ease(u))
    tmp = dst.copy()
    panel(tmp, x, y, w, h)
    ink = (0.25, 0.12, 0.05)
    rom = G['rom']
    if kind in ('rom', 'ficheros', 'repo'):
        for i, line in enumerate(G['insets'][kind]):
            font.draw(tmp, x + 10, y + 8 + i * 15, line, ink)
    elif kind == 'texturas':
        from ww.nitro3d import TexBank
        banks = G['nook'].banks
        names = [('b0', 'b0_pl'), ('b1', 'b1_pl'), ('w', 'w_pl')]
        cx = x + 10
        for nm, pl in names:
            for b in banks:
                if nm in b.texs:
                    im = b.decode(nm, pl)
                    sc = max(1, 56 // max(im.shape[:2]))
                    big = np.repeat(np.repeat(im, sc, 0), sc, 1)
                    blit(tmp, big, cx, y + 10)
                    cx += big.shape[1] + 8
                    break
        eyes = G['nook'].banks[0].decode('e.0', 'e_pl')
        blit(tmp, np.repeat(np.repeat(eyes, 1, 0), 1, 1), cx, y + 10)
        font.draw(tmp, x + 10, y + 78, 'Texturas NSBTX decodificadas', ink)
        font.draw(tmp, x + 10, y + 93, 'de Tom Nook', ink)
    elif kind == 'onda':
        wv = G['wave']
        n = w - 24
        idx = np.linspace(0, len(wv) - 1, n).astype(int)
        ys = (wv[idx] * 28).astype(int)
        for i in range(n):
            fill_rect(tmp, x + 12 + i, y + 40 - ys[i] if ys[i] > 0 else y + 40, 1, abs(ys[i]) + 1, (0.2, 0.45, 0.85))
        font.draw(tmp, x + 10, y + 78, 'Una sílaba de voz (onda SWAV)', ink)
        font.draw(tmp, x + 10, y + 93, 'del SDAT, 8000 Hz', ink)
    dst[...] = dst * (1 - a) + tmp * a


def frame(t):
    if not G:
        init()
    s = active(t)
    # --- actores
    vp, vyaw, vclip, vt = vil_walk(t)
    n_asset, n_clip, n_loop, n_tl, n_tex = actor_state('N', t, s)
    v_asset, v_clip, v_loop, v_tl, v_tex = actor_state('V', t, s)
    if vclip == 'walk1':
        v_clip, v_loop, v_tl = 'walk1', True, t * 0.75
        v_tex['e'] = 'e.0'
    # Nook mira a la cámara y al vecino
    nook_yaw = yaw_facing(1.0, 1.2)
    if t < 5.0:
        nook_yaw = yaw_facing(0.2, 1.0) + 0.0
        u = ease((t - 3.8) / 1.2)
        nook_yaw = (1 - u) * yaw_facing(0.2, 1.0) + u * yaw_facing(1.0, 1.2)
    def pose_of(asset, clip, tl, loop):
        if clip == 'talk1':
            return pose_layered(asset, 'wait1', tl, 'talk1', tl)
        return pose_at(asset, clip, tl, loop)
    acts = [
        dict(asset=n_asset, world=world_matrix(NOOK_POS, nook_yaw, 1.0), pose=pose_of(n_asset, n_clip, n_tl, n_loop), tex=n_tex),
        dict(asset=v_asset, world=world_matrix(vp, vyaw, 1.0), pose=pose_of(v_asset, v_clip, v_tl, v_loop), tex=v_tex),
    ]
    eye, tgt = cam_at(t)
    view = look_at(eye, tgt)
    cv = G['v'].render(view, acts)
    img = cv.to_image()[..., :3].astype(np.float32) / 255.0
    font = G['font']
    # --- título
    if t < 4.8:
        a = float(np.clip(min((t - 0.2) / 0.5, (4.8 - t) / 0.6), 0, 1))
        fill_rect(img, 0, 24, W, 118, (0.05, 0.12, 0.3), 0.55 * a)
        for txt, yy, sc in (('Animal Crossing: Wild World', 40, 3), ('De la ROM al vídeo', 100, 2)):
            mask = np.zeros((18, font.measure(txt) + 20), np.float32)
            cx = 1
            for ch in txt:
                g = font.glyph.get(ch)
                if g is not None:
                    mask[1:17, cx:cx + 16] = np.maximum(mask[1:17, cx:cx + 16], g)
                cx += font.advance(ch)
            big = np.repeat(np.repeat(mask, sc, 0), sc, 1)
            # sombra + texto
            hh, ww = big.shape
            x0 = (W - ww) // 2
            for (dx, dy, col) in ((sc, sc, (0.1, 0.2, 0.45)), (0, 0, (1.0, 1.0, 0.95))):
                reg = img[yy + dy:yy + dy + hh, x0 + dx:x0 + dx + ww]
                m = (big * a)[..., None]
                reg[...] = reg * (1 - m) + np.array(col, np.float32) * m
    # --- inset
    if s is not None and s['inset']:
        draw_inset(img, s['inset'], t, s)
    # --- diálogo
    if s is not None:
        bub = G['bubble']
        bx, by = (W - bub.shape[1]) // 2, H - bub.shape[0] - 16
        u = float(ease(min((t - s['t0']) / 0.2, 1.0)))
        blit(img, bub, bx, by + (1 - u) * 14, alpha=u)
        tx, ty = G['tpos']
        nx, ny = G['npos']
        name = 'Tom Nook' if s['who'] == 'N' else 'Vecino'
        font.draw(img, bx + nx + 4, by + ny - 0, name, (0.1, 0.25, 0.5))
        shown = int(max(0, (t - s['t0'])) * CPS)
        rem = shown
        for i, line in enumerate(s['wrapped']):
            part = line[:rem]
            rem -= len(line) + 1
            if part:
                font.draw(img, bx + tx, by + ty + i * 16, part, (0.25, 0.12, 0.05))
            if rem <= 0:
                break
    # --- fundidos
    f = 1.0
    f = min(f, (t) / 0.4)
    f = min(f, (DURATION - t) / 1.2)
    img *= float(np.clip(f, 0, 1))
    out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    return upscale(out)


def final_text(img, t):
    pass


def _worker(i):
    return frame(i / FPS)


def build_audio(rom, path):
    A = AU.AudioBank(rom)
    mix = AU.Mixer(DURATION + 2)
    mix.add(0.0, A.music(37, DURATION + 1), gain=0.55)
    vN = A.voice_set(18)
    vV = A.voice_set(19)
    rng = np.random.RandomState(3)
    sched = schedule(Font(rom), 240)
    for s in sched:
        voice, pitch, pan = (vN, 0.78, -0.2) if s['who'] == 'N' else (vV, 1.35, 0.2)
        for dt, w in AU.speech_blips(s['text'], voice, pitch, rng, CPS):
            if s['t0'] + dt < s['t1']:
                mix.add(s['t0'] + dt, w, gain=0.9, pan=pan)
    mix.fade_out(DURATION - 2.0, DURATION)
    mix.save(path, DURATION)
    return A, vN


if __name__ == '__main__':
    mp.freeze_support()
    out_dir = rutas.salida('animal-crossing')
    os.makedirs(out_dir, exist_ok=True)
    args = sys.argv[1:]
    if '--solo-frames' in args:
        ts = [float(x) for x in args[args.index('--solo-frames') + 1].split(',')]
        from PIL import Image
        init()
        tmp = os.path.join(rutas.trabajo('animal-crossing'), 'frames')
        os.makedirs(tmp, exist_ok=True)
        ims = [frame(t) for t in ts]
        for t, im in zip(ts, ims):
            Image.fromarray(im).save(os.path.join(tmp, 'f_%05.1f.png' % t))
        print('ok', len(ims))
        sys.exit(0)
    rom = Rom()
    wav = os.path.join(rutas.trabajo('animal-crossing'), '_audio_prueba.wav')
    A, vN = build_audio(rom, wav)
    n = int(DURATION * FPS)
    with mp.Pool(max(1, mp.cpu_count() - 1), initializer=init) as pool:
        write_video(pool.imap(_worker, range(n), chunksize=4), os.path.join(out_dir, 'prueba_nook.mp4'), audio=wav)
    print('hecho')
