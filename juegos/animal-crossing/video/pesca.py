"""Vídeo vertical (móvil, 1080x1920): un vecino pesca un salmón de río y lo explica, a lo bruto y con doble sentido.

Datos del salmón: ficha oficial de Animal Crossing: Wild World (textos españoles de la ROM: script/SPN/string/obj_etc_fish.bmg
ids 26 y 27) + curiosidades verificadas: FishBase (olfato), DFO Canadá / FishBase (1-4 años en el mar y regreso al río natal),
Scottish Wildlife Trust (saltos de más de 3 m).
Uso:  python -I video/pesca.py [--solo-frames t1,t2,...]
Salida: salida/salmon_vecino.mp4
"""
import os
import re
import sys
import multiprocessing as mp

os.environ.setdefault('VIDEO_VERTICAL', '1')        # antes de importar el motor: 360x640 x3

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from motor import *             # noqa: E402,F401,F403
from escena import Village      # noqa: E402
import audio as AU              # noqa: E402
import musica_pesca as MP       # noqa: E402
import sfx as SX            # noqa: E402

CPS = 21.0                      # caracteres por segundo al teclear
HOLD = 0.8                      # pausa tras acabar una línea
GAP = 0.25
T_START = 0.5
INK = (0.25, 0.12, 0.05)
JUMP_T = 1.4                    # duración del salto del salmón hasta la mano

# ---------------------------------------------------------------- datos
# (valor grande, rótulo, descripción, color, icono)
FACTS = [
    ('90 cm', 'Tamaño', 'Medida del salmón en Wild World', (0.25, 0.65, 0.72), 'regla'),
    ('160 cm', 'Salmón rey', 'El mayor de los salmones y muy caro', (0.90, 0.38, 0.33), 'corona'),
    ('1-4 años', 'En el mar', 'Después vuelve al río donde nació', (0.35, 0.52, 0.95), 'ola'),
    ('Olfato', 'Su brújula', 'Recuerda el olor de su río natal', (0.30, 0.70, 0.40), 'gota'),
    ('+3 m', 'De salto', 'Sube obstáculos de más de 3 metros', (0.97, 0.58, 0.22), 'flecha'),
    ('Sept.', 'Su mes', 'En ríos y estuarios, según el juego', (0.93, 0.74, 0.20), 'calendario'),
    ('Rosa', 'Su carne', 'Y aun así el juego dice «blanco»', (0.92, 0.52, 0.68), 'pez'),
]
FUENTES = 'Fuentes: Wild World · FishBase · DFO · SWT'

ICONS = {
    'regla': ['.........', '.........', '#########', '#.#.#.#.#', '#.#.#.#.#', '#########', '.........', '.........', '.........'],
    'corona': ['.........', '#...#...#', '##.###.##', '#########', '#########', '#########', '.........', '.........', '.........'],
    'ola': ['.........', '.........', '.##...##.', '#..#.#..#', '#...#...#', '.........', '.##...##.', '#..#.#..#', '#...#...#'],
    'gota': ['....#....', '....#....', '...###...', '..#####..', '.#######.', '.#######.', '.#######.', '..#####..', '...###...'],
    'flecha': ['....#....', '...###...', '..#####..', '.#######.', '...###...', '...###...', '...###...', '...###...', '...###...'],
    'calendario': ['.#.....#.', '#########', '#.......#', '#.#.#.#.#', '#.......#', '#.#.#.#.#', '#.......#', '#.#.#.#.#', '#########'],
    'pez': ['.........', '.........', '..###..#.', '.#####.##', '#.#######', '.#####.##', '..###..#.', '.........', '.........'],
}
ICONS = {k: np.array([[c == '#' for c in row] for row in v]) for k, v in ICONS.items()}

# ---------------------------------------------------------------- guion
# (texto, plano, evento, [(fragmento, n.º de dato que se revela al teclearlo)]) · plano: wide | vil | splash | board
# evento (al empezar la línea): cast = lanza la caña · nibble = pican · hit = se engancha · jump = el salmón salta a la mano
LINES = [
    ('Joder, qué puta mañana para pescar.', 'vil', None, []),
    ('¡Venga, cabrón, pica de una puta vez!', 'wide', 'cast', []),
    ('Dos horas aquí y ni una mierda...', 'vil', None, []),
    ('¡Hostia, pica! ¡Pica, coño, PICA!', 'wide', 'nibble', []),
    ('¡Tira como un cabrón! ¡Me cago en todo!', 'splash', 'hit', []),
    ('¡Joder, un SALMÓN! ¡Menudo pedazo de bicho!', 'splash', 'jump', []),
    ('¡Lo tengo, joder! ¡LO TENGO, COÑO!', 'splash', None, []),
    ('¡90 cm! Dicen que el tamaño no importa... ¡Mienten!', 'board', None, [('90 cm', 0)]),
    ('Y el salmón rey: 160 cm. ¡Qué complejo me da!', 'board', None, [('160 cm', 1)]),
    ('Mi ex decía que el tamaño no importaba...', 'vil', None, []),
    ('Pasa 1-4 años en el mar, el muy golfo.', 'board', None, [('1-4 años', 2)]),
    ('Y vuelve al río donde nació. ¡Por cojones!', 'vil', None, []),
    ('Lo encuentra por el olfato. ¡Menuda napia!', 'board', None, [('olfato', 3)]),
    ('Salta más de 3 m. ¡Todo por echar un polvo!', 'board', None, [('3 m', 4)]),
    ('Aparece en septiembre, en ríos y estuarios.', 'board', None, [('septiembre', 5)]),
    ('Su carne es rosa, pero el juego dice blanco.', 'board', None, [('rosa', 6)]),
    ('En resumen: ¡grande, fiel y saltarín, como yo!', 'board', 'resumen', []),
    ('¡Joder, qué rico está! Pura proteína, hostia.', 'vil', None, []),
    ('¡Y ahora a por el rey! ¡A tomar por saco!', 'wide', None, []),
]
TS = 2          # escala del texto del diálogo
KINDS = ['bars', 'zoom', 'iris', 'whip']       # transiciones, en orden de aparición
TW = 0.2                                        # semiduración de una transición
SWEARS = ('puta', 'mierda', 'coño', 'Joder', 'Hostia', 'cojones', 'saco', 'cabrón', 'polvo')


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
    out, reveals, ev = [], {}, {}
    for text, shot, event, revs in LINES:
        lines = wrap(font, text, width_px, TS)
        assert len(lines) <= 3, 'demasiado largo: %r' % text
        typ = len(text) / CPS
        for frag, k in revs:
            assert frag.lower() in text.lower(), (frag, text)
            reveals[k] = t + (text.lower().find(frag.lower()) + len(frag)) / CPS
        if event:
            ev[event] = t
        out.append(dict(text=text, wrapped=lines, shot=shot, t0=t, t1=t + typ, t_end=t + typ + HOLD))
        t += typ + HOLD + GAP
    ev['catch'] = ev['jump'] + JUMP_T
    ev['resumen'] += 0.5
    ev['cuts'] = [(out[i]['t0'] - GAP / 2, KINDS[k % len(KINDS)])
                  for k, i in enumerate(i for i in range(1, len(out)) if out[i]['shot'] != out[i - 1]['shot'])]
    ev['graw'] = [out[i]['t0'] + 0.35 for i in range(len(out)) if i % 2 == 0 and any(w in out[i]['text'] for w in SWEARS)]
    return out, reveals, ev, t


# ---------------------------------------------------------------- escenario: río
class Rio(Village):
    """Orilla de hierba a la izquierda y río a la derecha (agua con cáusticas que se desplazan), con los modelos y texturas de la ROM."""

    BANK_X = 0.9          # donde acaba la hierba
    WATER_X = 1.4         # donde empieza el agua
    WATER_Y = -0.2

    def __init__(self, rom):
        self.rom = rom
        self.static = []
        g = self._ground = TexBank(rom.get('bg/ct0/grd_set0a.nsbtx'))
        self.grass = g.decode('grd_grs', 'grd_pl')
        self.sand = g.decode('grd_ssa', 'grd_pl')
        self.caust = g.decode('grd_riv.0', 'grd_riv_pl')
        self.foam = g.decode('grd_was', 'grd_was_pl')
        self.blue = np.zeros((4, 4, 4), np.uint8)
        self.blue[...] = (62, 112, 222, 255)
        sx = lambda p, t=(): Asset(rom, p, t)
        cedar = sx('fg/tree/cedar_mdl/cedar_01s.nsbmd', ['fg/tree/cedar_tex/cedar_01s.nsbtx'])
        cedar2 = sx('fg/tree/cedar_mdl/cedar_03s.nsbmd', ['fg/tree/cedar_tex/cedar_03s.nsbtx'])
        tree = sx('fg/tree/tree_mdl/tree_01s.nsbmd', ['fg/tree/tree_tex/tree_01s.nsbtx'])
        tree3 = sx('fg/tree/tree_mdl/tree_03s.nsbmd', ['fg/tree/tree_tex/tree_03s.nsbtx'])
        cosmos = sx('fg/flower/cosmos/cosmos.nsbmd', ['fg/flower/cosmos/cosmos.nsbtx'])
        tulip = sx('fg/flower/tulip/tulip.nsbmd', ['fg/flower/tulip/tulip.nsbtx'])
        pansy = sx('fg/flower/pansy/pansy.nsbmd', ['fg/flower/pansy/pansy.nsbtx'])
        for a, p, y, s in [(cedar, (-4.5, 0, -5), 0.3, 2.6), (cedar2, (-7.5, 0, -9), 1.0, 2.8), (tree, (-3.4, 0, -11), 2.0, 2.4),
                           (tree3, (-9.5, 0, -2), 0.5, 2.7), (cedar, (-6, 0, 5), 0.0, 2.9), (tree, (-8, 0, 12), 1.0, 2.5),
                           (tree3, (-4.5, 0, -22), 2.5, 2.4), (cedar2, (-12, 0, 6), 0.7, 2.8)]:
            self.add(a, p, y, s)
        rng = np.random.RandomState(7)
        for i in range(40):
            a = [cosmos, tulip, pansy][i % 3]
            p = (rng.uniform(-6.5, 0.6), 0.0, rng.uniform(-8.0, 5.0))
            if abs(p[0] + 1.0) < 1.6 and abs(p[2] - 1.0) < 1.8:      # sitio del pescador
                continue
            self.add(a, p, rng.uniform(0, 6), 1.0)

    def _quads(self, cv, vp, x0, x1, z0, z1, y0, y1, tex, tile, shade, alpha=1.0, du=0.0, dv=0.0, step_x=4.0):
        """Suelo entre x0..x1 (y interpola y0->y1) en celdas de 4 unidades (para que no desaparezca con la cámara cerca)."""
        th, tw = tex.shape[:2]
        xs = np.arange(x0, x1 + 1e-6, step_x)
        if xs[-1] < x1 - 1e-6:
            xs = np.append(xs, x1)
        zs = np.arange(z0, z1 + 1e-6, 4.0)
        tris, uvs = [], []
        yy = lambda x: y0 + (y1 - y0) * (x - x0) / max(x1 - x0, 1e-6)
        for i in range(len(xs) - 1):
            for j in range(len(zs) - 1):
                a, b, c, d = xs[i], xs[i + 1], zs[j], zs[j + 1]
                q = [(a, yy(a), c), (b, yy(b), c), (b, yy(b), d), (a, yy(a), d)]
                uq = [((p[0] / tile + du) * tw, (p[2] / tile + dv) * th) for p in q]
                for tri in ((0, 1, 2), (0, 2, 3)):
                    tris.append([q[n] for n in tri])
                    uvs.append([uq[n] for n in tri])
        P = np.array(tris, np.float64)
        clip = np.concatenate([P, np.ones(P.shape[:2] + (1,))], -1) @ vp.T
        cv.draw(clip, np.array(uvs), tex, np.ones((len(P), 3, 3)) * shade, alpha, 0, (True, True, False, False))

    def draw_land(self, cv, view, proj, t):
        vp = proj @ view
        self._quads(cv, vp, -40, self.BANK_X, -40, 28, 0.0, 0.0, self.grass, 4.0, 0.92)
        self._quads(cv, vp, self.BANK_X, self.WATER_X, -40, 28, 0.0, self.WATER_Y, self.sand, 3.0, 0.95)
        wy = self.WATER_Y
        self._quads(cv, vp, self.WATER_X, 40, -40, 28, wy, wy, self.blue, 4.0, 1.0, step_x=8.0)
        # cáusticas: dos capas que se desplazan con la corriente (hacia la cámara) y brillan
        self._quads(cv, vp, self.WATER_X, 40, -40, 28, wy + 0.01, wy + 0.01, self.caust, 3.0, 1.0, 0.75, du=t * 0.05, dv=t * 0.22, step_x=8.0)
        self._quads(cv, vp, self.WATER_X, 40, -40, 28, wy + 0.015, wy + 0.015, self.caust, 4.5, 1.0, 0.45, du=-t * 0.03, dv=t * 0.13 + 0.37, step_x=8.0)
        self._quads(cv, vp, self.WATER_X, self.WATER_X + 0.8, -40, 28, wy + 0.02, wy + 0.02, self.foam, 2.0, 1.0, 0.9, dv=t * 0.1, step_x=8.0)

    def render(self, view, actors, t=0.0, fov=28.0, tint=(1, 1, 1)):
        cv = Canvas(W, H)
        proj = perspective(fov, W / H, 0.5, 200)
        self.sky(cv)
        self.draw_land(cv, view, proj, t)
        for asset, mesh, w in self.static:
            draw_model(cv, asset.model, asset.banks, w, view, proj, mesh=mesh, tint=tint)
        for a in actors:
            draw_model(cv, a['asset'].model, a['asset'].banks, a['world'], view, proj, override=a.get('pose'),
                       tex_override=a.get('tex'), tint=tint, ambient=a.get('ambient', 0.78))
        return cv, proj


# ---------------------------------------------------------------- estado global por proceso
G = {}


def init():
    rom = Rom()
    G['rom'] = rom
    G['v'] = Rio(rom)
    clips = {}
    for p in rom.list('anm/'):
        if p.endswith('.nsbca'):
            clips.update(load_clips(rom, [p]))
    clips.update(load_clips(rom, ['fish/01/fish26.nsbca', 'fish/03/fish_shadow.nsbca']))
    G['vil'] = Asset(rom, 'npc/model/16/17.nsbmd', ['npc/model/16/17.nsbtx'], clips)
    G['rod'] = Asset(rom, 'PItm/Mdl0/15.nsbmd', [], clips)
    G['sal'] = Asset(rom, 'fish/01/fish26.nsbmd', [], clips)
    G['shadow'] = Asset(rom, 'fish/03/fish_shadow.nsbmd', [], clips)
    G['font'] = Font(rom)
    img, tpos, npos = make_bubble(rom, 13, extra_rows=5)
    G['bubble'], G['tpos'], G['npos'] = img, tpos, npos
    G['text_w'] = img.shape[1] - tpos[0] - 30
    G['sched'], G['reveals'], G['ev'], G['end'] = schedule(G['font'], G['text_w'])
    E = G['ev']
    rng = np.random.RandomState(9)
    G['glints'] = [(rng.uniform(1.8, 5.0), rng.uniform(-6.0, 6.0), rng.uniform(0, 6.3)) for _ in range(26)]
    G['t_rey'] = G['sched'][-1]['t0']          # el salmón rey aparece bajo el agua en la última línea
    # punto exacto de la mano al presentar el pez (para que el salto aterrice ahí)
    pose = pose_at(G['vil'], 'comp_fish2', 0.0, False)
    G['vil'].model.pose(pose)
    G['hand_end'] = (WM @ G['vil'].model.node_world[11])[:3, 3].copy()


def active(t):
    for s in G['sched']:
        if s['t0'] <= t < s['t_end']:
            return s
    return None


def current_shot(t):
    """(nombre, inicio de la tanda de planos iguales, fin) del plano en el instante t."""
    S = G['sched']
    if t < T_START:
        return S[0]['shot'], 0.0, S[0]['t0']
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


# ---------------------------------------------------------------- personaje, caña, línea y pez
LINCE_POS = np.array([-0.8, 0.0, 1.0])
LINCE_YAW = yaw_facing(1.0, 0.35)
WM = world_matrix(LINCE_POS, LINCE_YAW, 1.0)
B0 = np.array([1.9, -0.2, 1.8])          # donde cae el flotador
SPLASH0 = np.array([1.9, -0.15, 1.8])    # de donde sale el salto
FS = 0.62                                # escala del salmón
ROD_TIP = np.array([0.0, 0.0, 3.06, 1.0])


def lince_clip(t):
    """(clip, loop, t_local) del pescador según los eventos del guion."""
    E = G['ev']
    if t < E['cast']:
        return 'pol_wait1', False, 0.0                  # caña recogida hacia atrás
    if t < E['nibble']:
        return 'pol_swing1', False, t - E['cast']       # lanza y se queda con la caña en alto (último fotograma)
    if t < E['hit']:
        return 'pol_wait_nibble1', True, t - E['nibble']
    if t < E['jump']:
        return 'pol_hit1', True, (t - E['hit']) * 1.3
    if t < E['catch']:
        return 'pol_get1', False, t - E['jump']
    return 'comp_fish2', False, t - E['catch']


def lince_state(t, s):
    asset = G['vil']
    clip, loop, tl = lince_clip(t)
    speaking = s is not None and t < s['t1']
    base = pose_at(asset, clip, tl, loop)
    if speaking:
        pose = dict(base)
        over = asset.anims['talk1']
        f = (t * 30.0) % max(over.num_frames, 1)
        fr = over.frame(f, asset.model)
        for i, c in enumerate(over.objs):
            sampled = any(k.kind == 'samples' for k in c['t']) or c['r'].kind == 'samples' or any(k.kind == 'samples' for k in c['s'])
            if sampled and i in fr:
                pose[i] = fr[i]
    else:
        pose = base
    eyes = 'e.2' if (t + 0.4) % 3.1 < 0.14 else 'e.0'
    if t >= G['ev']['catch']:
        eyes = 'e.5'
    tex = {'e': eyes, 'm': ('m.%d' % (1 + int(t * 8) % 2)) if speaking else 'm.0'}
    return pose, tex


def bob(t):
    return 0.03 * np.sin(t * 2.3)


def project(p, view, proj):
    c = proj @ view @ np.array([p[0], p[1], p[2], 1.0])
    if c[3] <= 1e-4:
        return None
    return (c[0] / c[3] * 0.5 + 0.5) * W, (1 - (c[1] / c[3] * 0.5 + 0.5)) * H


def fish_orient(d):
    """Matriz con el eje largo del pez (+Y) en la dirección d y su cara plana hacia la cámara (+Z)."""
    y = d / max(np.linalg.norm(d), 1e-9)
    x = np.cross(y, np.array([0.0, 0.0, 1.0]))
    if np.linalg.norm(x) < 1e-6:
        x = np.array([1.0, 0.0, 0.0])
    x /= np.linalg.norm(x)
    z = np.cross(x, y)
    m = np.eye(4)
    m[:3, 0], m[:3, 1], m[:3, 2] = x, y, z
    return m


def shadow_state(t):
    """(posición, dirección, alfa) de la sombra del salmón bajo el agua, o None."""
    E = G['ev']
    t_in = E['cast'] + 1.8
    wy = Rio.WATER_Y + 0.05
    if t_in <= t < E['jump']:
        if t < E['nibble']:
            s = np.clip((t - t_in) / (E['nibble'] - t_in), 0, 1)
            p = B0 + np.array([1.7 * (1 - s), 0, -1.2 * (1 - s)]) + 0.0
            d = B0 - p if s < 1 else np.array([-1.0, 0, 0.3])
        elif t < E['hit']:
            a = (t - E['nibble']) * 2.6
            p = B0 + np.array([0.55 * np.cos(a), 0, 0.55 * np.sin(a)])
            d = np.array([-np.sin(a), 0, np.cos(a)])
        else:
            a = (t - E['hit']) * 6.0
            p = B0 + np.array([0.75 * np.sin(a), 0, 0.5 * np.cos(a * 0.7)])
            d = np.array([np.cos(a), 0, -0.35 * np.sin(a * 0.7)])
        p = np.array([p[0], wy, p[2]])
        al = float(np.clip((t - t_in) / 0.6, 0, 1))
        return p, d, al, 1.0
    return None


def rey_state(t):
    """El salmón rey: una sombra gigante que cruza el río en la última línea."""
    t0 = G['t_rey']
    if t < t0 - 0.3:
        return None
    u = (t - t0) / 5.0
    p = np.array([2.7, Rio.WATER_Y + 0.05, 5.5 - 9.0 * u])
    return p, np.array([0.0, 0.0, -1.0]), float(np.clip((t - t0 + 0.3) / 0.6, 0, 1)), 1.8


def salmon_air(t):
    """Matriz del salmón en vuelo o sujeto con la mano; None si no está fuera del agua."""
    E = G['ev']
    if t < E['jump']:
        return None
    if t < E['catch']:
        u = (t - E['jump']) / JUMP_T
        end = G['hand_end']

        def pos(uu):
            return SPLASH0 * (1 - uu) + end * uu + np.array([0.0, 3.2 * 4 * uu * (1 - uu), 0.0])
        p = pos(u)
        d = pos(min(u + 0.03, 1.0)) - pos(max(u - 0.03, 0.0))
        m = fish_orient(d)
        m[:3, 3] = p
        return m @ np.diag([FS, FS, FS, 1.0]), p
    return 'hand', None


def bobber_state(t):
    """Posición del flotador, o None si aún no se ha lanzado / ya no está."""
    E = G['ev']
    if t < E['cast'] + 0.55 or t >= E['jump']:
        return None
    if t < E['cast'] + 1.1:
        u = (t - E['cast'] - 0.55) / 0.55
        return G['tip'] * (1 - u) + B0 * u + np.array([0, 1.2 * 4 * u * (1 - u), 0])
    p = B0.copy()
    sh = shadow_state(t)
    if t >= E['hit'] and sh is not None:
        p = sh[0].copy()
    p[1] = Rio.WATER_Y + 0.02 + bob(t) * 2.0
    if E['nibble'] <= t < E['hit']:
        p[1] -= 0.24 * max(0.0, np.sin((t - E['nibble']) * 2 * np.pi * 1.7)) ** 2
    return p


def draw_line(img, a, b, sag, view, proj, col=(0.96, 0.96, 0.92), alpha=0.9):
    for s in np.linspace(0, 1, 60):
        p = a * (1 - s) + b * s + np.array([0, -sag * 4 * s * (1 - s), 0])
        q = project(p, view, proj)
        if q is not None:
            fill_rect(img, round(q[0]), round(q[1]), 1, 1, col, alpha)


def draw_bobber(img, q):
    x, y = int(round(q[0])), int(round(q[1]))
    fill_rect(img, x - 2, y - 3, 5, 3, (0.92, 0.18, 0.15))
    fill_rect(img, x - 2, y, 5, 3, (1.0, 1.0, 0.95))
    fill_rect(img, x - 1, y - 4, 3, 1, (0.92, 0.18, 0.15))


def splash2d(img, q, age, k=1.0):
    """Anillo de agua que se abre y gotas que suben y caen."""
    if q is None or not 0 <= age < 0.9:
        return
    x, y = q
    r = (4 + 26 * age) * k
    a = 1 - age / 0.9
    for i in range(24):
        th = i / 24 * 2 * np.pi
        fill_rect(img, round(x + r * np.cos(th)), round(y + r * 0.35 * np.sin(th)), 2, 1, (1, 1, 1), 0.9 * a)
    for i in range(9):
        th = i * 0.7 + 0.3
        vx, vy = np.cos(th) * 22 * k, -(26 + 14 * (i % 3)) * k
        px, py = x + vx * age, y + vy * age + 70 * age * age * k
        fill_rect(img, round(px), round(py), 2, 2, (0.85, 0.95, 1.0), a)


# ---------------------------------------------------------------- cámara
# plano: (eye0, target0, eye1, target1, fov): se mueve despacio de 0 a 1 durante la tanda
SHOTS = {
    'wide': ((0.3, 3.0, 15.5), (0.3, 1.7, 0.8), (0.3, 2.8, 14.0), (0.3, 1.6, 0.8), 34.0),
    'board': ((0.4, 2.4, 17.8), (0.4, 2.3, 0.8), (0.4, 2.4, 17.0), (0.4, 2.25, 0.8), 34.0),
    'vil': ((0.6, 2.0, 10.0), (-0.4, 1.1, 1.0), (0.4, 2.0, 8.6), (-0.5, 1.1, 1.0), 34.0),
    'splash': ((-0.2, 1.8, 14.0), (-0.2, 1.2, 1.2), (-0.1, 1.8, 12.6), (-0.2, 1.2, 1.2), 34.0),
}


def camera(t):
    name, ta, tb = current_shot(t)
    e0, g0, e1, g1, fov = SHOTS[name]
    u = float(np.clip((t - ta) / max(tb - ta, 1e-3), 0, 1))
    return np.array(e0) * (1 - u) + np.array(e1) * u, np.array(g0) * (1 - u) + np.array(g1) * u, fov, name


# ---------------------------------------------------------------- 2D: textos y gráficos
def big_text(img, font, txt, y, sc_max, a, colors=((0.1, 0.2, 0.45), (1.0, 1.0, 0.95)), x_center=None, sc_force=None):
    w_txt = font.measure(txt) + 4
    sc = sc_force or max(1, min(sc_max, (W - 16) // (w_txt + 16)))
    mask = np.zeros((18, w_txt + 16), np.float32)
    cx = 1
    for ch in txt:
        g = font.glyph.get(ch)
        if g is not None:
            mask[1:17, cx:cx + 16] = np.maximum(mask[1:17, cx:cx + 16], g)
        cx += font.advance(ch)
    big = np.repeat(np.repeat(mask, sc, 0), sc, 1)
    hh, ww = big.shape
    x0 = ((W if x_center is None else x_center * 2) - ww) // 2 + 8 * sc      # la máscara lleva 16 px de margen a la derecha
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


def fish_sprite(t, w=140, h=68):
    """El salmón del juego (modelo fish26) nadando, de perfil y mirando a la izquierda, como RGBA."""
    cv = Canvas(w, h, bg=(0, 0, 0, 0))
    proj = perspective(22, w / h, 0.5, 50)
    view = look_at(np.array([0.0, 0.0, 3.6]), np.array([0.0, 0.0, 0.0]))
    c, s = 0.0, 1.0                           # giro de 90° sobre Z: la cabeza (+Y) pasa a -X
    rz = np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
    pose = pose_at(G['sal'], 'fish26', t * 1.2)
    draw_model(cv, G['sal'].model, G['sal'].banks, rz, view, proj, override=pose, ambient=0.9)
    return cv.to_image()


def reveal_times():
    r = G['reveals']
    return [r.get(k) for k in range(len(FACTS))]


def draw_board(dst, t, t0):
    font = G['font']
    u = back(min((t - t0) / 0.4, 1.0))
    if u <= 0:
        return
    px, py, pw, ph = 14, 22, W - 28, 276
    py += int((1 - u) * -(ph + 30))
    tmp = dst.copy()
    panel(tmp, px, py, pw, ph)
    rrect(tmp, px + 8, py + 8, pw - 16, 36, (0.25, 0.12, 0.05), 5)
    rrect(tmp, px + 9, py + 9, pw - 18, 34, (0.30, 0.68, 0.38), 5)
    fill_rect(tmp, px + 12, py + 11, pw - 24, 3, (1, 1, 1), 0.3)
    font.draw(tmp, px + 18, py + 12, 'Salmón de río', (1, 1, 0.95), shadow=(0.1, 0.35, 0.15), scale=2)
    sub = 'Wild World'
    font.draw(tmp, px + pw - 18 - font.measure(sub, 1), py + 20, sub, (1.0, 0.95, 0.5), shadow=(0.1, 0.35, 0.15))
    rt = reveal_times()
    shown = [i for i in range(len(FACTS)) if rt[i] is not None and t >= rt[i]]
    cur = max(shown) if shown else None
    summary = t >= G['ev']['resumen']
    cx0, cy0 = px + 12, py + 54
    cw, ch = pw - 24, ph - 54 - 12
    pre = cur is None                                  # antes del primer dato: tarjeta con interrogante
    if cur is None:
        cur = 0
    if not summary:
        val, nm, desc, col, ic = FACTS[cur]
        if pre:
            val = '?? cm'
        else:                                          # las cifras suben contando
            m_ = re.match(r'^(\+?)(\d+)( (?:cm|m))$', val)
            if m_:
                val = m_.group(1) + str(int(round(int(m_.group(2)) * float(ease((t - rt[cur]) / 0.5))))) + m_.group(3)
        a = 1.0 if pre else float(ease((t - rt[cur]) / 0.35))
        oy = int((1 - a) * 18)
        rrect(tmp, cx0, cy0 + oy, cw, ch, dark(col, 0.5), 5)
        rrect(tmp, cx0 + 2, cy0 + 2 + oy, cw - 4, ch - 4, (1.0, 1.0, 1.0), 4)
        fill_rect(tmp, cx0 + 3, cy0 + 3 + oy, cw - 6, 6, col)
        s_ = draw_icon(tmp, cx0 + 10, cy0 + 14 + oy, ic, col, sc=3)
        vs = next(k for k in (4, 3, 2) if font.measure(val, k) <= cw - s_ - 32 or k == 2)
        font.draw(tmp, cx0 + s_ + 18, cy0 + 8 + oy, val, dark(col, 0.62), shadow=(0.88, 0.85, 0.8), scale=vs, bold=True)
        font.draw(tmp, cx0 + 12, cy0 + 78 + oy, nm, INK, scale=2, bold=True)
        yy = cy0 + 116 + oy
        for ln in wrap(font, desc, cw - 24 - 140, 1)[:3]:
            font.draw(tmp, cx0 + 12, yy, ln, (0.45, 0.32, 0.22), bold=True)
            yy += 17
        spr = fish_sprite(t)
        blit(tmp, spr, cx0 + cw - 148, cy0 + 90 + oy, alpha=a)
        # fichas pequeñas con todos los datos (el actual resaltado)
        n = len(FACTS)
        cwid = 36
        x_ = cx0 + 10
        for i in range(n):
            f_col = FACTS[i][3]
            on = i == cur and not pre
            seen = rt[i] is not None and t >= rt[i]
            rrect(tmp, x_ + i * (cwid + 3), cy0 + ch - 30 + oy - (3 if on else 0), cwid, 24, dark(f_col, 0.5), 3)
            rrect(tmp, x_ + i * (cwid + 3) + 1, cy0 + ch - 29 + oy - (3 if on else 0), cwid - 2, 22, f_col if seen else (0.82, 0.8, 0.76), 3)
            draw_icon(tmp, x_ + i * (cwid + 3) + 8, cy0 + ch - 28 + oy - (3 if on else 0), FACTS[i][4], f_col, sc=1) if False else None
            ys, xs = np.nonzero(ICONS[FACTS[i][4]])
            for yy2, xx2 in zip(ys, xs):
                fill_rect(tmp, x_ + i * (cwid + 3) + 12 + xx2 * 1.4, cy0 + ch - 27 + oy - (3 if on else 0) + yy2 * 1.8, 1.5, 1.8, (1, 1, 0.95) if seen else (0.95, 0.93, 0.9))
        if not pre and t - rt[cur] < 0.8:
            top = cy0 + 16 + oy
            fill_rect(tmp, cx0 + 3, cy0 + 3 + oy, cw - 6, 6, (1, 1, 1), 0.55 * (1 - (t - rt[cur]) / 0.8))
            for k in range(6):
                ph_ = (t - rt[cur]) * 1.6 + k * 0.37
                sparkle(tmp, int(cx0 + 20 + (k * 47 + cur * 13) % (cw - 40)), int(top + 12 - 22 * (ph_ % 1.0) - k * 3), 2 + (k % 2))
    elif summary:
        rrect(tmp, cx0, cy0, cw, ch, (0.55, 0.32, 0.12), 5)
        rrect(tmp, cx0 + 2, cy0 + 2, cw - 4, ch - 4, (1.0, 1.0, 1.0), 4)
        for i, (val, nm, desc, col, ic) in enumerate(FACTS):
            yy = cy0 + 9 + i * 24
            rrect(tmp, cx0 + 10, yy + 1, 16, 16, col, 3)
            font.draw(tmp, cx0 + 34, yy, nm, INK, bold=True)
            font.draw(tmp, cx0 + cw - 12 - font.measure(val, 1), yy, val, dark(col, 0.6), bold=True)
        font.draw(tmp, cx0 + 10, cy0 + ch - 20, FUENTES, (0.45, 0.32, 0.22))
    dst[...] = tmp


# ---------------------------------------------------------------- efectos visuales y transiciones
_YY, _XX = np.mgrid[0:H, 0:W]
_R = np.hypot((_XX - W / 2) / (W / 2), (_YY - H / 2) / (H / 2))
VIGN = (1.0 - 0.30 * np.clip(_R - 0.55, 0, 1) ** 1.4)[..., None].astype(np.float32)
NAVY = np.array([0.08, 0.12, 0.28], np.float32)
ORANGE = np.array([0.98, 0.66, 0.25], np.float32)
BAND = np.array([[0.98, 0.62, 0.20], [1.0, 1.0, 0.93], [0.30, 0.68, 0.38], [0.35, 0.55, 0.95]], np.float32)
CONFETTI = [(0.98, 0.35, 0.3), (1.0, 0.85, 0.25), (0.3, 0.75, 0.45), (0.35, 0.55, 0.95), (0.95, 0.5, 0.75), (1, 1, 1)]


def back(u):
    """Entrada con rebote (ease-out-back): sobrepasa 1 y vuelve."""
    u = float(np.clip(u, 0, 1))
    c1 = 1.70158
    return 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2


def pulse(t, t0, d):
    """1 en t0 y baja linealmente a 0 en t0 + d."""
    return float(max(0.0, 1 - (t - t0) / d)) if t >= t0 else 0.0


def shift_xy(img, dx, dy):
    """Desplaza la imagen (bordes replicados): para el temblor de cámara."""
    m = max(abs(dx), abs(dy), 1)
    p = np.pad(img, ((m, m), (m, m), (0, 0)), 'edge')
    return p[m - dy:m - dy + H, m - dx:m - dx + W]


def shift_x_fill(img, dx, fill=0.92):
    out = np.full_like(img, fill)
    if dx > 0:
        out[:, dx:] = img[:, :W - dx]
    elif dx < 0:
        out[:, :W + dx] = img[:, -dx:]
    else:
        out[...] = img
    return out


def transition(img, t):
    """Apertura en iris al empezar y, en cada corte de plano, una de: barras diagonales, zoom con flash, iris o barrido."""
    if t < 0.5:
        a = float(ease(t / 0.5))
        r = 560 * a
        d = np.hypot(_XX - W / 2, _YY - H * 0.45)
        img[d > r] = NAVY
        img[(d > r - 5) & (d <= r)] = ORANGE
        return img
    for tc, kind in G['ev']['cuts']:
        if abs(t - tc) > TW:
            continue
        u = (t - tc) / TW
        a = float(ease(1 - abs(u)))                  # 0 lejos del corte, 1 en el corte
        if kind == 'bars':
            s_ = (_XX + 0.5 * _YY) / (W + 0.5 * H)
            if u < 0:
                c = float(ease(u + 1))
                cov = s_ < c
            else:
                c = float(ease(u))
                cov = s_ >= c
            edge = np.abs(s_ - c) < 0.012
            band = (s_ * 6).astype(int) % 4
            img = np.where(cov[..., None], BAND[band], img)
            img[edge] = NAVY
        elif kind == 'zoom':
            z = 1 + 0.45 * a
            ys = np.clip(((np.arange(H) - H / 2) / z + H / 2).astype(int), 0, H - 1)
            xs = np.clip(((np.arange(W) - W / 2) / z + W / 2).astype(int), 0, W - 1)
            img = img[ys][:, xs]
            img = img * (1 - 0.8 * a) + 0.8 * a
        elif kind == 'iris':
            r = 560 * (1 - a)
            d = np.hypot(_XX - W / 2, _YY - H * 0.45)
            img[d > r] = NAVY
            img[(d > r - 5) & (d <= r)] = ORANGE
        elif kind == 'whip':
            dx = int(W * a) * (-1 if u < 0 else 1)
            acc = np.zeros_like(img)
            for k in range(5):
                acc += shift_x_fill(img, int(dx * (1 - 0.1 * k)))
            img = acc / 5
            img = img * (1 - 0.25 * a) + 0.25 * a
    return img


def speed_lines(img, t, a=0.55, cy=None):
    """Líneas de velocidad radiales que parpadean (tirón de la caña)."""
    cy = H * 0.45 if cy is None else cy
    th = np.arctan2(_YY - cy, _XX - W / 2)
    r = np.hypot(_XX - W / 2, _YY - cy)
    n, ph = 54, int(t * 24)
    v = th / (2 * np.pi) * n + (ph % 7) * 0.37
    k = np.floor(v)
    f = v - k
    w = 0.10 + 0.22 * ((np.sin((k + ph * 7.3) * 12.9898) * 43758.5453) % 1.0)
    r0 = 150 + 90 * ((np.sin((k + ph * 3.1) * 78.233) * 12345.678) % 1.0)
    m = ((f < w) & (r > r0)).astype(np.float32)[..., None] * a
    return img * (1 - m) + m


def sunburst(img, cx, cy, t, a):
    """Rayos giratorios amarillos detrás de un rótulo."""
    th = np.arctan2(_YY - cy, _XX - cx)
    r = np.hypot(_XX - cx, _YY - cy)
    m = ((((th / (2 * np.pi)) * 16 + t * 0.5) % 1.0) < 0.5).astype(np.float32) * np.clip(1.2 - r / 420, 0, 1) * 0.3 * a
    col = np.array([1.0, 0.95, 0.55], np.float32)
    return img * (1 - m[..., None]) + col * m[..., None]


def pop_text(img, font, txt, cy, age, dur, colors=((0.55, 0.12, 0.10), (1.0, 0.93, 0.35))):
    """Rótulo de cómic que entra con rebote (tamaño medio → máximo+1 → máximo) y se apaga al final."""
    if not 0 <= age < dur:
        return
    w_txt = font.measure(txt) + 4
    fit = int(max(1, min(6, (W - 16) // (w_txt + 16))))
    sc = max(1, fit // 2) if age < 0.05 else (fit + 1 if age < 0.13 and (fit + 1) * w_txt < W else fit)
    a = 1.0 if age < dur - 0.2 else (dur - age) / 0.2
    big_text(img, font, txt, cy, sc, a, colors=colors, sc_force=sc)


def bubble_pop(img, font, q, text, age, dur, col=(0.55, 0.1, 0.1), fill=(1.0, 1.0, 0.95), scale=2):
    """Bocadillo pequeño sobre la cabeza (exclamación o palabrotas tachadas) con rebote."""
    if q is None or not 0 <= age < dur:
        return
    w = font.measure(text, scale) + 12
    h = 16 * scale + 8
    oy = int((1 - back(age / 0.18)) * 14)
    x = int(np.clip(q[0] - w / 2, 4, W - w - 4))
    y = int(q[1] - h - 12 + oy)
    rrect(img, x - 2, y - 2, w + 4, h + 4, (0.25, 0.12, 0.05), 5)
    rrect(img, x, y, w, h, fill, 4)
    cx = int(np.clip(q[0], x + 8, x + w - 8))
    for i in range(5):
        fill_rect(img, cx - 5 + i, y + h + 2 + i - 2, 10 - 2 * i, 1, (0.25, 0.12, 0.05))
        fill_rect(img, cx - 4 + i, y + h + 1 + i - 2, 8 - 2 * i, 1, fill)
    font.draw(img, x + 6, y + 4, text, col, scale=scale, bold=True)


def confetti(img, t, t0):
    age = t - t0
    if not 0 <= age < 2.6:
        return
    rng = np.random.RandomState(5)
    for i in range(60):
        x, v, ph = rng.uniform(0, W), rng.uniform(80, 200), rng.uniform(0, 6.28)
        y = -12 + v * age
        fill_rect(img, x + 14 * np.sin(ph + age * 5), y, 3, 5, CONFETTI[i % len(CONFETTI)])


def water_fx(img, t, view, proj, bp):
    """Destellos sobre el agua y ondas alrededor del flotador."""
    wy = Rio.WATER_Y + 0.02
    for x, z, ph in G['glints']:
        a = max(0.0, np.sin(t * 3.0 + ph)) ** 6
        if a > 0.25:
            q = project((x, wy, z), view, proj)
            if q is not None and 0 <= q[0] < W and 0 <= q[1] < H:
                fill_rect(img, round(q[0]) - 2, round(q[1]), 5, 1, (1, 1, 1), a)
                fill_rect(img, round(q[0]), round(q[1]) - 2, 1, 5, (1, 1, 1), a)
    if bp is not None:
        q = project((bp[0], wy, bp[2]), view, proj)
        if q is not None:
            for k in (0, 1):
                age = (t * 1.1 + k * 0.5) % 1.0
                r = 3 + 15 * age
                for i in range(22):
                    th = i / 22 * 2 * np.pi
                    fill_rect(img, round(q[0] + r * np.cos(th)), round(q[1] + 0.35 * r * np.sin(th)), 1, 1, (1, 1, 1), 0.6 * (1 - age))


def cast_trail(img, t, view, proj):
    """Estela blanca de la punta de la caña al lanzar."""
    E = G['ev']
    if not E['cast'] + 0.1 <= t < E['cast'] + 1.1:
        return
    pts = []
    for k in range(9):
        tt = t - k * 0.025
        pose, _ = lince_state(tt, None)
        G['vil'].model.pose(pose)
        pts.append(project((WM @ G['vil'].model.node_world[14] @ ROD_TIP)[:3], view, proj))
    for k in range(8):
        a, b = pts[k], pts[k + 1]
        if a is None or b is None:
            continue
        for s in np.linspace(0, 1, 6):
            fill_rect(img, round(a[0] * (1 - s) + b[0] * s), round(a[1] * (1 - s) + b[1] * s), 2, 2, (1, 1, 1), 0.8 * (1 - k / 8))


def shake_amp(t):
    E = G['ev']
    a = 1.4 if E['hit'] <= t < E['jump'] else 0.0
    return max(a, 5.0 * pulse(t, E['jump'], 0.5), 6.0 * pulse(t, E['catch'], 0.45), 3.0 * pulse(t, E['nibble'], 0.25),
               6.0 * pulse(t, G['t_rey'], 0.5))


def frame(t):
    if not G:
        init()
    E = G['ev']
    s = active(t)
    pose, tex = lince_state(t, s)
    vil = G['vil']
    vil.model.pose(pose)
    NW = vil.model.node_world
    acts = [dict(asset=vil, world=WM, pose=pose, tex=tex)]
    rod_vis = t < E['jump'] + 0.6
    if rod_vis:
        rw = WM @ NW[14]
        acts.append(dict(asset=G['rod'], world=rw, pose=None, tex={}))
        G['tip'] = (rw @ ROD_TIP)[:3]
    # sombra del salmón bajo el agua y salmón rey
    for st, scl in ((shadow_state(t), 0.8), (rey_state(t), 0.8)):
        if st is not None:
            p, d, al, k = st
            yaw = np.arctan2(d[0], d[2])
            wmat = world_matrix(p, yaw, scl * k)
            acts.append(dict(asset=G['shadow'], world=wmat, pose=pose_at(G['shadow'], 'fish_shadow', t) if 'fish_shadow' in G['shadow'].anims else None,
                             tex={}, ambient=1.0))
    sa = salmon_air(t)
    if sa is not None:
        if isinstance(sa[0], str):
            hm = WM @ NW[11] @ np.diag([FS, FS, FS, 1.0])
            acts.append(dict(asset=G['sal'], world=hm, pose=pose_at(G['sal'], 'fish26', t), tex={}, ambient=0.95))
        else:
            acts.append(dict(asset=G['sal'], world=sa[0], pose=pose_at(G['sal'], 'fish26', t), tex={}, ambient=0.95))
    eye, tgt, fov, shot = camera(t)
    fov -= 2 * pulse(t, E['nibble'], 0.3) + 3 * pulse(t, E['hit'], 0.3) + 5 * pulse(t, E['jump'], 0.4) + 4 * pulse(t, E['catch'], 0.5)   # golpes de zoom
    view = look_at(eye, tgt)
    cv, proj = G['v'].render(view, acts, t=t, fov=fov)
    img = cv.to_image()[..., :3].astype(np.float32) / 255.0
    font = G['font']
    board = shot == 'board' and t >= T_START - 0.2
    # --- agua, línea de pescar, flotador y salpicaduras
    bp = bobber_state(t)
    water_fx(img, t, view, proj, bp)
    if rod_vis and 'tip' in G:
        tip = G['tip']
        end = bp
        if end is None and E['jump'] <= t < E['catch']:
            end = salmon_air(t)[1]
        if end is not None and t >= E['cast'] + 0.4:
            slack = 0.5 if t < E['cast'] + 1.4 else (0.06 if t < E['jump'] else 0.2)
            draw_line(img, tip, end, slack, view, proj)
        if bp is not None:
            q = project(bp, view, proj)
            if q is not None:
                draw_bobber(img, q)
    cast_trail(img, t, view, proj)
    for te, pos, k in ((E['cast'] + 1.1, B0, 1.0), (E['nibble'], B0, 0.5), (E['hit'], B0, 0.8), (E['jump'], SPLASH0, 1.6)):
        splash2d(img, project(pos, view, proj), t - te, k)
    # --- efectos de acción (detrás del cuadro y los rótulos)
    if E['hit'] <= t < E['jump']:
        img = speed_lines(img, t)
    for te, d_ in ((E['jump'], 1.5), (G['t_rey'], 1.6)):
        if 0 <= t - te < d_:
            img = sunburst(img, W / 2, 80, t, min(1.0, (d_ - (t - te)) / 0.5))
    confetti(img, t, E['catch'])
    # --- cuadro de datos (solo en los planos 'board')
    if board:
        _, ta, _ = current_shot(t)
        draw_board(img, t, ta)
    # --- bocadillos sobre la cabeza y rótulos de cómic (no en los planos con cuadro)
    if not board:
        head = project((WM @ NW[15] @ np.array([0, 1.15, 0, 1.0]))[:3], view, proj)
        for te in (E['nibble'], E['hit']):
            bubble_pop(img, font, head, '!', t - te, 1.0, col=(0.9, 0.15, 0.1), fill=(1.0, 0.95, 0.5), scale=3)
        for i, tg in enumerate(E['graw']):
            bubble_pop(img, font, head, ('#@%&!', '$%&#*!', '@#!*%', '%&$@#!')[i % 4], t - tg, 0.95)
        for te, txt, d_ in ((E['cast'] + 0.25, '¡ZAS!', 1.0), (E['nibble'] + 0.05, '¡PICA!', 1.0), (E['hit'] + 0.05, '¡ENGANCHADO!', 1.1),
                            (E['jump'], '¡SALMÓN!', 1.5), (G['t_rey'], '¡EL REY!', 1.5)):
            pop_text(img, font, txt, 46, t - te, d_)
    # --- diálogo (texto ampliado x2)
    if s is not None:
        bub = G['bubble']
        bx, by = (W - bub.shape[1]) // 2, H - bub.shape[0] - 62
        uu = float(np.clip(min((t - s['t0']) / 0.2, 1.0), 0, 1))
        blit(img, bub, bx, by + (1 - back(uu)) * 18, alpha=float(ease(uu)))
        tx, ty = G['tpos']
        nx, ny = G['npos']
        font.draw(img, bx + nx + 6, by + ny + 3, 'Vecino', (0.1, 0.25, 0.5), bold=True)
        rem = int(max(0, (t - s['t0'])) * CPS)
        for i, line in enumerate(s['wrapped']):
            part = line[:rem]
            rem -= len(line) + 1
            if part:
                font.draw(img, bx + tx, by + ty + i * 30, part, INK, scale=TS, bold=True)
            if rem <= 0:
                break
    # --- temblor, viñeta, destellos, transiciones y fundido final
    a = shake_amp(t)
    if a > 0.3:
        rng = np.random.RandomState(int(t * FPS) + 17)
        img = shift_xy(img, int(round(rng.uniform(-a, a))), int(round(rng.uniform(-a, a))))
    img = img * VIGN
    fl = 0.55 * max(pulse(t, E['hit'], 0.18), pulse(t, E['catch'], 0.25), pulse(t, E['jump'], 0.12))
    if fl > 0:
        img = img * (1 - fl) + fl
    img = transition(img, t)
    f = min(1.0, (G['end'] + 1.0 - t) / 1.2)
    img = img * float(np.clip(f, 0, 1))
    out = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
    return upscale(out)


def _worker(i):
    return frame(i / FPS)


def build_audio(rom, path, duration):
    A = AU.AudioBank(rom)
    sched, reveals, ev, _ = schedule(Font(rom), G['text_w'])
    mix = AU.Mixer(duration + 3)
    music = MP.pista(A, duration + 1)
    env = np.ones(len(music), np.float32)           # la música baja un poco mientras habla el vecino
    for s in sched:
        env[int(s['t0'] * AU.SR):int(s['t1'] * AU.SR)] = 0.62
    k = int(0.15 * AU.SR)
    env = np.convolve(env, np.ones(k, np.float32) / k, 'same')
    mix.add(0.0, music * env[:, None], gain=0.45)
    voz = A.voice_set(19)
    rng = np.random.RandomState(3)
    for s in sched:
        for dt, w in AU.speech_blips(s['text'], voz, 1.3, rng, CPS):
            if s['t0'] + dt < s['t1']:
                mix.add(s['t0'] + dt, w, gain=0.95, pan=0.0)
    S = SX.SFX(A)
    put = lambda t, w, g=1.0, pan=0.0: mix.add(max(0.0, t), w, gain=g, pan=pan)
    # apertura y cortes de plano
    put(0.0, S.whoosh(0.5, True), 0.7)
    for tc, kind in ev['cuts']:
        if kind == 'bars':
            put(tc - 0.16, S.whoosh(0.36, True), 0.75, -0.1)
        elif kind == 'zoom':
            put(tc - 0.16, S.whoosh(0.34, True, boom=True), 0.85)
        elif kind == 'iris':
            put(tc - 0.16, S.whoosh(0.34, False), 0.7, 0.1)
            put(tc + 0.05, S.pop(79), 0.6)
        else:
            put(tc - 0.16, S.whoosh(0.3, True), 0.8, 0.15)
    # pesca
    put(ev['cast'] + 0.2, S.whoosh(0.4, True), 0.8)
    put(ev['cast'] + 1.1, S.splash(0.5), 0.8, 0.2)
    put(ev['cast'] + 1.1, S.plop(), 0.8, 0.2)
    put(ev['nibble'], S.alerta(), 0.85)
    for j in range(int((ev['hit'] - ev['nibble']) * 1.7)):
        put(ev['nibble'] + 0.3 + j / 1.7, S.tick(), 0.7, 0.2)
    put(ev['hit'], S.golpe(), 0.9)
    put(ev['hit'] + 0.05, S.splash(0.7), 0.6, 0.2)
    put(ev['hit'] + 0.15, S.ratchet(ev['jump'] - ev['hit'] - 0.2), 0.6)
    put(ev['jump'] - 1.0, S.trino(0.9), 0.5)
    put(ev['jump'], S.splash(1.0), 1.0, 0.2)
    put(ev['jump'], S.whoosh(0.5, True), 0.7)
    put(ev['catch'], S.fanfarria(), 1.0)
    put(ev['catch'], S.golpe(), 0.6)
    # rótulos de cómic y palabrotas tachadas
    for te in (ev['cast'] + 0.25, ev['nibble'] + 0.05, ev['hit'] + 0.05, ev['jump']):
        put(te, S.pop(88), 0.7)
    for tg in ev['graw']:
        put(tg, S.pop(76), 0.6)
        put(tg + 0.08, S.bleep(), 0.45)
    # datos y chistes
    for i, (k_, tt) in enumerate(sorted(reveals.items())):
        put(tt, S.ding(79 + (i % 4) * 2), 0.9)
    for s in sched:
        if any(w in s['text'] for w in ('tamaño', 'complejo', 'polvo', 'napia')):
            put(s['t1'] + 0.15, S.chiste(), 0.8)
    put(G['t_rey'], S.sting_rey(), 1.0)
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
            Image.fromarray(frame(t)).save(os.path.join(tmp, 'p_%05.1f.png' % t))
        print('ok', len(ts), 'duración total %.1f s' % DURATION)
        sys.exit(0)
    rom = Rom()
    wav = os.path.join(rutas.trabajo('animal-crossing'), '_audio_salmon.wav')
    build_audio(rom, wav, DURATION)
    n = int(DURATION * FPS)
    with mp.Pool(max(1, mp.cpu_count() - 1), initializer=init) as pool:
        write_video(pool.imap(_worker, range(n), chunksize=4), os.path.join(out_dir, 'salmon_vecino.mp4'), audio=wav)
    print('hecho', DURATION)
