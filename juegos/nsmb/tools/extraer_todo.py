"""Extractor de assets de New Super Mario Bros. (DS): ROM -> assets_extraidos/.

Uso (desde la raíz del repo):   python tools/extraer_todo.py [--solo categoria,...] [--sin-audio]
Categorías: modelos, jugadores, fondos, tilesets, fuentes, niveles, audio.
La ROM (*.nds de la raíz) sólo se lee; nunca se modifica.
"""
import sys, os, re, time, traceback, argparse, json
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(HERE, 'nsmb'))
sys.path.insert(0, os.path.join(ROOT, 'video'))
import numpy as np
from PIL import Image, ImageDraw
import rom, nitro3d as N, chars, level as L, backgrounds as B

OUT = rom.rutas.extraidos('nsmb')
CATALOGO = []          # (categoria, fichero, descripción, paso)
FALLOS = []            # (paso, elemento, mensaje)
PASO = ['']


def falla(par):
    FALLOS.append((PASO[0],) + tuple(par))


def out(*p):
    d = os.path.join(OUT, *p[:-1]); os.makedirs(d, exist_ok=True)
    return os.path.join(d, p[-1])


def reg(cat, path, desc):
    CATALOGO.append((cat, os.path.relpath(path, OUT).replace('\\', '/'), desc, PASO[0]))


def seguro(nombre):
    def deco(f):
        def w(*a, **k):
            t = time.time()
            try:
                f(*a, **k); print('  ok  %-10s %.1fs' % (nombre, time.time() - t))
            except Exception as e:
                falla((nombre, repr(e))); print('  FALLO', nombre, repr(e)); traceback.print_exc()
        return w
    return deco


def sheet(imgs, labels, path, cell=(96, 96), cols=10, bg=(70, 70, 90, 255), scale=1):
    """Hoja de contactos: imgs = PIL RGBA, labels = textos."""
    cw, ch = cell[0] * scale, cell[1] * scale + 12
    rows = (len(imgs) + cols - 1) // cols
    S = Image.new('RGBA', (cols * cw, max(rows, 1) * ch), bg); d = ImageDraw.Draw(S)
    for i, (im, lb) in enumerate(zip(imgs, labels)):
        x, y = (i % cols) * cw, (i // cols) * ch
        if im is not None:
            k = min(cell[0] / im.width, cell[1] / im.height, 4)
            k = max(1, int(k)) if k >= 1 else k
            t = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.NEAREST)
            S.alpha_composite(t, (x + (cw - t.width) // 2, y + 12 + (cell[1] * scale - t.height) // 2))
        d.text((x + 2, y), lb[:cw // 6], fill=(255, 255, 0, 255))
    S.convert('RGB').save(path)


# ------------------------------------------------------------------ modelos 3D
def _tex_for(nit, name):
    """TexLookup del modelo + sus texturas externas (.nsbtx / .nsbtx del mismo nombre)."""
    extra = []
    base = os.path.splitext(name)[0]
    for ext in ('.nsbtx',):
        try: extra.append(N.Nitro(rom.get(base + ext)))
        except Exception: pass
    return N.TexLookup(nit, *extra)


def render_fit(nit, anim=None, frame=0, target=96, yaw=90.0, texlook=None, midx=0):
    mdl = nit.models[midx]
    R = chars.rot_y(yaw)
    tris = mdl.triangles(anim, frame, root=R)
    if not tris: return None
    pts = np.array([[v[0], v[1]] for _, t in tris for v in t])
    ext = max(np.ptp(pts[:, 0]), np.ptp(pts[:, 1]), 1e-3)
    sc = target / ext
    img, _ = N.render_items([(tris, mdl, None, 0)], texlook or N.TexLookup(nit), scale=sc)
    return Image.fromarray(img, 'RGBA') if img is not None else None


def export_obj(nit, texlook, base, anim=None, frame=0, midx=0):
    """OBJ + MTL + PNG de texturas. Un grupo por material."""
    mdl = nit.models[midx]
    tris = mdl.triangles(anim, frame)
    if not tris: return False
    d = os.path.dirname(base); os.makedirs(d, exist_ok=True)
    name = os.path.basename(base)
    mats = {}
    V, T, Nn, faces = [], [], [], {}
    for mi, tri in tris:
        m = mdl.materials[mi]
        tex = texlook.get(m.tex, m.pal) if m.tex else None
        if tex is not None and mi not in mats:
            fn = '%s_%s.png' % (name, m.name)
            Image.fromarray(tex, 'RGBA').save(os.path.join(d, fn)); mats[mi] = (m.name, fn, tex.shape[1], tex.shape[0])
        w, h = (mats[mi][2], mats[mi][3]) if mi in mats else (1, 1)
        idx = []
        for v in tri:
            V.append(v[:3]); T.append((v[3] / w, 1 - v[4] / h)); Nn.append(v[6] if len(v) > 6 else (0, 1, 0))
            idx.append(len(V))
        faces.setdefault(mi, []).append(idx)
    with open(base + '.mtl', 'w') as f:
        for mi, (mn, fn, *_r) in mats.items():
            f.write('newmtl %s\nKd 1 1 1\nmap_Kd %s\n\n' % (mn, fn))
        if len(mats) < len(faces): f.write('newmtl sin_textura\nKd 0.7 0.7 0.7\n\n')
    with open(base + '.obj', 'w') as f:
        f.write('mtllib %s.mtl\n' % name)
        for v in V: f.write('v %.5f %.5f %.5f\n' % tuple(v))
        for t in T: f.write('vt %.5f %.5f\n' % t)
        for n in Nn: f.write('vn %.4f %.4f %.4f\n' % tuple(n))
        for mi, fl in faces.items():
            f.write('usemtl %s\n' % (mats[mi][0] if mi in mats else 'sin_textura'))
            for a, b, c in fl: f.write('f %d/%d/%d %d/%d/%d %d/%d/%d\n' % (a, a, a, b, b, b, c, c, c))
    return True


def categoria_modelo(path):
    n = os.path.basename(path)
    if path.startswith('player/'): return 'jugadores'
    if path.startswith('map/'): return 'mapa_del_mundo'
    if re.match(r'(I_|obj_|coin|hatena|normal_lift|barrel|jump_step|iron|balance|kuruma|m\d_sign|all_goal|ef_|hanabi|elec|burner|fire|bubble|boomerang|bellows|cork|e3|hammer_map|A_jiku|m_hole|koopa_key|big_iron)', n):
        return 'objetos'
    return 'enemigos'


@seguro('modelos')
def modelos():
    files = [f for f in rom.listdir('') if f.endswith('.nsbmd') or (f.endswith('_LZ.bin') and f.startswith('player/'))]
    por_cat = {}
    n_ok = 0
    for f in sorted(files):
        try:
            nit = N.Nitro(rom.getu(f) if f.endswith('_LZ.bin') else rom.get(f))
            if not nit.models: continue
            tl = _tex_for(nit, f)
            base = re.sub(r'\.(nsbmd|bin)$', '', os.path.basename(f)).replace('_LZ', '')
            cat = categoria_modelo(f)
            # animación representativa
            anims = {}
            try:
                for ext in ('.nsbca',):
                    fn = re.sub(r'\.nsbmd$', ext, f)
                    anims = {a.name: a for a in N.Nitro(rom.get(fn)).anims}
            except Exception: pass
            an = next((anims[k] for k in ('walk', 'wait', 'run') if k in anims), next(iter(anims.values()), None))
            im = render_fit(nit, an, 0, 320 if cat == 'mapa_del_mundo' else 96, texlook=tl)
            if im is None or np.asarray(im)[..., 3].astype(bool).sum() < 40: continue        # modelo vacío / sin geometría visible
            p = out(cat, 'png', base + '.png'); im.save(p); reg(cat, p, 'render ' + f)
            ob = out(cat, 'modelos_obj', base, base)
            if export_obj(nit, tl, ob, an, 0): reg(cat, ob + '.obj', 'OBJ+MTL+texturas de ' + f)
            por_cat.setdefault(cat, []).append((base, im)); n_ok += 1
        except Exception as e:
            falla(('modelo ' + f, repr(e)))
    for cat, lst in por_cat.items():
        p = out('hojas_contactos', 'modelos_%s.png' % cat)
        sheet([i for _, i in lst], [n for n, _ in lst], p, cell=(96, 96), cols=12)
        reg('hojas_contactos', p, 'hoja de contactos de %d modelos de %s' % (len(lst), cat))
    print('   modelos renderizados:', n_ok)


# ------------------------------------------------------------------ jugadores con animaciones
@seguro('jugadores')
def jugadores():
    pieces = [('mario_grande', chars.mario()), ('mario_pequeno', chars.mario(small=True)),
              ('luigi_grande', chars.mario(luigi=True)), ('luigi_pequeno', chars.mario(luigi=True, small=True))]
    todo_i, todo_l = [], []
    for nom, a in pieces:
        im, _ = a.sprite('wait', 0); p = out('jugadores', nom, 'pose_reposo.png'); im.save(p); reg('jugadores', p, nom + ' en reposo')
        todo_i.append(im); todo_l.append(nom)
        if nom != 'mario_grande': continue
        for an in ('run', 'walk', 'jump', 'jumped', 'tree_pose', 'goal_jump', 'wait', 'squat_start', 'swim', 'dead', 'spin_jump'):
            if an not in a.anims: continue
            nf = int(a.anims[an].num_frames); k = min(12, nf)
            fr = [a.sprite(an, int(i * (nf - 1) / max(1, k - 1)))[0] for i in range(k)]
            S = Image.new('RGBA', (64 * k, 64), (0, 0, 0, 0))
            for i, f in enumerate(fr): S.alpha_composite(f, (i * 64, 0))
            p = out('jugadores', nom, 'anim_%s.png' % an); S.save(p); reg('jugadores', p, 'animación %s de %s (%d de %d fotogramas)' % (an, nom, k, nf))
    # enemigos animados
    g, kp = chars.goomba(), chars.koopa()
    for nom, a in (('goomba', g), ('koopa', kp)):
        for an in ('walk', 'damage'):
            if an not in a.anims: continue
            nf = int(a.anims[an].num_frames); k = min(10, nf)
            fr = [a.sprite(an, int(i * (nf - 1) / max(1, k - 1)))[0] for i in range(k)]
            w, h = fr[0].size; S = Image.new('RGBA', (w * k, h), (0, 0, 0, 0))
            for i, f in enumerate(fr): S.alpha_composite(f, (i * w, 0))
            p = out('enemigos', 'anim_%s_%s.png' % (nom, an)); S.save(p); reg('enemigos', p, 'animación %s de %s' % (an, nom))
    p = out('hojas_contactos', 'jugadores.png'); sheet(todo_i, todo_l, p, cell=(64, 64), cols=4, scale=2)
    reg('hojas_contactos', p, 'Mario y Luigi, grande y pequeño')


# ------------------------------------------------------------------ fondos
@seguro('fondos')
def fondos():
    temas = {}
    for f in rom.listdir('BG_nsc/'):
        m = re.match(r'BG_nsc/d_2d_I_M_(back|free)_(.+?)(?:_UR)?_nsc\.bin', f)
        if m: temas.setdefault(m.group(2), set()).add(m.group(1))
    imgs, lbs = [], []
    for tema, kinds in sorted(temas.items()):
        for kind in ('back', 'free'):
            if kind not in kinds: continue
            try:
                im = B.layer(kind, tema)
                sky = Image.new('RGBA', im.size, (24, 144, 255, 255)); sky.alpha_composite(im)
                p = out('fondos', '%s_%s.png' % (kind, tema)); im.save(p); reg('fondos', p, 'capa %s del tema %s (transparente)' % (kind, tema))
                imgs.append(sky); lbs.append('%s %s' % (kind, tema))
            except Exception as e:
                falla(('fondo %s %s' % (kind, tema), repr(e)))
    p = out('hojas_contactos', 'fondos.png'); sheet(imgs, lbs, p, cell=(160, 160), cols=6)
    reg('hojas_contactos', p, 'capas de fondo (parallax) sobre cielo')


# ------------------------------------------------------------------ tilesets
@seguro('tilesets')
def tilesets():
    names = sorted(set(re.match(r'BG_unt/(.+)\.bin', f).group(1) for f in rom.listdir('BG_unt/') if not f.endswith('_hd.bin')))
    imgs, lbs = [], []
    for nm in names:
        m = re.match(r'(I_[MS])_(.+)$', nm)
        if not m or m.group(1) != 'I_M': continue
        tema = m.group(2); stage = nm; tik = 'I_M_tikei_' + tema
        sec = 'I_S_' + tema
        try:
            third, third_t = (sec, 'I_S_tikei_' + tema) if ('BG_unt/%s.bin' % sec) in rom.listdir('BG_unt/') and ('BG_ncg/d_2d_I_S_tikei_%s_ncg.bin' % tema) in rom.listdir('BG_ncg/') else (None, None)
            ts = L.Tileset(stage, tik, third, third_t)
            cells = {}
            for th in (1, 2, 3):
                for num in range(256):
                    im = ts.map16_img(th, num)
                    if im is not None and im[..., 3].any(): cells[(th, num)] = Image.fromarray(im, 'RGBA')
            if not cells: continue
            n = len(cells); cols_ = 32; rows = (n + cols_ - 1) // cols_
            S = Image.new('RGBA', (cols_ * 16, rows * 16), (0, 0, 0, 0))
            for i, im in enumerate(cells.values()): S.alpha_composite(im, ((i % cols_) * 16, (i // cols_) * 16))
            p = out('tilesets', 'tileset_%s.png' % tema); S.save(p); reg('tilesets', p, 'bloques Map16 del tema %s (%d)' % (tema, n))
            bg = Image.new('RGBA', S.size, (24, 144, 255, 255)); bg.alpha_composite(S); imgs.append(bg); lbs.append(tema)
        except Exception as e:
            falla(('tileset ' + nm, repr(e)))
    if imgs:
        p = out('hojas_contactos', 'tilesets.png'); sheet(imgs, lbs, p, cell=(256, 100), cols=3)
        reg('hojas_contactos', p, 'tilesets por tema')


# ------------------------------------------------------------------ fuentes
@seguro('fuentes')
def fuentes():
    import text, nftr
    for i, nom in ((0, 'font_a'), (1, 'font_b')):
        f = text.font(i)
        cols_ = 32; n = f.nglyphs; rows = (n + cols_ - 1) // cols_
        tw, th = f.tw + 1, f.th + 1
        S = np.zeros((rows * th, cols_ * tw, 4), np.uint8)
        pal = {0: (0, 0, 0, 0), 1: (255, 255, 255, 255), 2: (170, 170, 170, 255), 3: (90, 90, 90, 255)}
        for g in range(n):
            bm = f.glyph(g); y, x = (g // cols_) * th, (g % cols_) * tw
            for v, c in pal.items(): S[y:y + f.th, x:x + f.tw][bm == v] = c
        p = out('fuentes', nom + '_glifos.png'); Image.fromarray(S, 'RGBA').save(p); reg('fuentes', p, '%s: %d glifos %dx%d, %d bpp' % (nom, n, f.tw, f.th, f.depth))
    im = text.render('¡Hola, Mundo 1-1! Ñandú, ¿qué tal?  0123456789')
    p = out('fuentes', 'ejemplo_texto.png'); im.save(p); reg('fuentes', p, 'texto de ejemplo con font_a (es)')
    sheet([Image.open(out('fuentes', 'font_a_glifos.png')).convert('RGBA')], ['font_a'], out('hojas_contactos', 'fuentes.png'), cell=(512, 240), cols=1)
    reg('hojas_contactos', out('hojas_contactos', 'fuentes.png'), 'glifos de font_a')


# ------------------------------------------------------------------ niveles
@seguro('niveles')
def niveles():
    import world
    w = world.get()
    im = Image.new('RGBA', w.layer.size, (24, 144, 255, 255)); im.alpha_composite(w.layer)
    for cx, cy in w.coins: im.alpha_composite(w.coin_img, (cx * 16, cy * 16))
    p = out('niveles', 'mundo_1-1.png'); im.convert('RGB').save(p); reg('niveles', p, 'nivel 1-1 completo (tileset real + monedas + tuberías)')
    h = im.height
    S = Image.new('RGB', (2144, h * 2)); S.paste(im.crop((0, 0, 2144, h)).convert('RGB'), (0, 0)); S.paste(im.crop((2144, 0, 4288, h)).convert('RGB'), (0, h))
    q = out('hojas_contactos', 'nivel_1-1.png'); S.save(q); reg('hojas_contactos', q, 'nivel 1-1 (dos mitades)')


# ------------------------------------------------------------------ audio
_SON = []


def _sfx_worker(nm):
    import audio, sonido
    if not _SON: _SON.append(audio.son())
    a = _SON[0].efecto(nm, 4.0)
    idx = np.nonzero(np.abs(a).max(1) > 1e-3)[0]
    if not len(idx): return 0
    a = a[:idx[-1] + 1]; m = float(np.abs(a).max())
    sonido.guardar_wav(out('audio', 'efectos', nm + '.wav'), a / m * 0.8)
    return len(a) / sonido.FS


@seguro('audio')
def audio_():
    import audio, sonido, wave
    son = audio.son(); FS = sonido.FS

    def guardar(path, a, peak=0.9):
        a = np.asarray(a, np.float32); m = float(np.abs(a).max())
        if m > 0: a = a / m * peak
        sonido.guardar_wav(path, a)
    nb = ne = 0
    for nm in sorted(son.nombres):
        if not nm.startswith('BGM_'): continue
        try:
            a = son.renderizar(nm, 120)
            idx = np.nonzero(np.abs(a).max(1) > 1e-3)[0]; a = a[:idx[-1] + 1] if len(idx) else a
            p = out('audio', 'musica', nm + '.wav'); guardar(p, a); reg('audio', p, 'música %s (%.1f s)' % (nm, len(a) / FS)); nb += 1
        except Exception as e:
            falla(('bgm ' + nm, repr(e)))
    # Los efectos se renderizan en procesos aparte con tiempo límite: algunos (p. ej. SE_EMY_BOOMERANG) se quedan en un bucle sin fin.
    import multiprocessing as mp
    pend = sorted(set(son.efectos()))
    while pend:
        pool = mp.Pool(4)
        res = [(nm, pool.apply_async(_sfx_worker, (nm,))) for nm in pend]
        pend = []
        for k, (nm, r) in enumerate(res):
            try:
                v = r.get(timeout=60)
                if v:
                    p = out('audio', 'efectos', nm + '.wav'); reg('audio', p, 'efecto %s (%.2f s)' % (nm, v)); ne += 1
            except mp.TimeoutError:
                falla(('sfx ' + nm, 'tiempo excedido (bucle sin fin en la síntesis)'))
                pend = [n2 for n2, r2 in res[k + 1:] if not r2.ready()]
                for n2, r2 in res[k + 1:]:
                    if r2.ready():
                        try:
                            v = r2.get()
                            if v: reg('audio', out('audio', 'efectos', n2 + '.wav'), 'efecto %s (%.2f s)' % (n2, v)); ne += 1
                        except Exception as e: falla(('sfx ' + n2, repr(e)))
                break
            except Exception as e:
                falla(('sfx ' + nm, repr(e)))
        pool.terminate(); pool.join()
    print('   música: %d, efectos: %d' % (nb, ne))


# ------------------------------------------------------------------ README
def escribir_readme():
    cats = {}
    for c, f, d, _p in CATALOGO: cats.setdefault(c, []).append((f, d))
    with open(os.path.join(OUT, 'README.md'), 'w', encoding='utf-8') as fh:
        fh.write('# assets_extraidos — New Super Mario Bros. (DS, ROM europea española A2DP)\n\n')
        fh.write('Generado por `python tools/extraer_todo.py` a partir de la ROM. Regenerable; no se modifica la ROM.\n\n')
        fh.write('## Resumen\n\n| categoría | ficheros |\n|---|---|\n')
        for c, l in sorted(cats.items()): fh.write('| %s | %d |\n' % (c, len(l)))
        fh.write('\nLas hojas de contactos (`hojas_contactos/`) sirven para revisar cada categoría de un vistazo.\n')
        if FALLOS:
            fh.write('\n## Elementos que no se pudieron procesar\n\n')
            for _p, n, e in FALLOS[:80]: fh.write('- %s: `%s`\n' % (n, e[:140]))
            if len(FALLOS) > 80: fh.write('- … y %d más\n' % (len(FALLOS) - 80))
        fh.write('\n## Catálogo\n')
        for c, l in sorted(cats.items()):
            fh.write('\n### %s\n\n' % c)
            if len(l) > 60:
                fh.write('%d ficheros; ejemplos:\n\n' % len(l))
                l2 = l[:25]
            else:
                l2 = l
            for f, d in l2: fh.write('- `%s` — %s\n' % (f, d))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', default='')
    ap.add_argument('--sin-audio', action='store_true')
    a = ap.parse_args()
    todo = ['modelos', 'jugadores', 'fondos', 'tilesets', 'fuentes', 'niveles', 'audio']
    if a.solo: todo = [t for t in a.solo.split(',') if t]
    if a.sin_audio and 'audio' in todo: todo.remove('audio')
    os.makedirs(OUT, exist_ok=True)
    print('ROM:', rom.find_rom())
    f = dict(modelos=modelos, jugadores=jugadores, fondos=fondos, tilesets=tilesets, fuentes=fuentes, niveles=niveles, audio=audio_)
    estado = os.path.join(OUT, '_catalogo.json')
    previo = json.load(open(estado, encoding='utf-8')) if os.path.exists(estado) else {'cat': [], 'fallos': []}
    for t in todo:
        PASO[0] = t; f[t]()
    # se conserva lo de los pasos que no se han repetido en esta ejecución
    CATALOGO[:0] = [tuple(x) for x in previo['cat'] if x[3] not in todo]
    FALLOS[:0] = [tuple(x) for x in previo['fallos'] if x[0] not in todo]
    json.dump({'cat': CATALOGO, 'fallos': FALLOS}, open(estado, 'w', encoding='utf-8'), ensure_ascii=False)
    escribir_readme()
    print('listo: %d ficheros catalogados, %d fallos' % (len(CATALOGO), len(FALLOS)))


if __name__ == '__main__':
    main()
