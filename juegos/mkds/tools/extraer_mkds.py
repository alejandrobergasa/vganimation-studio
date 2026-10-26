"""Extractor de assets de Mario Kart DS (Europa): ROM -> biblioteca/mkds/extraidos/ (hojas de contactos + catálogos).

Uso (desde la raíz):   python -I tools/extraer_mkds.py [--solo pilotos,karts,circuitos,objetos,audio,fuentes]
La ROM ("Mario Kart DS*.nds" de la raíz) sólo se lee. Los modelos NO se copian: se leen de la ROM bajo demanda
(tools/mkds/modelos.py); aquí se generan las hojas de contactos y los catálogos para elegir recursos y revisarlos."""
import sys, os, argparse, time, csv, json, traceback
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, os.path.join(ROOT, 'video'))
import numpy as np
from PIL import Image, ImageDraw
import mk                                    # añade tools/mkds, tools/nsmb y video al path
from mk import escena as E
import modelos as M, mkrom, nftr

OUT = mk.rutas.extraidos('mkds')


def out(*p):
    d = os.path.join(OUT, *p[:-1]); os.makedirs(d, exist_ok=True)
    return os.path.join(d, p[-1])


def hoja(imgs, etiquetas, ruta, cols=6):
    w, h = imgs[0].size
    filas = (len(imgs) + cols - 1) // cols
    S = Image.new('RGB', (cols * w, filas * (h + 14)), (40, 44, 60)); d = ImageDraw.Draw(S)
    for i, (im, et) in enumerate(zip(imgs, etiquetas)):
        x, y = (i % cols) * w, (i // cols) * (h + 14)
        S.paste(im, (x, y + 14)); d.text((x + 3, y + 1), et, fill=(255, 255, 0))
    S.save(ruta)


def a_img(f):
    return Image.fromarray((np.clip(f, 0, 1) * 255).astype(np.uint8))


def pilotos():
    from mk import kart as K
    m = E.Motor(200, 260, ss=1); env = E.Entorno(niebla_fuerza=0, cielo=(.55, .7, .95))
    ims, et = [], []
    for nom in M.PILOTOS:
        try:
            k = K.Kart(m, nom, 'b')
        except Exception as e:
            print('  piloto', nom, 'falla', repr(e)); continue
        for yaw in (-35, 145):
            ins = k.instancias((0, 0, 0), yaw=yaw)
            ims.append(a_img(m.render(ins, E.Camara((0, 10, -26), (0, 3.5, 0), fov=40), env))); et.append('%s yaw%d' % (nom, yaw))
    hoja(ims, et, out('pilotos', 'hoja_pilotos.png'), 6)


def karts():
    from mk import kart as K
    m = E.Motor(200, 150, ss=1); env = E.Entorno(niebla_fuerza=0)
    ims, et = [], []
    for nom in M.PILOTOS:
        for t in 'abc':
            try:
                k = K.Kart(m, nom, t)
                if k.tipo != t: continue
                ims.append(a_img(m.render(k.instancias((0, 0, 0), yaw=65), E.Camara((0, 8, -20), (0, 3.2, 0), fov=35), env)))
                et.append('%s %s' % (nom, t))
            except Exception as e:
                print('  kart', nom, t, 'falla', repr(e))
    hoja(ims, et, out('karts', 'hoja_karts.png'), 6)


def circuitos():
    from mk import circuito as C
    m = E.Motor(240, 320, ss=1)
    ims, et, cat = [], [], []
    for nom in M.circuitos():
        try:
            m2 = E.Motor(240, 320, ss=1)
            w = C.Mundo(m2, nom)
            if w.pista is not None:
                a = w.pista.muestra(0); b = w.pista.muestra(40)
                yaw = np.radians(a['yaw']); f = np.array([np.sin(yaw), 0, np.cos(yaw)])
                cam = E.Camara(a['pos'] - f * 18 + [0, 9, 0], b['pos'] + [0, 2, 0], fov=60)
            else:
                p = w.malla.xyz.reshape(-1, 3); c = (p.min(0) + p.max(0)) / 2; r = float(np.ptp(p, 0).max())
                cam = E.Camara(c + [r * .5, r * .6, r * .7], c, fov=50)
            ims.append(a_img(m2.render(w.instancias(), cam, w.entorno))); et.append(nom)
            cat.append({'circuito': nom, 'triangulos': len(w.malla), 'largo_linea': round(float(w.pista.largo), 1) if w.pista else None,
                        'objetos': sorted(w.c.objetos), 'cielo': w.cielo is not None})
        except Exception as e:
            print('  circuito', nom, 'falla', repr(e)); ims.append(Image.new('RGB', (240, 320))); et.append(nom + ' FALLO')
    hoja(ims, et, out('circuitos', 'hoja_circuitos.png'), 8)
    json.dump(cat, open(out('circuitos', 'catalogo.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)


def objetos():
    m = E.Motor(160, 160, ss=1); env = E.Entorno(niebla_fuerza=0)
    ims, et = [], []
    arc = 'data/MainRace.carc'
    for ruta in sorted(mkrom.narc(arc)):
        if not ruta.endswith('.nsbmd'): continue
        try:
            cj = M.objeto(ruta, arc)
            if not cj.texlook.banks:
                tx = ruta[:-6] + '.nsbtx'
                if tx in mkrom.narc(arc): cj = M.objeto(ruta, arc, tx)
            mal = m.malla(cj)
            if not len(mal): continue
            p = mal.xyz.reshape(-1, 3); c = (p.min(0) + p.max(0)) / 2; r = float(np.ptp(p, 0).max()) * 1.6 + 1e-3
            ims.append(a_img(m.render([E.Instancia(mal, yaw=30)], E.Camara(c + [r * .6, r * .5, r], c, fov=35), env))); et.append(os.path.basename(ruta)[:-6])
        except Exception as e:
            print('  objeto', ruta, 'falla', repr(e))
    hoja(ims, et, out('objetos', 'hoja_objetos.png'), 7)


def fuentes():
    a = mkrom.narc('data/Main2D.carc')
    ims, et = [], []
    for n in ('LC_Font_m.NFTR', 'LC_Font_s.NFTR', 'marioFont.NFTR'):
        f = nftr.Font(a[n]); s = 'MARIO KART DS ¡Ñandú! 0123456789'
        W = sum((f.widths[f.char_index(c)] or (0, f.tw, f.tw))[2] for c in s) + 8
        img = np.zeros((f.th + 4, W, 3), np.uint8); x = 2
        for c in s:
            g = f.char_index(c); l, w, ad = f.widths[g] or (0, f.tw, f.tw)
            bm = f.glyph(g); v = (bm * (255 // max(1, bm.max()))).astype(np.uint8)
            xs = x + l
            if xs >= 0 and xs + f.tw <= W: img[2:2 + f.th, xs:xs + f.tw] = np.maximum(img[2:2 + f.th, xs:xs + f.tw], v[:, :, None])
            x += ad
        ims.append(Image.fromarray(img).resize((W * 4, (f.th + 4) * 4), Image.NEAREST)); et.append(n)
    w = max(i.width for i in ims)
    S = Image.new('RGB', (w, sum(i.height + 14 for i in ims)), (30, 30, 40)); d = ImageDraw.Draw(S); y = 0
    for i, e in zip(ims, et): d.text((2, y), e, fill=(255, 255, 0)); S.paste(i, (0, y + 14)); y += i.height + 14
    S.save(out('fuentes', 'fuentes.png'))


def audio():
    """Cataloga la música (76 secuencias) y los efectos (SSAR) sin nombres: duración, pico y energía.
    Renderiza WAV de los efectos cortos para poder elegirlos por métricas. Los ficheros van a cache/mkds/audio/."""
    import sonido
    from mk import audio as A
    son = A.son()
    filas = []
    d = os.path.join(mk.CACHE, 'audio'); os.makedirs(d, exist_ok=True)
    for i, (n, q) in enumerate(son.sdat.sequences):
        if q is None: continue
        try:
            a = A.bgm(i, 24)
            env = np.abs(a).max(1); idx = np.nonzero(env > 1e-3)[0]
            dur = (idx[-1] + 1) / sonido.FS if len(idx) else 0
            filas.append(('bgm', i, '', round(dur, 2), round(float(np.abs(a).max()), 3), round(float(np.sqrt((a ** 2).mean())), 4)))
        except Exception as e:
            filas.append(('bgm', i, 'ERROR ' + repr(e)[:40], 0, 0, 0))
    for (si, k, _), met in sorted(A.catalogar_sfx(4).items()):
        filas.append(('sfx', '%d:%d' % (si, k), met[0] if isinstance(met[0], str) else '', met[0] if not isinstance(met[0], str) else 0, met[1], met[2]))
    with open(out('audio', 'catalogo_audio.csv'), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f); w.writerow(['tipo', 'id', 'nota', 'duracion_s', 'pico', 'rms']); w.writerows(filas)
    print('  audio: %d entradas' % len(filas))


PASOS = {'fuentes': fuentes, 'pilotos': pilotos, 'karts': karts, 'objetos': objetos, 'circuitos': circuitos, 'audio': audio}

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--solo', default=','.join(PASOS))
    a = ap.parse_args()
    for nombre in a.solo.split(','):
        t = time.time()
        try:
            PASOS[nombre](); print('  ok  %-10s %.1fs' % (nombre, time.time() - t))
        except Exception:
            print('  FALLO', nombre); traceback.print_exc()
    print('Salida en', OUT)
