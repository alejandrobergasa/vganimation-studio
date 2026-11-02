"""Interfaz de Mario Party DS: gráficos 2D nativos, fuente y elementos animados en pantalla.

Formatos deducidos de la ROM A8TP (dentro de los contenedores `data/**_data_LZ.bin`):

    Paleta:  u16 bytes, u16 colores, BGR555...
    Tiles:   [u32 tamaño<<8,] u32 tiles<<8 | profundidad (0 = 4 bpp, 1 = 8 bpp), píxeles
    Mapa:    u32 tamaño<<8, u16 bytes, u8 ancho, u8 alto, entradas u16 de BG
    Celdas:  u32 n, n offsets (desde el byte 4); cada celda: u16 piezas, y por pieza atributos OAM
             (3 u16) y x, y (s16). Son los sprites compuestos del juego (marcadores, carteles, iconos).

Los elementos con animación (`Dialogo`, `Cartel`, `Contador`...) tienen `frame(t)`: se colocan con
`plano.sprite(elemento, pantalla=True, ...)` como cualquier capa.
"""
from functools import lru_cache
import struct

import numpy as np
from PIL import Image

from valedores import rutas

_TAM_OAM = {
    0: ((8, 8), (16, 16), (32, 32), (64, 64)),
    1: ((16, 8), (32, 8), (32, 16), (64, 32)),
    2: ((8, 16), (8, 32), (16, 32), (32, 64)),
}


def clasificar(d):
    """Tipo de un miembro 2D por su estructura: paleta, tiles, mapa, celdas, otro."""
    if len(d) < 8 or d[:4] in (b'HBDF', b'HSDF'):
        return 'otro'
    a, b = struct.unpack_from('<HH', d)
    if a == len(d) - 4 and b * 2 == a and a <= 512:
        return 'paleta'
    h = struct.unpack_from('<I', d)[0]
    if (h >> 8) + 4 == len(d) and h & 255 == 0:
        tam, w, alto = struct.unpack_from('<HBB', d, 4)
        if w and alto and w * alto * 2 == tam:
            return 'mapa'
        seg = struct.unpack_from('<I', d, 4)[0]
        if seg & 255 in (0, 1) and (seg >> 8) * (64 if seg & 1 else 32) + 8 == len(d):
            return 'tiles'
    if h & 255 in (0, 1) and (h >> 8) * (64 if h & 1 else 32) + 4 == len(d):
        return 'tiles'
    if 0 < h <= 2048 and 4 + h * 4 <= len(d):
        off = struct.unpack_from('<%dI' % h, d, 4)
        if off[0] == h * 4 and all(x <= y for x, y in zip(off, off[1:])) and off[-1] < len(d):
            n = struct.unpack_from('<H', d, 4 + off[0])[0]
            siguiente = off[1] if h > 1 else len(d) - 4
            if 0 < n <= 128 and siguiente - off[0] == 2 + n * 10:
                return 'celdas'
    return 'otro'


def paleta(d):
    """Colores RGBA (n, 4); el índice 0 es transparente."""
    colores = np.frombuffer(d, '<u2', offset=4)
    c = np.zeros((len(colores), 4), np.uint8)
    c[:, 0] = (colores & 31) * 255 // 31
    c[:, 1] = (colores >> 5 & 31) * 255 // 31
    c[:, 2] = (colores >> 10 & 31) * 255 // 31
    c[:, 3] = 255
    c[0, 3] = 0
    return c


def tiles(d):
    """(array de índices (n, 8, 8), profundidad)."""
    h = struct.unpack_from('<I', d)[0]
    if (h >> 8) + 4 == len(d) and h & 255 == 0 and len(d) >= 8:
        seg = struct.unpack_from('<I', d, 4)[0]
        if seg & 255 in (0, 1) and (seg >> 8) * (64 if seg & 1 else 32) + 8 == len(d):
            h, cuerpo = seg, d[8:]
        else:
            cuerpo = d[4:]
    else:
        cuerpo = d[4:]
    v = np.frombuffer(cuerpo, np.uint8)
    if h & 1:
        return v[:len(v) // 64 * 64].reshape(-1, 8, 8), 8
    return np.stack((v & 15, v >> 4), 1).reshape(-1)[:len(v) * 2 // 64 * 64].reshape(-1, 8, 8), 4


def pantalla(d_mapa, d_tiles, d_paleta):
    """Imagen de un mapa de BG con sus tiles y paleta."""
    tam, w, h = struct.unpack_from('<HBB', d_mapa, 4)
    m = np.frombuffer(d_mapa, '<u2', count=w * h, offset=8)
    t, prof = tiles(d_tiles)
    c = paleta(d_paleta)
    salida = np.zeros((h * 8, w * 8, 4), np.uint8)
    for i, e in enumerate(m):
        e = int(e)
        n = e & 1023
        if n >= len(t):
            continue
        ind = t[n]
        if e & 1024:
            ind = ind[:, ::-1]
        if e & 2048:
            ind = ind[::-1]
        if prof == 4:
            ind = ind.astype(np.int32) + (e >> 12) * 16
        y, x = divmod(i, w)
        ind = np.where(ind % (16 if prof == 4 else 256) == 0, 0, ind)
        salida[y * 8:y * 8 + 8, x * 8:x * 8 + 8] = c[np.minimum(ind, len(c) - 1)]
    return Image.fromarray(salida)


def celdas(d_celdas, d_tiles, d_paleta, mapeo=None):
    """Lista de imágenes RGBA, una por celda, con sus anclas: [(imagen, (x, y) del origen)]."""
    n = struct.unpack_from('<I', d_celdas)[0]
    off = struct.unpack_from('<%dI' % n, d_celdas, 4)
    t, prof = tiles(d_tiles)
    c = paleta(d_paleta)
    piezas_todas = []
    for o in off:
        q = 4 + o
        np_ = struct.unpack_from('<H', d_celdas, q)[0]
        piezas = []
        for k in range(np_):
            a0, a1, a2, x, y = struct.unpack_from('<HHHhh', d_celdas, q + 2 + k * 10)
            forma, tam = a0 >> 14, a1 >> 14
            if forma == 3:
                continue
            w, h = _TAM_OAM[forma][tam]
            piezas.append((x, y, w, h, a2 & 1023, a2 >> 12, bool(a1 & 0x1000), bool(a1 & 0x2000), a2 >> 10 & 3))
        piezas_todas.append(piezas)
    # El paso entre tiles (32, 64, 128 bytes) no se guarda: se toma el menor que cubra todas las piezas.
    if mapeo is None:
        necesario = max((p[4] + p[2] * p[3] // 64 for ps in piezas_todas for p in ps), default=0)
        mapeo = 1
        while mapeo < 16 and max((p[4] * mapeo + p[2] * p[3] // 64 for ps in piezas_todas for p in ps), default=0) < len(t) // 2 and necesario * mapeo * 2 < len(t):
            mapeo *= 2
    salida = []
    for piezas in piezas_todas:
        if not piezas:
            salida.append((Image.new('RGBA', (1, 1)), (0, 0)))
            continue
        x0, y0 = min(p[0] for p in piezas), min(p[1] for p in piezas)
        x1, y1 = max(p[0] + p[2] for p in piezas), max(p[1] + p[3] for p in piezas)
        lienzo = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        for x, y, w, h, tile, banco, hflip, vflip, _prio in reversed(piezas):
            ind = np.zeros((h, w), np.int32)
            k = tile * mapeo
            for fy in range(h // 8):
                for fx in range(w // 8):
                    if k < len(t):
                        ind[fy * 8:fy * 8 + 8, fx * 8:fx * 8 + 8] = t[k]
                    k += 1
            if hflip:
                ind = ind[:, ::-1]
            if vflip:
                ind = ind[::-1]
            opaco = ind != 0
            if prof == 4:
                ind = ind + banco * 16
            col = c[np.minimum(ind, len(c) - 1)]
            reg = lienzo[y - y0:y - y0 + h, x - x0:x - x0 + w]
            reg[opaco] = col[opaco]
            reg[opaco, 3] = 255
        salida.append((Image.fromarray(lienzo), (-x0, -y0)))
    return salida


class Banco2D:
    """Un contenedor de la ROM visto como colección de pantallas y sprites, con su catálogo."""

    def __init__(self, rec, contenedor):
        self.rec, self.contenedor = rec, contenedor
        self.miembros = sorted(o for o in rec.registros if o.startswith(contenedor + '::') and o.count('::') == contenedor.count('::') + 1)
        if not self.miembros:
            raise ValueError('El contenedor no tiene miembros: ' + contenedor)
        self.tipos = [clasificar(rec.datos(m)) for m in self.miembros]

    def _anterior(self, i, tipo):
        for k in range(i - 1, -1, -1):
            if self.tipos[k] == tipo:
                return k
        return None

    def _posterior(self, i, tipo, hasta=3):
        for k in range(i + 1, min(i + 1 + hasta, len(self.tipos))):
            if self.tipos[k] == tipo:
                return k
        return None

    def sprites(self, i, paleta_i=None, tiles_i=None, mapeo=None):
        """Sprites de las celdas del miembro `i`: lista de (imagen RGBA, origen)."""
        if self.tipos[i] != 'celdas':
            raise ValueError('El miembro %d no contiene celdas' % i)
        ti = self._anterior(i, 'tiles') if tiles_i is None else tiles_i
        pa = self._anterior(ti, 'paleta') if paleta_i is None else paleta_i
        if ti is None or pa is None:
            raise ValueError('No se han localizado tiles o paleta para las celdas %d' % i)
        d = self.rec.datos
        return celdas(d(self.miembros[i]), d(self.miembros[ti]), d(self.miembros[pa]), mapeo)

    def fondo(self, i, paleta_i=None, tiles_i=None):
        """Pantalla del mapa del miembro `i`."""
        if self.tipos[i] != 'mapa':
            raise ValueError('El miembro %d no es un mapa' % i)
        ti = tiles_i if tiles_i is not None else (self._posterior(i, 'tiles') or self._anterior(i, 'tiles'))
        pa = paleta_i if paleta_i is not None else (self._posterior(i, 'paleta') or self._anterior(ti, 'paleta'))
        if ti is None or pa is None:
            raise ValueError('No se han localizado tiles o paleta para el mapa %d' % i)
        d = self.rec.datos
        return pantalla(d(self.miembros[i]), d(self.miembros[ti]), d(self.miembros[pa]))

    def hoja(self, ancho=1200, escala=2, fondo=(58, 72, 110)):
        """Hoja de contactos con todos los fondos y sprites, rotulada con (miembro, celda)."""
        from PIL import ImageDraw
        filas = []
        for i, tipo in enumerate(self.tipos):
            try:
                if tipo == 'celdas':
                    filas.extend((f'{i}.{k}', im) for k, (im, _o) in enumerate(self.sprites(i)) if im.getbbox())
                elif tipo == 'mapa':
                    filas.append((f'{i}', self.fondo(i)))
            except (ValueError, IndexError, struct.error) as e:
                filas.append((f'{i}!{e}'[:18], Image.new('RGBA', (8, 8), (255, 0, 0, 255))))
        x, y, alto_fila = 4, 4, 0
        colocados = []
        for rotulo, im in filas:
            w, h = im.width * escala, im.height * escala
            if x + max(w, 42) > ancho:
                x, y, alto_fila = 4, y + alto_fila + 16, 0
            colocados.append((rotulo, im, x, y))
            x += max(w, 42) + 8
            alto_fila = max(alto_fila, h)
        lienzo = Image.new('RGBA', (ancho, y + alto_fila + 20), (*fondo, 255))
        dib = ImageDraw.Draw(lienzo)
        for rotulo, im, x, y in colocados:
            lienzo.alpha_composite(im.resize((im.width * escala, im.height * escala), Image.Resampling.NEAREST), (x, y + 11))
            dib.text((x, y), rotulo, fill=(255, 255, 160))
        return lienzo.convert('RGB')


# ------------------------------------------------------------------ fuente

@lru_cache(maxsize=1)
def _arm9():
    import ndspy.code
    import ndspy.rom
    rom = ndspy.rom.NintendoDSRom.fromFile(rutas.rom('mario-party-ds'))
    return bytes(ndspy.code.MainCodeFile(rom.arm9, rom.arm9RamAddress, rom.arm9CodeSettingsPointerAddress).save(compress=False))


OFFSET_FUENTE = 539456     # ' ' de la fuente 8×8 del ejecutable (A8TP): 96 glifos ASCII a 4 bpp
ACENTOS = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
           'ñ': 'n', 'Ñ': 'N', 'ü': 'u', 'Ü': 'U'}


class Fuente8:
    """Fuente de 8×8 que el juego lleva en su ejecutable: ASCII de 95 glifos.

    Las tildes, la ñ y los signos ¡¿ no existen en ella: se componen con píxeles de sus propios glifos."""

    def __init__(self, datos=None, espacio=1):
        d = _arm9() if datos is None else datos
        v = np.frombuffer(d, np.uint8, count=96 * 32, offset=OFFSET_FUENTE if datos is None else 0)
        self.glifos = (np.stack((v & 15, v >> 4), 1).reshape(-1, 8, 8) > 0)
        self.espacio = espacio

    def _glifo(self, c):
        if c in ACENTOS:
            g = self._glifo(ACENTOS[c]).copy()
            arriba = np.argmax(g.any(1))
            # Las mayúsculas llenan la celda: se baja la letra para hacer sitio a la tilde.
            if arriba < 2:
                g = np.vstack([np.zeros((2 - arriba, 8), bool), g[:8 - (2 - arriba)]])
                arriba = 2
            cols = np.flatnonzero(g.any(0))
            medio = (cols[0] + cols[-1] + 1) // 2 if len(cols) else 4
            fila = max(0, arriba - 2)
            if c in 'ñÑ':
                g[fila, max(0, medio - 2):min(8, medio + 2)] = True
            elif c in 'üÜ':
                g[fila, max(0, medio - 2)] = g[fila, min(7, medio + 1)] = True
            else:
                g[fila, min(7, medio)] = True
                if fila > 0:
                    g[fila - 1, min(7, medio + 1)] = True
            return g
        if c == '¡':
            return self._glifo('!')[::-1]
        if c == '¿':
            return self._glifo('?')[::-1, ::-1]
        o = ord(c) - 32
        if not 0 <= o < 96:
            raise ValueError('La fuente del juego no contiene el carácter %r' % c)
        return self.glifos[o]

    def ancho(self, texto):
        w = 0
        for c in texto:
            w += self._avance(c)
        return max(0, w - self.espacio)

    def _avance(self, c):
        if c == ' ':
            return 4 + self.espacio
        g = self._glifo(c)
        cols = np.flatnonzero(g.any(0))
        return (cols[-1] - cols[0] + 1 if len(cols) else 3) + self.espacio

    def texto(self, texto, escala=2, color=(255, 255, 255), sombra=(40, 40, 60), ancho=None, centrado=False, interlinea=2):
        """Imagen RGBA del texto; `\\n` separa líneas. Con `ancho` (en píxeles finales) reparte palabras."""
        lineas = []
        for parrafo in texto.split('\n'):
            if ancho is None:
                lineas.append(parrafo)
                continue
            limite = ancho / escala
            actual = ''
            for palabra in parrafo.split(' '):
                prueba = (actual + ' ' + palabra) if actual else palabra
                if self.ancho(prueba) > limite and actual:
                    lineas.append(actual)
                    actual = palabra
                else:
                    actual = prueba
            lineas.append(actual)
        W = max(1, max(self.ancho(l) for l in lineas)) + 1
        H = len(lineas) * (8 + interlinea) + 1
        tinta = np.zeros((H, W), bool)
        for fila, linea in enumerate(lineas):
            x = (W - 1 - self.ancho(linea)) // 2 if centrado else 0
            for c in linea:
                if c != ' ':
                    g = self._glifo(c)
                    cols = np.flatnonzero(g.any(0))
                    if len(cols):
                        recorte = g[:, cols[0]:cols[-1] + 1]
                        tinta[fila * (8 + interlinea):fila * (8 + interlinea) + 8, x:x + recorte.shape[1]] |= recorte
                x += self._avance(c)
        rgba = np.zeros((H, W, 4), np.uint8)
        if sombra is not None:
            s = np.zeros_like(tinta)
            s[1:, 1:] = tinta[:-1, :-1]
            rgba[s] = (*sombra, 255)
        rgba[tinta] = (*color, 255)
        im = Image.fromarray(rgba)
        return im.resize((W * escala, H * escala), Image.Resampling.NEAREST)


# ------------------------------------------------------------------ elementos en pantalla

def caja(w, h, relleno=(248, 244, 214), borde=(62, 54, 110), borde2=(255, 255, 255), escala=3, alfa=255):
    """Ventana con esquinas recortadas al estilo de las del juego; w y h en píxeles finales."""
    w0, h0 = max(8, w // escala), max(8, h // escala)
    a = np.zeros((h0, w0, 4), np.uint8)
    a[...] = (*relleno, alfa)
    a[:2], a[-2:], a[:, :2], a[:, -2:] = (*borde, 255), (*borde, 255), (*borde, 255), (*borde, 255)
    a[2], a[-3], a[:, 2], a[:, -3] = (*borde2, 255), (*borde2, 255), (*borde2, 255), (*borde2, 255)
    for dy, dx in ((0, 0), (0, 1), (1, 0)):
        for fy in (dy, h0 - 1 - dy):
            for fx in (dx, w0 - 1 - dx):
                a[fy, fx, 3] = 0
    return Image.fromarray(a).resize((w0 * escala, h0 * escala), Image.Resampling.NEAREST)


class Dialogo:
    """Caja de diálogo con texto que se escribe letra a letra y nombre del personaje.

    `sonido_letras(video, audio, ...)` coloca el «tecleo» en los mismos instantes."""

    def __init__(self, fuente, texto, tamano=(1000, 190), nombre=None, cps=24, escala=3, color=(52, 44, 96),
                 color_nombre=(255, 255, 255), fondo_nombre=(205, 40, 40), retrato=None, duracion=None, entrada=0.15):
        self.fuente, self.texto_total, self.tamano, self.cps = fuente, texto, tamano, cps
        self.escala, self.color, self.entrada, self.duracion = escala, color, entrada, duracion
        self.retrato = retrato.convert('RGBA') if retrato is not None else None
        margen_x = 8 * escala + (self.retrato.width + 8 * escala if self.retrato else 0)
        self.margen = (margen_x, 8 * escala)
        self.ancho_texto = tamano[0] - margen_x - 8 * escala
        # El reparto en líneas se hace una vez para que las palabras no salten mientras se escriben.
        self.lineas = self._repartir(texto)
        ventana = caja(tamano[0], tamano[1], escala=escala)
        self.alto_nombre = 0
        if nombre:
            rot = fuente.texto(nombre, escala=escala, color=color_nombre, sombra=None)
            self.alto_nombre = rot.height + 4 * escala
            base = Image.new('RGBA', (tamano[0], tamano[1] + self.alto_nombre - 2 * escala))
            base.alpha_composite(ventana, (0, self.alto_nombre - 2 * escala))
            eti = caja(rot.width + 12 * escala, rot.height + 6 * escala, relleno=fondo_nombre, borde=(90, 10, 20), borde2=fondo_nombre, escala=escala, alfa=255)
            base.alpha_composite(eti, (6 * escala, 0))
            base.alpha_composite(rot, (12 * escala, 3 * escala))
            ventana = base
        if self.retrato is not None:
            ventana = ventana.copy()
            ventana.alpha_composite(self.retrato, (8 * escala, self.alto_nombre + (tamano[1] - self.retrato.height) // 2 - escala))
        self.ventana = ventana
        self._memo = {}

    def _repartir(self, texto):
        lim = self.ancho_texto / self.escala
        salida = []
        for parrafo in texto.split('\n'):
            actual = ''
            for p in parrafo.split(' '):
                prueba = (actual + ' ' + p) if actual else p
                if self.fuente.ancho(prueba) > lim and actual:
                    salida.append(actual)
                    actual = p
                else:
                    actual = prueba
            salida.append(actual)
        return salida

    @property
    def fin_escritura(self):
        return self.entrada + sum(len(l) for l in self.lineas) / self.cps

    def instantes_letra(self, cada=2):
        """Segundos, relativos al inicio, en los que suena una letra (omite los espacios)."""
        t, salida, n = self.entrada, [], 0
        for l in self.lineas:
            for c in l:
                if c != ' ':
                    n += 1
                    if n % cada == 0:
                        salida.append(t)
                t += 1 / self.cps
        return salida

    def sonar_letras(self, video, efecto, desde=0.0, plano=None, volumen=0.5, cada=2):
        """Coloca el sonido de tecleo: `efecto` = rec.efecto(nombre)."""
        for i in self.instantes_letra(cada):
            video.sonido(efecto, desde=desde + i, plano=plano, volumen=volumen)

    def frame(self, t):
        if self.duracion is not None and t >= self.duracion:
            return Image.new('RGBA', self.ventana.size)
        k = 1.0 if self.entrada <= 0 else min(1.0, t / self.entrada)
        n = max(0, int((t - self.entrada) * self.cps))
        clave = (n, k >= 1)
        if clave not in self._memo:
            im = self.ventana.copy()
            alto_linea = (8 + 2) * self.escala
            resto = n
            for i, linea in enumerate(self.lineas):
                if resto <= 0:
                    break
                visible = linea[:resto]
                resto -= len(linea)
                if visible.strip():
                    im.alpha_composite(self.fuente.texto(visible, escala=self.escala, color=self.color, sombra=None),
                                       (self.margen[0], self.alto_nombre + self.margen[1] + i * alto_linea))
            self._memo[clave] = im
        im = self._memo[clave]
        if k < 1:
            alto = max(1, round(im.height * k))
            sal = Image.new('RGBA', im.size)
            sal.paste(im.resize((im.width, alto), Image.Resampling.NEAREST), (0, im.height - alto))
            return sal
        return im


class Cartel:
    """Rótulo grande que entra con rebote y sale: «¡MINIJUEGO!», «¡TURNO DE MARIO!», «¡GANADOR!»."""

    def __init__(self, fuente, texto, escala=6, color=(255, 240, 80), sombra=(150, 30, 20), duracion=2.0, entrada=0.28, salida=0.2, fondo=None, relleno=16):
        self.im = fuente.texto(texto, escala=escala, color=color, sombra=sombra, centrado=True)
        if fondo is not None:
            base = caja(self.im.width + relleno * 2, self.im.height + relleno * 2, relleno=fondo, escala=max(2, escala // 2))
            base.alpha_composite(self.im, ((base.width - self.im.width) // 2, (base.height - self.im.height) // 2))
            self.im = base
        self.duracion, self.entrada, self.salida = duracion, entrada, salida
        self.lienzo = (round(self.im.width * 1.3), round(self.im.height * 1.3))

    def frame(self, t):
        sal = Image.new('RGBA', self.lienzo)
        if t >= self.duracion:
            return sal
        if t < self.entrada:
            u = t / self.entrada
            k = 1.28 * u if u < 0.7 else 1.28 - 0.28 * (u - 0.7) / 0.3
        elif t > self.duracion - self.salida:
            k = max(0.0, (self.duracion - t) / self.salida)
        else:
            k = 1.0
        if k <= 0.02:
            return sal
        im = self.im.resize((max(1, round(self.im.width * k)), max(1, round(self.im.height * k))), Image.Resampling.NEAREST)
        x = (self.lienzo[0] - im.width) // 2
        y = (self.lienzo[1] - im.height) // 2
        sal.alpha_composite(im, (max(x, 0), max(y, 0)), (max(-x, 0), max(-y, 0)))
        return sal


class Contador:
    """Marcador de valor animado (monedas, estrellas, puntos), con icono y salto al cambiar.

    `valor`: número o Pista (función del tiempo)."""

    def __init__(self, fuente, valor, icono=None, escala=4, color=(255, 255, 255), sombra=(30, 30, 50), ceros=2, prefijo=''):
        self.fuente, self.valor, self.escala, self.color, self.sombra, self.ceros, self.prefijo = fuente, valor, escala, color, sombra, ceros, prefijo
        self.icono = icono.convert('RGBA') if icono is not None else None
        self._memo = {}

    def frame(self, t):
        v = round(self.valor(t) if callable(self.valor) else self.valor)
        previo = round(self.valor(t - 0.08) if callable(self.valor) else self.valor)
        salto = v != previo
        clave = (v, salto)
        if clave not in self._memo:
            r = self.fuente.texto('%s%0*d' % (self.prefijo, self.ceros, v), escala=self.escala, color=self.color, sombra=self.sombra)
            ic = self.icono
            ancho = r.width + (ic.width + self.escala * 2 if ic else 0)
            alto = max(r.height, ic.height if ic else 0) + self.escala * 2
            im = Image.new('RGBA', (ancho, alto))
            x = 0
            if ic:
                im.alpha_composite(ic, (0, (alto - ic.height) // 2))
                x = ic.width + self.escala * 2
            im.alpha_composite(r, (x, (alto - r.height) // 2 - (self.escala if salto else 0)))
            self._memo[clave] = im
        return self._memo[clave]


class Barra:
    """Barra de progreso o tiempo: `valor` de 0 a 1, número o función del tiempo."""

    def __init__(self, tamano=(360, 28), valor=1.0, color=(90, 220, 90), color_bajo=(235, 60, 50), fondo=(40, 40, 70), borde=(255, 255, 255), escala=3):
        self.tamano, self.valor, self.color, self.color_bajo, self.fondo, self.borde, self.escala = tamano, valor, color, color_bajo, fondo, borde, escala

    def frame(self, t):
        v = max(0.0, min(1.0, self.valor(t) if callable(self.valor) else self.valor))
        e = self.escala
        w, h = self.tamano[0] // e, self.tamano[1] // e
        a = np.zeros((h, w, 4), np.uint8)
        a[...] = (*self.borde, 255)
        a[1:-1, 1:-1] = (*self.fondo, 255)
        c = self.color_bajo if v < 0.25 else self.color
        fin = 1 + round((w - 2) * v)
        a[1:-1, 1:fin] = (*c, 255)
        a[1, 1:fin] = tuple(min(255, x + 60) for x in c) + (255,)
        return Image.fromarray(a).resize((w * e, h * e), Image.Resampling.NEAREST)
