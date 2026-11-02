"""Recursos nativos para los motores de montaje de los nuevos juegos DS."""
from functools import lru_cache
import json
from pathlib import Path
import struct

import ndspy.rom
import ndspy.lz10
import numpy as np
from PIL import Image

from . import nitro, rutas
from .recursos_nds import lectores, fondo_layton
from .video_nds import Clip, Fuente, Superposicion


def cadena(d, o):
    if not 0 <= o < len(d):
        raise ValueError('Cadena fuera del archivo')
    fin = d.find(b'\0', o)
    return bytes(d[o:fin if fin >= 0 else len(d)]).decode('shift_jis', errors='replace')


@lru_cache(maxsize=1)
def graficos():
    return lectores()[0]


def textura(datos, paleta, tipo, ancho, alto, transparente=True, datos4x4=b''):
    if not 0 < ancho <= 1024 or not 0 < alto <= 1024 or tipo not in range(1, 8):
        raise ValueError('Dimensiones o formato de textura no válidos')
    colores = np.frombuffer(bytes(paleta) + b'\0' * 512, '<u2')
    return graficos()._decode_tex(bytes(datos) + bytes(datos4x4), tipo, ancho, alto,
        0, 0, len(datos), colores, transparente)


def animacion_layton(datos):
    """ARC: partes lineales, paleta común y secuencias de índices/tiempos DS."""
    d, _ = nitro.descomprimir(datos, level5=True)
    n, tipo = struct.unpack_from('<HH', d)
    if not 0 < n <= 512 or tipo not in (3, 4):
        raise ValueError('ARC de animación no válido')
    pos, fotogramas = 4, []
    for _ in range(n):
        w, h, partes, _ = struct.unpack_from('<4H', d, pos)
        pos += 8
        if not 0 < w <= 1024 or not 0 < h <= 1024 or not 0 < partes <= 1024:
            raise ValueError('Fotograma ARC fuera de límites')
        piezas = []
        for _ in range(partes):
            x, y, wx, hy = struct.unpack_from('<4H', d, pos)
            pos += 8
            if wx > 7 or hy > 7:
                raise ValueError('Parte ARC fuera de límites')
            pw, ph = 8 << wx, 8 << hy
            tam = pw * ph // (2 if tipo == 3 else 1)
            if pos + tam > len(d):
                raise ValueError('Parte ARC truncada')
            piezas.append((x, y, pw, ph, d[pos:pos + tam]))
            pos += tam
        fotogramas.append((w, h, piezas))
    nc = nitro.u32(d, pos)
    pos += 4
    if not 0 < nc <= 256 or pos + 2 * nc > len(d):
        raise ValueError('Paleta ARC no válida')
    paleta = d[pos:pos + 2 * nc]
    pos += 2 * nc
    imagenes = []
    for w, h, piezas in fotogramas:
        im = Image.new('RGBA', (w, h))
        for x, y, pw, ph, raw in piezas:
            im.alpha_composite(textura(raw, paleta, tipo, pw, ph), (x, y))
        imagenes.append(im)
    clips = {'todos': Clip(imagenes)}
    # Los 30 bytes reservados preceden a la tabla de nombres de animación.
    pos += 30
    if pos + 4 > len(d):
        return clips
    na = nitro.u32(d, pos)
    pos += 4
    if na > 256 or pos + na * 30 > len(d):
        raise ValueError('Tabla de animaciones ARC no válida')
    nombres = [d[pos + i * 30:pos + (i + 1) * 30].split(b'\0')[0].decode('ascii', 'replace') for i in range(na)]
    pos += na * 30
    for nombre in nombres:
        nf = nitro.u32(d, pos)
        pos += 4
        if nf > 10000 or pos + nf * 12 > len(d):
            raise ValueError('Secuencia ARC truncada')
        ids = struct.unpack_from('<%dI' % nf, d, pos) if nf else []
        tiempos = struct.unpack_from('<%dI' % nf, d, pos + nf * 4) if nf else []
        indices = struct.unpack_from('<%dI' % nf, d, pos + nf * 8) if nf else []
        pos += nf * 12
        if nf and all(i < len(imagenes) for i in indices):
            clips[nombre or str(len(clips))] = Clip([imagenes[i] for i in indices], [max(1, t) / 60 for t in tiempos])
    return clips


def alinear_cara_layton(cuerpos, caras, maximo=40):
    """Posición (x, y) de la capa facial sobre el cuerpo de un personaje de Layton.

    Los ARC no guardan ese desplazamiento (lo da el guion del juego). El cuerpo ya trae
    una boca/cara por defecto y el parche de `*_e_face.arc` la sustituye, así que se busca
    el par cuerpo/parche que coincide píxel a píxel y se devuelve dónde encaja.
    Devuelve ((x, y), error medio por píxel opaco); falla si ninguna posición encaja bien.
    """
    from numpy.lib.stride_tricks import sliding_window_view
    mejor = None
    for cuerpo in cuerpos:
        B = np.asarray(cuerpo.convert('RGBA'), np.int16)
        for cara in caras:
            P = np.asarray(cara.convert('RGBA'), np.int16)
            h, w = P.shape[:2]
            opaco = P[..., 3] > 0
            if not opaco.any() or h > B.shape[0] or w > B.shape[1]:
                continue
            ventanas = np.moveaxis(sliding_window_view(B, (h, w), axis=(0, 1)), 2, -1)
            error = (np.abs(ventanas - P).sum(-1) * opaco).sum((-1, -2))
            y, x = np.unravel_index(error.argmin(), error.shape)
            medio = error[y, x] / opaco.sum()
            if mejor is None or medio < mejor[1]:
                mejor = ((int(x), int(y)), float(medio))
    if mejor is None or mejor[1] > maximo:
        raise ValueError('No se puede situar la capa facial automáticamente; indica posicion=(x, y)')
    return mejor


def imagenes_phoenix(datos):
    """Localiza cabeceras autocontenidas; valida tamaño de píxeles y paleta.

    No usa offsets de otras regiones. Sólo los bloques con cabecera completa se
    declaran imágenes; los gráficos sin cabecera necesitan su mapa específico.
    """
    salida = []
    for o in range(0, len(datos) - 20, 4):
        tipo, ew, eh = datos[o:o + 3]
        if tipo not in (3, 4, 6) or ew > 5 or eh > 5:
            continue
        h, tam, pal, npal = struct.unpack_from('<4I', datos, o + 4)
        w, alto = 8 << ew, 8 << eh
        esperado = w * alto // (2 if tipo == 3 else 1)
        if h not in range(20, 129) or tam != esperado or pal < h + tam or not 0 < npal <= 512 or npal % 2:
            continue
        if o + pal + npal > len(datos):
            continue
        salida.append((o, textura(datos[o + h:o + h + tam], datos[o + pal:o + pal + npal], tipo, w, alto)))
    return salida


def texturas_sm64(datos):
    """Texturas BMD propias de SM64DS, enlazadas por los materiales del modelo."""
    if len(datos) < 0x30:
        raise ValueError('BMD truncado')
    nt, ot, npal, op, nm, om = struct.unpack_from('<6I', datos, 0x14)
    if nt > 4096 or npal > 4096 or nm > 4096 or ot + nt * 20 > len(datos) or om + nm * 48 > len(datos):
        raise ValueError('Tablas BMD fuera de límites')
    asociaciones = {}
    for i in range(nm):
        tex, pal = struct.unpack_from('<II', datos, om + i * 48 + 4)
        if tex < nt:
            asociaciones[(tex, pal)] = True
    salida = []
    for ti, pi in asociaciones:
        p = ot + ti * 20
        no, off, tam, wh, param = struct.unpack_from('<5I', datos, p)
        tipo = param >> 26 & 7
        w, h = 8 << (param >> 20 & 7), 8 << (param >> 23 & 7)
        paleta = b''
        if pi != 0xFFFFFFFF:
            if pi >= npal or op + pi * 16 + 12 > len(datos):
                raise ValueError('Índice de paleta BMD no válido')
            _, po, pl = struct.unpack_from('<3I', datos, op + pi * 16)
            paleta = datos[po:po + pl]
        raw = datos[off:off + tam]
        extra = datos[off + tam:off + tam + tam // 2] if tipo == 5 else b''
        im = textura(raw, paleta, tipo, w, h, bool(param & (1 << 29)), extra)
        salida.append((cadena(datos, no), im))
    return salida


def texturas_party(datos):
    """HBDF/HSDF: IMGO, PLTO y enlaces TEXO, usando las longitudes de sus bloques."""
    if datos[:4] not in (b'HBDF', b'HSDF'):
        return []
    def bloques(magia):
        p = datos.find(magia)
        while p >= 0:
            if p + 8 <= len(datos):
                tam = nitro.u32(datos, p + 4)
                if 0 < tam <= len(datos) - p - 8:
                    yield p + 8, p + 8 + tam
            p = datos.find(magia, p + 4)
    def nombre(pos):
        if datos[pos:pos + 4] != b'NAME':
            raise ValueError('Bloque NAME no válido')
        n = nitro.u32(datos, pos + 4)
        return datos[pos + 8:pos + 8 + n].split(b'\0')[0].decode('ascii', 'replace'), pos + 8 + n
    paletas, enlaces, imagenes = {}, {}, []
    for p, fin in bloques(b'PLTO'):
        n, q = nombre(p)
        tam, compr = struct.unpack_from('<II', datos, q)
        raw = datos[q + 8:q + 8 + tam]
        paletas[n] = nitro.descomprimir(raw)[0] if compr else raw
    for p, fin in bloques(b'TEXO'):
        q = p + 8
        if datos[q:q + 4] == b'NAME':
            n, q = nombre(q)
            if datos[q:q + 4] == b'NAME':
                pal, q = nombre(q)
                enlaces[n] = pal
    for p, fin in bloques(b'IMGO'):
        n, q = nombre(p)
        tipo, w, h, param, tam, t4, compr = struct.unpack_from('<IHH4I', datos, q)
        q += 24
        raw = datos[q:q + tam]
        extra = datos[q + tam:q + tam + t4]
        if compr:
            raw = nitro.descomprimir(raw)[0]
        pal = paletas.get(enlaces.get(n, n))
        if pal is None and tipo != 7:
            continue
        imagenes.append((n, textura(raw, pal or b'', tipo, w, h, bool(param >> 29 & 1), extra)))
    return imagenes


def imagen_pac_inazuma(datos):
    """PAC de paleta, mapa y tiles; usa las dimensiones del bloque de control."""
    entradas = nitro.tabla_pares(datos)
    if entradas is None or len(entradas) not in (3, 4):
        raise ValueError('El PAC no contiene una imagen 2D con mapa')
    pal, mapa, raw = [e[2] for e in entradas[:3]]
    if len(pal) > 512 or not len(pal) or len(pal) % 2:
        raise ValueError('Paleta PAC no compatible')
    if len(entradas) == 4 and len(entradas[3][2]) >= 16:
        w, h = struct.unpack_from('<HH', entradas[3][2], 12)
    else:
        w, h = 256, len(mapa) // 2 // 32 * 8
    if not 0 < w <= 1024 or not 0 < h <= 1024 or w % 8 or h % 8 or len(mapa) < w * h // 32:
        raise ValueError('Mapa PAC fuera de límites')
    nc = len(pal) // 2
    # 16 colores por banco -> tiles de 4 bpp; 256 colores -> 8 bpp.
    depth = 8 if nc == 256 and len(raw) >= w * h else 4
    pix = np.frombuffer(raw, 'uint8')
    if depth == 4:
        pix = np.stack((pix & 15, pix >> 4), axis=1).reshape(-1)
    tiles = pix[:len(pix) // 64 * 64].reshape(-1, 8, 8)
    colores = np.array([graficos().bgr555(v) for v in np.frombuffer(pal, '<u2')], dtype='uint8')
    colores[0,3] = 0
    resultado = np.zeros((h,w,4),dtype='uint8')
    for i, e in enumerate(np.frombuffer(mapa[:w*h//32], '<u2')):
        t, banco = int(e)&1023, int(e)>>12
        if t >= len(tiles):
            raise ValueError('Tile PAC fuera de límites')
        indices=tiles[t]
        if e&1024:indices=indices[:,::-1]
        if e&2048:indices=indices[::-1]
        indices=indices.astype('uint16')+(banco*16 if depth==4 else 0)
        if np.max(indices)>=nc:
            raise ValueError('Banco de paleta PAC fuera de límites')
        y,x=divmod(i,w//8)
        resultado[y*8:y*8+8,x*8:x*8+8]=colores[indices]
    return Image.fromarray(resultado)


class Recursos:
    """Catálogo extraído y acceso de sólo lectura a la ROM del juego indicado."""
    def __init__(self, juego):
        self.juego = juego
        self.base = Path(rutas.extraidos(juego))
        p = self.base / 'catalogo.json'
        if not p.is_file():
            raise FileNotFoundError('Primero ejecuta: python valedores.py extraer ' + juego)
        self.catalogo = json.loads(p.read_text('utf-8'))
        self.registros = {r['origen']: r for r in self.catalogo['recursos']}
        self._rom = None

    def buscar(self, texto='', tipo=None):
        return [n for n, r in self.registros.items() if texto.lower() in n.lower() and (tipo is None or r['tipo'] == tipo)]

    def datos(self, origen):
        r = self.registros[origen]
        nombre = next((d for d in r['derivados'] if d.endswith('/descomprimido.bin')), r['original'])
        return (self.base / nombre).read_bytes()

    def imagen(self, origen, indice=0):
        r = self.registros[origen]
        png = [d for d in r['derivados'] if d.endswith('.png') and not d.endswith('/fuente.png')]
        if png:
            with Image.open(self.base / png[indice]) as im:
                return im.convert('RGBA')
        d = self.datos(origen)
        if self.juego == 'inazuma-eleven':
            return imagen_pac_inazuma(d)
        if self.juego == 'mario-party-ds':
            return texturas_party(d)[indice][1]
        if self.juego == 'super-mario-64-ds' and origen.lower().endswith('.bmd'):
            return texturas_sm64(d)[indice][1]
        if self.juego == 'phoenix-wright-3' and origen == 'data.bin':
            return self.graficos_phoenix()[indice][1].copy()
        raise ValueError('No hay una imagen compatible en ' + origen)

    @lru_cache(maxsize=1)
    def graficos_phoenix(self):
        return imagenes_phoenix(self.datos('data.bin'))

    @lru_cache(maxsize=1)
    def fondos_phoenix(self):
        """Pantallas LZ10 con paleta de 256 colores y tiles 8x8, 256x192."""
        d = self.datos('data.bin')
        fondos = []
        p = d.find(b'\x10\x00\xc2\x00')
        while p >= 0:
            try:
                u = ndspy.lz10.decompress(d[p:p+131072])
                if len(u) == 49664:
                    indices=np.frombuffer(u[512:],'uint8').reshape(24,32,8,8).transpose(0,2,1,3).reshape(192,256)
                    fondos.append((p, textura(indices.tobytes(), u[:512], 4, 256, 192, False)))
            except (IndexError, ValueError, struct.error):
                pass
            p = d.find(b'\x10\x00\xc2\x00', p+4)
        return fondos

    def clip(self, origen, animacion='todos'):
        if self.juego == 'profesor-layton' and origen.startswith('data/ani/') and origen.endswith('.arc'):
            return animacion_layton(self.datos(origen))[animacion]
        return Clip([self.imagen(origen)])

    def personaje_layton(self, nombre, animacion='talk', posicion=None):
        """Personaje de Layton listo para `plano.sprite`: cuerpo `data/ani/<nombre>.arc` con la
        capa facial `<nombre>_e_face.arc` (boca/ojos) en su sitio. Cuerpo y cara conservan sus
        tiempos de animación. La posición se deduce de las imágenes; `posicion` la fuerza.
        Los personajes sin `_e_face` (p. ej. objetos) se devuelven solo con el cuerpo."""
        if self.juego != 'profesor-layton':
            raise ValueError('Este constructor corresponde a Profesor Layton')
        cuerpo = animacion_layton(self.datos('data/ani/%s.arc' % nombre))
        if animacion not in cuerpo:
            raise ValueError('%s no tiene la animación %r; hay: %s' % (nombre, animacion, ', '.join(cuerpo)))
        origen_cara = 'data/ani/%s_e_face.arc' % nombre
        if origen_cara not in self.registros:
            return cuerpo[animacion]
        cara = animacion_layton(self.datos(origen_cara))
        if animacion not in cara:
            raise ValueError('%s_e_face no tiene la animación %r; hay: %s' % (nombre, animacion, ', '.join(cara)))
        if posicion is None:
            posicion, _ = alinear_cara_layton(cuerpo['todos'].imagenes, cara['todos'].imagenes)
        return Superposicion(cuerpo[animacion], cara[animacion], tuple(posicion))

    def _banco_personajes(self):
        if self.juego!='inazuma-eleven':
            raise ValueError('Este lector de personajes RPG corresponde a Inazuma Eleven')
        if not hasattr(self,'_sprites_rpg'):
            from .recursos_nds import _modulo
            lector=_modulo('sprites_inazuma',Path(rutas.motor_dir(self.juego))/'sprites.py')
            self._sprites_rpg=lector.BancoPersonajes(self.datos)
        return self._sprites_rpg

    def personajes(self):
        """Jugadores de unitbase con los ids de cabeza y paleta de sus sprites pequeños."""
        return [dict(u) for u in self._banco_personajes().unidades]

    def personaje(self,nombre='Mark',**opciones):
        """Clip RPG nativo: cuerpo, cabeza y paletas; no usa los retratos face2d."""
        return self._banco_personajes().personaje(nombre,**opciones)

    def personaje_personalizado(self,nombre,animacion='quieto',**opciones):
        """Carga el personaje adaptado; nunca usa la fotografía como sustituto silencioso."""
        from .personajes import cargar
        return cargar(self.juego,nombre,animacion,**opciones)

    def textura_personalizada(self,nombre,**opciones):
        from .personajes import textura
        return textura(self.juego,nombre,**opciones)

    def modelo(self, origen, bancos=(), animacion=None, **kw):
        from .modelos_video_nds import modelo_sm64, modelo_nitro, modelo_party
        if self.juego == 'super-mario-64-ds':
            return modelo_sm64(self.datos(origen), **kw)
        if self.juego == 'mario-party-ds':
            return modelo_party(self.datos(origen), [self.datos(n) for n in bancos], **kw)
        return modelo_nitro(self.datos(origen), [self.datos(n) for n in bancos],
                            self.datos(animacion) if animacion else None, **kw)

    def fuente(self, origen=None):
        if origen is None:
            fuentes = self.buscar(tipo='fuente NFTR')
            if not fuentes:
                raise ValueError('Este juego aún no tiene fuente NFTR catalogada; usa gráficos sin texto añadido')
            def cobertura(n):
                f=lectores()[1].Font(self.datos(n))
                # Las ROMs europeas pueden incluir también una fuente japonesa.
                # Prioriza la que contiene los signos y tildes del español.
                return sum(ord(c) in f.cmap for c in '¡¿ñÑáéíóú') if f.enc != 2 else 0
            origen = max(fuentes,key=cobertura)
        # Las NFTR de Layton no incluyen el hueco entre letras en el avance.
        return Fuente(self.datos(origen), espaciado=1 if self.juego == 'profesor-layton' else 0)

    def musica(self, nombre, segundos):
        if segundos <= 0:
            raise ValueError('La duración de música debe ser positiva')
        nombres = self.buscar(tipo='banco SDAT')
        if not nombres:
            raise ValueError('La ROM no tiene un banco SDAT catalogado')
        _, _, sonido = lectores()
        son = sonido.Sonido(rutas.rom(self.juego), nombres[0])
        audio=son.renderizar(nombre, segundos=segundos)
        if not audio.size or float(np.max(np.abs(audio))) < 1e-7:
            raise ValueError('La secuencia no produjo sonido; elige otra o utiliza audio SADL: '+nombre)
        return audio, sonido.FS

    def canciones(self):
        nombres = self.buscar(tipo='banco SDAT')
        if not nombres:
            return []
        import ndspy.soundArchive
        sdat = ndspy.soundArchive.SDAT(self.datos(nombres[0]))
        return [n for n, s in sdat.sequences if n and s is not None]

    def audio(self, origen, segundos=None):
        from .sonido_video_nds import sadl
        d=self.datos(origen)
        if d[:4]==b'sadl':return sadl(d,segundos)
        raise ValueError('El recurso no es audio SADL; para SSEQ utiliza musica(nombre, segundos)')
