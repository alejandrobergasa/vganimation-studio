"""Escena 3D real para los modelos de la DS: actores, cámara en perspectiva, luces, partículas y calcas.

A diferencia de `VistaModelo` (un modelo ortográfico por capa), aquí todos los objetos comparten
perspectiva y profundidad: un actor puede pasar por delante de otro, la cámara puede entrar en el
escenario y un primer plano tiene la deformación real de la lente. Unidades: las del modelo, y en
arriba, +z hacia la cámara cuando el actor mira de frente. Un `Escena3D` tiene `frame(t)`, así que se
usa como cualquier otra capa: `plano.escena(escena)`.
"""
import math

import numpy as np
from PIL import Image

from . import raster3d
from .video_nds import Pista, valor


def _vec(v, t):
    """Vector o función del tiempo que devuelve un vector."""
    r = v(t) if callable(v) else v
    return np.array([valor(c, t) for c in r], np.float64)


def _unitario(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v


# Encuadres de cine: fracción de altura del personaje que se ve y punto al que se mira.
ENCUADRES = {
    'detalle':     (0.24, 0.73),   # solo la cara
    'primer_plano': (0.44, 0.68),  # la cara queda en el tercio superior: deja sitio a un diálogo
    'medio':       (0.66, 0.60),
    'americano':   (0.85, 0.56),
    'entero':      (1.25, 0.50),
    'general':     (2.60, 0.45),
    'gran_general': (6.00, 0.40),
}


class Camara:
    """Cámara con posición, objetivo, lente y balanceo animables mediante claves o funciones."""

    def __init__(self, posicion=(0, 8, 30), objetivo=(0, 5, 0), fov=40, balanceo=0):
        self.claves = [(0.0, posicion, objetivo, fov, balanceo, 'suave')]
        self.temblores = []
        self.seguimiento = None
        self.aspecto = 16 / 9          # La escena lo actualiza al dibujar: en vertical, los planos se alejan.

    def clave(self, t, posicion=None, objetivo=None, fov=None, balanceo=None, curva='suave'):
        """Añade una clave: la cámara llega a ese estado en `t`. Lo que no se indique se conserva."""
        previa = self.claves[-1]
        self.claves.append((float(t), previa[1] if posicion is None else posicion,
                            previa[2] if objetivo is None else objetivo,
                            previa[3] if fov is None else fov,
                            previa[4] if balanceo is None else balanceo, curva))
        self.claves.sort(key=lambda c: c[0])
        return self

    def corte(self, t, posicion, objetivo=None, fov=None, balanceo=None):
        """Cambio instantáneo de plano en `t`."""
        previa = self._clave_en(t)
        self.clave(t - 1e-4, posicion=previa[0], objetivo=previa[1], fov=previa[2], balanceo=previa[3], curva='recta')
        return self.clave(t, posicion, objetivo, fov, balanceo, curva='corte')

    def _clave_en(self, t):
        anterior = self.claves[0]
        for c in self.claves:
            if c[0] <= t:
                anterior = c
        return anterior[1:5]

    def encuadre(self, tipo, actor, t=0, angulo=0.0, altura=0.0, curva='suave', fov=32, corte=False,
                 lado=0.0, seguir=True):
        """Plano de un actor: `angulo` respecto a su frente (rad), `altura` sube o baja la cámara
        (picado > 0, contrapicado < 0), `lado` lo desplaza en cuadro. Con `seguir` acompaña al actor."""
        if tipo not in ENCUADRES:
            raise ValueError('Encuadre desconocido; hay: ' + ', '.join(ENCUADRES))
        fraccion, mirada = ENCUADRES[tipo]
        alto = actor.altura()
        visible = alto * fraccion
        distancia = visible / 2 / math.tan(math.radians(fov) / 2)
        ang0 = angulo

        def obj(tt):
            c = actor.posicion(tt if seguir else t)
            return (c[0] + lado * visible * math.cos(ang0), c[1] + alto * mirada, c[2] - lado * visible * math.sin(ang0))

        def pos(tt):
            c = actor.posicion(tt if seguir else t)
            g = valor(actor.giro, tt if seguir else t) + ang0
            d = distancia * max(1.0, 0.85 / self.aspecto)
            return (c[0] + d * math.sin(g),
                    c[1] + alto * mirada + altura * d,
                    c[2] + d * math.cos(g))
        return (self.corte(t, pos, obj, fov) if corte else self.clave(t, pos, obj, fov, curva=curva))

    def dos_personajes(self, a, b, t=0, angulo=0.0, altura=0.08, margen=1.5, fov=32, curva='suave', corte=False):
        """Plano conjunto que mantiene a dos actores en cuadro aunque se muevan."""
        def obj(tt):
            return (a.posicion(tt) + b.posicion(tt)) / 2 + np.array([0, a.altura() * 0.55, 0])

        def pos(tt):
            ca, cb = a.posicion(tt), b.posicion(tt)
            sep = np.linalg.norm(ca - cb) + a.altura() * margen
            d = sep / 2 / math.tan(math.radians(fov) / 2) / min(1.0, self.aspecto)
            m = (ca + cb) / 2
            # Perpendicular a la línea que los une: el plano respeta el eje de 180 grados.
            eje = _unitario(cb - ca + np.array([1e-4, 0, 0]))
            normal = np.array([-eje[2], 0, eje[0]])
            if normal[2] < 0:
                normal = -normal
            c, s = math.cos(angulo), math.sin(angulo)
            normal = np.array([normal[0] * c + normal[2] * s, 0, -normal[0] * s + normal[2] * c])
            return m + normal * d + np.array([0, a.altura() * 0.55 + altura * d, 0])
        return (self.corte(t, pos, obj, fov) if corte else self.clave(t, pos, obj, fov, curva=curva))

    def orbita(self, centro, radio, altura, angulo0, angulo1, desde, duracion, fov=None):
        """Giro alrededor de un punto o actor, de `angulo0` a `angulo1` (rad)."""
        curva = Pista([(desde, angulo0), (desde + duracion, angulo1)], curva='suave')

        def cen(tt):
            return centro.centro(tt) if hasattr(centro, 'centro') else _vec(centro, tt)

        def pos(tt):
            c, g = cen(tt), curva(tt)
            return (c[0] + radio * math.sin(g), c[1] + altura, c[2] + radio * math.cos(g))
        self.clave(desde, pos, cen, fov, curva='corte' if not self.claves else 'suave')
        return self.clave(desde + duracion, pos, cen, fov, curva='recta')

    def temblor(self, desde, duracion, intensidad=0.35, frecuencia=17.0):
        """Vibración con caída progresiva: golpes, explosiones, pisotones."""
        self.temblores.append((desde, duracion, intensidad, frecuencia))
        return self

    def estado(self, t):
        """(posición, objetivo, fov, balanceo) evaluados en `t`."""
        cl = self.claves
        a = cl[0]
        b = None
        for c in cl:
            if c[0] <= t:
                a = c
            elif b is None:
                b = c
        p0, o0, f0, r0 = _vec(a[1], t), _vec(a[2], t), valor(a[3], t), valor(a[4], t)
        if b is not None and b[5] != 'corte':
            u = (t - a[0]) / max(b[0] - a[0], 1e-6)
            if b[5] == 'suave':
                u = u * u * (3 - 2 * u)
            p0 = p0 + (_vec(b[1], t) - p0) * u
            o0 = o0 + (_vec(b[2], t) - o0) * u
            f0 = f0 + (valor(b[3], t) - f0) * u
            r0 = r0 + (valor(b[4], t) - r0) * u
        for desde, dur, k, fr in self.temblores:
            if desde <= t < desde + dur:
                caida = 1 - (t - desde) / dur
                o0 = o0 + k * caida * np.array([math.sin(t * fr * 6.1), math.sin(t * fr * 7.3 + 1), math.sin(t * fr * 5.2 + 2)])
        return p0, o0, f0, r0


class Actor3D:
    """Modelo con transformación animada, animaciones nativas mezcladas y poses añadidas."""

    def __init__(self, modelo, x=0, y=0, z=0, giro=0, escala=1, animaciones=None, nombre=None, sombra=False):
        self.modelo, self.nombre, self.sombra = modelo, nombre, sombra
        self.x, self.y, self.z, self.giro, self.escala = x, y, z, giro, escala
        self.animaciones = dict(animaciones or {})
        self.linea = []
        self.extras = []
        self.calcas = []
        self.visible = True
        self.ocultos = set()
        self.base = modelo.paquete()
        self.reposo = modelo.locales_reposo()
        self.inversas = np.array([o['global_inv'] for o in modelo.objetos_party])
        self._alto = None
        self._memo = (None, None)

    # ---------------------------------------------------------------- animación

    def anim(self, animacion, desde=0.0, velocidad=1.0, bucle=True, mezcla=0.18, inicio=0.0):
        """Encadena una animación en `desde`, fundida con la anterior durante `mezcla` segundos."""
        a = self.animaciones[animacion] if isinstance(animacion, str) else animacion
        if isinstance(animacion, str) and animacion not in self.animaciones:
            raise ValueError('El actor no tiene la animación %r' % animacion)
        self.linea.append((float(desde), a, velocidad, bucle, mezcla, inicio))
        self.linea.sort(key=lambda e: e[0])
        self._memo = (None, None)
        return self

    def pose(self, funcion):
        """Añade una pose sobre la animación: función t -> {objeto: (rx, ry, rz)} en radianes."""
        self.extras.append(funcion)
        return self

    def mirar(self, objetivo, desde=0.0, hasta=math.inf, hueso='face', limite=0.9, fundido=0.25):
        """Gira la cabeza hacia un actor o punto durante un intervalo, sin romper la animación."""
        def f(t):
            if not desde <= t < hasta:
                return {}
            k = min(1.0, (t - desde) / fundido, (hasta - t) / fundido)
            # Sin poses añadidas: dos actores que se miran entre sí no deben consultarse sin fin.
            destino = objetivo.posicion_cabeza(t, extras=False) if hasattr(objetivo, 'posicion_cabeza') else _vec(objetivo, t)
            d = destino - self.posicion_cabeza(t, extras=False)
            g = valor(self.giro, t)
            yaw = (math.atan2(d[0], d[2]) - g + math.pi) % (2 * math.pi) - math.pi
            pitch = -math.atan2(d[1], math.hypot(d[0], d[2]))
            return {hueso: (k * max(-limite, min(limite, pitch)), k * max(-limite, min(limite, yaw)), 0.0)}
        return self.pose(f)

    def _valores_animacion(self, entrada, t):
        desde, a, vel, bucle, _m, inicio = entrada
        cuadro = inicio + (t - desde) * a.FPS * vel
        cuadro = cuadro % a.cuadros if bucle else min(max(cuadro, 0.0), a.cuadros)
        return a.muestrear(cuadro)

    def _aplicar(self, base, muestra):
        v = base.copy()
        indice = self.modelo.indice_objeto
        for nombre, (tr, ro, es) in muestra.items():
            i = indice.get(nombre)
            if i is None:
                continue
            for k, x in enumerate((*tr, *ro, *es)):
                if x is not None:
                    v[i, k] = x
        return v

    def locales(self, t, extras=True):
        """Valores locales (objetos, 9) en `t`: animación, mezcla entre clips y poses añadidas."""
        v = self.reposo
        actual = previa = None
        for e in self.linea:
            if e[0] <= t:
                previa, actual = actual, e
        if actual is not None:
            v = self._aplicar(self.reposo, self._valores_animacion(actual, t))
            if previa is not None and actual[4] > 0 and t < actual[0] + actual[4]:
                w = (t - actual[0]) / actual[4]
                w = w * w * (3 - 2 * w)
                antes = self._aplicar(self.reposo, self._valores_animacion(previa, t))
                dif = v - antes
                dif[:, 3:6] = (dif[:, 3:6] + math.pi) % (2 * math.pi) - math.pi
                v = antes + dif * w
        if extras and self.extras:
            v = v.copy()
            indice = self.modelo.indice_objeto
            for f in self.extras:
                for nombre, rot in f(t).items():
                    i = indice.get(nombre, nombre if isinstance(nombre, int) else None)
                    if i is not None:
                        v[i, 3:6] += rot
        return v

    # ---------------------------------------------------------------- transformación

    def posicion(self, t):
        return np.array([valor(self.x, t), valor(self.y, t), valor(self.z, t)], np.float64)

    def mundo(self, t):
        """Matriz 3x4 del actor en el mundo (giro en Y y escala uniforme)."""
        g, e = valor(self.giro, t), valor(self.escala, t)
        c, s = math.cos(g) * e, math.sin(g) * e
        return np.array([[c, 0, s, valor(self.x, t)], [0, e, 0, valor(self.y, t)], [-s, 0, c, valor(self.z, t)]])

    def hueso(self, nombre, t=0.0, extras=True):
        """Posición en el mundo de un objeto del modelo (para enganchar cámara o partículas)."""
        g = self.modelo.globales(self.locales(t, extras))[self.modelo.indice_objeto[nombre]]
        return self.mundo(t) @ np.array([g[0, 3], g[1, 3], g[2, 3], 1.0])

    def posicion_cabeza(self, t=0.0, extras=True):
        i = self.modelo.indice_objeto
        return self.hueso('face', t, extras) if 'face' in i else self.centro(t)

    def altura(self):
        """Altura del actor de pie en unidades del mundo: la de la primera animación, o la de reposo."""
        if self._alto is None:
            p = self.transformar(self.linea[0][0] if self.linea else 0.0)[0]
            local = p[..., 1].reshape(-1) - valor(self.y, self.linea[0][0] if self.linea else 0.0)
            self._alto = max(float(local.max()), 1e-3)
        return self._alto

    def centro(self, t=0.0):
        return self.posicion(t) + np.array([0, self.altura() * 0.5, 0])

    def transformar(self, t):
        """Vértices y normales en el mundo, con la pose de `t`. Se memoriza por fotograma."""
        if self._memo[0] == t:
            return self._memo[1]
        base = self.base
        glob = self.modelo.globales(self.locales(t))
        delta = glob @ self.inversas
        rot = delta[:, :3, :3].astype(np.float32)
        tra = delta[:, :3, 3].astype(np.float32)
        p = np.einsum('tij,tvj->tvi', rot[base.obj], base.p) + tra[base.obj][:, None, :]
        n = np.einsum('tij,tvj->tvi', rot[base.obj], base.n)
        M = self.mundo(t).astype(np.float32)
        p = p @ M[:3, :3].T + M[:3, 3]
        n = n @ M[:3, :3].T
        self._memo = (t, (p, n))
        return p, n


class Particulas:
    """Partículas deterministas con textura de la ROM, siempre de cara a la cámara."""

    def __init__(self, imagen, origen, desde=0.0, cantidad=24, vida=0.8, velocidad=6.0, gravedad=-14.0,
                 tamano=1.0, tamano_final=None, dispersion=1.0, arriba=1.0, semilla=1, emision=0.0, alfa=1.0, giro=2.0):
        self.imagen = imagen.convert('RGBA') if hasattr(imagen, 'convert') else imagen
        self.origen, self.desde, self.vida = origen, desde, vida
        self.gravedad, self.tamano = gravedad, tamano
        self.tamano_final = tamano if tamano_final is None else tamano_final
        self.alfa = alfa
        r = np.random.default_rng(semilla)
        d = r.normal(size=(cantidad, 3))
        d[:, 1] = np.abs(d[:, 1]) * arriba
        d[:, [0, 2]] *= dispersion
        self.vel = _unitario_filas(d) * velocidad * r.uniform(0.45, 1.0, (cantidad, 1))
        self.retardo = r.uniform(0, max(emision, 1e-6), cantidad)
        self.vidas = vida * r.uniform(0.7, 1.0, cantidad)
        self.fase = r.uniform(0, 6.28, cantidad)
        self.giro = giro * r.uniform(-1, 1, cantidad)

    def instantes(self, t):
        """Lista de (posición, tamaño, alfa, ángulo) de las partículas vivas."""
        c = self.origen(self.desde) if callable(self.origen) else (
            self.origen.hueso('face', self.desde) if hasattr(self.origen, 'hueso') else np.asarray(self.origen, float))
        u = t - self.desde - self.retardo
        vivas = (u >= 0) & (u < self.vidas)
        salida = []
        for i in np.flatnonzero(vivas):
            k = u[i] / self.vidas[i]
            p = c + self.vel[i] * u[i] + np.array([0, 0.5 * self.gravedad * u[i] ** 2, 0])
            salida.append((p, self.tamano + (self.tamano_final - self.tamano) * k, self.alfa * (1 - k * k),
                           self.fase[i] + self.giro[i] * u[i]))
        return salida


def _unitario_filas(a):
    return a / np.maximum(np.linalg.norm(a, axis=1, keepdims=True), 1e-6)


def _sombra_textura():
    y, x = np.mgrid[0:32, 0:32] + 0.5
    r = np.hypot(x - 16, y - 16) / 16
    a = np.clip(1 - r, 0, 1) ** 0.7 * 150
    im = np.zeros((32, 32, 4), np.uint8)
    im[..., 3] = a.astype(np.uint8)
    return im


class Escena3D:
    """Conjunto de actores, cámara, fondo, luz y efectos. `frame(t)` devuelve la imagen renderizada."""

    def __init__(self, tamano=(640, 360), fondo=(40, 60, 110), camara=None, luz=(0.35, -0.75, -0.55),
                 ambiente=0.72, niebla=None, cerca=0.4):
        self.tamano = tuple(tamano)
        if any(n <= 0 for n in self.tamano):
            raise ValueError('Tamaño de escena no válido')
        self.fondo, self.camara = fondo, camara or Camara()
        self.luz = _unitario(np.array(luz, np.float64))
        self.ambiente, self.niebla, self.cerca = ambiente, niebla, cerca
        self.actores, self.particulas = [], []
        self.texturas = raster3d.Texturas()
        self._lotes_materiales = {}

    # ---------------------------------------------------------------- contenido

    def actor(self, modelo, **kw):
        a = modelo if isinstance(modelo, Actor3D) else Actor3D(modelo, **kw)
        self.actores.append(a)
        return a

    def emitir(self, particulas):
        self.particulas.append(particulas)
        return particulas

    # ---------------------------------------------------------------- render

    def _materiales(self, modelo):
        """Convierte los materiales del modelo a identificadores del banco de texturas."""
        clave = id(modelo)
        if clave in self._lotes_materiales:
            return self._lotes_materiales[clave]
        n = len(modelo.materials)
        tex, alfa, modo, tinte = np.full(n, -1, np.int64), np.ones(n, np.float32), np.zeros(n, np.int64), np.ones((n, 3), np.float32)
        for i, m in enumerate(modelo.materials):
            alfa[i] = m.alpha
            tinte[i] = m.diffuse
            if m.tex:
                im = modelo.get(m.tex, m.pal)
                if im is None:
                    continue
                tex[i] = self.texturas.registrar((id(modelo), m.tex), im, m.rep_s, m.rep_t, m.flip_s, m.flip_t)
                a = im[..., 3]
                if ((a > 0) & (a < 255)).any():
                    modo[i] = 1
            if m.alpha < 1:
                modo[i] = 1
        self._lotes_materiales[clave] = (tex, alfa, modo, tinte)
        return self._lotes_materiales[clave]

    def _proyectar(self, p, cam, tam):
        """Vértices del mundo a pantalla, recortando contra el plano cercano."""
        pos, r, u, f, focal = cam
        v = p - pos
        xc, yc, zc = v @ r, v @ u, v @ f
        return xc, yc, zc

    def _lote(self, p, luz, uv, tex, alfa, modo, tinte, cam):
        """Proyecta triángulos (t, 3, ...) a arrays del rasterizador."""
        pos, r, u, f, focal = cam
        W, H = self.tamano
        v = p.astype(np.float64) - pos
        xc, yc, zc = v @ r, v @ u, v @ f
        cerca = self.cerca
        delante = zc > cerca
        todos = delante.all(1)
        algunos = delante.any(1) & ~todos
        if algunos.any():
            # Triángulos que cruzan el plano cercano: se recortan uno a uno (son pocos).
            nuevos = []
            for t in np.flatnonzero(algunos):
                poly = []
                for a in range(3):
                    b = (a + 1) % 3
                    za, zb = zc[t, a], zc[t, b]
                    if za > cerca:
                        poly.append((xc[t, a], yc[t, a], za, uv[t, a, 0], uv[t, a, 1], luz[t, a]))
                    if (za > cerca) != (zb > cerca):
                        k = (cerca - za) / (zb - za)
                        poly.append((xc[t, a] + (xc[t, b] - xc[t, a]) * k, yc[t, a] + (yc[t, b] - yc[t, a]) * k, cerca,
                                     uv[t, a, 0] + (uv[t, b, 0] - uv[t, a, 0]) * k, uv[t, a, 1] + (uv[t, b, 1] - uv[t, a, 1]) * k,
                                     luz[t, a] + (luz[t, b] - luz[t, a]) * k))
                for k in range(1, len(poly) - 1):
                    nuevos.append((t, poly[0], poly[k], poly[k + 1]))
        i = np.flatnonzero(todos)
        X, Y, Z = xc[i], yc[i], zc[i]
        UV, L = uv[i], luz[i]
        T, A, M, C = tex[i], alfa[i], modo[i], tinte[i]
        if algunos.any() and nuevos:
            extra = np.array([[n[1], n[2], n[3]] for n in nuevos], np.float64)
            idx = np.array([n[0] for n in nuevos])
            X, Y, Z = np.concatenate([X, extra[..., 0]]), np.concatenate([Y, extra[..., 1]]), np.concatenate([Z, extra[..., 2]])
            UV = np.concatenate([UV, extra[..., 3:5].astype(np.float32)])
            L = np.concatenate([L, extra[..., 5].astype(np.float32)])
            T, A, M, C = np.concatenate([T, tex[idx]]), np.concatenate([A, alfa[idx]]), np.concatenate([M, modo[idx]]), np.concatenate([C, tinte[idx]])
        if not len(X):
            return None
        w = 1.0 / Z
        xy = np.stack([W / 2 + X * w * focal, H / 2 - Y * w * focal], -1).astype(np.float64)
        # Descarta lo que cae entero fuera de cuadro antes de entrar en el bucle compilado.
        mn, mx = xy.min(1), xy.max(1)
        ok = (mx[:, 0] > 0) & (mn[:, 0] < W) & (mx[:, 1] > 0) & (mn[:, 1] < H)
        return dict(xy=xy[ok], w_inv=w[ok].astype(np.float64), uv=(UV[ok].astype(np.float64) * w[ok][..., None]),
                    luz=(L[ok].astype(np.float64) * w[ok]), tex=T[ok], alfa=A[ok].astype(np.float64), modo=M[ok],
                    tinte=C[ok].astype(np.float64), prof=Z[ok].mean(1))

    def _cuadrado(self, centro, rx, ry, tex_id, alfa, cam, modo=1, tamano_tex=(1, 1), tinte=(1, 1, 1)):
        """Quad (dos triángulos) con los vectores rx, ry dados."""
        c = np.asarray(centro, np.float64)
        a, b, d, e = c - rx + ry, c + rx + ry, c + rx - ry, c - rx - ry
        p = np.array([[a, b, d], [a, d, e]])
        tw, th = tamano_tex
        uv = np.array([[[0, 0], [tw, 0], [tw, th]], [[0, 0], [tw, th], [0, th]]], np.float64)
        return self._lote(p, np.ones((2, 3), np.float64), uv, np.full(2, tex_id, np.int64),
                          np.full(2, alfa, np.float64), np.full(2, modo, np.int64),
                          np.tile(np.array(tinte, np.float64), (2, 1)), cam)

    def frame(self, t):
        W, H = self.tamano
        fondo = self.fondo
        if hasattr(fondo, 'frame'):
            fondo = fondo.frame(t)
        if isinstance(fondo, Image.Image):
            color = np.asarray(fondo.convert('RGBA').resize((W, H), Image.Resampling.NEAREST), np.float32) / 255.0
        elif callable(fondo):
            color = np.asarray(fondo(t, W, H), np.float32)
        else:
            color = np.zeros((H, W, 4), np.float32)
            color[..., :3] = np.array(fondo[:3], np.float32) / 255.0
            color[..., 3] = 1.0
        color = color.copy()
        zbuf = np.zeros((H, W), np.float32)
        self.camara.aspecto = self.tamano[0] / self.tamano[1]
        pos, obj, fov, bal = self.camara.estado(t)
        f = _unitario(obj - pos)
        r = _unitario(np.cross(f, np.array([0.0, 1.0, 0.0])))
        if np.linalg.norm(r) < 1e-6:
            r = np.array([1.0, 0, 0])
        u = np.cross(r, f)
        if bal:
            c, s = math.cos(bal), math.sin(bal)
            r, u = r * c + u * s, -r * s + u * c
        focal = H / 2 / math.tan(math.radians(fov) / 2)
        cam = (pos, r, u, f, focal)
        opacos, mezcla = [], []

        for a in self.actores:
            if not (a.visible(t) if callable(a.visible) else a.visible):
                continue
            p, n = a.transformar(t)
            m = a.modelo
            b = a.base
            tex, alfa, modo, tinte = self._materiales(m)
            luz = self.ambiente + (1 - self.ambiente) * np.maximum(0.0, -(n @ self.luz.astype(np.float32)))
            seleccion = np.ones(len(p), bool)
            if a.ocultos:
                oc = [i for i, mt in enumerate(m.materials) if mt.tex in a.ocultos or mt.name in a.ocultos]
                seleccion &= ~np.isin(b.mat, oc)
            s = np.flatnonzero(seleccion)
            lote = self._lote(p[s], luz[s], b.uv[s], tex[b.mat[s]], alfa[b.mat[s]], modo[b.mat[s]], tinte[b.mat[s]], cam)
            if lote is not None:
                es = lote['modo'] == 0
                opacos.append({k: v[es] for k, v in lote.items()})
                mezcla.append({k: v[~es] for k, v in lote.items()})
            if a.sombra:
                sid = self.texturas.registrar('__sombra', _sombra_textura())
                centro = a.posicion(t) + np.array([0, 0.03, 0])
                e = a.altura() * 0.28
                q = self._cuadrado(centro, np.array([e, 0, 0]), np.array([0, 0, -e]), sid, 1.0, cam, tamano_tex=(32, 32))
                if q is not None:
                    mezcla.append(q)
            for calca in a.calcas:
                tid = self.texturas.registrar(*calca.textura(t))
                i = calca.indices
                nt = len(i)
                q = self._lote(p[i], luz[i], calca.uv, np.full(nt, tid, np.int64), np.ones(nt, np.float32),
                               np.full(nt, 2, np.int64), np.ones((nt, 3), np.float32), cam)
                if q is not None:
                    mezcla.append(q)

        for grupo in self.particulas:
            tid = self.texturas.registrar(('__part', id(grupo)), np.asarray(grupo.imagen, np.uint8))
            th, tw = np.asarray(grupo.imagen).shape[:2]
            for cen, tam, al, ang in grupo.instantes(t):
                ca, sa = math.cos(ang) * tam, math.sin(ang) * tam
                q = self._cuadrado(cen, r * ca + u * sa, -r * sa + u * ca, tid, al, cam, tamano_tex=(tw, th))
                if q is not None:
                    mezcla.append(q)

        niebla = None
        if self.niebla:
            cerca, lejos, fuerza, col = self.niebla
            niebla = np.array([cerca, lejos, 0, fuerza, *(np.array(col, np.float32) / 255.0)], np.float32)
        for lote in opacos:
            raster3d.dibujar(color, zbuf, lote, self.texturas, niebla)
        mezcla = [m for m in mezcla if len(m['xy'])]
        if mezcla:
            junto = {k: np.concatenate([m[k] for m in mezcla]) for k in mezcla[0]}
            orden = np.argsort(-junto['prof'], kind='stable')
            raster3d.dibujar(color, zbuf, {k: v[orden] for k, v in junto.items()}, self.texturas, niebla)
        return Image.fromarray((np.clip(color, 0, 1) * 255).astype(np.uint8), 'RGBA')
