"""Motor de vídeo de Inazuma Eleven; gráficos y audio de su ROM."""
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta / 'valedores.toml').is_file():
        sys.path.insert(0,str(carpeta / 'nucleo'))
        break
else:
    raise RuntimeError('No se encuentra valedores.toml')
from PIL import Image
from valedores.video_nds import Video as _Video, Plano, Clip, Fuente, Superposicion, interpolar
from valedores.activos_video_nds import Recursos as _Recursos
from valedores.recursos_nds import _modulo

_rpg=_modulo('rpg_inazuma',Path(__file__).with_name('rpg.py'))
Recorrido,ActorDireccional,EscenaRPG=_rpg.Recorrido,_rpg.ActorDireccional,_rpg.EscenaRPG

JUEGO = 'inazuma-eleven'

# Las NFTR de la ROM (FONT12, FONT12N, FONT12T, FONT8) son Shift-JIS, pero guardan las letras
# latinas acentuadas en el rango 0xA1-0xDF (el de katakana de media anchura). Mapa carácter -> código.
LATINO = {'Ù': 0xA1, 'Ú': 0xA2, 'Û': 0xA3, 'Ü': 0xA4, '¿': 0xA5, 'Ñ': 0xA9, 'Ó': 0xAB,
          'à': 0xB1, 'á': 0xB2, 'â': 0xB3, 'ã': 0xB4, 'ä': 0xB5, 'ç': 0xB8,
          'è': 0xB9, 'é': 0xBA, 'ê': 0xBB, 'ë': 0xBC, 'ì': 0xBD, 'í': 0xBE, 'î': 0xBF, 'ï': 0xC0,
          'ñ': 0xC2, 'ò': 0xC3, 'ó': 0xC4, 'ô': 0xC5, 'ö': 0xC7,
          'ù': 0xC9, 'ú': 0xCA, 'û': 0xCB, 'ü': 0xCC, '€': 0xCE,
          'À': 0xD0, 'Á': 0xD1, 'Ç': 0xD7, 'È': 0xD8, 'É': 0xD9, 'Ì': 0xDC, 'Í': 0xDD, '¡': 0xDF}

# Ventana de mensaje nativa: está dibujada en la pantalla de aviso srd_s02 (256x192).
VENTANA = ('data_iz/pic2d/sp/srd_s02.pac_', (6, 46, 250, 146))


class Video(_Video):
    def __init__(self, **opciones):
        super().__init__(JUEGO, **opciones)

    def plano_rpg(self,duracion,escenario,**opciones):
        escena=EscenaRPG(escenario,self.tamano,**opciones)
        plano=self.plano(duracion)
        plano.sprite(escena,x=0,y=0,ancla=(0,0),pantalla=True)
        return plano,escena


class Recursos(_Recursos):
    def __init__(self):
        super().__init__(JUEGO)

    def escenario(self,nombre='mr01b01',**opciones):
        return _rpg.FondoRPG(self,nombre,**opciones)

    def fuente(self, origen='data_iz/font/FONT12.NFTR'):
        """NFTR del juego con las letras acentuadas y los signos ¿ ¡ € del español."""
        # FONT12 guarda avances iguales al ancho de tinta: el montaje necesita
        # un píxel lógico entre letras para que sus trazos no se unan.
        return Fuente(self.datos(origen), extra=LATINO, espaciado=1)

    def ventana(self, ancho, alto, borde=8):
        """Ventana de diálogo del juego (borde marrón sobre blanco) a ancho x alto píxeles DS.

        Trocea en 9 partes la caja nativa de srd_s02; las esquinas y los bordes se copian tal cual
        y el centro se rellena con el blanco interior. Sin texto: el interior queda liso.
        """
        caja = self.imagen(VENTANA[0]).crop(VENTANA[1]).convert('RGBA')
        w, h = caja.size
        if ancho < 2 * borde + 1 or alto < 2 * borde + 1 or ancho > 1024 or alto > 1024:
            raise ValueError('Tamaño de ventana no válido')
        salida = Image.new('RGBA', (ancho, alto), (255, 255, 255, 255))
        # esquinas
        for (sx, sy, dx, dy) in ((0, 0, 0, 0), (w - borde, 0, ancho - borde, 0),
                                 (0, h - borde, 0, alto - borde), (w - borde, h - borde, ancho - borde, alto - borde)):
            salida.paste(caja.crop((sx, sy, sx + borde, sy + borde)), (dx, dy))
        # bordes: una tira de 1 px del centro estirada
        cx, cy = w // 2, h // 2
        arriba = caja.crop((cx, 0, cx + 1, borde)).resize((ancho - 2 * borde, borde), Image.Resampling.NEAREST)
        abajo = caja.crop((cx, h - borde, cx + 1, h)).resize((ancho - 2 * borde, borde), Image.Resampling.NEAREST)
        izq = caja.crop((0, cy, borde, cy + 1)).resize((borde, alto - 2 * borde), Image.Resampling.NEAREST)
        der = caja.crop((w - borde, cy, w, cy + 1)).resize((borde, alto - 2 * borde), Image.Resampling.NEAREST)
        salida.paste(arriba, (borde, 0))
        salida.paste(abajo, (borde, alto - borde))
        salida.paste(izq, (0, borde))
        salida.paste(der, (ancho - borde, borde))
        return salida
