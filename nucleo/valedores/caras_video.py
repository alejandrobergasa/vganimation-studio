"""Caras de foto proyectadas sobre la malla de la cabeza de un modelo 3D.

La foto no se pega como una capa plana: se proyecta sobre la malla de la cabeza en su atlas UV,
así que gira con el modelo. El atlas se amplía ×4 para que la cara se reconozca; el resto de la
cabeza conserva la textura nativa, teñida al tono de piel de la foto. Sirve para los BMD de
SM64DS y para los HBDF de Mario Party DS: solo necesita materials, texturas y tris.
"""
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates


def color_piel(foto, hitos):
    """Color medio de la mejilla de la foto, en RGB 0..1. `hitos` = (fila ojos, fila barbilla, columna centro)."""
    ojos, barbilla, centro = hitos
    d = float(barbilla - ojos)
    if d <= 0:
        raise ValueError('Los hitos de la cara deben tener la barbilla por debajo de los ojos')
    a = np.asarray(foto.convert('RGB'), np.float32) / 255.0
    x, y = int(centro + 0.30 * d), int(ojos + 0.30 * d)
    r = max(2, int(0.05 * d))
    recorte = a[max(0, y - r):y + r, max(0, x - r):x + r].reshape(-1, 3)
    if not recorte.size:
        raise ValueError('Los hitos de la cara dejan la mejilla fuera de la foto')
    return recorte.mean(0)


def atlas_cara(modelo, material, foto, hitos, pelo=None, escala=4,
               mx=1.70, my0=1.12, my1=3.90, zmin=0.55, tener_pelo=True, nuca_min_y=2.55,
               brillo=1.0):
    """Devuelve el atlas de la cabeza con la foto proyectada.

    - `modelo`: objeto con `materials`, `texturas` y `tris` (ModeloSM64).
    - `material`: nombre del material de la cabeza (p. ej. `mat_bm_head`).
    - `foto`: ruta o imagen PIL de identidad.
    - `hitos`: (fila de los ojos, fila de la barbilla, columna del centro) en píxeles de la foto.
    - `pelo`: None = calvo (se pinta piel); tupla RGB 0..1 = color de pelo en la nuca y las orejas.
    - `mx`, `my0`, `my1`: rectángulo de la cara en coordenadas del modelo.
    - `zmin`: profundidad mínima para considerar que un téxel está en la cara delantera.
    """
    if not isinstance(escala, int) or not 1 <= escala <= 8:
        raise ValueError('La escala debe ser un entero entre 1 y 8')
    mat = next((m for m in modelo.materials if m.name == material), None)
    if mat is None:
        raise ValueError('El modelo no tiene el material ' + material)
    base = modelo.texturas.get(mat.tex)
    if base is None:
        raise ValueError('El material no tiene textura en el modelo')
    tris = [t for i, t in modelo.tris if modelo.materials[i] is mat]
    if not tris:
        raise ValueError('El material no tiene geometría')
    foto = Image.open(foto).convert('RGB') if not isinstance(foto, Image.Image) else foto.convert('RGB')
    ojos, barbilla, centro = hitos
    d = float(barbilla - ojos)
    if d <= 0:
        raise ValueError('Los hitos de la cara deben tener la barbilla por debajo de los ojos')

    H, W = base.shape[:2]
    Ae, Af = W * escala, H * escala
    at = np.asarray(Image.fromarray(base).resize((Ae, Af), Image.Resampling.NEAREST), np.float32) / 255.0
    pos = np.full((Af, Ae, 3), np.nan, np.float32)
    # Rasteriza la malla de la cabeza en el atlas y guarda la posición 3D de cada téxel.
    for tri in tris:
        uv = np.array([[v[3] * escala, v[4] * escala] for v in tri], np.float32)
        xyz = np.array([v[0:3] for v in tri], np.float32)
        x0, y0 = np.floor(uv.min(0)).astype(int)
        x1, y1 = np.ceil(uv.max(0)).astype(int) + 1
        x0, y0 = max(x0, 0), max(y0, 0)
        x1, y1 = min(x1, Ae), min(y1, Af)
        if x1 <= x0 or y1 <= y0:
            continue
        den = (uv[1, 1] - uv[2, 1]) * (uv[0, 0] - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (uv[0, 1] - uv[2, 1])
        if abs(den) < 1e-9:
            continue
        gy, gx = np.meshgrid(np.arange(y0, y1) + 0.5, np.arange(x0, x1) + 0.5, indexing='ij')
        w0 = ((uv[1, 1] - uv[2, 1]) * (gx - uv[2, 0]) + (uv[2, 0] - uv[1, 0]) * (gy - uv[2, 1])) / den
        w1 = ((uv[2, 1] - uv[0, 1]) * (gx - uv[2, 0]) + (uv[0, 0] - uv[2, 0]) * (gy - uv[2, 1])) / den
        w2 = 1 - w0 - w1
        dentro = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
        if not dentro.any():
            continue
        p = w0[..., None] * xyz[0] + w1[..., None] * xyz[1] + w2[..., None] * xyz[2]
        pos[y0:y1, x0:x1][dentro] = p[dentro]

    valido = ~np.isnan(pos[..., 0])
    piel = np.clip(color_piel(foto, hitos) * brillo, 0, 1)
    lum = at[..., :3].mean(-1)
    skin_nativa = (at[..., 0] > 0.55) & (at[..., 1] > 0.35) & (at[..., 2] > 0.22) & (at[..., 0] > at[..., 2] * 1.15)
    media = float(lum[skin_nativa].mean()) if skin_nativa.any() else 0.6
    factor = np.clip(lum / max(0.45, media), 0.55, 1.3)
    tinte = np.asarray(piel, np.float32)[None, None, :] * factor[..., None]
    at[..., :3] = np.where(skin_nativa[..., None], tinte, at[..., :3])
    # Bigote y zonas oscuras de la cara que queden fuera de la foto: se pintan de piel.
    oscuro = valido & (pos[..., 2] > zmin) & (pos[..., 1] > my0) & (pos[..., 1] < my1) & (lum < 0.38)
    at[oscuro, :3] = np.asarray(piel, np.float32)[None, :] * factor[oscuro, None]

    # Tarjeta cuadrada con el recorte de la cara y los lados rellenos de piel: mantiene la proporción.
    T, B = ojos - 0.55 * d, barbilla + 0.32 * d
    L, R = centro - 0.52 * d, centro + 0.52 * d
    ancho_cara, alto_cara = max(1, int(round(R - L))), max(1, int(round(B - T)))
    lado = max(ancho_cara, alto_cara)
    card = np.empty((lado, lado, 3), np.float32)
    card[:] = np.asarray(piel, np.float32)[None, None, :]
    gx, gy = np.meshgrid(np.arange(ancho_cara) + 0.5, np.arange(alto_cara) + 0.5, indexing='xy')
    sx0 = L + gx / ancho_cara * (R - L)
    sy0 = T + gy / alto_cara * (B - T)
    a = np.asarray(foto, np.float32) / 255.0
    recorte = np.stack([map_coordinates(a[..., ch], [sy0, sx0], order=1, mode='nearest') for ch in range(3)], -1)
    ox, oy = (lado - ancho_cara) // 2, (lado - alto_cara) // 2
    card[oy:oy + alto_cara, ox:ox + ancho_cara] = recorte

    yy, xx = np.where(valido)
    px, py, pz = pos[yy, xx, 0], pos[yy, xx, 1], pos[yy, xx, 2]
    foto_mask = (pz > zmin) & (np.abs(px) < mx) & (py > my0) & (py < my1)
    sx = (px + mx) / (2 * mx) * lado
    sy = (my1 - py) / (my1 - my0) * lado
    rgb = np.stack([map_coordinates(card[..., ch], [sy, sx], order=1, mode='nearest') for ch in range(3)], -1)
    at[yy[foto_mask], xx[foto_mask], :3] = np.clip(rgb[foto_mask] * brillo, 0, 1)

    if tener_pelo:
        cabello = np.asarray(piel if pelo is None else pelo, np.float32)
        sel_pelo = (py > my1) & ~foto_mask
        sel_trasera = (pz < 0.25) & (py > nuca_min_y) & ~foto_mask
        pelo_mask = np.zeros_like(valido)
        trasera = np.zeros_like(valido)
        pelo_mask[yy[sel_pelo], xx[sel_pelo]] = True
        trasera[yy[sel_trasera], xx[sel_trasera]] = True
        for mascara in (pelo_mask, trasera):
            at[mascara, :3] = cabello[None, :] * factor[mascara, None]
    return Image.fromarray((np.clip(at, 0, 1) * 255).astype(np.uint8))


def vestir(vista, material, atlas, escala=4, ocultar=('mat_bm_eye', 'mat_eye'), sin_gorra=False):
    """Aplica el atlas a la cabeza de un VistaModelo y oculta los parches de ojos/boca nativos."""
    mat = next((m for m in vista.modelo.materials if m.name == material), None)
    if mat is None:
        raise ValueError('El modelo no tiene el material ' + material)
    vista.reemplazar_textura(mat.tex, atlas, escala=escala)
    for m in vista.modelo.materials:
        if m.name in ocultar or (sin_gorra and m.name == 'mat_bm_head_c'):
            m.alpha = 0.0
    return vista


def cara(vista, foto, hitos, material='mat_bm_head', pelo=None, escala=4,
         ocultar=('mat_bm_eye', 'mat_eye'), sin_gorra=False, **opciones):
    """Atajo: construye el atlas con la foto y lo aplica a la cabeza del modelo."""
    atlas = atlas_cara(vista.modelo, material, foto, hitos, pelo=pelo, escala=escala, **opciones)
    vestir(vista, material, atlas, escala=escala, ocultar=ocultar, sin_gorra=sin_gorra)
    return atlas
