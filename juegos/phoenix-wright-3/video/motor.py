"""Motor de vídeo de Phoenix Wright 3; gráficos y audio de su ROM."""
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
from valedores.recursos_nds import _modulo

_juicio=_modulo('juicio_phoenix',Path(__file__).with_name('juicio.py'))
Busto,impacto,rotulo_impacto,banda_sonora=_juicio.Busto,_juicio.impacto,_juicio.rotulo_impacto,_juicio.banda_sonora

JUEGO = 'phoenix-wright-3'

class Video(_Video):
    def __init__(self, **opciones):
        super().__init__(JUEGO, **opciones)

    def renderizar(self,nombre='video.mp4',audio_redes=False):
        archivo=super().renderizar(nombre)
        return _juicio.normalizar_audio_redes(archivo) if audio_redes else archivo

class Recursos(_Recursos):
    def __init__(self):
        super().__init__(JUEGO)
