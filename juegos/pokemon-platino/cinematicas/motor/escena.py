"""Motor de cinemáticas estilo Pokémon Platino.

Coordenadas: el mapa se mide en tiles de 16x16 px. La pantalla es la de la DS (256x192) y se
escala al exportar. El tiempo va en frames a 30 fps (como el juego en el mapa).

Una escena es una lista de PASOS. Cada paso ejecuta una o varias ACCIONES en paralelo y termina
cuando acaban todas. Una acción es un generador que hace `yield` una vez por frame.
"""
import math
import os
import shutil
import subprocess
import tempfile

from PIL import Image

from . import catalogo
from .recursos import (DIRS, TRABAJO, frames_personaje, fuente, frames_flecha, imagen, ventana_mensaje)

TILE = 16
ANCHO, ALTO = 256, 192


def _aux(salida, sufijo):
    """Fichero auxiliar (hoja de revisión, audio suelto) de una salida: va a la carpeta de trabajo, no a la bandeja de salida."""
    return os.path.join(TRABAJO, os.path.basename(salida) + sufijo)

VELOCIDAD = {'andar': 8, 'correr': 4, 'sprint': 2, 'lento': 16}  # frames por tile
OPUESTA = {'arriba': 'abajo', 'abajo': 'arriba', 'izquierda': 'derecha', 'derecha': 'izquierda'}
DELTA = {'arriba': (0, -1), 'abajo': (0, 1), 'izquierda': (-1, 0), 'derecha': (1, 0)}


# ====================================================================== mapa

class Mapa:
    def __init__(self, texto, leyenda, fondo='cesped'):
        """texto: rejilla de caracteres (una fila por línea). leyenda: {caracter: suelo o
        ('suelo', 'objeto')}. Los objetos se anclan en el tile donde está el caracter."""
        filas = [l for l in texto.strip('\n').split('\n')]
        self.alto = len(filas)
        self.ancho = max(len(f) for f in filas)
        self.suelo = [[fondo] * self.ancho for _ in range(self.alto)]
        self.objetos = []  # (nombre, tx, ty)
        for ty, fila in enumerate(filas):
            for tx, ch in enumerate(fila):
                v = leyenda.get(ch)
                if v is None:
                    continue
                suelo, obj = (v if isinstance(v, tuple) else (v, None))
                if suelo:
                    self.suelo[ty][tx] = suelo
                if obj:
                    self.objetos.append((obj, tx, ty))

    def poner(self, objeto, tx, ty):
        self.objetos.append((objeto, tx, ty))

    def dibujar_suelo(self, lienzo, camx, camy, t):
        tx0, ty0 = int(camx // TILE), int(camy // TILE)
        for ty in range(ty0, ty0 + ALTO // TILE + 2):
            for tx in range(tx0, tx0 + ANCHO // TILE + 2):
                if not (0 <= tx < self.ancho and 0 <= ty < self.alto):
                    continue
                nombre = self.suelo[ty][tx]
                capas = []
                d = catalogo.SUELOS[nombre]
                if 'sobre' in d:
                    capas.append(d['sobre'])
                capas.append(nombre)
                for c in capas:
                    fr = catalogo.frames_suelo(c)
                    vel = catalogo.SUELOS[c].get('velocidad', 8)
                    img = fr[(t // vel) % len(fr)]
                    # las texturas grandes se muestrean según la posición en el mundo
                    sx, sy = (tx * TILE) % img.width, (ty * TILE) % img.height
                    trozo = img.crop((sx, sy, sx + TILE, sy + TILE))
                    lienzo.alpha_composite(trozo, (int(tx * TILE - camx), int(ty * TILE - camy)))

    def dibujables(self):
        """(y_base, función_dibujo) de cada objeto para ordenarlos con los personajes."""
        out = []
        for nombre, tx, ty in self.objetos:
            def dib(lienzo, camx, camy, nombre=nombre, tx=tx, ty=ty):
                for img, (ox, oy) in catalogo.piezas_objeto(nombre):
                    lienzo.alpha_composite(img, (int(tx * TILE + ox - camx), int(ty * TILE + oy - camy)))
            out.append((ty * TILE + TILE, dib))
        return out


# ====================================================================== personajes

class Personaje:
    def __init__(self, escena, sprite, tx, ty, mira='abajo', sombra=True, frames=None):
        self.escena = escena
        self.nombre = sprite
        self.frames = frames if frames is not None else frames_personaje(sprite)
        self.x, self.y = tx * TILE, ty * TILE  # esquina sup. izq. del tile, en píxeles
        self.dir = mira
        self.fase = 0          # 0 quieto, 1 paso A, 2 quieto, 3 paso B
        self.set_correr = len(self.frames) >= 32
        self.usando_correr = False
        self.pasos = 0
        self.salto = 0         # desplazamiento vertical extra (saltos)
        self.visible = True
        self.sombra = sombra
        self.burbuja = None    # (imagen, dy)
        self.empuje = (0, 0)   # desplazamiento extra en px (golpes, temblores); no cambia el tile
        self.pose = None       # imagen fija que sustituye al frame de andar (sentado, agachado...)
        self.encima = []       # (imagen, dx, dy): cosas que lleva (caja sobre la cabeza...), en px
        self.alfa = 1.0        # opacidad (fantasmas, apariciones)
        self.tinte = None      # (r, g, b, fuerza 0-1): tiñe el sprite (cara que cambia de color...)

    @property
    def tile(self):
        return round(self.x / TILE), round(self.y / TILE)

    def frame_actual(self):
        if self.pose is not None:
            return self.pose
        base = 16 if (self.usando_correr and self.set_correr) else 0
        i = base + DIRS[self.dir] * 4 + self.fase
        return self.frames[i % len(self.frames)]

    @property
    def elevacion(self):
        """Píxeles que sube el suelo bajo el personaje (solo en mapas reales con relieve)."""
        f = getattr(self.escena.mapa, 'elevacion', None)
        return f(self.x, self.y) if f else 0.0

    def _origen(self, camx, camy, img=None):
        """Esquina superior izquierda en pantalla de un sprite de 32x32 (o del tamaño de 'img': se apoya
        centrado en el borde inferior del tile)."""
        ex, ey = self.empuje
        w, h = (32, 32) if img is None else img.size
        return (int(self.x + 8 - w // 2 - camx + ex),
                int(round(self.y + 16 - h - self.elevacion + ey) - camy))

    def dibujar(self, lienzo, camx, camy):
        if not self.visible:
            return
        img = self.frame_actual()
        if self.tinte:
            img = _tenir(img, self.tinte)
        if self.alfa < 1:
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda v: int(v * self.alfa)))
        sx, sy = self._origen(camx, camy, img)
        if self.sombra and self.alfa > 0.5:
            k = imagen('efectos_mapa/017/kage.png')
            lienzo.alpha_composite(k, (sx + img.width // 2 - k.width // 2, sy + img.height - k.height // 2 - 2))
        lienzo.alpha_composite(img, (sx, sy - int(self.salto)))
        for e, dx, dy in self.encima:
            lienzo.alpha_composite(e, (sx + img.width // 2 - e.width // 2 + dx, sy - int(self.salto) + dy))
        tapar = getattr(self.escena.mapa, 'tapar', None)
        if tapar:  # lo que está delante en el mapa (árboles, tejados) tapa al personaje
            tapar(lienzo, camx, camy, (sx - 8, sy - int(self.salto) - 2 - 24, sx + img.width + 8, sy + img.height + 2),
                  self.y + TILE)

    def dibujar_burbuja(self, lienzo, camx, camy):
        if not (self.visible and self.burbuja):
            return
        fr = self.frame_actual()
        sx, sy = self._origen(camx, camy, fr)
        img, dy = self.burbuja
        lienzo.alpha_composite(img, (sx + fr.width // 2 - img.width // 2,
                                     int(sy - int(self.salto) - img.height + 6 + dy)))

    # -------------------------------------------------- acciones (generadores)

    def mirar(self, direccion):
        """Gira al personaje (dura 1 frame). direccion: 'arriba','abajo','izquierda','derecha'
        o otro Personaje para mirarle."""
        def acc():
            d = direccion
            if isinstance(d, Personaje):
                dx, dy = d.x - self.x, d.y - self.y
                d = ('derecha' if dx > 0 else 'izquierda') if abs(dx) >= abs(dy) else ('abajo' if dy > 0 else 'arriba')
            self.dir = d
            self.fase = 0
            yield
        return acc()

    def andar(self, direccion, tiles=1, modo='andar'):
        """Camina 'tiles' casillas. modo: 'andar' (8 f/tile), 'correr' (4 f/tile), 'sprint' (2 f/tile, como
        la bici; para persecuciones), 'lento' (16)."""
        def acc():
            self.dir = direccion
            self.usando_correr = modo in ('correr', 'sprint')
            n = VELOCIDAD[modo]
            dx, dy = DELTA[direccion]
            bloq = getattr(self.escena.mapa, 'bloqueado', None)
            for _ in range(tiles):
                tx, ty = self.tile
                if bloq and bloq(tx + dx, ty + dy) and 0 <= tx + dx < self.escena.mapa.ancho:
                    print('AVISO: %s pisa un tile bloqueado (%d, %d) en el mapa'
                          % (os.path.basename(str(self.nombre)), tx + dx, ty + dy))
                paso = 1 if self.pasos % 2 == 0 else 3
                for f in range(n):
                    self.x += dx * TILE / n
                    self.y += dy * TILE / n
                    self.fase = paso if f < n // 2 else 0
                    yield
                self.pasos += 1
            self.x, self.y = round(self.x), round(self.y)
            self.fase = 0
            self.usando_correr = False
        return acc()

    def correr(self, direccion, tiles=1):
        return self.andar(direccion, tiles, 'correr')

    def ruta(self, *tramos, modo='andar'):
        """Varios tramos seguidos: ruta(('derecha', 3), ('arriba', 2))."""
        def acc():
            for d, n in tramos:
                yield from self.andar(d, n, modo)
        return acc()

    def saltar(self, altura=8, frames=8):
        """Saltito en el sitio (como cuando un PNJ se sorprende)."""
        def acc():
            for f in range(frames + 1):
                self.salto = altura * math.sin(math.pi * f / frames)
                yield
            self.salto = 0
        return acc()

    def emocion(self, tipo='!', frames=30):
        """Burbuja sobre la cabeza. '!' = sorpresa (la del entrenador que te ve)."""
        img = {'!': imagen('efectos_mapa/004/sisen_ef.png')}[tipo]

        def acc():
            for f in range(frames):
                dy = [6, 3, 0, -1, 0][f] if f < 5 else 0  # aparece con un pequeño rebote
                self.burbuja = (img, dy)
                yield
            self.burbuja = None
        return acc()

    def golpear(self, victima, frames=24, sonido='SEQ_SE_DP_KOUKA_H'):
        """Puñetazo a otro personaje: se gira hacia él, se lanza unos píxeles, aparece el destello de
        impacto de los ataques del juego (efectos_ataques/33, sus 2 celdas pequeñas) sobre la víctima, la
        víctima retrocede y tiembla y la pantalla vibra. Los dos vuelven a su tile al acabar.
        sonido: efecto que suena en el impacto (por defecto, el golpe «supereficaz» del combate)."""
        impacto = [imagen('efectos_ataques/33/celda_%02d.png' % i) for i in range(2)]

        def acc():
            esc = self.escena
            dx, dy = victima.x - self.x, victima.y - self.y
            self.dir = (('derecha' if dx > 0 else 'izquierda') if abs(dx) >= abs(dy)
                        else ('abajo' if dy > 0 else 'arriba'))
            ux, uy = DELTA[self.dir]
            for f in range(frames):
                if f < 4:                                   # carga hacia atrás
                    self.empuje = (-ux * f, -uy * f)
                elif f < 7:                                 # se lanza
                    k = (f - 3) * 3
                    self.empuje = (ux * k, uy * k)
                    self.fase = 1
                else:                                       # vuelve a su sitio
                    k = max(0, 9 - (f - 6))
                    self.empuje = (ux * k, uy * k)
                    self.fase = 0
                if f == 6 and sonido:
                    esc.audio.append((esc.t, 'sonido', sonido, 0.8))
                if 6 <= f < 18:                             # impacto
                    g = f - 6
                    r = max(0, 6 - g)
                    sacudida = (2 if g % 2 else -2) if g < 8 else 0
                    victima.empuje = (ux * r + (sacudida if uy else 0), uy * r + (sacudida if ux else 0))
                    esc.temblor = ((3 if g % 2 else -3) if g < 6 else 0, (2 if g % 2 else -2) if g < 4 else 0)
                    if g < 6:   # en el punto de contacto, a la altura del pecho (la 3.ª celda es enorme)
                        img = impacto[(0, 1, 1, 1, 0, 0)[g]]
                        ex = victima.x + 8 - img.width // 2 - ux * 8
                        ey = victima.y - victima.elevacion - img.height // 2 - uy * 7
                        esc.efectos.append((img, ex, ey))
                else:
                    victima.empuje = (0, 0)
                    esc.temblor = (0, 0)
                yield
            self.empuje = victima.empuje = (0, 0)
            esc.temblor = (0, 0)
        return acc()

    def posar(self, pose):
        """Pose fija: un índice de self.frames (los custom pueden traer frames extra: sentado, agachado...),
        una imagen, o None para volver a andar normal."""
        def acc():
            self.pose = self.frames[pose] if isinstance(pose, int) else pose
            yield
        return acc()

    def cambiar_sprite(self, sprite):
        """Cambia de ropa/sprite sin moverlo (ponerse el sombrero, cambiarse de sudadera...)."""
        def acc():
            self.frames = frames_personaje(sprite) if isinstance(sprite, str) else sprite
            self.nombre = sprite if isinstance(sprite, str) else self.nombre
            self.set_correr = len(self.frames) >= 32
            yield
        return acc()

    def llevar(self, img=None, dx=0, dy=-12):
        """Muestra un objeto sobre el personaje (p. ej. una caja sobre la cabeza). img=None lo quita."""
        def acc():
            self.encima = [] if img is None else [(img, dx, dy)]
            yield
        return acc()

    def mover(self, dx, dy, frames, arco=0, animar=False):
        """Desplaza el personaje dx, dy píxeles en 'frames' (no tiene por qué ser un tile entero). arco: altura
        de la parábola (lanzamientos). animar: mueve las piernas como al andar."""
        def acc():
            x0, y0 = self.x, self.y
            for f in range(1, frames + 1):
                k = f / frames
                self.x, self.y = x0 + dx * k, y0 + dy * k
                self.salto = arco * 4 * k * (1 - k)
                if animar:
                    self.fase = (1 if (f // 4) % 4 == 1 else 3 if (f // 4) % 4 == 3 else 0)
                yield
            self.salto = 0
            self.fase = 0
        return acc()

    def desvanecer(self, entrada=True, frames=15):
        """Aparece (entrada=True) o desaparece fundiéndose."""
        def acc():
            self.visible = True
            for f in range(frames + 1):
                self.alfa = f / frames if entrada else 1 - f / frames
                yield
            self.visible = entrada
            self.alfa = 1.0
        return acc()

    def tenir(self, color=None, fuerza=0.6):
        """Tiñe el sprite (color RGB) o quita el tinte (None)."""
        def acc():
            self.tinte = None if color is None else (color + (fuerza,))
            yield
        return acc()

    def temblar(self, frames=12, amplitud=2):
        """Tiembla en el sitio (rabia, miedo, forcejeo)."""
        def acc():
            for f in range(frames):
                self.empuje = ((amplitud if f % 2 else -amplitud), 0)
                yield
            self.empuje = (0, 0)
        return acc()

    def desaparecer(self):
        def acc():
            self.visible = False
            yield
        return acc()

    def aparecer(self):
        def acc():
            self.visible = True
            yield
        return acc()

    def teletransportar(self, tx, ty):
        def acc():
            self.x, self.y = tx * TILE, ty * TILE
            yield
        return acc()


# ====================================================================== escena

class Escena:
    def __init__(self, mapa, fps=30, escala=3, tipo_ventana=1, t0=0.0):
        """t0: segundo del montaje en el que empieza la escena (para escenas sincronizadas con un audio
        externo: hasta() y subtitulos() usan tiempos absolutos)."""
        self.mapa = mapa
        self.t0 = t0
        self.subs = []               # (t_ini, t_fin, texto) en segundos absolutos
        self.capas = {}              # nombre -> [imagen, x, y, alfa, orden]: capas fijas en pantalla
        self.tinte_pantalla = None   # (r, g, b, alfa 0-1) encima de todo salvo el diálogo
        self.filtro = None           # función(PIL RGB, t) -> PIL RGB aplicada al final (CRT, sepia...)
        self.efectos_pantalla = []   # (imagen, x, y) en px de pantalla; un solo frame
        self.ventana = None          # (x, y, w, h) del diálogo; None = la de abajo
        self.audio_base = None       # (ruta wav, segundo de inicio): pista externa para el MP4
        self.fondo = []              # acciones en segundo plano (en_paralelo)
        self.fps = fps
        self.escala = escala
        self.tipo_ventana = tipo_ventana
        self.personajes = []
        self.pasos = []
        self.fondo_paralelo = []
        self.camx = self.camy = 0
        self.objetivo_camara = None
        self.dialogo_activo = None   # (texto_lineas_visibles, mostrar_flecha)
        self.negro = 0.0             # 0 = sin fundido, 1 = negro
        self.temblor = (0, 0)        # desplazamiento de la cámara (golpes)
        self.efectos = []            # (imagen, x, y) en px de mapa; se dibujan encima un solo frame
        self.audio = []              # (frame, tipo, nombre, valor): música y efectos de sonido
        self.t = 0

    # -------------------------------------------------- construcción

    def personaje(self, sprite, tx, ty, mira='abajo', **kw):
        p = Personaje(self, sprite, tx, ty, mira, **kw)
        self.personajes.append(p)
        return p

    def objeto(self, img, tx, ty, sombra=False, visible=True):
        """Un objeto del mundo (caja, banco, estatua...) que se ordena en profundidad con los personajes y
        admite sus acciones (mover, desaparecer, posar...). img: imagen o ruta relativa a
        sprites_extraidos/. Se apoya centrado en el borde inferior del tile (tx, ty)."""
        if isinstance(img, str):
            img = imagen(img)
        p = Personaje(self, 'objeto', tx, ty, 'abajo', sombra=sombra, frames=[img] * 16)
        p.pose = img
        p.visible = visible
        self.personajes.append(p)
        return p

    @property
    def ahora(self):
        """Segundo absoluto del frame actual."""
        return self.t0 + self.t / self.fps

    def subtitulos(self, lista):
        """Diálogos sincronizados con la voz: [(t_ini, t_fin, 'TEXTO'), ...] en segundos absolutos. Se
        dibujan con la ventana del juego sin parar la escena (el texto se escribe al empezar y la flecha
        aparece al final). Si un texto tiene más de 2 líneas, sus páginas se reparten el tiempo."""
        self.subs.extend(lista)
        self.subs.sort()

    def camara_sigue(self, personaje):
        self.objetivo_camara = personaje

    def camara_fija(self, tx, ty):
        """Centra la cámara en un tile y deja de seguir a nadie."""
        f = getattr(self.mapa, 'elevacion', None)
        self.objetivo_camara = (tx * TILE + 8, ty * TILE + 8 - (f(tx * TILE, ty * TILE) if f else 0))

    def hacer(self, *acciones):
        """Añade un paso: las acciones indicadas se ejecutan a la vez."""
        self.pasos.append(list(acciones))
        return self

    def esperar(self, frames):
        def acc():
            for _ in range(frames):
                yield
        return self.hacer(acc())

    def hasta(self, segundo):
        """Acción: espera hasta ese segundo absoluto (t0 + frames/fps). Si ya ha pasado, avisa."""
        def acc():
            objetivo = int(round((segundo - self.t0) * self.fps))
            if self.t > objetivo + 1:
                print('AVISO: hasta(%.2f) llega tarde: ya vamos por %.2f s' % (segundo, self.ahora))
            while self.t < objetivo:
                yield
        return acc()

    def esperar_hasta(self, segundo):
        """Paso que espera hasta ese segundo absoluto."""
        return self.hacer(self.hasta(segundo))

    def accion(self, funcion):
        """Acción de un frame que ejecuta funcion() (cambios de estado sueltos)."""
        def acc():
            funcion()
            yield
        return acc()

    def durante(self, frames, funcion):
        """Acción que llama a funcion(f) en cada uno de 'frames' frames (f = 0..frames-1)."""
        def acc():
            for f in range(frames):
                funcion(f)
                yield
        return acc()

    # -------------------------------------------------- acciones de escena

    def cambiar_mapa(self, mapa, sigue=None, fija=None):
        """Cambia de escenario (úsalo con la pantalla en negro, entre dos fundidos). sigue=personaje o
        fija=(tx, ty) para la cámara en el mapa nuevo. Coloca antes a los personajes con
        teletransportar() y oculta con desaparecer() a los que no estén."""
        def acc():
            self.mapa = mapa
            if sigue is not None:
                self.camara_sigue(sigue)
            elif fija is not None:
                self.camara_fija(*fija)
            yield
        return acc()

    def musica(self, nombre, volumen=0.55):
        """Empieza un tema del juego (SSEQ, p. ej. 'SEQ_CITY01_D') en bucle; sustituye al anterior.
        Lista de nombres: python ../tools/sonido.py <rom> --lista"""
        def acc():
            self.audio.append((self.t, 'musica', nombre, volumen))
            yield
        return acc()

    def parar_musica(self, frames=30):
        """Baja la música hasta el silencio en 'frames' (no espera: la escena sigue)."""
        def acc():
            self.audio.append((self.t, 'fundido_musica', None, frames))
            yield
        return acc()

    def sonido(self, nombre, volumen=0.8):
        """Efecto de sonido del juego (p. ej. 'SEQ_SE_DP_SELECT'). Dura 1 frame; suena entero."""
        def acc():
            self.audio.append((self.t, 'sonido', nombre, volumen))
            yield
        return acc()

    def dialogo(self, texto, espera=45, velocidad=1, sonido=True):
        """Ventana de mensaje con el marco y la fuente del juego. Las líneas se separan con '\\n'
        (2 líneas por ventana; con más, se pasa de página). velocidad = caracteres por frame.
        sonido: el «clic» del juego (SEQ_SE_DP_SELECT) al pasar cada página."""
        lineas = texto.split('\n')
        paginas = [lineas[i:i + 2] for i in range(0, len(lineas), 2)]

        def acc():
            for pag in paginas:
                total = sum(len(l) for l in pag)
                shown = 0.0
                while shown < total:
                    shown += velocidad
                    self.dialogo_activo = (_recortar(pag, int(shown)), False)
                    yield
                for _ in range(espera):
                    self.dialogo_activo = (pag, True)
                    yield
                if sonido:
                    self.audio.append((self.t, 'sonido', 'SEQ_SE_DP_SELECT', 0.5))
            self.dialogo_activo = None
            yield
        return acc()

    def fundido(self, entrada=True, frames=15):
        """entrada=True: de negro a imagen. entrada=False: de imagen a negro."""
        def acc():
            for f in range(frames + 1):
                v = f / frames
                self.negro = 1 - v if entrada else v
                yield
        return acc()


    # -------------------------------------------------- capas, efectos y cámara

    def mostrar(self, nombre, img, x=None, y=None, frames=10, efecto='fundido', orden=0):
        """Muestra una imagen fija en pantalla (inserto de un objeto, título, rótulo...). x, y: esquina en
        píxeles de pantalla (None = centrada). efecto: 'fundido', 'subir' (entra desde abajo), 'zoom' o
        None. orden: las capas con orden mayor van encima. Se quita con ocultar(nombre)."""
        if isinstance(img, str):
            img = imagen(img)
        x = (ANCHO - img.width) // 2 if x is None else x
        y = (ALTO - img.height) // 2 if y is None else y

        def acc():
            for f in range(1, frames + 1):
                k = f / frames
                if efecto == 'subir':
                    self.capas[nombre] = [img, x, int(y + (1 - k) ** 2 * (ALTO - y)), 1.0, orden]
                elif efecto == 'zoom':
                    s = max(0.05, k)
                    im = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.NEAREST)
                    self.capas[nombre] = [im, x + (img.width - im.width) // 2, y + (img.height - im.height) // 2,
                                          1.0, orden]
                else:
                    self.capas[nombre] = [img, x, y, k if efecto == 'fundido' else 1.0, orden]
                yield
            self.capas[nombre] = [img, x, y, 1.0, orden]
        return acc()

    def cambiar_capa(self, nombre, img):
        """Cambia la imagen de una capa sin moverla (animaciones de insertos)."""
        def acc():
            if nombre in self.capas:
                self.capas[nombre][0] = img
            yield
        return acc()

    def ocultar(self, nombre, frames=10, efecto='fundido'):
        """Quita una capa de mostrar() (efecto 'fundido', 'bajar' o None)."""
        def acc():
            c = self.capas.get(nombre)
            if c is not None and efecto:
                img, x, y, a, o = c
                for f in range(1, frames + 1):
                    k = f / frames
                    if efecto == 'bajar':
                        self.capas[nombre] = [img, x, int(y + k * k * (ALTO - y)), a, o]
                    else:
                        self.capas[nombre] = [img, x, y, a * (1 - k), o]
                    yield
            self.capas.pop(nombre, None)
            yield
        return acc()

    def mover_capa(self, nombre, dx, dy, frames):
        """Desplaza una capa en pantalla (paneo de un inserto, chat que sube...)."""
        def acc():
            c = self.capas[nombre]
            x0, y0 = c[1], c[2]
            for f in range(1, frames + 1):
                c = self.capas.get(nombre)
                if c is None:
                    return
                k = f / frames
                k = k * k * (3 - 2 * k)
                c[1], c[2] = round(x0 + dx * k), round(y0 + dy * k)
                yield
        return acc()

    def tenir_pantalla(self, color=None, alfa=0.4, frames=10):
        """Tiñe toda la imagen (filtro rojo, luz amarilla...). color=None lo quita con un fundido."""
        def acc():
            ini = self.tinte_pantalla
            for f in range(1, frames + 1):
                k = f / frames
                if color is None:
                    if ini is None:
                        break
                    self.tinte_pantalla = ini[:3] + (ini[3] * (1 - k),)
                else:
                    a0 = ini[3] if ini and ini[:3] == tuple(color) else 0
                    self.tinte_pantalla = tuple(color) + (a0 + (alfa - a0) * k,)
                yield
            self.tinte_pantalla = None if color is None else tuple(color) + (alfa,)
        return acc()

    def destello(self, color=(255, 255, 255), frames=12, pico=1.0):
        """Fogonazo: la pantalla se llena de 'color' y vuelve (explosiones, luz de la caja...)."""
        def acc():
            prev = self.tinte_pantalla
            for f in range(frames):
                self.tinte_pantalla = tuple(color) + (pico * (1 - f / frames),)
                yield
            self.tinte_pantalla = prev
        return acc()

    def poner_filtro(self, filtro):
        """Filtro para toda la pantalla: 'crt' (tele vieja: barrido, viñeta, ruido), 'sepia', una función
        propia (PIL RGB, t) -> PIL RGB, o None para quitarlo."""
        def acc():
            self.filtro = {'crt': filtro_crt, 'sepia': filtro_sepia}[filtro] if isinstance(filtro, str) else filtro
            yield
        return acc()

    def animacion(self, imgs, x, y, frames, cada=4, pantalla=False, centro=True):
        """Efecto animado (humo, fuego, chispas...) durante 'frames' frames; imgs se alternan cada 'cada'
        frames. x, y en px de mapa (o de pantalla con pantalla=True); con centro=True es el centro de la
        imagen. Va encima de los personajes. Ponlo en paralelo con otras acciones."""
        imgs = [imagen(i) if isinstance(i, str) else i for i in imgs]

        def acc():
            for f in range(frames):
                img = imgs[(f // cada) % len(imgs)]
                ox, oy = (img.width // 2, img.height // 2) if centro else (0, 0)
                (self.efectos_pantalla if pantalla else self.efectos).append((img, x - ox, y - oy))
                yield
        return acc()

    def camara_mover(self, tx, ty, frames=30):
        """Paneo suave de la cámara hasta centrarla en el tile (tx, ty); se queda fija allí."""
        def acc():
            o = self.objetivo_camara
            if isinstance(o, Personaje):
                x0, y0 = o.x + 8, o.y + 8 - o.elevacion
            elif o is None:
                x0, y0 = self.camx + ANCHO // 2, self.camy + ALTO // 2
            else:
                x0, y0 = o
            f_el = getattr(self.mapa, 'elevacion', None)
            x1, y1 = tx * TILE + 8, ty * TILE + 8 - (f_el(tx * TILE, ty * TILE) if f_el else 0)
            for f in range(1, frames + 1):
                k = f / frames
                k = k * k * (3 - 2 * k)
                self.objetivo_camara = (x0 + (x1 - x0) * k, y0 + (y1 - y0) * k)
                yield
        return acc()

    def temblor_pantalla(self, frames=20, amplitud=3):
        """La pantalla vibra y se va calmando."""
        def acc():
            for f in range(frames):
                a = amplitud * (1 - f / frames)
                self.temblor = (int(a if f % 2 else -a), int(a / 2 if f % 4 < 2 else -a / 2))
                yield
            self.temblor = (0, 0)
        return acc()

    # -------------------------------------------------- render

    def _actualizar_camara(self):
        o = self.objetivo_camara
        if o is None:
            return
        cx, cy = (o.x + 8, o.y + 8 - o.elevacion) if isinstance(o, Personaje) else o
        x0, y0, x1, y1 = getattr(self.mapa, 'limites', (0, 0, self.mapa.ancho * TILE, self.mapa.alto * TILE))
        # si la sala es más pequeña que la pantalla (interiores), se centra en negro como en el juego
        self.camx = (x0 + x1 - ANCHO) // 2 if x1 - x0 <= ANCHO else min(max(cx - ANCHO // 2, x0), x1 - ANCHO)
        self.camy = (y0 + y1 - ALTO) // 2 if y1 - y0 <= ALTO else min(max(cy - ALTO // 2, y0), y1 - ALTO)

    def dibujar(self):
        lienzo = Image.new('RGBA', (ANCHO, ALTO), (0, 0, 0, 255))
        self._actualizar_camara()
        cx, cy = int(self.camx) + self.temblor[0], int(self.camy) + self.temblor[1]
        self.mapa.dibujar_suelo(lienzo, cx, cy, self.t)
        cosas = self.mapa.dibujables() + [(p.y + TILE, p.dibujar) for p in self.personajes]
        for _, dib in sorted(cosas, key=lambda c: c[0]):
            dib(lienzo, cx, cy)
        for img, x, y in self.efectos:
            _pegar(lienzo, img, int(x - cx), int(y - cy))
        self.efectos = []
        for p in self.personajes:
            p.dibujar_burbuja(lienzo, cx, cy)
        for img, x, y, a, _ in sorted(self.capas.values(), key=lambda c: c[4]):
            if a < 1:
                img = img.copy()
                img.putalpha(img.getchannel('A').point(lambda v, a=a: int(v * a)))
            _pegar(lienzo, img, int(x), int(y))
        for img, x, y in self.efectos_pantalla:
            _pegar(lienzo, img, int(x), int(y))
        self.efectos_pantalla = []
        if self.tinte_pantalla and self.tinte_pantalla[3] > 0:
            r, g, b, a = self.tinte_pantalla
            lienzo.alpha_composite(Image.new('RGBA', (ANCHO, ALTO), (int(r), int(g), int(b), int(255 * min(1, a)))))
        if self.filtro:
            lienzo = self.filtro(lienzo.convert('RGB'), self.t).convert('RGBA')
        sub = self._subtitulo()
        if sub:
            self._dibujar_dialogo(lienzo, *sub)
        elif self.dialogo_activo:
            self._dibujar_dialogo(lienzo, *self.dialogo_activo)
        if self.negro > 0:
            capa = Image.new('RGBA', (ANCHO, ALTO), (0, 0, 0, int(255 * self.negro)))
            lienzo.alpha_composite(capa)
        return lienzo.convert('RGB')

    def _subtitulo(self):
        """(líneas visibles, flecha) del subtítulo que toca en este frame, o None."""
        ahora = self.ahora
        for t_ini, t_fin, texto, *tipo in self.subs:
            if t_ini <= ahora < t_fin:
                tipo = tipo[0] if tipo else None
                lineas = texto.split('\n') if '\n' in texto else envolver(texto)
                paginas = [lineas[i:i + 2] for i in range(0, len(lineas), 2)]
                pesos = [max(1, sum(len(l) for l in p)) for p in paginas]
                total = sum(pesos)
                t = t_ini
                for k, (pag, w) in enumerate(zip(paginas, pesos)):
                    dur = (t_fin - t_ini) * w / total
                    if ahora < t + dur or k == len(paginas) - 1:
                        n = sum(len(l) for l in pag)
                        escritos = int((ahora - t) * self.fps * 1.5) + 1   # 1,5 letras por frame
                        return (_recortar(pag, escritos), escritos >= n, tipo)
                    t += dur
        return None

    def _dibujar_dialogo(self, lienzo, lineas, flecha, tipo=None):
        x, y, w, h = self.ventana or (2, 144, 252, 46)
        lienzo.alpha_composite(ventana_mensaje(w, h, self.tipo_ventana if tipo is None else tipo), (x, y))
        f = fuente()
        for i, l in enumerate(lineas):
            f.dibujar(lienzo, l, x + 14, y + 6 + i * 16)
        if flecha:
            fr = frames_flecha()
            img = fr[(self.t // 4) % len(fr)]
            lienzo.alpha_composite(img, (x + w - 30, y + h - 14))

    def frames(self):
        """Genera todos los frames (PIL.Image 256x192) de la escena."""
        self.t = 0
        for paso in self.pasos:
            activas = list(paso)
            while activas:
                vivas = []
                for a in activas:
                    try:
                        next(a)
                        vivas.append(a)
                    except StopIteration:
                        pass
                activas = vivas
                if not activas:
                    break
                self._avanzar_fondo()
                yield self.dibujar()
                self.t += 1
        yield self.dibujar()

    def _avanzar_fondo(self):
        vivas = []
        for a in self.fondo:
            try:
                next(a)
                vivas.append(a)
            except StopIteration:
                pass
        self.fondo = vivas

    def en_paralelo(self, *acciones):
        """Acción (1 frame) que lanza otras acciones en segundo plano: siguen corriendo mientras el guion
        avanza (humo que sale cada poco, alguien que camina al fondo...). Empiezan en el frame siguiente."""
        def acc():
            self.fondo.extend(acciones)
            yield
        return acc()

    # -------------------------------------------------- exportar

    def renderizar(self, salida, gif=True, mp4=True, hoja_contacto=True, cada=10):
        """Escribe <salida>.gif, <salida>.mp4 (con sonido si la escena usa musica()/sonido()/dialogo())
        y una hoja de contactos en la carpeta de trabajo (un frame de cada 'cada', para revisar la escena sin reproducirla)."""
        os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
        self.audio = []
        fr = [im.resize((ANCHO * self.escala, ALTO * self.escala), Image.NEAREST) for im in self.frames()]
        print('%d frames (%.1f s a %d fps)' % (len(fr), len(fr) / self.fps, self.fps))
        wav = None
        if self.audio and mp4:
            from . import audio
            wav = _aux(salida, '_audio.wav')
            audio.guardar_wav(wav, audio.mezclar(self.audio, len(fr) / self.fps, self.fps))
        if gif:
            fr[0].save(salida + '.gif', save_all=True, append_images=fr[1:], duration=round(1000 / self.fps),
                       loop=0, optimize=False, disposal=1)
            print('->', salida + '.gif')
        if mp4 and shutil.which('ffmpeg'):
            tmp = tempfile.mkdtemp()
            try:
                for i, im in enumerate(fr):
                    im.save(os.path.join(tmp, '%05d.png' % i))
                pista = ['-i', wav, '-c:a', 'aac', '-b:a', '192k', '-shortest'] if wav else []
                subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(self.fps),
                                '-i', os.path.join(tmp, '%05d.png')] + pista + ['-c:v', 'libx264', '-pix_fmt',
                                'yuv420p', '-crf', '16', salida + '.mp4'], check=True)
                print('->', salida + '.mp4' + (' (con sonido)' if wav else ''))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
                if wav and os.path.exists(wav):
                    os.remove(wav)
        if hoja_contacto:
            sel = fr[::cada]
            cols = 6
            pw, ph = ANCHO, ALTO
            hoja = Image.new('RGB', (cols * pw, ((len(sel) + cols - 1) // cols) * ph))
            for i, im in enumerate(sel):
                hoja.paste(im.resize((pw, ph), Image.NEAREST), ((i % cols) * pw, (i // cols) * ph))
            hoja.save(_aux(salida, '_hoja.png'))
            print('->', _aux(salida, '_hoja.png'))
        return fr

    def exportar(self, salida, duracion=None, cada=15, audio_base=None, desde=None):
        """Render en streaming para escenas largas (minutos): los frames van directos a ffmpeg sin guardarse
        en memoria. No hace GIF. Escribe <salida>.mp4, <salida>_hoja.png (1 de cada 'cada' frames, con el
        segundo absoluto) y, si hay efectos o música del juego, <salida>_sfx.wav (para el montaje final).
        duracion: segundos exactos del vídeo (recorta o alarga con el último frame).
        audio_base: wav externo (voces, música) del que se toma el tramo [t0, t0 + duracion] para el MP4.
        desde: segundo absoluto desde el que empezar a escribir (para revisar el final de una escena)."""
        from PIL import ImageDraw
        os.makedirs(os.path.dirname(os.path.abspath(salida)), exist_ok=True)
        self.audio = []
        n_total = None if duracion is None else int(round(duracion * self.fps))
        f0 = 0 if desde is None else int(round((desde - self.t0) * self.fps))
        W, H = ANCHO * self.escala, ALTO * self.escala
        tmp_mp4 = _aux(salida, '_video.mp4')
        proc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
                                 '-s', '%dx%d' % (W, H), '-framerate', str(self.fps), '-i', '-', '-c:v', 'libx264',
                                 '-pix_fmt', 'yuv420p', '-crf', '16', tmp_mp4], stdin=subprocess.PIPE)
        hoja = []
        n = 0
        ultimo = None
        for i, im in enumerate(self.frames()):
            if n_total is not None and i >= n_total:
                break
            ultimo = im
            if i < f0:
                continue
            proc.stdin.write(im.resize((W, H), Image.NEAREST).tobytes())
            if (i - f0) % cada == 0:
                hoja.append((self.t0 + i / self.fps, im))
            n += 1
        if n_total is not None:
            if f0 + n < n_total:
                print('(la escena dura %.2f s; se alarga el último frame hasta %.2f s)' % ((f0 + n) / self.fps, duracion))
            while f0 + n < n_total:
                proc.stdin.write(ultimo.resize((W, H), Image.NEAREST).tobytes())
                n += 1
        proc.stdin.close()
        proc.wait()
        dur = n / self.fps
        print('%d frames (%.2f s a %d fps)' % (n, dur, self.fps))
        sfx = None
        if self.audio:
            from . import audio
            sfx = _aux(salida, '_sfx.wav')
            ev = [(fr - f0, *resto) for fr, *resto in self.audio if fr >= f0]
            audio.guardar_wav(sfx, audio.mezclar(ev, dur, self.fps))
        entradas, filtro = [], None
        t_ini = self.t0 + f0 / self.fps
        if audio_base:
            entradas += ['-ss', '%.4f' % t_ini, '-t', '%.4f' % dur, '-i', audio_base]
        if sfx:
            entradas += ['-i', sfx]
        if audio_base and sfx:
            filtro = ['-filter_complex', '[1:a][2:a]amix=inputs=2:normalize=0[a]', '-map', '0:v', '-map', '[a]']
        elif entradas:
            filtro = ['-map', '0:v', '-map', '1:a']
        if entradas:
            subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp_mp4] + entradas + filtro +
                           ['-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', '%.4f' % dur, salida + '.mp4'],
                           check=True)
            os.remove(tmp_mp4)
        else:
            shutil.move(tmp_mp4, salida + '.mp4')
        print('->', salida + '.mp4')
        cols = 6
        lam = Image.new('RGB', (cols * ANCHO, ((len(hoja) + cols - 1) // cols) * (ALTO + 12)), (20, 20, 20))
        d = ImageDraw.Draw(lam)
        for i, (seg, im) in enumerate(hoja):
            x, y = (i % cols) * ANCHO, (i // cols) * (ALTO + 12)
            lam.paste(im, (x, y + 12))
            d.text((x + 2, y), '%d:%05.2f' % (seg // 60, seg % 60), fill=(255, 255, 0))
        lam.save(_aux(salida, '_hoja.png'))
        print('->', _aux(salida, '_hoja.png'))


def envolver(texto, ancho=204):
    """Parte un texto en líneas que caben en la ventana de diálogo (ancho en px con la fuente del juego)."""
    f = fuente()
    lineas, actual = [], ''
    for palabra in texto.split():
        prueba = (actual + ' ' + palabra).strip()
        if f.ancho(prueba) <= ancho or not actual:
            actual = prueba
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _pegar(lienzo, img, x, y):
    """alpha_composite que admite posiciones fuera de pantalla (recorta)."""
    if x >= lienzo.width or y >= lienzo.height or x + img.width <= 0 or y + img.height <= 0:
        return
    if x < 0 or y < 0:
        img = img.crop((max(0, -x), max(0, -y), img.width, img.height))
        x, y = max(0, x), max(0, y)
    lienzo.alpha_composite(img, (x, y))


def _tenir(img, tinte):
    r, g, b, k = tinte
    mezcla = Image.blend(img.convert('RGBA'), Image.new('RGBA', img.size, (r, g, b, 255)), k)
    mezcla.putalpha(img.getchannel('A'))
    return mezcla


def filtro_crt(im, t=0):
    """Recuerdo en una tele vieja: tono verdoso, líneas de barrido, banda clara que baja, viñeta y ruido."""
    import numpy as np
    a = np.asarray(im).astype(np.float32)
    a = a * 0.65 + a.mean(axis=2, keepdims=True) * 0.35
    a *= np.array([0.86, 1.04, 0.92], np.float32)
    h, w = a.shape[:2]
    filas = np.arange(h)
    barrido = 1 - 0.18 * (filas % 3 == 0)
    banda = 1 + 0.12 * np.exp(-(((filas - (t * 3) % (h + 60) + 30) / 10.0) ** 2))
    a *= (barrido * banda)[:, None, None]
    yy, xx = np.mgrid[0:h, 0:w]
    vin = 1 - 0.45 * (((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) ** 1.5
    a *= np.clip(vin, 0.35, 1)[..., None]
    a += np.random.RandomState(t % 977).normal(0, 5, (h, w, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGB')


def filtro_sepia(im, t=0):
    import numpy as np
    lum = np.asarray(im).astype(np.float32) @ np.array([0.3, 0.59, 0.11], np.float32)
    out = np.stack([lum * 1.07 + 20, lum * 0.95 + 8, lum * 0.75], axis=2)
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def _recortar(lineas, n):
    out = []
    for l in lineas:
        out.append(l[:max(0, n)])
        n -= len(l)
    return out
