"""Motor de vídeo de Super Mario 64 DS; gráficos y audio de su ROM."""
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta / 'valedores.toml').is_file():
        sys.path.insert(0,str(carpeta/'nucleo'))
        break
else:
    raise RuntimeError('No se encuentra valedores.toml')
from valedores.video_nds import Video as _Video, Plano, Clip, Fuente, Superposicion, interpolar
from valedores.activos_video_nds import Recursos as _Recursos

JUEGO = 'super-mario-64-ds'

class Video(_Video):
    def __init__(self, **opciones):
        super().__init__(JUEGO, **opciones)

class Recursos(_Recursos):
    def __init__(self):
        super().__init__(JUEGO)
