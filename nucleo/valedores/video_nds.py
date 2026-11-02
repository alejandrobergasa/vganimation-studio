"""Motor de montaje animado DS: planos, capas, clips, cámara, texto y audio.

Trabaja con los gráficos nativos decodificados por cada juego. No emula el juego:
los movimientos de los actores y de cámara se componen en una línea de tiempo.
"""
from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import subprocess
import wave

import numpy as np
from PIL import Image
from scipy.signal import resample_poly

from . import rutas


def valor(v, t):
    """Una propiedad admite un número o una función del tiempo local del plano."""
    return float(v(t) if callable(v) else v)


def interpolar(inicio, fin, duracion):
    if duracion <= 0:
        raise ValueError('La duración de la interpolación debe ser positiva')
    def curva(t):
        u = max(0, min(1, t / duracion))
        u = u * u * (3 - 2 * u)
        return inicio + (fin - inicio) * u
    return curva


class Pista:
    """Valor animado por claves [(t, valor), ...]: se usa donde se admite una función del tiempo.

    `curva` es 'suave' (ease-in-out), 'recta', 'entrada' (acelera), 'salida' (frena), 'rebote' o 'corte'.
    Cada clave puede añadir su propia curva: (t, valor, 'salida').
    """
    def __init__(self, claves, curva='suave'):
        if not claves:
            raise ValueError('Una pista necesita al menos una clave')
        self.claves = sorted(((c[0], c[1], c[2] if len(c) > 2 else curva) for c in claves), key=lambda c: c[0])

    def __call__(self, t):
        cl = self.claves
        if t <= cl[0][0]:
            return float(cl[0][1])
        for (t0, v0, _), (t1, v1, curva) in zip(cl, cl[1:]):
            if t < t1:
                return v0 + (v1 - v0) * _curva((t - t0) / max(t1 - t0, 1e-9), curva)
        return float(cl[-1][1])


def _curva(u, curva):
    if curva == 'suave':
        return u * u * (3 - 2 * u)
    if curva == 'recta':
        return u
    if curva == 'entrada':
        return u * u
    if curva == 'salida':
        return 1 - (1 - u) * (1 - u)
    if curva == 'corte':
        return 0.0
    if curva == 'rebote':
        n, d = 7.5625, 2.75
        if u < 1 / d:
            return n * u * u
        if u < 2 / d:
            u -= 1.5 / d
            return n * u * u + 0.75
        if u < 2.5 / d:
            u -= 2.25 / d
            return n * u * u + 0.9375
        u -= 2.625 / d
        return n * u * u + 0.984375
    raise ValueError('Curva desconocida: ' + str(curva))


@dataclass
class Clip:
    imagenes: list
    duraciones: list = field(default_factory=list)
    repetir: bool = True

    def __post_init__(self):
        self.imagenes = [im.convert('RGBA') for im in self.imagenes]
        if not self.imagenes:
            raise ValueError('Un clip necesita al menos una imagen')
        if not self.duraciones:
            self.duraciones = [1 / 12] * len(self.imagenes)
        if len(self.duraciones) != len(self.imagenes) or any(d <= 0 for d in self.duraciones):
            raise ValueError('Duraciones de clip no válidas')

    def frame(self, t):
        total = sum(self.duraciones)
        t = max(0, t) % total if self.repetir else min(max(0, t), total - 1e-9)
        for im, duracion in zip(self.imagenes, self.duraciones):
            if t < duracion:
                return im
            t -= duracion
        return self.imagenes[-1]


class Superposicion:
    """Une dos actores/ clips sin perder sus tiempos de animación independientes."""
    def __init__(self, base, encima, posicion):
        self.base, self.encima, self.posicion = base, encima, posicion

    def frame(self, t):
        im = self.base.frame(t).copy().convert('RGBA')
        im.alpha_composite(self.encima.frame(t), self.posicion)
        return im


@dataclass
class Capa:
    clip: Clip
    x: object = 0
    y: object = 0
    escala: object = 1
    opacidad: object = 1
    giro: object = 0
    desde: float = 0
    hasta: float = math.inf
    ancla: tuple = (0.5, 1)
    pantalla: bool = False


class Plano:
    def __init__(self, duracion, fondo=None, color=(0, 0, 0, 255)):
        if not math.isfinite(duracion) or duracion <= 0:
            raise ValueError('El plano necesita una duración positiva y finita')
        self.duracion, self.fondo, self.color = duracion, fondo, color
        self.capas = []
        self.efectos = []
        self.transicion = None
        self.camara_x = self.camara_y = 0
        self.zoom = 1

    def sprite(self, imagen, **kw):
        clip = imagen if hasattr(imagen, 'frame') else Clip([imagen])
        capa = Capa(clip, **kw)
        self.capas.append(capa)
        return capa

    def escena(self, escena, tamano_video=None, **kw):
        """Añade una escena 3D (o cualquier actor con `frame`) a pantalla completa, sin cámara 2D.

        La escena se renderiza a su resolución interna y se amplía sin filtrar, como una DS."""
        ancho = (tamano_video or (1280, 720))[0]
        kw.setdefault('escala', ancho / escena.tamano[0])
        kw.setdefault('x', 0)
        kw.setdefault('y', 0)
        kw.setdefault('ancla', (0, 0))
        return self.sprite(escena, pantalla=True, **kw)

    def efecto(self, funcion):
        """Postproceso del fotograma: función (imagen RGB, t) -> imagen RGB. Ver valedores.efectos_video."""
        self.efectos.append(funcion)
        return funcion

    def frame(self, t, tamano):
        im = Image.new('RGBA', tamano, self.color)
        zoom = valor(self.zoom, t)
        if not 0 < zoom <= 32:
            raise ValueError('Zoom fuera de límites')
        if self.fondo is not None:
            fondo = self.fondo.frame(t) if hasattr(self.fondo, 'frame') else self.fondo
            fondo = fondo.convert('RGBA')
            escala = max(tamano[0] / fondo.width, tamano[1] / fondo.height) * zoom
            fondo = fondo.resize((math.ceil(fondo.width * escala), math.ceil(fondo.height * escala)), Image.Resampling.NEAREST)
            im.alpha_composite(fondo, (round((tamano[0] - fondo.width) / 2 - valor(self.camara_x,t)*zoom),
                                       round((tamano[1] - fondo.height) / 2 - valor(self.camara_y,t)*zoom)))
        for c in self.capas:
            if not c.desde <= t < c.hasta:
                continue
            local = t - c.desde
            actor = c.clip.frame(local)
            escala = valor(c.escala, local) * (1 if c.pantalla else zoom)
            if not 0 < escala <= 128:
                raise ValueError('Escala fuera de límites')
            actor = actor.resize((max(1, round(actor.width * escala)), max(1, round(actor.height * escala))), Image.Resampling.NEAREST)
            giro = valor(c.giro, local)
            if giro:
                actor = actor.rotate(giro, resample=Image.Resampling.NEAREST, expand=True)
            opacidad = max(0, min(1, valor(c.opacidad, local)))
            if opacidad < 1:
                actor.putalpha(actor.getchannel('A').point(lambda p: round(p * opacidad)))
            x, y = valor(c.x, local), valor(c.y, local)
            if not c.pantalla:
                x = (x - valor(self.camara_x, t) - tamano[0]/2) * zoom + tamano[0]/2
                y = (y - valor(self.camara_y, t) - tamano[1]/2) * zoom + tamano[1]/2
            im.alpha_composite(actor, (round(x - c.ancla[0] * actor.width), round(y - c.ancla[1] * actor.height)))
        im = im.convert('RGB')
        for efecto in self.efectos:
            im = efecto(im, t)
        return im


class Fuente:
    """Fuente NFTR del propio juego, sin sustituir glifos por fuentes del sistema."""
    def __init__(self, datos, extra=None, espaciado=0):
        from .recursos_nds import lectores
        self.f = lectores()[1].Font(datos)
        # Carácter -> código NFTR para glifos que Shift-JIS no codifica (p. ej. las
        # letras latinas acentuadas que algunas ROMs europeas guardan en 0xA1-0xDF).
        self.extra = dict(extra or {})
        # Si es > 0, los glifos se colocan por su tinta con ese hueco fijo (px de la
        # fuente) en vez de por avance/margen. Las NFTR de Layton mezclan glifos con
        # avance == ancho de tinta (letras pegadas) y otros con margen propio (huecos
        # desiguales); los avances solo se usan para el espacio.
        self.espaciado = espaciado
        if self.f.depth not in (1, 2) or self.f.rot:
            raise ValueError('Profundidad o rotación NFTR todavía no compatible')

    def texto(self, texto, escala=1, color='white', ancho=None):
        f = self.f
        lineas = texto.split('\n')
        glifos = []
        anchos = []
        for linea in lineas:
            fila, x, hueco = [], 0, 0
            for ch in linea:
                codigo = ord(ch)
                if ch in self.extra:
                    codigo = self.extra[ch]
                elif f.enc == 2:
                    codigo = int.from_bytes(ch.encode('shift_jis'), 'big')
                elif f.enc == 3:
                    codigo = int.from_bytes(ch.encode('cp1252'), 'big')
                if codigo not in f.cmap:
                    raise ValueError('La fuente del juego no contiene el carácter %r' % ch)
                i = f.cmap[codigo]
                izq, w, avance = f.widths[i] or (f.dleft, f.dwidth, f.dadv)
                pix = f.glyph(i)
                hueco = 0
                if self.espaciado:
                    columnas = np.flatnonzero(pix.any(axis=0))
                    if len(columnas):
                        hueco = self.espaciado
                        # La tinta empieza en x; el siguiente glifo, tras el hueco fijo.
                        izq, avance = -int(columnas[0]), int(columnas[-1] - columnas[0]) + 1 + self.espaciado
                if ancho is not None and x + avance > ancho / escala:
                    raise ValueError('El texto excede el ancho; divide la frase en líneas')
                a = Image.fromarray((pix.astype('uint16') * 255 // ((1 << f.depth) - 1)).astype('uint8'))
                im = Image.new('RGBA', a.size, color)
                im.putalpha(a)
                fila.append((im, x + izq))
                x += avance
            glifos.append(fila)
            anchos.append(x - hueco)  # sin el hueco que sigue a la última letra
        salida = Image.new('RGBA', (max(1, max(anchos)), max(1, len(lineas) * f.height)))
        for y, fila in enumerate(glifos):
            for im, x in fila:
                salida.alpha_composite(im, (x, y * f.height))
        return salida.resize((max(1, round(salida.width * escala)), max(1, round(salida.height * escala))), Image.Resampling.NEAREST)


class Video:
    def __init__(self, juego, formato='horizontal', fps=30, tamano=None):
        if formato not in ('horizontal', 'vertical') or not 1 <= fps <= 120:
            raise ValueError('Formato o fps no válido')
        self.juego, self.fps = juego, fps
        self.tamano = tamano or ((1280, 720) if formato == 'horizontal' else (1080, 1920))
        if any(n <= 0 or n % 2 for n in self.tamano):
            raise ValueError('Las dimensiones del vídeo deben ser positivas y pares')
        self.planos, self.audios = [], []

    @property
    def duracion(self):
        return sum(p.duracion for p in self.planos)

    def plano(self, duracion, **kw):
        plano = Plano(duracion, **kw)
        self.planos.append(plano)
        return plano

    def audio(self, muestras, frecuencia=32768, desde=0, volumen=1):
        muestras = np.asarray(muestras, dtype='float32')
        if muestras.ndim == 1:
            muestras = np.repeat(muestras[:, None], 2, axis=1)
        elif muestras.ndim == 2 and muestras.shape[1] == 1:
            muestras = np.repeat(muestras, 2, axis=1)
        if muestras.ndim != 2 or muestras.shape[1] != 2 or not np.all(np.isfinite(muestras)):
            raise ValueError('Se necesita audio mono o estéreo con muestras finitas')
        if desde < 0 or frecuencia <= 0 or volumen < 0:
            raise ValueError('Tiempo, frecuencia o volumen de audio no válido')
        frecuencia = round(frecuencia)
        if frecuencia != 32768:
            divisor = math.gcd(32768, frecuencia)
            muestras = resample_poly(muestras, 32768 // divisor, frecuencia // divisor, axis=0)
        self.audios.append((desde, volumen, muestras))

    def sonido(self, audio, desde=0, volumen=1, pan=0.0, plano=None):
        """Coloca un efecto: `audio` = (muestras, frecuencia). `desde` es relativo a `plano` si se indica.

        `pan` va de -1 (izquierda) a 1 (derecha)."""
        muestras, frecuencia = audio
        if plano is not None:
            desde += self.inicio_plano(plano)
        muestras = np.asarray(muestras, dtype='float32')
        if muestras.ndim == 1:
            muestras = np.repeat(muestras[:, None], 2, axis=1)
        if pan:
            pan = max(-1.0, min(1.0, pan))
            muestras = muestras * np.array([min(1.0, 1 - pan), min(1.0, 1 + pan)], dtype='float32')
        self.audio(muestras, frecuencia, desde=desde, volumen=volumen)

    def inicio_plano(self, plano):
        """Segundo del vídeo en el que empieza un plano."""
        t = 0.0
        for p in self.planos:
            if p is plano:
                return t
            t += p.duracion
        raise ValueError('El plano no pertenece a este vídeo')

    def frame(self, t):
        if not self.planos:
            raise ValueError('El vídeo no tiene planos')
        t = max(0, min(t, self.duracion - 1e-9))
        inicio = 0.0
        for i, p in enumerate(self.planos):
            if t < inicio + p.duracion or i == len(self.planos) - 1:
                local = min(t - inicio, p.duracion - 1e-9)
                return self._con_transicion(i, local)
            inicio += p.duracion
        raise AssertionError('Tiempo fuera de los planos')

    def _con_transicion(self, i, local):
        """Compone el fotograma: una transición dura lo indicado y queda centrada en el corte."""
        p = self.planos[i]
        siguiente = self.planos[i + 1] if i + 1 < len(self.planos) else None
        if p.transicion is not None and i > 0 and local < p.transicion[1] / 2:
            from .efectos_video import transicion
            previo = self.planos[i - 1]
            tipo, duracion = p.transicion
            a = previo.frame(previo.duracion - 1e-9, self.tamano)
            return transicion(tipo, a, p.frame(local, self.tamano), (local + duracion / 2) / duracion)
        if siguiente is not None and siguiente.transicion is not None and local >= p.duracion - siguiente.transicion[1] / 2:
            from .efectos_video import transicion
            tipo, duracion = siguiente.transicion
            u = (local - (p.duracion - duracion / 2)) / duracion
            return transicion(tipo, p.frame(local, self.tamano), siguiente.frame(0, self.tamano), u)
        return p.frame(local, self.tamano)

    def renderizar(self, nombre='video.mp4'):
        if not self.planos:
            raise ValueError('El vídeo no tiene planos')
        if Path(nombre).name != nombre or not nombre.lower().endswith('.mp4'):
            raise ValueError('Indica sólo el nombre del MP4; la carpeta se obtiene de valedores.rutas')
        destino = Path(rutas.salida(self.juego)) / nombre
        trabajo = Path(rutas.trabajo(self.juego))
        frames = round(self.duracion * self.fps)
        if frames < 1:
            raise ValueError('El vídeo dura menos de un fotograma')
        duracion = frames / self.fps
        temporal = trabajo / (Path(nombre).stem + '_sin_audio.mp4')
        error = trabajo / (Path(nombre).stem + '_ffmpeg.log')
        comando = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s',
                   '%dx%d' % self.tamano, '-r', str(self.fps), '-i', '-', '-an', '-c:v', 'libx264',
                   '-preset', 'fast', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(temporal)]
        with error.open('wb') as log:
            proceso = subprocess.Popen(comando, stdin=subprocess.PIPE, stderr=log)
            try:
                for i in range(frames):
                    proceso.stdin.write(self.frame(i / self.fps).tobytes())
                proceso.stdin.close()
            except BaseException:
                proceso.kill()
                proceso.wait()
                raise
            if proceso.wait() != 0:
                raise RuntimeError('Falló el codificador: ' + str(error))
        mezcla = np.zeros((round(duracion * 32768), 2), dtype='float32')
        for desde, volumen, muestras in self.audios:
            inicio = round(desde * 32768)
            n = min(len(muestras), max(0, len(mezcla) - inicio))
            mezcla[inicio:inicio + n] += muestras[:n] * volumen
        pico = float(np.max(np.abs(mezcla)))
        if pico > 0:
            mezcla *= min(1, 0.85 / pico)
            fundido = min(512, len(mezcla) // 2)
            mezcla[:fundido] *= np.linspace(0, 1, fundido)[:, None]
            mezcla[-fundido:] *= np.linspace(1, 0, fundido)[:, None]
        wav = trabajo / (Path(nombre).stem + '_mezcla.wav')
        with wave.open(str(wav), 'wb') as f:
            f.setnchannels(2)
            f.setsampwidth(2)
            f.setframerate(32768)
            f.writeframes((np.clip(mezcla, -1, 1) * 32767).astype('<i2').tobytes())
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(temporal), '-i', str(wav),
                        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
                        '-t', str(duracion), '-movflags', '+faststart', str(destino)], check=True)
        return str(destino)
