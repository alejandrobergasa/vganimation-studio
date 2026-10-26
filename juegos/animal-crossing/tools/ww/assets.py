"""Carga de modelos y texturas del juego desde la ROM (NARC con bmd0 + nsbtx externos)."""
import ndspy.narc
import numpy as np

from .nitro3d import Model, TexBank, sections


def narc_files(rom, path):
    n = ndspy.narc.NARC(rom.get(path))
    out = {}

    def walk(f, pre=''):
        for nm, sub in f.folders:
            walk(sub, pre + nm + '/')
        for i, nm in enumerate(f.files):
            out[pre + nm] = bytes(n.files[f.firstID + i])
    walk(n.filenames)
    if not out:
        out = {'#%d' % i: bytes(f) for i, f in enumerate(n.files)}
    return out


def load_model(rom, model_path, tex_paths=(), name=None):
    """model_path: .nsbmd o .arc (se toma a/bmd/bmd0). Devuelve (Model, [TexBank]) con las texturas internas
    y las de tex_paths (nsbtx) en ese orden de búsqueda."""
    if model_path.endswith('.arc'):
        d = narc_files(rom, model_path)['a/bmd/bmd0']
    else:
        d = rom.get(model_path)
    m = Model(d, name)
    banks = []
    for t in tex_paths:             # los bancos externos tienen prioridad (p. ej. ojos e.0-e.7)
        banks.append(TexBank(rom.get(t)))
    if 'TEX0' in sections(d):
        banks.append(TexBank(d))
    if any(x.pal == 'house_pl' for x in m.materials):
        banks.append(TexBank(rom.get('str/house_pl/house_pl_%s.nsbtx' % ('w' if model_path.rsplit('.', 1)[0].endswith('w') else 's'))))
    return m, banks


def fit_camera(model, override=None, margin=2.4, tilt=0.15, yaw=0.0):
    """Posición de cámara que encuadra el modelo (mira a +Z del modelo cuando yaw=0, hacia -Z el frente)."""
    from .render3d import build_mesh
    from .raster import look_at
    mesh = build_mesh(model, override)
    P = np.concatenate([g[1].reshape(-1, 3) for g in mesh])
    lo, hi = P.min(0), P.max(0)
    ctr = (lo + hi) / 2
    ext = float(max(hi - lo))
    eye = ctr + np.array([np.sin(yaw), tilt, -np.cos(yaw)]) * ext * margin
    return look_at(eye, ctr), mesh
