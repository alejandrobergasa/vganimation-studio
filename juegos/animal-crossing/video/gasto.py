"""Vídeo vertical (móvil, 1080x1920): Tom Nook explica a un vecino en qué se gasta el dinero público en España.

Datos: IGAE, «Gasto público 2019-2023», COFOG, Administraciones Públicas, 2023 (provisional), millones de euros.
Uso:  python -I video/gasto.py [--solo-frames t1,t2,...]
Salida: salida/gasto_publico.mp4
"""
import os
import sys
import multiprocessing as mp

os.environ.setdefault('VIDEO_VERTICAL', '1')        # antes de importar el motor: 360x640 x3

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from motor import *             # noqa: E402,F401,F403
from escena import Village      # noqa: E402
import audio as AU              # noqa: E402
import reggaeton as RG          # noqa: E402

CPS = 22.0                      # caracteres por segundo al teclear
HOLD = 0.9                      # pausa tras acabar una línea
GAP = 0.3
T_START = 3.4
INK = (0.25, 0.12, 0.05)

# ---------------------------------------------------------------- datos (IGAE, 2023 P, millones de euros)
TOTAL = 680952
INTERESES = 35707
CATS = [  # nombre, millones, color, icono
    ('Protección social', 277104, (0.95, 0.45, 0.35), 'gente'),
    ('Sanidad', 98624, (0.95, 0.55, 0.75), 'corazon'),
    ('Servicios generales', 84784, (0.60, 0.48, 0.88), 'edificio'),
    ('Asuntos económicos', 74958, (0.98, 0.78, 0.25), 'moneda'),
    ('Educación', 63040, (0.35, 0.65, 0.95), 'libro'),
    ('Orden público', 27443, (0.35, 0.42, 0.72), 'escudo'),
    ('Cultura y ocio', 18729, (0.50, 0.82, 0.45), 'nota'),
    ('Medio ambiente', 14640, (0.22, 0.62, 0.38), 'arbol'),
    ('Defensa', 13987, (0.58, 0.58, 0.58), 'estrella'),
    ('Vivienda', 7643, (0.82, 0.56, 0.35), 'casa'),
]
PCT = [v * 100.0 / TOTAL for _, v, _, _ in CATS]
PCT_INT = INTERESES * 100.0 / TOTAL


def fmt(x):
    return ('%.1f' % x).replace('.', ',')


ICONS = {
    'corazon': ['.........', '.##...##.', '####.####', '#########', '#########', '.#######.', '..#####..', '...###...', '....#....'],
    'gente': ['...###...', '..#####..', '..#####..', '...###...', '.#######.', '#########', '.#######.', '.##...##.', '.##...##.'],
    'edificio': ['....#....', '..#####..', '.#######.', '#########', '.#.#.#.#.', '.#.#.#.#.', '.#.#.#.#.', '#########', '#########'],
    'moneda': ['..#####..', '.#.....#.', '#..###..#', '#.#.....#', '#..##...#', '#.#.....#', '#..###..#', '.#.....#.', '..#####..'],
    'libro': ['#########', '#.##.##.#', '#.##.##.#', '#.##.##.#', '#.##.##.#', '#.##.##.#', '#.##.##.#', '#.......#', '#########'],
    'escudo': ['.#######.', '#########', '#########', '#########', '#########', '.#######.', '..#####..', '...###...', '....#....'],
    'nota': ['...#####.', '...#...#.', '...#...#.', '...#...#.', '...#...#.', '.###.###.', '####.###.', '.##...#..', '.........'],
    'arbol': ['...###...', '..#####..', '.#######.', '#########', '.#######.', '..#####..', '....#....', '....#....', '...###...'],
    'estrella': ['....#....', '....#....', '...###...', '#########', '.#######.', '..#####..', '..##.##..', '.##...##.', '.#.....#.'],
    'casa': ['....#....', '...###...', '..#####..', '.#######.', '#########', '.#######.', '.##...##.', '.##.#.##.', '.##.#.##.'],
}
ICONS = {k: np.array([[c == '#' for c in row] for row in v]) for k, v in ICONS.items()}

# ---------------------------------------------------------------- guion
# (quién, texto, emote del oyente, plano, revelados) · plano: wide | nook | vil | board
# revelados: [(fragmento del texto, n.º de categorías visibles al teclearlo)] o 'int' para el recuadro de intereses.
LINES = [
    ('N', '¡Hola, vecino! Soy Tom Nook, sí, sí.', None, 'wide', []),
    ('N', '¿Sabes en qué gasta España tu dinero?', None, 'wide', []),
    ('V', 'Pues... ¡ni idea, Tom!', 'niko', 'vil', []),
    ('N', 'En 2023 gastó 681.000 millones de euros.', None, 'nook', []),
    ('N', 'Imagina que son 100 €. ¡Mira cómo se reparten!', None, 'board', []),
    ('N', '40,7 € a protección social: pensiones y paro.', None, 'board', [('40,7', 1)]),
    ('V', '¡Casi la mitad!', 'happy', 'vil', []),
    ('N', '14,5 € a sanidad: hospitales y médicos.', None, 'board', [('14,5', 2)]),
    ('N', '12,5 € a servicios generales.', None, 'board', [('12,5', 3)]),
    ('N', '¡Y 5,2 € son solo intereses de la deuda!', None, 'board', [('5,2', 'int')]),
    ('V', '¿Intereses? ¡Como los de mi hipoteca!', 'hatena', 'vil', []),
    ('N', '¡Sí, sí! 11 € a asuntos económicos.', 'happy', 'board', [('11 €', 4)]),
    ('N', '9,3 € a educación: colegios y universidades.', None, 'board', [('9,3', 5)]),
    ('N', '4 € a orden público: policía y justicia.', None, 'board', [('4 €', 6)]),
    ('N', '2,8 € a cultura y ocio.', None, 'board', [('2,8', 7)]),
    ('N', '2,1 € a medio ambiente.', None, 'board', [('2,1', 8)]),
    ('N', '2,1 € a defensa y solo 1,1 € a vivienda.', None, 'board', [('2,1', 9), ('1,1', 10)]),
    ('V', '¡Qué claro lo explicas, Tom!', 'niko', 'board', []),
    ('N', 'Datos de la IGAE, 2023. ¡Y ahora hablemos de tu hipoteca!', 'niko', 'wide', []),
]
DESC = ['Pensiones, paro y ayudas', 'Hospitales, médicos y medicinas', 'Administración general y deuda',
        'Transporte, energía y campo', 'Colegios, institutos y universidades', 'Policía, tribunales y cárceles',
        'Deporte, museos y teatros', 'Parques, residuos y aguas', 'Fuerzas Armadas', 'Vivienda y servicios del barrio']
TS = 2          # escala del texto del diálogo


def wrap(font, text, width_px, scale=1):
    lines, cur = [], ''
    for w in text.split(' '):
        cand = (cur + ' ' + w).strip()
        if font.measure(cand, scale) <= width_px:
            cur = cand
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def schedule(font, width_px):
    t = T_START
    out = []
    reveals = {}
    for who, text, emote, shot, revs in LINES:
        lines = wrap(font, text, width_px, TS)
        assert len(lines) <= 3, 'demasiado largo: %r' % text
        typ = len(text) / CPS
        for frag, k in revs:
            reveals[k] = t + (text.find(frag) + len(frag)) / CPS
        out.append(dict(who=who, text=text, wrapped=lines, emote=emote, shot=shot, t0=t, t1=t + typ, t_end=t + typ + HOLD))
        t += typ + HOLD + GAP
    return out, reveals, t


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
    img, tpos, npos = make_bubble(rom, 13, extra_rows=5)
    G['bubble'], G['tpos'], G['npos'] = img, tpos, npos
    G['text_w'] = img.shape[1] - tpos[0] - 30
    G['sched'], G['reveals'], G['end'] = schedule(G['font'], G['text_w'])


def active(t):
    for s in G['sched']:
        if s['t0'] <= t < s['t_end']:
            return s
    return None


def current_shot(t):
    """(nombre, inicio de la tanda de planos iguales, fin) del plano en el instante t."""
    S = G['sched']
    if t < T_START:
        return 'wide', 0.0, S[0]['t0']
    idx = 0
    for i, s in enumerate(S):
        if s['t0'] - GAP / 2 <= t:
            idx = i
    name = S[idx]['shot']
    a = idx
    while a > 0 and S[a - 1]['shot'] == name:
        a -= 1
    b = idx
    while b < len(S) - 1 and S[b + 1]['shot'] == name:
        b += 1
    return name, S[a]['t0'] - GAP / 2, S[b]['t_end']


def blink(t, phase):
    return (t + phase) % 3.1 < 0.14


def emote_clip(kind, t_since):
    if kind is None:
        return 'wait1', True, 0.0
    a, b = 'mr_%s1' % kind, 'mr_%s2' % kind
    n1 = G['nook'].anims[a].num_frames / 30.0
    if t_since < n1 or b not in G['nook'].anims:
        return a, False, t_since
    return b, True, t_since - n1


def actor_state(who, t, s):
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
    if s is not None and s['who'] != who and s['emote'] in ('happy', 'niko'):
        eyes = 'e.5'
    if s is not None and s['who'] != who and s['emote'] == 'hatena':
        eyes = 'e.6' if (t - s['t0']) < 1.2 else 'e.0'
    tex['e'] = eyes
    if who == 'V':
        tex['m'] = 'm.%d' % (1 + int(t * 8) % 2) if speaking else 'm.0'
    return asset, clip, loop, tl, tex


# ---------------------------------------------------------------- cámara
NOOK_POS = np.array([-1.25, 0.0, 1.0])
VIL_POS = np.array([1.25, 0.0, 1.0])
# plano: (eye0, target0, eye1, target1, fov): se mueve despacio de 0 a 1 durante la tanda
SHOTS = {
    'wide': ((0.0, 3.4, 18.5), (0.0, 1.6, 0.8), (0.0, 3.0, 16.0), (0.0, 1.4, 0.8), 34.0),
    'board': ((0.0, 2.4, 17.8), (0.0, 2.3, 0.8), (0.0, 2.4, 17.0), (0.0, 2.25, 0.8), 34.0),
    'nook': ((1.2, 1.9, 7.4), (-1.25, 1.35, 1.0), (0.6, 1.85, 6.4), (-1.25, 1.35, 1.0), 34.0),
    'vil': ((-1.2, 1.9, 7.4), (1.25, 1.4, 1.0), (-0.6, 1.85, 6.4), (1.25, 1.4, 1.0), 34.0),
}


def camera(t):
    name, ta, tb = current_shot(t)
    e0, g0, e1, g1, fov = SHOTS[name]
    u = float(np.clip((t - ta) / max(tb - ta, 1e-3), 0, 1))
    e = np.array(e0) * (1 - u) + np.array(e1) * u
    g = np.array(g0) * (1 - u) + np.array(g1) * u
    return e, g, fov, name


def vil_walk(t):
    t0, t1 = 0.4, 2.7
    x0 = 8.5
    if t < t0:
        return np.array([x0, 0, 1.0]), yaw_facing(-1, 0.1), 'walk1', t
    if t < t1:
        u = (t - t0) / (t1 - t0)
        return np.array([x0 + (VIL_POS[0] - x0) * u, 0, 1.0]), yaw_facing(-1, 0.1), 'walk1', t
    u = ease((t - t1) / 0.6)
    yaw = (1 - u) * yaw_facing(-1, 0.1) + u * yaw_facing(-0.8, 1.4)
    return VIL_POS.copy(), yaw, None, t


# ---------------------------------------------------------------- 2D: textos y gráficos
def big_text(img, font, txt, y, sc_max, a, colors=((0.1, 0.2, 0.45), (1.0, 1.0, 0.95)), x_center=None):
    w_txt = font.measure(txt) + 4
    sc = max(1, min(sc_max, (W - 16) // (w_txt + 16)))
    mask = np.zeros((18, w_txt + 16), np.float32)
    cx = 1
    for ch in txt:
        g = font.glyph.get(ch)
        if g is not None:
            mask[1:17, cx:cx + 16] = np.maximum(mask[1:17, cx:cx + 16], g)
        cx += font.advance(ch)
    big = np.repeat(np.repeat(mask, sc, 0), sc, 1)
    hh, ww = big.shape
    x0 = ((W if x_center is None else x_center * 2) - ww) // 2
    for (dx, dy, col) in ((sc, sc, colors[0]), (0, 0, colors[1])):
        yy0, xx0 = y + dy, x0 + dx
        reg = img[max(yy0, 0):yy0 + hh, max(xx0, 0):xx0 + ww]
        m = (big[:reg.shape[0], :reg.shape[1]] * a)[..., None]
        reg[...] = reg * (1 - m) + np.array(col, np.float32) * m
    return sc


def rrect(dst, x, y, w, h, color, r=3, alpha=1.0):
    """Rectángulo con esquinas redondeadas (pixel art)."""
    for i in range(r):
        inset = r - int(round(np.sqrt(r * r - (r - i - 0.5) ** 2)))
        fill_rect(dst, x + inset, y + i, w - 2 * inset, 1, color, alpha)
        fill_rect(dst, x + inset, y + h - 1 - i, w - 2 * inset, 1, color, alpha)
    fill_rect(dst, x, y + r, w, h - 2 * r, color, alpha)


def panel(dst, x, y, w, h):
    """Cuadro estilo Animal Crossing: sombra, borde naranja, interior crema con puntitos."""
    rrect(dst, x - 3, y - 2, w + 6, h + 8, (0.0, 0.0, 0.0), 6, 0.28)
    rrect(dst, x - 3, y - 3, w + 6, h + 6, (0.55, 0.32, 0.12), 6)
    rrect(dst, x - 2, y - 2, w + 4, h + 4, (0.97, 0.66, 0.25), 6)
    rrect(dst, x, y, w, h, (1.0, 0.97, 0.86), 5)
    for yy in range(y + 6, y + h - 4, 12):
        for xx in range(x + 6 + (yy // 12 % 2) * 6, x + w - 4, 12):
            fill_rect(dst, xx, yy, 2, 2, (0.98, 0.91, 0.72))


def dark(col, k=0.55):
    return tuple(c * k for c in col)


def draw_icon(dst, x, y, name, color, sc=2):
    """Ficha redondeada de color con el icono (9x9 ampliado sc veces) en blanco. Devuelve su lado."""
    n = 9 * sc + 4
    rrect(dst, x, y, n + 2, n + 2, (0.25, 0.12, 0.05), 3)
    rrect(dst, x + 1, y + 1, n, n, color, 3)
    fill_rect(dst, x + 3, y + 2, n - 4, 2, (1, 1, 1), 0.35)
    ys, xs = np.nonzero(ICONS[name])
    for yy, xx in zip(ys, xs):
        fill_rect(dst, x + 3 + xx * sc, y + 3 + yy * sc, sc, sc, (1.0, 1.0, 0.95))
    return n + 2


def sparkle(dst, cx, cy, r, col=(1.0, 0.98, 0.7)):
    fill_rect(dst, cx - r, cy, 2 * r + 1, 1, col)
    fill_rect(dst, cx, cy - r, 1, 2 * r + 1, col)
    fill_rect(dst, cx - 1, cy - 1, 3, 3, (1, 1, 1))


def reveal_times():
    r = G['reveals']
    return [r.get(k + 1) for k in range(10)], r.get('int')


def draw_board(dst, t, name_shot_t0):
    font = G['font']
    u = float(ease(min((t - name_shot_t0) / 0.3, 1.0)))
    if u <= 0:
        return
    px, py, pw, ph = 14, 22, W - 28, 276
    py += int((1 - u) * -(ph + 30))
    tmp = dst.copy()
    panel(tmp, px, py, pw, ph)
    # cinta de título
    rrect(tmp, px + 8, py + 8, pw - 16, 36, (0.25, 0.12, 0.05), 5)
    rrect(tmp, px + 9, py + 9, pw - 18, 34, (0.30, 0.68, 0.38), 5)
    fill_rect(tmp, px + 12, py + 11, pw - 24, 3, (1, 1, 1), 0.3)
    font.draw(tmp, px + 18, py + 12, 'Gasto público', (1, 1, 0.95), shadow=(0.1, 0.35, 0.15), scale=2)
    sub = '2023'
    font.draw(tmp, px + pw - 18 - font.measure(sub, 2), py + 12, sub, (1.0, 0.95, 0.5), shadow=(0.1, 0.35, 0.15), scale=2)
    rt, rint = reveal_times()
    shown = [i for i in range(10) if rt[i] is not None and t >= rt[i]]
    cur = max(shown) if shown else None
    summary = cur == 9 and t > rt[9] + 2.2
    # --- columna de 100 €
    x0, w0, k100 = px + 16, 76, 1.8
    y_b = py + ph - 14
    y_t = y_b - 100 * k100
    font.draw(tmp, x0 + 14, y_t - 20, '100 €', INK, bold=True)
    rrect(tmp, x0 - 3, y_t - 3, w0 + 6, 100 * k100 + 6, (0.25, 0.12, 0.05), 4)
    rrect(tmp, x0, y_t, w0, 100 * k100, (0.92, 0.88, 0.76), 3)
    cum = 0.0
    for i, (nm, v, col, ic) in enumerate(CATS):
        p = PCT[i]
        a = float(ease((t - rt[i]) / 0.55)) if rt[i] is not None and t >= rt[i] else 0.0
        if a > 0:
            seg_h = max(2.0, p * k100 * a)
            top = y_b - cum * k100 - seg_h
            fill_rect(tmp, x0, top, w0, seg_h, col)
            fill_rect(tmp, x0, top, 7, seg_h, (1, 1, 1), 0.28)                 # brillo
            fill_rect(tmp, x0 + w0 - 6, top, 6, seg_h, (0, 0, 0), 0.14)         # sombra
            fill_rect(tmp, x0, top, w0, 1, dark(col, 0.45))
            if i == 2 and rint is not None and t >= rint:
                h_i = PCT_INT * k100 * float(ease((t - rint) / 0.5))
                for yy in range(int(h_i)):
                    for xx in range(w0):
                        if (xx + yy) % 6 < 2:
                            fill_rect(tmp, x0 + xx, y_b - cum * k100 - yy - 1, 1, 1, (0.28, 0.18, 0.55))
            if p * k100 >= 15 and a >= 1.0:
                lab = fmt(p)
                font.draw(tmp, x0 + (w0 - font.measure(lab)) // 2, top + (seg_h - 12) // 2 - 2, lab, (1, 1, 1), shadow=dark(col, 0.4))
            if i == cur and t - rt[i] < 0.8:                                   # destello y chispas
                fill_rect(tmp, x0, top, w0, seg_h, (1, 1, 1), 0.55 * (1 - (t - rt[i]) / 0.8))
                for k in range(5):
                    ph_ = (t - rt[i]) * 1.6 + k * 0.37
                    sparkle(tmp, int(x0 + 8 + (k * 17 + i * 13) % (w0 - 8)), int(top - 4 - 22 * (ph_ % 1.0) - k * 3), 2 + (k % 2))
        cum += p
    # --- tarjeta de la categoría actual o resumen
    cx0, cy0 = x0 + w0 + 16, py + 54
    cw, ch = px + pw - 12 - cx0, ph - 54 - 12
    if cur is not None and not summary:
        nm, v, col, ic = CATS[cur]
        a = float(ease((t - rt[cur]) / 0.35))
        oy = int((1 - a) * 18)
        rrect(tmp, cx0, cy0 + oy, cw, ch, dark(col, 0.5), 5)
        rrect(tmp, cx0 + 2, cy0 + 2 + oy, cw - 4, ch - 4, (1.0, 1.0, 1.0), 4)
        fill_rect(tmp, cx0 + 3, cy0 + 3 + oy, cw - 6, 6, col)
        s_ = draw_icon(tmp, cx0 + 10, cy0 + 16 + oy, ic, col, sc=3)
        val = '%s €' % fmt(PCT[cur])
        vs = 3 if font.measure(val, 3) <= cw - s_ - 26 else 2
        font.draw(tmp, cx0 + s_ + 18, cy0 + 22 + oy, val, dark(col, 0.62), shadow=(0.88, 0.85, 0.8), scale=vs, bold=True)
        yy = cy0 + 16 + s_ + 10 + oy
        for ln in wrap(font, nm, cw - 20, 2):
            font.draw(tmp, cx0 + 10, yy, ln, INK, scale=2, bold=True)
            yy += 30
        for ln in wrap(font, DESC[cur], cw - 20, 1)[:2]:
            font.draw(tmp, cx0 + 10, yy + 2, ln, (0.45, 0.32, 0.22))
            yy += 17
        if cur == 2 and rint is not None and t >= rint:
            by_ = cy0 + ch - 38 + oy
            rrect(tmp, cx0 + 6, by_, cw - 12, 32, (0.90, 0.86, 0.98), 4)
            for q in range(18):
                for r_ in range(16):
                    if (q + r_) % 5 < 2:
                        fill_rect(tmp, cx0 + 12 + q, by_ + 8 + r_, 1, 1, (0.28, 0.18, 0.55))
            font.draw(tmp, cx0 + 36, by_ + 3, 'Intereses de la', (0.28, 0.18, 0.55), bold=True)
            font.draw(tmp, cx0 + 36, by_ + 16, 'deuda: %s €' % fmt(PCT_INT), (0.28, 0.18, 0.55), bold=True)
    elif summary:
        rrect(tmp, cx0, cy0, cw, ch, (0.55, 0.32, 0.12), 5)
        rrect(tmp, cx0 + 2, cy0 + 2, cw - 4, ch - 4, (1.0, 1.0, 1.0), 4)
        for i, (nm, v, col, ic) in enumerate(CATS):
            yy = cy0 + 8 + i * 20
            rrect(tmp, cx0 + 8, yy + 1, 14, 14, col, 3)
            font.draw(tmp, cx0 + 28, yy, nm, INK)
            val = fmt(PCT[i])
            font.draw(tmp, cx0 + cw - 10 - font.measure(val), yy, val, dark(col, 0.6), bold=True)
    dst[...] = tmp


def frame(t):
    if not G:
        init()
    s = active(t)
    vp, vyaw, vclip, vt = vil_walk(t)
    n_asset, n_clip, n_loop, n_tl, n_tex = actor_state('N', t, s)
    v_asset, v_clip, v_loop, v_tl, v_tex = actor_state('V', t, s)
    if vclip == 'walk1':
        v_clip, v_loop, v_tl = 'walk1', True, t * 0.75
        v_tex['e'] = 'e.0'
    u = float(ease((t - 2.4) / 0.8))
    nook_yaw = (1 - u) * yaw_facing(0.2, 1.0) + u * yaw_facing(0.8, 1.4)

    def pose_of(asset, clip, tl, loop):
        if clip == 'talk1':
            return pose_layered(asset, 'wait1', tl, 'talk1', tl)
        return pose_at(asset, clip, tl, loop)
    acts = [
        dict(asset=n_asset, world=world_matrix(NOOK_POS, nook_yaw, 1.0), pose=pose_of(n_asset, n_clip, n_tl, n_loop), tex=n_tex),
        dict(asset=v_asset, world=world_matrix(vp, vyaw, 1.0), pose=pose_of(v_asset, v_clip, v_tl, v_loop), tex=v_tex),
    ]
    eye, tgt, fov, shot = camera(t)
    cv = G['v'].render(look_at(eye, tgt), acts, fov=fov)
    img = cv.to_image()[..., :3].astype(np.float32) / 255.0
    font = G['font']
    # --- cuadro de datos (solo en los planos 'board')
    if shot == 'board' and t >= T_START - 0.2:
        _, ta, _ = current_shot(t)
        draw_board(img, t, ta)
    # --- título
    if t < 3.3:
        a = float(np.clip(min((t - 0.15) / 0.4, (3.3 - t) / 0.5), 0, 1))
        fill_rect(img, 0, 40, W, 150, (0.05, 0.12, 0.3), 0.6 * a)
        big_text(img, font, '¿A dónde va', 54, 3, a)
        big_text(img, font, 'tu dinero público?', 100, 3, a)
        big_text(img, font, 'España · 2023', 150, 2, a, colors=((0.1, 0.2, 0.45), (1.0, 0.85, 0.35)))
    # --- diálogo (texto ampliado x2)
    if s is not None:
        bub = G['bubble']
        bx, by = (W - bub.shape[1]) // 2, H - bub.shape[0] - 62
        uu = float(ease(min((t - s['t0']) / 0.2, 1.0)))
        blit(img, bub, bx, by + (1 - uu) * 14, alpha=uu)
        tx, ty = G['tpos']
        nx, ny = G['npos']
        name = 'Tom Nook' if s['who'] == 'N' else 'Vecino'
        font.draw(img, bx + nx + 6, by + ny + 3, name, (0.1, 0.25, 0.5), bold=True)
        rem = int(max(0, (t - s['t0'])) * CPS)
        for i, line in enumerate(s['wrapped']):
            part = line[:rem]
            rem -= len(line) + 1
            if part:
                font.draw(img, bx + tx, by + ty + i * 30, part, INK, scale=TS, bold=True)
            if rem <= 0:
                break
    # --- fundidos
    f = min(1.0, t / 0.4, (G['end'] + 1.0 - t) / 1.2)
    img *= float(np.clip(f, 0, 1))
    out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    return upscale(out)


def _worker(i):
    return frame(i / FPS)


def build_audio(rom, path, duration):
    A = AU.AudioBank(rom)
    sched, reveals, _ = schedule(Font(rom), G['text_w'])
    mix = AU.Mixer(duration + 2)
    music = RG.pista(A, duration + 1)
    # el volumen de la música baja un poco mientras alguien habla
    env = np.ones(len(music), np.float32)
    for s in sched:
        env[int(s['t0'] * AU.SR):int(s['t1'] * AU.SR)] = 0.62
    k = int(0.15 * AU.SR)
    env = np.convolve(env, np.ones(k, np.float32) / k, 'same')
    mix.add(0.0, music * env[:, None], gain=0.5)
    vN = A.voice_set(18)
    vV = A.voice_set(19)
    rng = np.random.RandomState(3)
    for s in sched:
        voice, pitch, pan = (vN, 0.78, -0.2) if s['who'] == 'N' else (vV, 1.35, 0.2)
        for dt, w in AU.speech_blips(s['text'], voice, pitch, rng, CPS):
            if s['t0'] + dt < s['t1']:
                mix.add(s['t0'] + dt, w, gain=0.9, pan=pan)
    # un «ding» agudo al aparecer cada categoría
    for k_, tt in reveals.items():
        w = vN[3]
        n = max(8, int(len(w) / 2.4))
        mix.add(tt, np.interp(np.linspace(0, len(w) - 1, n), np.arange(len(w)), w).astype(np.float32), gain=0.55)
    mix.fade_out(duration - 1.8, duration)
    mix.save(path, duration)


if __name__ == '__main__':
    mp.freeze_support()
    out_dir = rutas.salida('animal-crossing')
    os.makedirs(out_dir, exist_ok=True)
    args = sys.argv[1:]
    init()
    DURATION = G['end'] + 1.8
    if '--solo-frames' in args:
        ts = [float(x) for x in args[args.index('--solo-frames') + 1].split(',')]
        from PIL import Image
        tmp = os.path.join(rutas.trabajo('animal-crossing'), 'frames')
        os.makedirs(tmp, exist_ok=True)
        for t in ts:
            Image.fromarray(frame(t)).save(os.path.join(tmp, 'g_%05.1f.png' % t))
        print('ok', len(ts), 'duración total %.1f s' % DURATION)
        sys.exit(0)
    rom = Rom()
    wav = os.path.join(rutas.trabajo('animal-crossing'), '_audio_gasto.wav')
    build_audio(rom, wav, DURATION)
    n = int(DURATION * FPS)
    with mp.Pool(max(1, mp.cpu_count() - 1), initializer=init) as pool:
        write_video(pool.imap(_worker, range(n), chunksize=4), os.path.join(out_dir, 'gasto_publico.mp4'), audio=wav)
    print('hecho', DURATION)
