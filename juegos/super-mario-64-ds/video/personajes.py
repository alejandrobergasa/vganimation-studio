"""Caras de foto sobre los BMD de SM64DS (implementación compartida en valedores.caras_video)."""
from valedores.caras_video import color_piel, atlas_cara, vestir, cara as _cara


def cara(vista, foto, hitos, material='mat_bm_head', **opciones):
    """Atajo con el material de cabeza de `b_mario_all.bmd` por defecto."""
    return _cara(vista, foto, hitos, material=material, **opciones)
