"""Sprites RPG pequeños de Inazuma: cuerpo PCB + cabeza PCH + paletas PPB/PPH."""
import struct
import unicodedata

import numpy as np
from PIL import Image

from valedores import nitro
from valedores.video_nds import Clip


# Cinco vistas nativas hacia sur/izquierda/norte; las tres del lado derecho se reflejan.
DIRECCIONES = {'sur': (0, False), 'suroeste': (1, False), 'oeste': (2, False),
               'noroeste': (3, False), 'norte': (4, False), 'noreste': (3, True),
               'este': (2, True), 'sureste': (1, True)}


def normalizar(nombre):
    return ''.join(c for c in unicodedata.normalize('NFD', nombre.casefold()) if not unicodedata.combining(c))


class Pieza:
    def __init__(self, datos):
        datos, _ = nitro.descomprimir(datos)
        partes = nitro.tabla_pares(datos)
        if partes is None or len(partes) != 2:
            raise ValueError('El sprite RPG necesita metadatos y píxeles')
        self.meta, self.pixeles = (p[2] for p in partes)
        if len(self.meta) < 16:
            raise ValueError('Metadatos de sprite truncados')
        tabla = nitro.u32(self.meta, 4)
        if tabla + 4 > len(self.meta):
            raise ValueError('Tabla de celdas fuera del sprite')
        cantidad, self.flags = struct.unpack_from('<HH', self.meta, tabla)
        if not 0 < cantidad <= 4096 or tabla + 4 + cantidad * 4 > len(self.meta):
            raise ValueError('Índice de celdas de sprite no válido')
        self.celdas = struct.unpack_from('<%dI' % cantidad, self.meta, tabla + 4)

    def frame(self, indice, paleta):
        if not 0 <= indice < len(self.celdas):
            raise ValueError('Celda de sprite fuera de límites')
        p = self.celdas[indice]
        if p + 12 > len(self.meta) or len(paleta) != 32:
            raise ValueError('Cabecera de celda o paleta de sprite no válida')
        ancla_x, ancla_y, ancho, alto, n, _ = struct.unpack_from('<6H', self.meta, p)
        if not 0 < ancho <= 256 or not 0 < alto <= 256 or n > 128 or p + 12 + n * 16 > len(self.meta):
            raise ValueError('Piezas de celda fuera de límites')
        colores = np.frombuffer(paleta, '<u2')
        rgba = np.stack(((colores & 31)*255//31, (colores>>5 & 31)*255//31,
                         (colores>>10 & 31)*255//31, np.full(16,255)), axis=1).astype('uint8')
        rgba[0,3] = 0
        # Los offsets y el ancla pertenecen a un mismo lienzo lógico de 32x32.
        # No se recorta cada fotograma: así los pies no saltan al animar.
        im = Image.new('RGBA', (64,64))
        for i in range(n):
            x,y,a0,a1,ew,eh,offset = struct.unpack_from('<6HI',self.meta,p+12+i*16)
            if ew>5 or eh>5:
                raise ValueError('Dimensiones de pieza no compatibles')
            w,h = 8<<ew,8<<eh
            cantidad = w*h//2
            if offset+cantidad>len(self.pixeles):
                raise ValueError('Píxeles del sprite fuera de límites')
            raw=np.frombuffer(self.pixeles[offset:offset+cantidad],'uint8')
            # Estos sprites guardan cada pieza en líneas, no en tiles de 8x8.
            indices=np.stack((raw&15,raw>>4),axis=1).reshape(h,w)
            fragmento=Image.fromarray(rgba[indices])
            if a1 & 0x1000:fragmento=fragmento.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if a1 & 0x2000:fragmento=fragmento.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            im.alpha_composite(fragmento,(int(x)-ancla_x+32,int(y)-ancla_y+48))
        return im


class BancoPersonajes:
    def __init__(self, datos):
        self.datos = datos
        self._paquetes = {}
        self._piezas = {}
        self.unidades = []
        d=datos('data_iz/logic/sp/unitbase.dat')
        if len(d)%96:
            raise ValueError('Tabla unitbase de la ROM YEES no válida')
        for i in range(1,len(d)//96):
            fila=d[i*96:(i+1)*96]
            nombre=fila[:32].split(b'\0')[0]
            if not nombre or nombre.startswith(b'\x96\xa2\x92\xe8'):
                continue
            nombre=nombre.decode('cp1252',errors='replace')
            apodo=fila[32:64].split(b'\0')[0].decode('cp1252',errors='replace')
            cabeza,paleta=struct.unpack_from('<HH',fila,0x48)
            self.unidades.append({'id':i,'nombre':nombre,'apodo':apodo,'cabeza':cabeza*100,
                                   'paleta_cabeza':paleta,'tamano':fila[0x54]})

    def paquete(self,tipo):
        if tipo not in self._paquetes:
            base='data_iz/spr/char/'+tipo
            entradas=nitro.paquete_inazuma(self.datos(base+'.pkh'),self.datos(base+'.pkb'))
            self._paquetes[tipo]={int(n.split('_')[1].split('.')[0],16):d for n,o,d in entradas}
        return self._paquetes[tipo]

    def pieza(self,tipo,indice):
        clave=(tipo,indice)
        if clave not in self._piezas:
            try:self._piezas[clave]=Pieza(self.paquete(tipo)[indice])
            except KeyError as exc:raise ValueError('No existe %s con id %d en esta ROM'%(tipo,indice)) from exc
        return self._piezas[clave]

    def personaje(self,nombre='Mark',direccion='sur',accion='caminar',fps=8,cuerpo=100,paleta_cuerpo=1):
        if direccion not in DIRECCIONES or accion not in ('quieto','caminar') or not 0<fps<=60:
            raise ValueError('Dirección, acción o velocidad del sprite no válida')
        candidatos=[u for u in self.unidades if u['id']==nombre] if isinstance(nombre,int) else [
            u for u in self.unidades if normalizar(nombre) in (normalizar(u['nombre']),normalizar(u['apodo']))]
        if len(candidatos)!=1:
            raise ValueError('Usa el nombre completo o id de un personaje de personajes()')
        u=candidatos[0]
        cb=self.pieza('pcb',cuerpo);cc=self.pieza('pch',u['cabeza'])
        try:pb=self.paquete('ppb')[paleta_cuerpo];pc=self.paquete('pph')[u['paleta_cabeza']]
        except KeyError as exc:raise ValueError('Paleta RPG inexistente en esta ROM') from exc
        vista,reflejar=DIRECCIONES[direccion]
        indices=[(0,4,8,12,17)[vista]] if accion=='quieto' else list(range(20+vista*4,24+vista*4))
        imagenes=[]
        for i in indices:
            im=cb.frame(i,pb);im.alpha_composite(cc.frame(i,pc))
            # Lienzo 32x48 con el pie en (16,47), idéntico para todos los frames.
            im=im.crop((16,0,48,48))
            if reflejar:im=im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            imagenes.append(im)
        clip=Clip(imagenes,[1/fps]*len(imagenes))
        clip.nombre=u['nombre']
        clip.origenes={'cuerpo':cuerpo,'cabeza':u['cabeza'],'paleta_cuerpo':paleta_cuerpo,'paleta_cabeza':u['paleta_cabeza']}
        return clip
