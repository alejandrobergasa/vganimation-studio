"""Motor de vídeo de Mario Party DS; gráficos, animaciones y audio de su ROM."""
from functools import lru_cache
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta / 'valedores.toml').is_file():
        sys.path.insert(0,str(carpeta/'nucleo'))
        break
else:
    raise RuntimeError('No se encuentra valedores.toml')
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from PIL import Image

from valedores import rutas
from valedores.video_nds import Video as _Video, Plano, Clip, Fuente, Superposicion, interpolar, Pista
from valedores.activos_video_nds import Recursos as _Recursos, texturas_party
from valedores.anmf_party import AnimacionParty
from valedores.caras_foto import CaraFoto, Hitos, detectar_hitos
from valedores.escena3d import Actor3D, Camara, Escena3D, Particulas
from valedores.modelos_video_nds import ModeloParty
from valedores import efectos_video as efectos
import interfaz
import personajes

JUEGO = 'mario-party-ds'

# Tableros: modelo principal de cada `bmap_NN`.
ESCENARIOS = {
    'fuente':     'data/bmap_00_LZ.bin::00005.bin',
    'jardin':     'data/bmap_01_LZ.bin::00019.bin',
    'musica':     'data/bmap_02_LZ.bin::00018.bin',
    'jungla':     'data/bmap_03_LZ.bin::00021.bin',
    'biblioteca': 'data/bmap_04_LZ.bin::00020.bin',
    'pinball':    'data/bmap_05_LZ.bin::00020.bin',
}
# Texturas de efectos de `mpds_efc_LZ.bin` (humo, destellos, golpe, sudor, estrellas...).
EFECTOS_TEXTURA = ('kemuri01_A5I3', 'kemuri02_A5I3', 'piyo_a3i5', 'glitter01_A5I3', 'ase03_PLT256', 'hit02_aA5I3',
                   'bikkuri_PLT256', 'star01_PLT256', 'a1_a5i3', 'a2_a5i3', 'hi_a5i3')
# Voces por personaje: cada archivo SSAR agrupa sus frases (SE_<clave>_001...).
VOCES = {'mario': 'SQA_SEMAV', 'luigi': 'SQA_SELUV', 'wario': 'SQA_SEWRV', 'yoshi': 'SQA_SEYOV',
         'peach': 'SQA_SEPEV', 'daisy': 'SQA_SEDAV', 'waluigi': 'SQA_SEWLV', 'toad': 'SQA_SEKIV'}
# Iconos del marcador del tablero en mbgui_dep (miembro 3, paleta 0): celda.
ICONOS = {'marcador_azul': 1, 'marcador_rojo': 2, 'marcador_verde': 3, 'marcador_amarillo': 4,
          'primero': 5, 'segundo': 6, 'tercero': 7, 'cuarto': 8, 'cero': 9, 'cpu': 19,
          'objeto1': 20, 'objeto2': 21, 'objeto3': 22, 'objeto4': 23, 'objeto5': 24, 'objeto6': 25, 'objeto7': 26, 'objeto8': 27,
          'moneda': 35, 'estrella': 36, 'ficha_azul': 37, 'ficha_roja': 38, 'ficha_verde': 39, 'ficha_amarilla': 40,
          'flecha': 41, 'ronda': 44}


class Video(_Video):
    def __init__(self, **opciones):
        super().__init__(JUEGO, **opciones)

    def plano_escena(self, duracion, escena, inicio=0.0, transicion=None):
        """Plano a pantalla completa de una `Escena3D`, desde el segundo `inicio` de su línea de tiempo."""
        plano = self.plano(duracion)
        plano.escena(_EscenaDesde(escena, inicio) if inicio else escena, self.tamano)
        plano.transicion = transicion
        return plano


class _EscenaDesde:
    """Permite cortar entre planos de una misma escena manteniendo su tiempo."""
    def __init__(self, escena, inicio):
        self.escena, self.inicio, self.tamano = escena, inicio, escena.tamano

    def frame(self, t):
        return self.escena.frame(self.inicio + t)


class Recursos(_Recursos):
    def __init__(self):
        super().__init__(JUEGO)
        self._sonido = None
        self._efectos = {}

    # ---------------------------------------------------------- 3D

    def personaje(self, nombre='mario', foto=None, **opciones):
        """Actor 3D con animaciones nativas y, si se indica, cara de foto. Ver personajes.personaje."""
        return personajes.personaje(self, nombre, foto=foto, **opciones)

    def animaciones(self, nombre='mario'):
        return personajes.animaciones(self, nombre)

    def animacion(self, origen, nombre=None):
        """Cualquier ANMF de la ROM (minijuegos, tableros, objetos): `Recursos.buscar` da los orígenes."""
        return AnimacionParty(self.datos(origen), nombre or origen)

    def objeto(self, origen, bancos=(), **actor):
        """Actor de un modelo cualquiera de la ROM. `bancos`: miembros con las texturas si van aparte."""
        return Actor3D(ModeloParty(self.datos(origen), [self.datos(b) for b in bancos]), **actor)

    def escenario(self, nombre='jardin', **actor):
        """Tablero completo como actor estático: 'fuente', 'jardin', 'musica', 'jungla', 'biblioteca', 'pinball'."""
        if nombre not in ESCENARIOS:
            raise ValueError('Escenario desconocido; hay: ' + ', '.join(ESCENARIOS))
        return self.objeto(ESCENARIOS[nombre], **actor)

    def dado(self, **actor):
        return self.objeto('data/mpds_dice.bin::00000.bin', **actor)

    def textura_efecto(self, nombre='star01_PLT256'):
        """Textura RGBA de los efectos del juego, para `Particulas`."""
        for o in self.registros:
            if o.startswith('data/mpds_efc_LZ.bin::') or o.startswith('data/bmap_sys_LZ.bin::'):
                d = self.datos(o)
                if d[:4] == b'HBDF':
                    for n, im in texturas_party(d):
                        if n == nombre:
                            return im.convert('RGBA')
        raise ValueError('No está la textura de efecto %s; hay: %s' % (nombre, ', '.join(EFECTOS_TEXTURA)))

    # ---------------------------------------------------------- interfaz

    def fuente_juego(self):
        """Fuente 8×8 del ejecutable; tildes y ñ compuestas con sus píxeles."""
        return interfaz.Fuente8()

    def interfaz(self, contenedor='data/SP/mbgui_dep_LZ.bin'):
        """Banco de pantallas y sprites 2D de un contenedor. `.hoja()` genera su catálogo visual."""
        return interfaz.Banco2D(self, contenedor)

    def icono(self, nombre='estrella', escala=2):
        """Icono del marcador del tablero: ver motor.ICONOS."""
        if nombre not in ICONOS:
            raise ValueError('Icono desconocido; hay: ' + ', '.join(ICONOS))
        im = self.interfaz().sprites(3, paleta_i=0)[ICONOS[nombre]][0]
        return im.resize((im.width * escala, im.height * escala), Image.Resampling.NEAREST)

    # ---------------------------------------------------------- sonido

    def _banco_sonido(self):
        if self._sonido is None:
            from valedores.recursos_nds import lectores
            self._sonido = lectores()[2].Sonido(rutas.rom(JUEGO), 'data/MPDS_sound.sdat')
        return self._sonido

    def efectos(self, prefijo='SE_'):
        """Nombres de los 1750 efectos de la ROM: `SE_SYS` sistema, `SE_MGP` minijuegos, `SE_M101` un minijuego..."""
        return [n for n in self._banco_sonido().efectos() if n.startswith(prefijo)]

    def efecto(self, nombre, segundos=4.0):
        """Sintetiza un efecto con sus bancos nativos: (muestras, frecuencia), sin el silencio final."""
        if nombre not in self._efectos:
            son = self._banco_sonido()
            try:
                a = son.efecto(nombre, segundos=segundos)
            except KeyError:
                raise ValueError('No existe el efecto ' + nombre) from None
            activo = np.flatnonzero(np.abs(a).max(1) > 1e-4)
            if not len(activo):
                raise ValueError('El efecto %s no produce sonido' % nombre)
            self._efectos[nombre] = a[:activo[-1] + 1]
        return self._efectos[nombre], 32768

    def voces(self, personaje='mario'):
        """Efectos de voz de un personaje."""
        archivo = VOCES.get(personaje)
        if archivo is None:
            raise ValueError('Personaje sin voces; hay: ' + ', '.join(VOCES))
        for n, ar in self._banco_sonido().sdat.sequenceArchives:
            if n == archivo and ar is not None:
                return [k for k, _ in ar.sequences]
        raise ValueError('El archivo de voces %s no está en el SDAT' % archivo)

    def muestrario(self, prefijo='SE_SYS', separacion=0.4, maximo=60):
        """Une efectos con silencios para escucharlos: devuelve (muestras, frecuencia, [(segundo, nombre)]).

        Sirve para que una persona elija: los nombres de la ROM son números y medir no equivale a oír."""
        trozos, indice, t = [], [], 0.0
        for n in self.efectos(prefijo)[:maximo]:
            try:
                a, fs = self.efecto(n)
            except ValueError:
                continue
            indice.append((round(t, 2), n))
            trozos += [a, np.zeros((int(separacion * fs), 2), a.dtype)]
            t += len(a) / fs + separacion
        if not trozos:
            raise ValueError('Ningún efecto con el prefijo ' + prefijo)
        return np.concatenate(trozos), 32768, indice
