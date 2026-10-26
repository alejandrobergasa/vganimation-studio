"""MapaReal con las texturas animadas del juego (agua, flores...)."""
import os
import sys

import numpy as np
from PIL import Image

from motor import mapa_real as _m
from motor.mapa_real import ZONAS, INTERIORES, _rom, CACHE, RAIZ

PASO = 9    # frames de escena (30 fps) que dura cada fotograma de la animación, como los 9 ticks del juego


def _cargar_estados(fila, col, filas, cols, hora, K):
    """(array [n, H, W, 4] con la imagen de cada estado de la animación, o None si la zona no se anima)."""
    ruta = os.path.join(CACHE, 'anim_%d_%d_%d_%d_K%g_h%g.npz' % (fila, col, filas, cols, K, hora))
    if os.path.exists(ruta):
        d = np.load(ruta)
        return d['estados'] if d['estados'].shape[0] > 1 else None
    sys.path.insert(0, os.path.join(RAIZ, 'tools'))
    import mapa3d_v2
    print('Renderizando animación de la zona %s...' % ((fila, col, filas, cols),))
    mundo = mapa3d_v2.MundoAnim(_rom())
    anim = mundo.animadas(fila, col, filas, cols)
    n = max(anim.values()) if anim else 1
    estados = np.stack([mundo.render_estado(fila, col, filas, cols, k, K, hora) for k in range(n)]) if anim \
        else np.zeros((1,))
    np.savez_compressed(ruta, estados=estados)
    return estados if anim and n > 1 else None


class MapaReal(_m.MapaReal):
    def __init__(self, zona=None, fila=None, col=None, filas=1, cols=1, hora=12, K=1.0, land=None, animado=True):
        super().__init__(zona, fila, col, filas, cols, hora, K, land)
        self.estados = None
        if animado and zona not in INTERIORES and land is None:
            if zona is not None:
                fila, col, filas, cols = ZONAS[zona]
            self.estados = _cargar_estados(fila, col, filas, cols, hora, K)
            if self.estados is not None:
                self._fondos = [Image.fromarray(e).convert('RGBA') for e in self.estados]
                # el alfa y la profundidad no cambian: solo las texturas
                self.fondo = self._fondos[0]

    def dibujar_suelo(self, lienzo, camx, camy, t):
        if self.estados is not None:
            self.fondo = self._fondos[(t // PASO) % len(self._fondos)]
        super().dibujar_suelo(lienzo, camx, camy, t)
