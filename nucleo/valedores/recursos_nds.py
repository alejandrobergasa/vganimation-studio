"""Extracción base de Nintendo DS: originales, contenedores y recursos verificables.

No es un motor de vídeo ni reconstruye formatos gráficos propietarios. Cada
recurso mantiene su procedencia y los límites de la conversión en catalogo.json.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import wave

import ndspy.narc
import ndspy.rom
import ndspy.soundArchive
import numpy as np
from PIL import Image, ImageDraw

from . import nitro, rutas


ALCANCE = ('Extracción base: archivos originales NitroFS, contenedores compatibles, '
           'texturas Nitro, fuentes NFTR, fondos de Layton y muestras de sonido SDAT. '
           'Los formatos propietarios pendientes se conservan sin convertir. '
           'No incluye un motor de cinemáticas ni convierte música SSEQ a WAV.')
MAGIAS = {b'BMD0': 'modelo Nitro', b'BTX0': 'texturas Nitro', b'BCA0': 'animación Nitro',
          b'BTP0': 'animación de texturas', b'BTA0': 'animación de materiales',
          b'BMA0': 'animación de materiales', b'RGCN': 'tiles Nitro',
          b'RLCN': 'paleta Nitro', b'RECN': 'celdas Nitro', b'RCSN': 'mapa Nitro',
          b'RNAN': 'animación 2D Nitro', b'RTFN': 'fuente NFTR',
          b'SDAT': 'banco SDAT', b'NARC': 'contenedor NARC',
          b'sadl': 'audio SADL (pendiente)', b'MODS': 'vídeo MODS (pendiente)'}


def _modulo(nombre, fichero):
    spec = importlib.util.spec_from_file_location(nombre, fichero)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def lectores():
    """Reutiliza los lectores existentes, sin necesitar la ROM ni assets de NSMB."""
    base = Path(rutas.juego_dir('nsmb')) / 'tools' / 'nsmb'
    return (_modulo('nds_graficos', base / 'ndsgfx.py'),
            _modulo('nds_fuente', base / 'nftr.py'),
            _modulo('nds_sonido', base / 'sonido.py'))


def nombre_seguro(nombre):
    """Nombre portable; los ids del catálogo evitan colisiones entre archivos."""
    limpio = re.sub(r'[^\w.\-]', '_', nombre, flags=re.UNICODE).strip('. ')[:90] or 'recurso'
    return '_' + limpio


def fondo_layton(datos):
    """Paleta BGR555, tiles 8x8 de 8 bpp y mapa con flips horizontales/verticales."""
    if len(datos) < 12:
        raise ValueError('Fondo truncado')
    nc = nitro.u32(datos)
    if not 1 <= nc <= 256 or 4 + 2 * nc + 4 > len(datos):
        raise ValueError('Paleta del fondo no válida')
    pal = np.frombuffer(datos, '<u2', nc, 4)
    colores = np.stack(((pal & 31) * 255 // 31, (pal >> 5 & 31) * 255 // 31,
                        (pal >> 10 & 31) * 255 // 31, np.full(nc, 255)), axis=1).astype('uint8')
    p = 4 + nc * 2
    nt = nitro.u32(datos, p)
    p += 4
    if not 0 < nt <= 65536 or p + 64 * nt + 4 > len(datos):
        raise ValueError('Tiles del fondo fuera de límites')
    tiles = np.frombuffer(datos, 'uint8', nt * 64, p).reshape(nt, 8, 8)
    p += 64 * nt
    w, h = struct.unpack_from('<HH', datos, p)
    p += 4
    if not 0 < w <= 128 or not 0 < h <= 128 or p + 2 * w * h > len(datos):
        raise ValueError('Mapa del fondo fuera de límites')
    salida = np.zeros((h * 8, w * 8, 4), dtype='uint8')
    for i, e in enumerate(np.frombuffer(datos, '<u2', w * h, p)):
        t = int(e) & 1023
        if t >= nt or np.max(tiles[t]) >= nc:
            raise ValueError('Índice del fondo fuera de límites')
        imagen = tiles[t]
        if e & 1024:
            imagen = imagen[:, ::-1]
        if e & 2048:
            imagen = imagen[::-1]
        y, x = divmod(i, w)
        salida[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = colores[imagen]
    return Image.fromarray(salida)


def miembros(juego, nombre, datos, buscar):
    """(tipo, entradas) o (None, []); cada entrada contiene nombre, offset y bytes."""
    bajo = nombre.lower()
    if datos.startswith(b'NARC'):
        ar = ndspy.narc.NARC(datos)
        return 'NARC', [(ar.filenames.filenameOf(i) or '%05d.bin' % i, None, bytes(d))
                        for i, d in enumerate(ar.files)]
    if juego == 'inazuma-eleven' and bajo.endswith('.pkb'):
        cab = buscar(nombre[:-4] + '.pkh')
        return 'PKB/PKH', nitro.paquete_inazuma(cab, datos)
    if juego == 'phoenix-wright-3' and bajo == 'mes_all.bin':
        return 'mes_all', nitro.scripts_phoenix(datos)
    if juego == 'inazuma-eleven' and bajo.endswith(('.pac', '.pac_')):
        lista = nitro.tabla_pares(datos)
        if lista is not None:
            return 'PAC', lista
    if juego == 'mario-party-ds' and bajo.endswith('.bin'):
        # El offset del archivo se mide desde el byte posterior al contador.
        lista = nitro.tabla_pares(datos, relativo=4)
        if lista is not None:
            return 'archivo Mario Party', lista
    return None, []


class Extractor:
    def __init__(self, juego, rom, salida, rapido=False):
        self.juego = juego
        self.rom = rom
        self.salida = Path(salida)
        self.rapido = rapido
        self.gfx, self.fuentes, self.sonido = lectores()
        self.registros = []
        self.avisos = []
        self.imagenes = []
        self.errores = []

    def escribir(self, relativo, datos):
        p = self.salida / relativo
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(datos)
        return relativo

    def imagen(self, relativo, imagen, registro):
        p = self.salida / relativo
        p.parent.mkdir(parents=True, exist_ok=True)
        imagen.save(p)
        registro['derivados'].append(relativo)
        self.imagenes.append(relativo)

    def aviso(self, registro, mensaje, error=False):
        registro['avisos'].append(mensaje)
        self.avisos.append('%s: %s' % (registro['origen'], mensaje))
        if error:
            self.errores.append(self.avisos[-1])

    def convertir(self, datos, base, registro):
        magia = datos[:4]
        if magia in (b'BMD0', b'BTX0'):
            seccion = self.gfx.find_tex0(datos)
            esperadas = seccion[struct.unpack_from('<H', seccion, 0xE)[0] + 1] if seccion else 0
            texturas = self.gfx.decode_textures(datos)
            for i, (nombre, paleta, im) in enumerate(texturas):
                dest = '%s/texturas/%03d%s.png' % (base, i, nombre_seguro(nombre))
                self.imagen(dest, im, registro)
            if texturas:
                self.aviso(registro, 'Paletas de texturas elegidas por el lector Nitro; revisar visualmente.')
            if len(texturas) != esperadas:
                self.aviso(registro, 'El bloque TEX0 produjo %d/%d texturas; requiere revisión.' %
                           (len(texturas), esperadas), error=True)
        elif magia == b'RTFN':
            f = self.fuentes.Font(datos)
            if f.depth not in (1, 2) or f.rot:
                self.aviso(registro, 'NFTR con profundidad/rotación pendiente; se conserva el original.')
                return
            ancho, alto = 32 * (f.tw + 2), ((f.nglyphs + 31) // 32) * (f.th + 2)
            if not 0 < ancho * alto <= 32 * 1024 * 1024:
                raise ValueError('Atlas de fuente fuera de límites')
            atlas = Image.new('RGBA', (ancho, alto))
            for i in range(f.nglyphs):
                alpha = (f.glyph(i).astype('uint16') * 255 // ((1 << f.depth) - 1)).astype('uint8')
                glifo = Image.new('RGBA', (f.tw, f.th), 'white')
                glifo.putalpha(Image.fromarray(alpha))
                atlas.paste(glifo, ((i % 32) * (f.tw + 2), (i // 32) * (f.th + 2)))
            self.imagen(base + '/fuente.png', atlas, registro)
            mapa = {'ancho': f.tw, 'alto': f.th, 'columnas': 32, 'separacion': 2,
                    'codificacion_nftr': f.enc, 'mapa_codigos': f.cmap, 'anchos': f.widths}
            registro['derivados'].append(self.escribir(base + '/fuente.json',
                json.dumps(mapa, ensure_ascii=False, indent=2).encode('utf-8')))
        elif magia == b'SDAT':
            self.audio(datos, base, registro)
        elif self.juego == 'profesor-layton' and '/bg/' in registro['origen'].lower():
            self.imagen(base + '/fondo.png', fondo_layton(datos), registro)

    def audio(self, datos, base, registro):
        banco = ndspy.soundArchive.SDAT(datos)
        catalogo = {}
        tipos = [('secuencias', 'sequences', 'sseq'), ('bancos', 'banks', 'sbnk'),
                 ('muestras', 'waveArchives', 'swar'), ('efectos', 'sequenceArchives', 'ssar'),
                 ('streams', 'streams', 'strm')]
        for etiqueta, atributo, extension in tipos:
            catalogo[etiqueta] = []
            for i, (nombre, obj) in enumerate(getattr(banco, atributo)):
                if obj is None:
                    continue
                cat = {'id': i, 'nombre': nombre}
                catalogo[etiqueta].append(cat)
                guardado = obj.save()
                if isinstance(guardado, tuple):
                    guardado = guardado[0]
                dest = '%s/audio/%s/%04d%s.%s' % (base, etiqueta, i, nombre_seguro(nombre or ''), extension)
                cat['archivo'] = self.escribir(dest, guardado)
                registro['derivados'].append(dest)
        muestras = self.sonido.Banco(banco)
        for i, (nombre, ar) in enumerate(banco.waveArchives):
            if ar is None:
                continue
            limite = min(4, len(ar.waves)) if self.rapido else len(ar.waves)
            for k in range(limite):
                try:
                    s, frecuencia, bucle = muestras.muestra(i, k)
                    pcm = (np.clip(s, -1, 1) * 32767).astype('<i2')
                    if not len(pcm) or not 1000 <= frecuencia <= 192000:
                        raise ValueError('Duración o frecuencia de muestra no válida')
                    dest = '%s/audio/wav/%04d_%04d.wav' % (base, i, k)
                    p = self.salida / dest
                    p.parent.mkdir(parents=True, exist_ok=True)
                    with wave.open(str(p), 'wb') as wav:
                        wav.setnchannels(1)
                        wav.setsampwidth(2)
                        wav.setframerate(round(frecuencia))
                        wav.writeframes(pcm.tobytes())
                    registro['derivados'].append(dest)
                    catalogo.setdefault('wav', []).append({'archivo': dest, 'segundos': len(s) / frecuencia,
                        'pico': float(np.max(np.abs(s))), 'bucle_muestra': bucle})
                except (ValueError, IndexError, struct.error) as exc:
                    self.aviso(registro, 'Muestra %d/%d: %s' % (i, k, exc), error=True)
        dest = base + '/audio/catalogo.json'
        registro['derivados'].append(self.escribir(dest,
            json.dumps(catalogo, ensure_ascii=False, indent=2).encode('utf-8')))
        self.aviso(registro, 'SSEQ/SSAR conservados como secuencias; los WAV son muestras de instrumentos, no canciones.')

    def recurso(self, nombre, datos, base, origen, buscar, profundidad=0):
        registro = {'origen': origen, 'nombre': nombre, 'bytes': len(datos),
                    'sha256': hashlib.sha256(datos).hexdigest(), 'derivados': [], 'avisos': []}
        self.registros.append(registro)
        extension = re.sub(r'[^A-Za-z0-9_.]', '_', Path(nombre).suffix)[:24]
        registro['original'] = self.escribir(base + '/original' + extension, datos)
        bajo = nombre.lower()
        datos = bytes(datos)
        # PKB y data.bin contienen varios flujos; no son un único bloque LZ.
        contenedor = bajo.endswith('.pkb') or (self.juego == 'phoenix-wright-3' and bajo == 'data.bin')
        envuelto = datos.startswith(b'LZ77') or (self.juego == 'profesor-layton'
                   and bajo.endswith(('.arc', '.arj', '.bgx')))
        intentar = not contenedor and (envuelto or (len(datos) >= 4 and datos[0] in (0x10, 0x11, 0x30)))
        if intentar:
            try:
                contenido, metodo = nitro.descomprimir(datos, level5=self.juego == 'profesor-layton')
                if metodo:
                    datos = contenido
                    registro['compresion'] = metodo
                    registro['derivados'].append(self.escribir(base + '/descomprimido.bin', datos))
            except ValueError as exc:
                # Firmas de un byte también pueden ser datos sin comprimir.
                if envuelto or bajo.endswith(('.pac_', '.nsbmd_')):
                    self.aviso(registro, str(exc), error='no compatible' not in str(exc))
                    registro['tipo'] = 'compresión pendiente o dañada'
                    return
        registro['tipo'] = MAGIAS.get(datos[:4], 'binario propietario o datos sin cabecera')
        try:
            tipo, entradas = miembros(self.juego, nombre, datos, buscar)
            if tipo:
                registro['tipo'] = tipo
                registro['miembros'] = len(entradas)
                if profundidad >= 6:
                    self.aviso(registro, 'Límite de anidamiento alcanzado; original conservado.', error=True)
                    return
                seleccion = entradas[:16] if self.rapido else entradas
                for i, (n, offset, d) in enumerate(seleccion):
                    self.recurso(n, d, '%s/miembros/%05d' % (base, i),
                                 origen + '::' + n, buscar, profundidad + 1)
                return
            self.convertir(datos, base, registro)
        except (ValueError, KeyError, IndexError, struct.error, AssertionError, OverflowError) as exc:
            self.aviso(registro, '%s: %s' % (type(exc).__name__, exc), error=True)

    def ejecutar(self):
        archivos = [(i, self.rom.filenames.filenameOf(i), d) for i, d in enumerate(self.rom.files)]
        # Los ficheros sin nombre suelen ser overlays; también se conservan.
        if self.rapido:
            con_nombre = [x for x in archivos if x[1]]
            prioritarios = [x for x in con_nombre if x[1].lower().endswith(('.nftr', '.sdat', '.narc', '.pkb'))
                           or '/bg/' in x[1].lower()]
            ids = {x[0] for x in prioritarios[:16] + con_nombre[:16]}
            archivos = [x for x in archivos if x[0] in ids]
        for n, (i, nombre, datos) in enumerate(archivos, 1):
            nombre = nombre or '_sin_nombre/%05d.bin' % i
            self.recurso(nombre, datos, 'archivos/%05d' % i, nombre, self.rom.getFileByName)
            if n % 100 == 0:
                print('  %d/%d archivos de la ROM' % (n, len(archivos)), flush=True)
        resumen = dict(Counter(r['tipo'] for r in self.registros))
        catalogo = {'juego': self.juego, 'codigo': bytes(self.rom.idCode).decode('ascii'),
                    'alcance': ALCANCE, 'rapido': self.rapido, 'total_nitrofs': len(self.rom.files),
                    'archivos_nitrofs_procesados': len(archivos), 'tipos': resumen,
                    'errores': self.errores, 'recursos': self.registros}
        self.escribir('catalogo.json', json.dumps(catalogo, ensure_ascii=False, indent=2).encode('utf-8'))
        self.escribir('avisos.log', ('\n'.join(self.avisos) + '\n').encode('utf-8'))
        self.escribir('errores.log', ('\n'.join(self.errores) + '\n').encode('utf-8'))
        if self.imagenes:
            self.hoja()
        nombre = rutas.manifiesto(self.juego)['nombre']
        texto = ('# %s — recursos\n\n%s\n\n' % (nombre, ALCANCE)
                 + ('**Muestra parcial (--rapido).**\n\n' if self.rapido else '')
                 + '%d/%d archivos NitroFS procesados; %d recursos incluidos los miembros.\n\n' % (
                     len(archivos), len(self.rom.files), len(self.registros))
                 + '- `archivos/<id>/original.*`: bytes originales; nombres y procedencia en `catalogo.json`.\n'
                 + '- `descomprimido.bin` y `miembros/`: contenedores abiertos sin cambiar el original.\n'
                 + '- `texturas/`, `fuente.png`, `fondo.png`: conversiones gráficas compatibles.\n'
                 + '- `audio/`: bancos nativos y muestras WAV; no son canciones renderizadas.\n'
                 + '- `catalogo.json`, `avisos.log`, `errores.log`: cobertura y problemas por recurso.\n\n'
                 + 'Consulta CONOCIMIENTO.md del juego para los formatos pendientes. '
                 + 'Revisa los PNG a tamaño real antes de usarlos. '
                 + 'Una extracción base terminada no implica que todos los binarios tengan decodificador.\n')
        self.escribir('README.md', texto.encode('utf-8'))
        print('%d recursos; %d imágenes; %d avisos; %d errores.' % (
            len(self.registros), len(self.imagenes), len(self.avisos), len(self.errores)), flush=True)
        return not self.errores

    def hoja(self):
        # Una hoja limitada evita imágenes de cientos de megapíxeles.
        seleccion = self.imagenes[:60]
        im = Image.new('RGB', (640, ((len(seleccion) + 3) // 4) * 140), '#222222')
        dibujar = ImageDraw.Draw(im)
        for i, relativo in enumerate(seleccion):
            with Image.open(self.salida / relativo) as recurso:
                mini = recurso.convert('RGBA')
            mini.thumbnail((152, 112), Image.Resampling.NEAREST)
            x, y = (i % 4) * 160, (i // 4) * 140
            im.paste(mini, (x + (160 - mini.width) // 2, y), mini)
            dibujar.text((x + 4, y + 115), relativo[:8] + '/' + relativo.split('/')[-1][:16], fill='white')
        im.save(self.salida / 'hoja.png')


def principal(juego, argv=None):
    ap = argparse.ArgumentParser(description='Extrae recursos base de ' + rutas.manifiesto(juego)['nombre'])
    ap.add_argument('--rom', default=None)
    ap.add_argument('--salida', default=None)
    ap.add_argument('--rapido', action='store_true', help='muestra parcial de archivos y miembros')
    args = ap.parse_args(argv)
    rom = ndspy.rom.NintendoDSRom.fromFile(args.rom or rutas.rom(juego))
    codigo = bytes(rom.idCode).decode('ascii')
    if codigo not in rutas.manifiesto(juego)['rom']['codigos']:
        ap.error('La ROM %s no corresponde a %s' % (codigo, juego))
    extractor = Extractor(juego, rom, args.salida or rutas.extraidos(juego), args.rapido)
    print(ALCANCE, flush=True)
    return 0 if extractor.ejecutar() else 1
