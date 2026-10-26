"""Extrae todos los sprites, tiles y texturas de Pokémon Platino (ES) a PNG.

Uso:  python -I extract.py <rom.nds> <carpeta_salida>
"""
import sys, os, re, json, struct, unicodedata, traceback
import numpy as np
import ndspy.rom, ndspy.narc, ndspy.codeCompression
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ndsgfx as G
from msg import decode_msg, CH
from names import OTHERPOKE, ICON_FORMS, MMODEL_HINTS, NARC_INFO

# caracteres latinos (Latin-1 a partir de 0x15F) y símbolos usados en nombres
for _c in range(0xC0, 0x100):
    CH[_c + 0x9F] = chr(_c)
CH.update({0x1BB: '_m', 0x1BC: '_f', 0x1B3: "'", 0x1A9: '', 0x1AA: '', 0x1C4: ':', 0x1B4: '', 0x1B5: ''})

ROM = None
OUT = None
STATS = {'png': 0}


def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^A-Za-z0-9_]+', '_', s.lower()).strip('_')
    return re.sub(r'_+', '_', s) or 'x'


def save(img, *path):
    p = os.path.join(OUT, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    img.save(p)
    STATS['png'] += 1


def save_json(obj, *path):
    p = os.path.join(OUT, *path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def narc(path):
    return [G.unwrap(f) for f in ndspy.narc.NARC(ROM.getFileByName(path)).files]


def messages(i):
    return decode_msg(ndspy.narc.NARC(ROM.getFileByName('msgdata/pl_msg.narc')).files[i])


def decrypt_pt(raw):
    a = np.frombuffer(raw, '<u2').copy()
    seed = int(a[0])
    for i in range(a.size):
        a[i] ^= seed & 0xFFFF
        seed = (seed * 0x41C64E6D + 0x6073) & 0xFFFFFFFF
    return a.tobytes()


def enc_graphic(data):
    g = G.Graphic(data)
    g.raw = decrypt_pt(g.raw)
    return g


def strip_frames(img, fw):
    return [img.crop((x, 0, x + fw, img.height)) for x in range(0, img.width, fw)]


# ------------------------------------------------------------------ Pokémon

def species_names():
    names = messages(412)
    out = []
    for i, n in enumerate(names):
        out.append('%03d_%s' % (i, slug(n) if i else 'nada'))
    return out


def do_pokemon():
    names = species_names()
    files = narc('poketool/pokegra/pl_pokegra.narc')
    views = [('espalda', 'hembra'), ('espalda', ''), ('frente', 'hembra'), ('frente', '')]
    for sp in range(len(files) // 6):
        f = files[sp * 6: sp * 6 + 6]
        name = names[sp] if sp < len(names) else '%03d' % sp
        pals = [G.Palette(f[4]), G.Palette(f[5])]
        for k, (view, gender) in enumerate(views):
            if G.magic(f[k]) != b'RGCN':
                continue
            g = enc_graphic(f[k])
            idx = g.image_indices()
            for pal, pname in zip(pals, ('normal', 'shiny')):
                fn = name + ('_hembra' if gender else '') + '.png'
                save(G.render(idx, pal.table()), 'pokemon', view, pname, fn)
    print('pokemon ok')


def do_otherpoke():
    files = narc('poketool/pokegra/pl_otherpoke.narc')
    gfx = [i for i, f in enumerate(files) if G.magic(f) == b'RGCN']
    pals = [i for i, f in enumerate(files) if G.magic(f) == b'RLCN']
    for gi, fi in enumerate(gfx):
        name, view, pal_list = OTHERPOKE[gi]
        g = enc_graphic(files[fi])
        idx = g.image_indices()
        for pname, pal_i in pal_list:
            pal = G.Palette(files[pals[pal_i]])
            save(G.render(idx, pal.table()), 'pokemon', 'formas', view, pname, name + '.png')
    print('otherpoke ok')


def do_icons():
    names = species_names()
    files = narc('poketool/icongra/pl_poke_icon.narc')
    pal = G.Palette(files[0])
    arm9 = ndspy.codeCompression.decompress(ROM.arm9)
    table = arm9[0xF0815 - 1: 0xF0815 - 1 + 600]
    gfx = [i for i, f in enumerate(files) if G.magic(f) == b'RGCN']
    for n, fi in enumerate(gfx):
        if n < len(names):
            name = names[n]
        elif n - len(names) < len(ICON_FORMS):
            name = ICON_FORMS[n - len(names)]
        else:
            name = 'icono_%03d' % n
        g = G.Graphic(files[fi])
        idx = g.image_indices(width_tiles=4)  # 32x64: dos frames verticales
        save(G.render(idx, pal.table(table[n] if n < len(table) else 0)), 'pokemon', 'iconos', name + '.png')
    save(pal.swatch(), 'pokemon', 'iconos', '_paletas.png')
    print('icons ok')


def do_footprints():
    names = species_names()
    files = narc('poketool/pokefoot/pokefoot.narc')
    pal = G.Palette(files[0])
    cells = G.Cells(files[2])
    gfx = [f for f in files if G.magic(f) == b'RGCN']
    for n, f in enumerate(gfx):
        im = cells.render_cell(0, G.Graphic(f), pal)
        name = names[n + 1] if n + 1 < len(names) else '%03d' % (n + 1)
        save(im, 'pokemon', 'huellas', name + '.png')
    print('footprints ok')


# ------------------------------------------------------------------ entrenadores

def do_trainers():
    classes = messages(619)
    for arc, view in (('trfgra', 'frente'), ('trbgra', 'espalda')):
        files = narc('poketool/trgra/%s.narc' % arc)
        for t in range(len(files) // 5):
            f = files[t * 5: t * 5 + 5]
            if view == 'frente':
                name = '%03d_%s' % (t, slug(classes[t]) if t < len(classes) else 'clase')
            else:
                name = '%02d_%s' % (t, TRBACK[t] if t < len(TRBACK) else 'espalda')
            pal = G.Palette(f[1])
            # imagen fija 160x80 (2 frames) cifrada
            g = enc_graphic(f[4])
            save(G.render(g.image_indices(), pal.table()), 'entrenadores', view, 'estatico', name + '.png')
            # animación por celdas
            export_cells(G.Graphic(f[0]), pal, G.Cells(f[2]), G.parse_nanr(f[3]),
                         ('entrenadores', view, 'animado', name))
    print('trainers ok')


TRBACK = ['lucas', 'maya', 'israel_barry', 'cheryl', 'riley', 'marley', 'buck', 'mira',
          'lucas_diamante_perla', 'maya_diamante_perla', 'israel_barry_alt']


def export_cells(gfx, pal, cells, anims, path, pal_offset=0, sheet=True):
    """Exporta cada celda como PNG (mismo lienzo para todas) + JSON de animación + spritesheet."""
    b = cells.bounds()
    frames = []
    for i in range(len(cells.cells)):
        im = cells.render_cell(i, gfx, pal, pal_offset, bounds=b)
        if im is None:
            frames.append(None)
            continue
        save(im, *path, 'celda_%02d.png' % i)
        frames.append(im)
    # "VRAM transfer": todas las celdas usan el tile 0 y el NCGR trae varios bloques de tiles,
    # que el juego va cargando como frames. Se exporta cada bloque con la celda 0.
    vram = []
    if cells.cells and all(o['tile'] == 0 for c in cells.cells for o in c[:1]):
        used = cells.tiles_used(0, gfx.depth)
        if used and gfx.ntiles >= used * 2:
            for k in range(gfx.ntiles // used):
                im = cells.render_cell(0, gfx, pal, pal_offset, bounds=b, tile_base=k * used)
                save(im, *path, 'frame_vram_%02d.png' % k)
                vram.append(im)
            frames = vram
    valid = [im for im in frames if im is not None]
    if sheet and valid:
        w, h = valid[0].size
        cols = min(len(frames), 8)
        rows = (len(frames) + cols - 1) // cols
        s = Image.new('RGBA', (w * cols, h * rows))
        for i, im in enumerate(frames):
            if im is not None:
                s.paste(im, ((i % cols) * w, (i // cols) * h))
        save(s, *path, '_spritesheet.png')
    meta = {'origen_celdas': {'x': b[0], 'y': b[1]}, 'tam_celda': [b[2] - b[0], b[3] - b[1]],
            'columnas_spritesheet': min(len(frames), 8) if frames else 0,
            'celdas': len(cells.cells), 'animaciones': anims or [], 'frames_vram': len(vram),
            'nota': ('duration en frames de 60fps; cell = indice de celda_XX.png. Si frames_vram > 0, '
                     'la animacion real son los frame_vram_XX.png en orden (el spritesheet los contiene) '
                     'y las celdas solo aportan desplazamientos.')}
    save_json(meta, *path, 'animaciones.json')


# ------------------------------------------------------------------ texturas 3D

MAP_PAIRS = None


def map_pairs():
    """{textura: [paletas por frecuencia]} a partir de los materiales de todos los modelos de mapa."""
    global MAP_PAIRS
    if MAP_PAIRS is None:
        import collections
        c = collections.defaultdict(collections.Counter)
        for path in ('fielddata/land_data/land_data.narc', 'fielddata/build_model/build_model.narc'):
            for x in ndspy.narc.NARC(ROM.getFileByName(path)).files:
                i = x.find(b'BMD0')
                if i >= 0:
                    for t, p in G.material_pairs(bytes(x[i:])).items():
                        c[t][p] += 1
        MAP_PAIRS = {t: [p for p, _ in v.most_common()] for t, v in c.items()}
    return MAP_PAIRS


ALL_PALS = None


def all_map_palettes():
    global ALL_PALS
    if ALL_PALS is None:
        ALL_PALS = {}
        for path in ('fielddata/areadata/area_map_tex/map_tex_set.narc',
                     'fielddata/areadata/area_build_model/areabm_texset.narc'):
            for x in ndspy.narc.NARC(ROM.getFileByName(path)).files:
                for k, v in G.palettes_of(x).items():
                    ALL_PALS.setdefault(k, v)
    return ALL_PALS


def export_textures(data, path, prefix='', overrides=None):
    n = 0
    extra = all_map_palettes() if overrides is not None else None
    for tname, pname, img in sorted(G.decode_textures(data, overrides, extra), key=frame_key):
        save(img, *path, prefix + slug(tname) + '.png')
        n += 1
    return n


def do_mmodel():
    files = narc('data/mmodel/mmodel.narc')
    for i, f in enumerate(files):
        if G.magic(f) not in (b'BTX0', b'BMD0'):
            continue
        texs = G.decode_textures(f)
        if not texs:
            continue
        texs.sort(key=frame_key)
        hint = MMODEL_HINTS.get(i)
        stem = slug(texs[0][0].rsplit('.', 1)[0])
        base = '%03d_%s' % (i, stem) + ('_' + hint if hint else '')
        # frames individuales + tira horizontal (en orden de frame) para animar
        for k, (tname, pname, img) in enumerate(texs):
            save(img, 'personajes_mapa', base, 'frame_%02d.png' % k)
        save_json({'textura_original': [t[0] for t in texs], 'paleta': [t[1] for t in texs],
                   'tam_frame': list(texs[0][2].size)}, 'personajes_mapa', base, 'info.json')
        if len(texs) > 1:
            w, h = texs[0][2].size
            same = [t for t in texs if t[2].size == (w, h)]
            strip = Image.new('RGBA', (w * len(same), h))
            for k, t in enumerate(same):
                strip.paste(t[2], (k * w, 0))
            save(strip, 'personajes_mapa', base, '_tira.png')
    files = narc('data/mmodel/fldeff.narc')
    for i, f in enumerate(files):
        if G.magic(f) in (b'BTX0', b'BMD0'):
            export_textures(f, ('efectos_mapa', '%03d' % i))
    print('mmodel ok')


def frame_key(t):
    m = re.match(r'(.*?)[._]?(\d+)$', t[0])
    return (m.group(1), int(m.group(2))) if m else (t[0], -1)


def do_map_textures():
    areas = narc('fielddata/areadata/area_map_tex/map_tex_set.narc')
    for i, f in enumerate(areas):
        export_textures(f, ('tilesets_mapa', 'terreno', 'set_%03d' % i), overrides=map_pairs())
    areas = narc('fielddata/areadata/area_build_model/areabm_texset.narc')
    for i, f in enumerate(areas):
        export_textures(f, ('tilesets_mapa', 'edificios_por_zona', 'set_%03d' % i), overrides=map_pairs())
    blds = narc('fielddata/build_model/build_model.narc')
    for i, f in enumerate(blds):
        export_textures(f, ('tilesets_mapa', 'modelos_edificios', '%03d' % i))
    anims = narc('data/fldtanime.narc')
    for i, f in enumerate(anims):
        if G.magic(f) == b'BTX0':
            export_textures(f, ('tilesets_mapa', 'animados', '%02d' % i), overrides=map_pairs())
    for fid, name in iter_root_files():
        if name.lower().endswith('.nsbtx') or name.lower().endswith('.nsbmd'):
            export_textures(G.unwrap(ROM.files[fid]), ('tilesets_mapa', 'sueltos', slug(name.rsplit('.', 1)[0])))
    print('map textures ok')


def iter_root_files():
    def walk(folder, prefix=''):
        for i, n in enumerate(folder.files):
            yield folder.firstID + i, prefix + n
        for n, sub in folder.folders:
            yield from walk(sub, prefix + n + '/')
    yield from walk(ROM.filenames)


# ------------------------------------------------------------------ genérico 2D

def nearest(i, cands, prefer_before=True):
    if not cands:
        return None
    best = min(cands, key=lambda c: (abs(c - i), c > i if prefer_before else c < i))
    return best


def pair(src, dst, i):
    """Elige el fichero de 'dst' asociado al índice i de 'src'."""
    if not dst:
        return None
    if len(src) == len(dst):
        return dst[src.index(i)]
    return nearest(i, dst)


def _ok(fn, data):
    try:
        fn(data)
        return True
    except Exception:
        return False


def do_generic(path, outdir, files=None):
    files = files if files is not None else narc(path)
    by = {}
    for i, f in enumerate(files):
        by.setdefault(G.magic(f), []).append(i)
    ncgr, nclr, ncer, nanr, nscr = (by.get(m, []) for m in (b'RGCN', b'RLCN', b'RECN', b'RNAN', b'RCSN'))
    info = NARC_INFO.get(path, {})
    count = 0
    for i in nclr:
        try:
            save(G.Palette(files[i]).swatch(), outdir, '_paletas', '%03d.png' % i)
        except Exception:
            pass
    used_by_cells = set()
    G_ = {i: G.Graphic(files[i]) for i in ncgr if _ok(G.Graphic, files[i])}
    P_ = {i: G.Palette(files[i]) for i in nclr if _ok(G.Palette, files[i])}

    def best_gfx(i, need_tiles):
        cands = [g for g in G_ if G_[g].ntiles >= need_tiles and G_[g].raw]
        if len(ncgr) == len(nscr if i in nscr else ncer) and ncgr:
            k = (nscr if i in nscr else ncer).index(i)
            if ncgr[k] in cands:
                return ncgr[k]
        return min(cands, key=lambda g: (abs(g - i), g > i)) if cands else None

    def best_pal(gi, banks_needed=1):
        if gi in info.get('pal', {}):
            return info['pal'][gi]
        d = G_[gi].depth
        cands = [p for p in P_ if (len(P_[p].colors) >= (256 if d == 8 else 16 * banks_needed)) or len(P_) == 1]
        cands = cands or list(P_)
        if not cands:
            return None
        if len(ncgr) == len(nclr) and nclr[ncgr.index(gi)] in cands:
            return nclr[ncgr.index(gi)]
        return min(cands, key=lambda p: (abs(p - gi), p < gi))

    for i in ncer:
        try:
            cells = G.Cells(files[i])
            need = max([cells.tiles_used(c) for c in range(len(cells.cells))] or [1])
            gi = info.get('cells_gfx', {}).get(i) or best_gfx(i, need)
            if gi is None:
                continue
            banks = 1 + max([o['pal'] for c in cells.cells for o in c] or [0])
            pi = best_pal(gi, banks)
            if pi is None:
                continue
            ai = pair(ncer, nanr, i)
            anims = G.parse_nanr(files[ai]) if ai is not None else []
            export_cells(G_[gi], P_[pi], cells, anims, (outdir, 'sprites_celdas', '%03d_gfx%03d' % (i, gi)))
            used_by_cells.add(gi)
            count += 1
        except Exception as e:
            log('cells', path, i, e)
    for i in nscr:
        try:
            scr = G.Screen(files[i])
            if not scr.entries.size:
                continue
            need = int((scr.entries & 0x3FF).max()) + 1
            cands = sorted((g for g in G_ if G_[g].ntiles >= need and G_[g].raw), key=lambda g: abs(g - i))[:8]
            if len(ncgr) == len(nscr):
                gi = ncgr[nscr.index(i)] if ncgr[nscr.index(i)] in cands else None
            else:
                gi = None
            if gi is None and cands:
                gi = min(cands, key=lambda g: (round(G.seam_score(scr, G_[g]), 2), abs(g - i)))
            if gi is None:
                continue
            banks = 1 + int((scr.entries >> 12).max())
            pi = best_pal(gi, banks)
            if pi is None:
                continue
            save(scr.render(G_[gi], P_[pi]), outdir, 'pantallas', '%03d_gfx%03d_pal%03d.png' % (i, gi, pi))
            count += 1
        except Exception as e:
            log('screen', path, i, e)
    for i in ncgr:
        pi = info.get('pal', {}).get(i) or pair(ncgr, nclr, i)
        try:
            gfx = G.Graphic(files[i])
            if not gfx.raw:
                continue
            pal = G.Palette(files[pi]) if pi is not None else None
            table = pal.table(0, gfx.depth) if pal else G.grayscale_palette(gfx.depth)
            if gfx.has_dims and gfx.w_tiles and gfx.h_tiles and gfx.w_tiles * gfx.h_tiles <= gfx.ntiles * 2:
                idx = gfx.image_indices()
            else:
                idx = gfx.image_indices(width_tiles=16 if gfx.ntiles >= 16 else max(1, gfx.ntiles))
            save(G.render(idx, table), outdir, 'tiles', '%03d.png' % i)
            count += 1
        except Exception as e:
            log('gfx', path, i, e)
    for m in (b'BTX0', b'BMD0'):
        for i in by.get(m, []):
            try:
                export_textures(files[i], (outdir, 'texturas_3d', '%03d' % i))
            except Exception as e:
                log('tex', path, i, e)
    return count


ERRORS = []


def log(*a):
    ERRORS.append(' '.join(str(x) for x in a))


SPECIAL = {
    'poketool/pokegra/pl_pokegra.narc', 'poketool/pokegra/pokegra.narc', 'poketool/pokegra/otherpoke.narc',
    'poketool/pokegra/pl_otherpoke.narc', 'poketool/icongra/pl_poke_icon.narc', 'poketool/icongra/poke_icon.narc',
    'poketool/trgra/trbgra.narc', 'poketool/trgra/trfgra.narc', 'poketool/pokefoot/pokefoot.narc',
    'data/mmodel/mmodel.narc', 'data/mmodel/fldeff.narc', 'fielddata/areadata/area_map_tex/map_tex_set.narc',
    'fielddata/areadata/area_build_model/areabm_texset.narc', 'fielddata/build_model/build_model.narc',
    'data/fldtanime.narc', 'itemtool/itemdata/item_icon.narc',
    'wazaeffect/effectclact/wechar.narc', 'wazaeffect/effectclact/wecell.narc',
    'wazaeffect/effectclact/wecellanm.narc', 'wazaeffect/effectclact/wepltt.narc',
}
# versiones Diamante/Perla duplicadas que Platino no usa
SKIP_DP = {'resource/spa/b_plist/b_plist_gra.narc', 'resource/spa/bag/bag_gra.narc',
           'resource/spa/p_status/pst_gra.narc', 'resource/spa/pokelist/plist_gra.narc',
           'graphic/winframe.narc', 'graphic/font.narc', 'battle/graphic/batt_bg.narc',
           'resource/spa/battle_graphic/batt_obj.narc'}


def do_all_generic():
    for fid, name in iter_root_files():
        if name in SPECIAL or name in SKIP_DP or name.startswith('msgdata'):
            continue
        data = ROM.files[fid]
        if data[:4] == b'NARC':
            files = narc(name)
            kinds = {G.magic(f) for f in files}
            if not kinds & {b'RGCN', b'BTX0', b'BMD0'}:
                continue
            out = os.path.join('graficos_juego', NARC_INFO.get(name, {}).get('cat', 'otros'),
                               slug(name.rsplit('.', 1)[0].replace('/', '__')))
            # NARCs anidados
            nested = [i for i, f in enumerate(files) if G.magic(f) == b'NARC']
            for i in nested:
                sub = [G.unwrap(x) for x in ndspy.narc.NARC(files[i]).files]
                do_generic(name + '#%d' % i, os.path.join(out, 'sub_%02d' % i), sub)
            do_generic(name, out, files)
    # ficheros sueltos en data/
    loose = {}
    for fid, name in iter_root_files():
        d = G.unwrap(ROM.files[fid])
        if G.magic(d) in (b'RGCN', b'RLCN', b'RECN', b'RNAN', b'RCSN') and '/' in name:
            loose.setdefault(name.rsplit('.', 1)[0], {})[G.magic(d)] = d
    for base, parts in loose.items():
        if b'RGCN' not in parts:
            continue
        files = list(parts.values())
        if b'RLCN' not in parts:  # buscar paleta con nombre parecido
            for k, v in loose.items():
                if b'RLCN' in v and (k.split('/')[-1][:4] == base.split('/')[-1][:4]):
                    files.append(v[b'RLCN']); break
        do_generic(base, os.path.join('graficos_juego', 'sueltos', slug(base.replace('/', '__'))), files)
    print('generic ok')


# ------------------------------------------------------------------ objetos y ataques

def do_items():
    files = narc('itemtool/itemdata/item_icon.narc')
    names = messages(392)
    # tabla objeto -> (gfx, pal) en arm9: se busca por patrón conocido
    arm9 = ndspy.codeCompression.decompress(ROM.arm9)
    table = find_item_table(arm9, len(names))
    done = set()
    if table:
        for item, (gi, pi, *_ ) in enumerate(table):
            if gi >= len(files) or pi >= len(files) or G.magic(files[gi]) != b'RGCN':
                continue
            g = G.Graphic(files[gi]); p = G.Palette(files[pi])
            idx = g.image_indices(width_tiles=4)
            nm = '%03d_%s' % (item, slug(names[item]) if item < len(names) else 'objeto')
            save(G.render(idx, p.table()), 'objetos', 'iconos', nm + '.png')
            done.add(gi)
    for i, f in enumerate(files):  # el resto, emparejado con la paleta siguiente
        if G.magic(f) == b'RGCN' and i not in done:
            pi = i + 1 if i + 1 < len(files) and G.magic(files[i + 1]) == b'RLCN' else None
            g = G.Graphic(f)
            t = G.Palette(files[pi]).table() if pi else G.grayscale_palette(g.depth)
            save(G.render(g.image_indices(width_tiles=4 if g.ntiles == 16 else None), t), 'objetos', 'iconos_sin_nombre', '%03d.png' % i)
    print('items ok', 'tabla' if table else 'sin tabla')


def find_item_table(arm9, nitems):
    # entradas de 8 bytes: u16 datos, u16 icono, u16 paleta, u16 gen. Objeto 1 (Master Ball): icono 2, paleta 3
    pat = struct.pack('<HH', 2, 3)
    pos = arm9.find(pat)
    while pos >= 0:
        start = pos - 2 - 8  # entrada 0 + campo datos de la 1
        if start >= 0:
            ok = True
            ent = []
            for k in range(nitems):
                d, gi, pi, gen = struct.unpack_from('<HHHH', arm9, start + k * 8)
                if gi > 800 or pi > 800:
                    ok = False; break
                ent.append((gi, pi))
            if ok and ent[2] == (4, 5) if len(ent) > 2 else False:
                return ent
        pos = arm9.find(pat, pos + 1)
    return None


def do_moves():
    chars = narc('wazaeffect/effectclact/wechar.narc')
    cells = narc('wazaeffect/effectclact/wecell.narc')
    anms = narc('wazaeffect/effectclact/wecellanm.narc')
    pals = narc('wazaeffect/effectclact/wepltt.narc')
    for i in range(len(chars)):
        try:
            g = G.Graphic(chars[i])
            p = G.Palette(pals[i]) if i < len(pals) else None
            if p is None:
                continue
            save(G.render(g.image_indices(width_tiles=16 if g.ntiles >= 16 else max(1, g.ntiles)), p.table(0, g.depth)),
                 'efectos_ataques', '%02d' % i, '_tiles.png')
            if i < len(cells) and G.magic(cells[i]) == b'RECN':
                an = G.parse_nanr(anms[i]) if i < len(anms) and G.magic(anms[i]) == b'RNAN' else []
                export_cells(g, p, G.Cells(cells[i]), an, ('efectos_ataques', '%02d' % i))
        except Exception as e:
            log('moves', i, e)
    print('moves ok')


def do_battle_bg():
    files = narc('battle/graphic/pl_batt_bg.narc')
    scr = G.Screen(files[2])
    momentos = ('dia', 'tarde', 'noche')
    for k, gi in enumerate(range(3, 26)):
        g = G.Graphic(files[gi])
        for t, m in enumerate(momentos):
            pi = 172 + k * 3 + t
            if pi < len(files) and G.magic(files[pi]) == b'RLCN':
                save(scr.render(g, G.Palette(files[pi])), 'combate', 'fondos', 'fondo_%02d_%s.png' % (k, m))
    print('battle bg ok')


def do_interface():
    """Fuente del juego (atlas + anchos) y marcos de mensaje, listos para el motor de cinemáticas."""
    d = narc('graphic/pl_font.narc')[0]
    wo, n = struct.unpack_from('<II', d, 4)
    rev = {v: k for k, v in CH.items() if len(v) == 1}
    rev.update({'¡': 0x1A9, '¿': 0x1AA, "'": 0x1B3, ':': 0x1C4, '♂': 0x1BB, '♀': 0x1BC, '…': 0x1AF})
    cols = 32
    atlas = np.zeros(((n + cols - 1) // cols * 16, cols * 16, 4), np.uint8)
    pal = np.array([[0, 0, 0, 0], [80, 80, 88, 255], [168, 168, 176, 255], [0, 0, 0, 0]], np.uint8)
    for i in range(n):
        w16 = np.frombuffer(d[0x10 + i * 64: 0x10 + i * 64 + 64], '<u2')
        px = np.zeros(256, np.uint8)
        for k in range(8):
            px[k::8] = (w16 >> (14 - 2 * k)) & 3
        t = px.reshape(4, 8, 8)
        g = np.vstack([np.hstack([t[0], t[1]]), np.hstack([t[2], t[3]])])
        y, x = (i // cols) * 16, (i % cols) * 16
        atlas[y:y + 16, x:x + 16] = pal[g]
    save(Image.fromarray(atlas, 'RGBA'), 'interfaz', 'fuente', 'fuente_juego.png')
    chars = {}
    for ch, code in rev.items():
        i = code - 1
        if 0 <= i < n and ch != '\n':
            chars[ch] = {'glifo': i, 'ancho': d[wo + i]}
    save_json({'columnas_atlas': cols, 'tam_glifo': 16, 'alto_linea': 16,
               'colores': {'texto': [80, 80, 88], 'sombra': [168, 168, 176]},
               'nota': 'En el atlas el texto es (80,80,88) y la sombra (168,168,176); se pueden recolorear.',
               'caracteres': chars}, 'interfaz', 'fuente', 'fuente_juego.json')
    files = narc('graphic/pl_winframe.narc')
    for k, gi in enumerate(range(2, 24)):
        g = G.Graphic(files[gi]); p = G.Palette(files[gi + 22])
        im = G.render(g.image_indices(), p.table(0, g.depth))
        name = 'tipo_%02d.png' % k if k < 20 else ('flechas.png' if k == 20 else 'flechas2.png')
        save(im, 'interfaz', 'marcos_mensaje', name)
    for gi, pi in ((0, 24), (1, 25)):
        g = G.Graphic(files[gi])
        save(G.render(g.image_indices(), G.Palette(files[pi]).table()), 'interfaz', 'marcos_sistema', 'sistema_%d.png' % gi)
    print('interface ok')


def main():
    global ROM, OUT
    ROM = ndspy.rom.NintendoDSRom.fromFile(sys.argv[1])
    OUT = sys.argv[2]
    steps = sys.argv[3:] or ['pokemon', 'otherpoke', 'icons', 'footprints', 'trainers', 'mmodel',
                             'map_textures', 'items', 'moves', 'battle_bg', 'interface', 'all_generic']
    for s in steps:
        try:
            globals()['do_' + s]()
        except Exception:
            traceback.print_exc()
    print('PNG escritos:', STATS['png'], 'errores:', len(ERRORS))
    with open(os.path.join(OUT, '_errores_extraccion.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(ERRORS))


if __name__ == '__main__':
    main()
