"""Motor de cinemáticas 3D de Mario Kart DS (vertical 1080x1920). Ver skills/cinematica-mkds."""
import os, sys
_AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(_AQUI, '..', '..'))
# Las piezas de bajo nivel (nitro3d, nftr, sonido) se comparten con NSMB: son la misma librería de la DS.
_NSMB = os.path.join(RAIZ, '..', 'nsmb', 'tools', 'nsmb')
for p in (os.path.join(RAIZ, 'tools', 'mkds'), _NSMB, os.path.join(RAIZ, 'video')):
    if p not in sys.path: sys.path.insert(0, p)
import mkrom                                   # noqa: E402  (deja listo `valedores.rutas`)
rutas = mkrom.rutas
CACHE = rutas.cache('mkds')
SALIDA = rutas.salida('mkds')
