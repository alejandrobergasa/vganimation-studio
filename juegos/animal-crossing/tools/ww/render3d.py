"""Utilidades para dibujar modelos Nitro en un Canvas (malla posada vectorizada + iluminación)."""
import numpy as np

from .raster import Canvas, perspective, look_at


def _shape_arrays(model, shp):
    """Geometría local de una forma como arrays (cacheado en el modelo)."""
    cache = model.__dict__.setdefault('_shape_cache', {})
    if shp in cache:
        return cache[shp]
    tris = model.shapes[shp]
    if not tris:
        cache[shp] = None
        return None
    n = len(tris)
    pos = np.empty((n, 3, 3), np.float64)
    uv = np.empty((n, 3, 2), np.float64)
    nrm = np.empty((n, 3, 3), np.float64)
    mi = np.full((n, 3), -1, np.int32)
    for i, tri in enumerate(tris):
        for j, v in enumerate(tri):
            pos[i, j] = v[0:3]
            uv[i, j] = v[3:5]
            nrm[i, j] = v[5]
            if v[7] is not None:
                mi[i, j] = v[7]
    cache[shp] = (pos, uv, nrm, mi)
    return cache[shp]


def _apply(m, p):
    """Aplica una matriz 4x4 a puntos (..,3)."""
    return p @ m[:3, :3].T + m[:3, 3]


def build_mesh(model, override=None):
    """Triángulos posados en espacio del modelo: [(material, pos(T,3,3), uv(T,3,2), nrm(T,3,3))]."""
    groups = {}
    for shp, mat, cur, stack in model.pose(override):
        arr = _shape_arrays(model, shp)
        if arr is None:
            continue
        pos, uv, nrm, mi = arr
        if (mi < 0).all():
            P = _apply(cur, pos)
            N = nrm @ cur[:3, :3].T
        else:
            P = np.empty_like(pos)
            N = np.empty_like(nrm)
            for k in np.unique(mi):
                m = cur if k < 0 else stack.get(int(k), cur)
                sel = mi == k
                P[sel] = _apply(m, pos[sel])
                N[sel] = nrm[sel] @ m[:3, :3].T
        g = groups.setdefault(mat, ([], [], []))
        g[0].append(P)
        g[1].append(uv)
        g[2].append(N)
    return [(mat, np.concatenate(a), np.concatenate(b), np.concatenate(c)) for mat, (a, b, c) in groups.items()]


LIGHT = np.array([-0.35, -0.6, -0.7])
LIGHT /= np.linalg.norm(LIGHT)


def material_texture(model, banks, m, tex_name=None):
    tex_name = tex_name or m.tex
    if not tex_name:
        return None
    for b in banks:
        if tex_name in b.texs:
            # la paleta puede vivir en otro banco (p. ej. house_pl); se prefiere la más grande
            srcs = [x for x in banks if m.pal in x.pals]
            src = (b if m.pal in b.pals else (srcs[0] if srcs else None))
            if src is not None and src.pal_size < 64:        # paleta marcador: buscar la real en otro banco
                big = [x for x in srcs if x.pal_size >= 1024]
                if big:
                    src = max(big, key=lambda x: x.pal_size)
            return b.decode(tex_name, m.pal, src)
    return None


def draw_model(canvas, model, banks, world, view, proj, override=None, ambient=0.72, tint=(1, 1, 1), mesh=None,
               light=None, tex_override=None):
    """world: matriz 4x4 modelo->mundo. light: dirección de luz en mundo (hacia donde apunta)."""
    mesh = mesh if mesh is not None else build_mesh(model, override)
    vp = proj @ view @ world
    nm = world[:3, :3]
    L = LIGHT if light is None else np.asarray(light, np.float64) / np.linalg.norm(light)
    for mat, P, UV, N in sorted(mesh, key=lambda g: model.materials[g[0]].alpha < 1):
        m = model.materials[mat]
        if m.cull == 0:
            continue
        tex = material_texture(model, banks, m, (tex_override or {}).get(m.name))
        T = P.shape[0]
        ph = np.concatenate([P, np.ones((T, 3, 1))], -1)
        clip = ph @ vp.T
        uv = UV.copy()
        uv[..., 0] = uv[..., 0] * m.sx + m.tx
        uv[..., 1] = uv[..., 1] * m.sy + m.ty
        nw = N @ nm.T
        nn = np.linalg.norm(nw, axis=-1, keepdims=True)
        nw = nw / np.maximum(nn, 1e-6)
        ndl = np.clip(-(nw @ L), 0, 1)
        sh = ambient + (1 - ambient) * ndl
        shade = np.repeat(sh[..., None], 3, -1) * np.array(tint)
        if tex is None:
            shade = shade * np.array(m.diffuse)
        # NDS: bits 6-7 de los atributos: 1 = solo trasera, 2 = solo frontal, 3 = ambas (Canvas: 1 descarta área>0 = cara trasera, 2 descarta área<0 = frontal)
        cull = {1: 2, 2: 1, 3: 0}[m.cull]
        canvas.draw(clip, uv, tex, shade, m.alpha, cull, (m.rep_s, m.rep_t, m.flip_s, m.flip_t))
