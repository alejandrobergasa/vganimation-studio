"""Extractor de assets de Animal Crossing: Wild World (ROM europea, ADMP) -> biblioteca/animal-crossing/extraidos/.

Un solo comando regenera todo:

    python -I tools/extraer.py                  # todo
    python -I tools/extraer.py --rapido         # unas pocas muestras por categoría
    python -I tools/extraer.py --fase texturas modelos   # solo algunas fases
    python -I tools/extraer.py --rom otra.nds --salida otra_carpeta

Fases: 2d, texturas, modelos, audio. Cada elemento que falla se anota en assets_extraidos/errores.log
(no detiene el proceso). Al final se generan hojas de contactos en assets_extraidos/_hojas/ y el README.
"""
import argparse
import multiprocessing as mp
import os
import re
import subprocess
import sys
import time

import numpy as np
from PIL import Image

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
from ww.rom import Rom, JUEGO, rutas as RUTAS                     # noqa: E402
from ww.assets import load_model                       # noqa: E402
from ww.nitro3d import TexBank                         # noqa: E402
from ww.raster import Canvas, perspective, look_at     # noqa: E402
from ww.render3d import build_mesh, draw_model, material_texture  # noqa: E402
from ww import gfx2d                                   # noqa: E402

RAIZ = os.path.abspath(os.path.join(AQUI, '..'))
SALIDA = RUTAS.extraidos(JUEGO)

# (prefijo en la ROM, carpeta de salida legible). El primero que coincide gana.
CATEGORIAS_3D = [
    ('npc/model/', 'modelos/vecinos'),
    ('npc_sp/model/', 'modelos/npcs_especiales'),
    ('PBody/', 'modelos/jugador'), ('PHead/', 'modelos/jugador'), ('PGls/', 'modelos/jugador'),
    ('PItm/', 'modelos/jugador_objetos'),
    ('str/shop/', 'modelos/edificios_tiendas'), ('str/npcHs/', 'modelos/edificios_casas_vecinos'),
    ('str/arc/', 'modelos/edificios_estructuras'), ('str/chkp/', 'modelos/edificios_estructuras'),
    ('str/count/', 'modelos/edificios_estructuras'),
    ('fg/tree/', 'modelos/flora_arboles'), ('fg/flower/', 'modelos/flora_flores'), ('fg/grass/', 'modelos/flora_hierba'),
    ('fg/stone/', 'modelos/flora_piedras'), ('fg/hole/', 'modelos/flora_hoyos'), ('fg/eff_tree/', 'modelos/flora_efectos'),
    ('fg/icon/', 'modelos/flora_iconos'),
    ('ftr/', 'modelos/muebles'), ('roomObj/', 'modelos/objetos_habitacion'),
    ('fish/', 'modelos/peces'), ('insect/', 'modelos/bichos'),
    ('snowman/', 'modelos/varios'), ('shadow/', 'modelos/varios'), ('caution/', 'modelos/varios'),
]
CATEGORIAS_TEX = [
    ('bg/', 'texturas/terreno'), ('wall/', 'texturas/paredes'), ('carpet/', 'texturas/suelos'),
    ('cloth/', 'texturas/ropa'), ('PFcTx/', 'texturas/caras_jugador'), ('PPal/', 'texturas/jugador'),
    ('str/plHsTex/', 'texturas/casas_jugador'), ('str/npcHsTex/', 'texturas/casas_vecinos'),
    ('str/house_pl/', 'texturas/casas_jugador'),
]

LOG = []


def anota(msg):
    LOG.append(msg)


def categoria(ruta, tabla, defecto):
    for pre, cat in tabla:
        if ruta.startswith(pre):
            return cat
    return defecto


def slug(ruta):
    r = ruta.rsplit('.', 1)[0]
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', r.replace('/', '__'))


def limpio(s):
    return re.sub(r'\W+', '_', s)


def guardar_png(arr, ruta):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    Image.fromarray(np.asarray(arr, np.uint8)).save(ruta)


_ROM = None


def _rom(path=None):
    global _ROM
    if _ROM is None:
        _ROM = Rom(path) if path else Rom()
    return _ROM


def _init(path):
    _rom(path)


# ---------------------------------------------------------------- texturas
def tex_a_png(rom, ruta, destino):
    """Todas las texturas de un banco NSBTX como PNG RGBA (el índice 0 de las paletas de 4/16/256 colores
    es transparente, como en la DS). Devuelve cuántos PNG se escribieron."""
    bank = TexBank(rom.get(ruta))
    tex, pals = bank.names()
    n = 0
    for t in tex:
        p = t + '_pl' if t + '_pl' in pals else (t if t in pals else (pals[0] if pals else None))
        try:
            img = bank.decode(t, p)
        except Exception:
            continue
        guardar_png(img, os.path.join(destino, categoria(ruta, CATEGORIAS_TEX, 'texturas/varios'),
                                      '%s__%s.png' % (slug(ruta), limpio(t))))
        n += 1
    return n


def fase_texturas(rom, salida, rapido):
    rutas = [p for p in rom.list() if p.endswith('.nsbtx')]
    if rapido:
        cuenta, sel = {}, []
        for p in rutas:
            c = categoria(p, CATEGORIAS_TEX, 'varios') + p.split('/')[0]
            if cuenta.get(c, 0) < 3:
                cuenta[c] = cuenta.get(c, 0) + 1
                sel.append(p)
        rutas = sel
    total = 0
    for p in rutas:
        try:
            total += tex_a_png(rom, p, salida)
        except Exception as e:
            anota('textura %s: %s' % (p, e))
    print('  texturas: %d PNG desde %d bancos' % (total, len(rutas)))


# ---------------------------------------------------------------- modelos
def hermanas_tex(rom, ruta):
    """Bancos de textura externos probables: mismo nombre, <nombre>_tex, carpeta _tex paralela."""
    d, f = ruta.rsplit('/', 1)
    stem = f.rsplit('.', 1)[0]
    cand = ['%s/%s.nsbtx' % (d, stem), '%s/%s_tex.nsbtx' % (d, stem)]
    if '_mdl' in d:
        cand.append(d.replace('_mdl', '_tex') + '/%s.nsbtx' % stem)
    if ruta.startswith('str/shop/a/'):                  # los rótulos/fachadas viven en str/shop/n/ con el mismo nombre
        cand.append(ruta.replace('/shop/a/', '/shop/n/').rsplit('.', 1)[0] + '.nsbtx')
    m = re.match(r'str/npcHs/(\d+)/obj_house\d+_(\d+)([sw])', ruta)
    if m:                                               # casas de vecinos: str/npcHsTex/<letra>/house_<letra><n><estación>
        L = chr(65 + int(m.group(1)))
        cand.append('str/npcHsTex/%s/house_%s%s%s.nsbtx' % (L, L, m.group(2), m.group(3)))
    return [c for c in cand if c in rom.index]


def lista_modelos(rom):
    pref = tuple(p for p, _ in CATEGORIAS_3D)
    return [p for p in rom.list() if p.endswith('.nsbmd') or (p.endswith('.arc') and p.startswith(pref))]


def obj_texto(model, mesh, nombre):
    """OBJ + MTL con los triángulos en pose por defecto."""
    lineas, caras = [], []
    k = 1
    for mat, P, UV, N in mesh:
        m = model.materials[mat]
        caras.append('usemtl %s' % limpio(m.name))
        for t in range(P.shape[0]):
            idx = []
            for j in range(3):
                lineas.append('v %.5f %.5f %.5f' % tuple(P[t, j]))
                idx.append(k)
                k += 1
            caras.append('f ' + ' '.join('%d/%d/%d' % (i, i, i) for i in idx))
    vt, vn = [], []
    for mat, P, UV, N in mesh:
        m = model.materials[mat]
        for t in range(P.shape[0]):
            for j in range(3):
                vt.append('vt %.5f %.5f' % (UV[t, j, 0] * m.sx + m.tx, 1.0 - (UV[t, j, 1] * m.sy + m.ty)))
                vn.append('vn %.4f %.4f %.4f' % tuple(N[t, j]))
    mtl = ['newmtl %s\nKd 1 1 1\nmap_Kd %s__%s.png\n' % (limpio(m.name), nombre, limpio(m.tex or 'none'))
           for m in model.materials]
    return 'mtllib %s.mtl\n' % nombre + '\n'.join(lineas + vt + vn + caras) + '\n', '\n'.join(mtl)


def procesar_modelo(args):
    ruta, salida = args
    try:
        rom = _rom()
        model, banks = load_model(rom, ruta, hermanas_tex(rom, ruta))
        mesh = build_mesh(model)
        if not mesh:
            return ruta, 'sin geometría'
        nombre = slug(ruta)
        d = os.path.join(salida, categoria(ruta, CATEGORIAS_3D, 'modelos/varios'), nombre)
        os.makedirs(d, exist_ok=True)
        for m in model.materials:
            img = material_texture(model, banks, m)
            if img is not None:
                guardar_png(img, os.path.join(d, '%s__%s.png' % (nombre, limpio(m.tex))))
        o, mt = obj_texto(model, mesh, nombre)
        open(os.path.join(d, nombre + '.obj'), 'w').write(o)
        open(os.path.join(d, nombre + '.mtl'), 'w').write(mt)
        P = np.concatenate([g[1].reshape(-1, 3) for g in mesh])
        lo, hi = P.min(0), P.max(0)
        ctr = (lo + hi) / 2
        ext = float(max(np.linalg.norm(hi - lo), 1e-3))
        proj = perspective(30.0, 1.0, 0.1, 1000)
        for nm, yaw in (('frente', 0.0), ('tres_cuartos', 0.6)):
            eye = ctr + np.array([np.sin(yaw), 0.25, np.cos(yaw)]) * ext * 1.55
            cv = Canvas(256, 256)
            draw_model(cv, model, banks, np.eye(4), look_at(eye, ctr), proj, mesh=mesh, ambient=0.8)
            guardar_png((np.clip(cv.color, 0, 1) * 255 + 0.5).astype(np.uint8), os.path.join(d, 'vista_%s.png' % nm))
        return ruta, None
    except Exception as e:
        return ruta, '%s: %s' % (type(e).__name__, e)


def fase_modelos(rom, salida, rapido, rom_path):
    mods = lista_modelos(rom)
    if rapido:
        cuenta, sel = {}, []
        for p in mods:
            c = categoria(p, CATEGORIAS_3D, 'varios')
            if cuenta.get(c, 0) < 3:
                cuenta[c] = cuenta.get(c, 0) + 1
                sel.append(p)
        mods = sel
    t0 = time.time()
    ok = 0
    with mp.Pool(max(os.cpu_count() - 1, 1), initializer=_init, initargs=(rom_path,)) as pool:
        for ruta, err in pool.imap_unordered(procesar_modelo, [(p, salida) for p in mods], chunksize=4):
            if err:
                anota('modelo %s: %s' % (ruta, err))
            else:
                ok += 1
    print('  modelos: %d/%d correctos (%.0f s)' % (ok, len(mods), time.time() - t0))


# ---------------------------------------------------------------- audio
BGM_HORAS = list(range(22, 46))        # supuesto: 24 temas, uno por hora (el SDAT no tiene nombres)
KK = list(range(176, 247))
SFX = list(range(99, 172))
VOCES = list(range(10, 20))
_SON = None


def _son():
    global _SON
    if _SON is None:
        from ww.synth import Sonido
        _SON = Sonido(_rom().raw('sound_dataEUR.sdat'))
    return _SON


def _render_seq(args):
    idx, seg, ruta = args
    try:
        from ww.synth import guardar_wav
        a = np.asarray(_son().renderizar(idx, segundos=seg), np.float32)
        m = np.abs(a).max()
        if m > 0:
            a = a * (0.89 / m)
        guardar_wav(ruta, a)
        return idx, None
    except Exception as e:
        return idx, '%s: %s' % (type(e).__name__, e)


def wav_a_ogg(ruta):
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', ruta, '-c:a', 'libvorbis', '-q:a', '5', ruta[:-4] + '.ogg'])
    return r.returncode == 0


def fase_audio(rom, salida, rapido, rom_path):
    d = os.path.join(salida, 'audio')
    lim = 2 if rapido else None
    trabajos = []
    for h, i in enumerate(BGM_HORAS[:lim]):
        trabajos.append((i, 60, os.path.join(d, 'bgm_por_hora', 'bgm_%02dh_seq%03d.wav' % (h, i))))
    for n, i in enumerate(KK[:lim]):
        trabajos.append((i, 90, os.path.join(d, 'kk_slider', 'kk_%02d_seq%03d.wav' % (n + 1, i))))
    for i in SFX[:lim]:
        trabajos.append((i, 4, os.path.join(d, 'sfx', 'sfx_seq%03d.wav' % i)))
    for _, _, p in trabajos:
        os.makedirs(os.path.dirname(p), exist_ok=True)
    t0 = time.time()
    ok = 0
    with mp.Pool(max(os.cpu_count() - 1, 1), initializer=_init, initargs=(rom_path,)) as pool:
        for idx, err in pool.imap_unordered(_render_seq, trabajos):
            if err:
                anota('audio seq %d: %s' % (idx, err))
            else:
                ok += 1
    from ww.synth import guardar_wav
    son = _son()
    nv = 0
    for s in VOCES[:lim]:
        try:
            for w in range(len(son.sdat.waveArchives[s][1].waves)):
                x, rate, _ = son.banco.muestra(s, w)
                x = np.asarray(x, np.float32)
                p = os.path.join(d, 'voces', 'voz%02d' % s, 'silaba_%03d.wav' % w)
                os.makedirs(os.path.dirname(p), exist_ok=True)
                guardar_wav(p, np.stack([x, x], 1), rate)
                nv += 1
        except Exception as e:
            anota('voces %d: %s' % (s, e))
    n_ogg = 0
    for raiz, _, fs in os.walk(d):
        if os.sep + 'voces' in raiz:
            continue
        for f in fs:
            if f.endswith('.wav') and wav_a_ogg(os.path.join(raiz, f)):
                n_ogg += 1
    print('  audio: %d secuencias, %d sílabas de voz, %d OGG (%.0f s)' % (ok, nv, n_ogg, time.time() - t0))


# ---------------------------------------------------------------- 2D
def fase_2d(rom, salida, rapido):
    sys.path.insert(0, os.path.join(RAIZ, 'video'))
    from motor import make_bubble
    for nombre in ('fontA', 'fontB', 'fontASub'):
        try:
            attr, img = rom.get('font/%s_attr.bin' % nombre), rom.get('font/%s_img.bin' % nombre)
            n = len(attr) // 4
            cols = 32
            hoja_ = np.zeros(((n + cols - 1) // cols * 16, cols * 16, 4), np.uint8)
            for i in range(n):
                for y in range(16):
                    row = int.from_bytes(img[i * 32 + y * 2:i * 32 + y * 2 + 2], 'big')
                    for x in range(16):
                        if (row >> (15 - x)) & 1:
                            hoja_[(i // cols) * 16 + y, (i % cols) * 16 + x] = (40, 20, 10, 255)
            guardar_png(hoja_, os.path.join(salida, 'fuentes', '%s_glifos.png' % nombre))
        except Exception as e:
            anota('fuente %s: %s' % (nombre, e))
    for v in ('a_mes0a_bg_nsc', 'a_mes0b_bg_nsc', 'a_mes1a_bg_nsc'):
        try:
            guardar_png(make_bubble(rom, 8, v)[0], os.path.join(salida, 'interfaz', 'dialogo_%s.png' % v))
        except Exception as e:
            anota('burbuja %s: %s' % (v, e))
    for p in rom.list():
        if p.endswith('_ncg.bin') and p[:-8] + '_ncl.bin' in rom.index:
            base = p[:-8]
            try:
                pal = gfx2d.palette(rom.get(base + '_ncl.bin'))
                bpp = 4 if len(pal) <= 16 or rom.get(p).__len__() < 0x4000 else 8
                sheet = gfx2d.tile_sheet(gfx2d.tiles(rom.get(p), bpp), pal, 32, 0, bpp)
                carpeta = 'fondos' if p.startswith('sky/') else 'interfaz'
                guardar_png(sheet, os.path.join(salida, carpeta, slug(base) + '_tiles.png'))
            except Exception as e:
                anota('tiles %s: %s' % (p, e))
    print('  2D: fuentes, nubes de diálogo y láminas de tiles')


# ---------------------------------------------------------------- hojas de contactos y README
def hoja(imgs, destino, cols, celda):
    if not imgs:
        return
    filas = (len(imgs) + cols - 1) // cols
    lienzo = Image.new('RGB', (cols * celda, filas * celda), (120, 160, 200))
    for i, p in enumerate(imgs):
        try:
            im = Image.open(p).convert('RGBA')
            im.thumbnail((celda - 4, celda - 4), Image.NEAREST)
            lienzo.paste(im, ((i % cols) * celda + (celda - im.width) // 2, (i // cols) * celda + (celda - im.height) // 2), im)
        except Exception:
            pass
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    lienzo.save(destino)


def fase_hojas(salida):
    h = os.path.join(salida, '_hojas')
    mod_root = os.path.join(salida, 'modelos')
    if os.path.isdir(mod_root):
        for cat in sorted(os.listdir(mod_root)):
            v = sorted(os.path.join(mod_root, cat, m, 'vista_tres_cuartos.png') for m in os.listdir(os.path.join(mod_root, cat))
                       if os.path.exists(os.path.join(mod_root, cat, m, 'vista_tres_cuartos.png')))
            for part in range(0, len(v), 48):
                hoja(v[part:part + 48], os.path.join(h, 'modelos_%s_%d.png' % (cat, part // 48)), 8, 128)
    tex_root = os.path.join(salida, 'texturas')
    if os.path.isdir(tex_root):
        for cat in sorted(os.listdir(tex_root)):
            v = sorted(os.path.join(tex_root, cat, f) for f in os.listdir(os.path.join(tex_root, cat)) if f.endswith('.png'))
            for part in range(0, len(v), 96):
                hoja(v[part:part + 96], os.path.join(h, 'texturas_%s_%d.png' % (cat, part // 96)), 12, 96)
    print('  hojas de contactos en', h)


def contar(salida):
    out = {}
    for raiz, _, fs in os.walk(salida):
        rel = os.path.relpath(raiz, salida).split(os.sep)
        if rel[0].startswith('_') or rel[0] == '.':
            continue
        k = '/'.join(rel[:2]) if rel[0] in ('modelos', 'texturas', 'audio') and len(rel) > 1 else rel[0]
        for f in fs:
            e = f.rsplit('.', 1)[-1].lower()
            out.setdefault(k, {}).setdefault(e, 0)
            out[k][e] += 1
    return out


def escribe_readme(rom, salida, rapido, seg):
    filas = ['| `%s` | %s |' % (k, ', '.join('%d %s' % (v, e) for e, v in sorted(c.items())))
             for k, c in sorted(contar(salida).items())]
    txt = """# assets_extraidos

Generado por `python -I tools/extraer.py` desde `%s` (código de juego **%s**, región **Europa**; los rótulos de
tienda salen en español). **No edites a mano**: se regenera por completo.
%s
Duración de la última ejecución: %.0f s.

## Contenido

| Carpeta | Ficheros |
|---|---|
%s

## Formatos

- **Texturas** (`texturas/` y las de cada modelo): PNG RGBA. El color de índice 0 de las paletas de 4, 16 y 256 colores
  es transparente (como en la DS); A3I5/A5I3 usan su alfa propio.
- **Modelos** (`modelos/<categoría>/<nombre>/`): `.obj` + `.mtl` en pose por defecto (sin animar), PNG de sus texturas y
  `vista_frente.png` / `vista_tres_cuartos.png` renderizadas con el rasterizador propio (`tools/ww/raster.py`).
  Las animaciones (`.nsbca`) no se exportan a fichero: las usa directamente `video/motor.py`.
- **Audio** (`audio/`): WAV y OGG. `bgm_por_hora/` = secuencias 22-45 del SDAT (*orden horario supuesto*; el SDAT no tiene
  nombres), `kk_slider/` = 176-246, `sfx/` = 99-171, `voces/vozNN/` = sílabas de los archivos de ondas 10-19.
  Se sintetizan con `tools/ww/synth.py` (sintetizador SSEQ/SBNK/SWAR propio): suena parecido, no idéntico, al hardware.
- **Interfaz / fuentes / fondos**: glifos de fontA/fontB/fontASub, nubes de diálogo montadas con los tiles reales de `a_mes`
  y láminas de tiles (paleta 0) de los pares NCG/NCL.
- **Hojas de contactos** (`_hojas/`): para validar a ojo cada categoría.

## Limitaciones conocidas

- Las secuencias del SDAT no tienen nombre: BGM / K.K. / SFX se deducen por rangos de índices.
- Los gráficos 2D del menú (`.bch/.bpl/.bsc`) aún no se decodifican.
- Algunos modelos no tienen textura localizable por nombre; ver `errores.log`.
""" % (os.path.basename(RUTAS.rom(JUEGO)), rom.game_code, '\n> Ejecución `--rapido`: solo unas pocas muestras por categoría.\n' if rapido else '', seg, '\n'.join(filas))
    open(os.path.join(salida, 'README.md'), 'w', encoding='utf-8').write(txt)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rom', default=None)
    ap.add_argument('--salida', default=SALIDA)
    ap.add_argument('--rapido', action='store_true')
    ap.add_argument('--fase', nargs='*', default=['2d', 'texturas', 'modelos', 'audio'],
                    choices=['2d', 'texturas', 'modelos', 'audio'])
    a = ap.parse_args()
    t0 = time.time()
    rom = _rom(a.rom)
    print('ROM: %s  código %s' % (rom.title, rom.game_code))
    os.makedirs(a.salida, exist_ok=True)
    if '2d' in a.fase:
        fase_2d(rom, a.salida, a.rapido)
    if 'texturas' in a.fase:
        fase_texturas(rom, a.salida, a.rapido)
    if 'modelos' in a.fase:
        fase_modelos(rom, a.salida, a.rapido, a.rom)
    if 'audio' in a.fase:
        fase_audio(rom, a.salida, a.rapido, a.rom)
    fase_hojas(a.salida)
    open(os.path.join(a.salida, 'errores.log'), 'w', encoding='utf-8').write('\n'.join(LOG) + '\n')
    escribe_readme(rom, a.salida, a.rapido, time.time() - t0)
    print('hecho en %.0f s; %d avisos en errores.log' % (time.time() - t0, len(LOG)))


if __name__ == '__main__':
    mp.freeze_support()
    main()
