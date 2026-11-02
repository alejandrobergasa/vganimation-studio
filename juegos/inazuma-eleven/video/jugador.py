"""Montaje de jugadores 3D de Inazuma Eleven a partir de las piezas de la ROM.

Un personaje del juego son cuatro modelos Nitro que comparten esqueleto (22 huesos, mismas coordenadas en
reposo): cuerpo (`model/char/pbb|psb`, con su banco de texturas `ptb`), cabeza (`pbh|psh`), cara (`pbf|psf`,
un plano en coordenadas del hueso `head`) y zapatos (`pbs|pss`). Las animaciones de esqueleto son BCA0 dentro
de `model/char/pcm.pkb` (una por PAC, miembro 00002). Se rasteriza con el mismo rasterizador que el resto de
modelos DS del repo.

La cara admite una foto: se sustituye la textura `face00` por la imagen y se reproyectan las UV del plano.
"""
import math
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from valedores import rutas

PREFIJO = 'data_iz/model/char/'
HUESO_CABEZA = 2          # ranura de pila donde el modelo de cabeza guarda la matriz del hueso `head`


@lru_cache(maxsize=1)
def _g():
    sys.path.insert(0, str(Path(rutas.juego_dir('nsmb')) / 'tools' / 'nsmb'))
    import nitro3d
    return nitro3d


def piezas(rec, tipo):
    """Orígenes ordenados de un tipo de pieza (pbb, pbh, pbf, pbs, psb, psh, psf, pss, ptb, pcm)."""
    return sorted(n for n in rec.registros if n.startswith(PREFIJO + tipo + '.pkb::') and n.count('::') == 1)


class _Textura(object):
    """TexLookup que puede sustituir una textura por una imagen propia (la cara)."""
    def __init__(self, nitros, reemplazos=None):
        self.base = _g().TexLookup(*nitros)
        self.reemplazos = reemplazos or {}

    def get(self, tex, pal):
        if tex in self.reemplazos:
            return self.reemplazos[tex]
        return self.base.get(tex, pal)


def textura_cara(foto, caja, lado=64, piel=None, ovalo=(.50, .56)):
    """Textura de cara a partir de una foto: `caja` es el recuadro (x0, y0, x1, y1) de la cara en la foto.

    Devuelve (array RGBA lado×lado, color de piel). Fuera del óvalo de la foto se rellena con el color de piel
    (mediana de la zona de las mejillas) para que el plano de la cara no deje huecos."""
    im = foto.convert('RGBA').crop(caja).resize((lado, lado), Image.Resampling.LANCZOS)
    a = np.asarray(im).astype('float32')
    if piel is None:
        zona = a[int(lado * .55):int(lado * .8), int(lado * .22):int(lado * .78), :3].reshape(-1, 3)
        piel = tuple(int(v) for v in np.median(zona, axis=0))
    y, x = np.mgrid[0:lado, 0:lado]
    r = np.sqrt(((x - lado / 2 + .5) / (lado * ovalo[0])) ** 2 + ((y - lado / 2 + .5) / (lado * ovalo[1])) ** 2)
    w = np.clip((1.0 - r) / .35, 0, 1)[..., None]
    base = np.zeros_like(a)
    base[..., :3] = piel
    base[..., 3] = 255
    a[..., 3] = 255
    return (a * w + base * (1 - w)).astype('uint8'), piel


# Huesos del esqueleto común (índices del modelo)
CHEST, ARM1L, ARM2L, ARM3L, ARM1R, ARM2R, ARM3R, HEAD = 3, 4, 5, 6, 7, 8, 9, 10
LEG1L, LEG2L, LEG3L, LEG1R, LEG2R, LEG3R, WAIST = 16, 17, 18, 19, 20, 21, 2


def _rot(ax, ay, az):
    cx, sx, cy, sy, cz, sz = math.cos(ax), math.sin(ax), math.cos(ay), math.sin(ay), math.cos(az), math.sin(az)
    X = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Y = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Z = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Z @ Y @ X


class Pose:
    """«Animación» procedural sobre el esqueleto del juego: `fn(fotograma) -> {hueso: (rx, ry, rz) en rad}`.

    Se suma a la rotación local de cada hueso (la pose de reposo del modelo es una T). Con el mismo
    contrato que las animaciones BCA (`sample`), así que sirve en `Model.triangles(anim, frame)`."""
    def __init__(self, fn, num_frames=1):
        self.fn, self.num_frames, self.name = fn, num_frames, 'pose'

    def sample(self, i, frame, t, r, s):
        e = self.fn(frame).get(i)
        if e is None:
            return t, r, s
        R = _rot(*e)
        return t, (R if r is None else r @ R), s


def reposo(f=0):
    """Brazos caídos, rodillas rectas, respiración ligera."""
    b = .02 * math.sin(f / 30 * 2 * math.pi * .5)
    return {ARM1L: (0, 0, -1.30 + b), ARM1R: (0, 0, 1.30 - b), ARM2L: (0, 0, -.12), ARM2R: (0, 0, .12),
            CHEST: (b, 0, 0)}


def camina(f=0, ciclo=36):
    a = math.sin(f / ciclo * 2 * math.pi)
    d = {ARM1L: (-.5 * a, 0, -1.25), ARM1R: (.5 * a, 0, 1.25), ARM2L: (-.35 * max(0, -a), 0, -.2), ARM2R: (-.35 * max(0, a), 0, .2),
         LEG1L: (.55 * a, 0, 0), LEG1R: (-.55 * a, 0, 0),
         LEG2L: (.5 * max(0, -a), 0, 0), LEG2R: (.5 * max(0, a), 0, 0),
         WAIST: (0, 0, .03 * a)}
    return d


def habla(f=0):
    """Gesticula con una mano mientras habla."""
    a = math.sin(f / 30 * 2 * math.pi * 1.6)
    d = reposo(f)
    d[ARM1R] = (0, 0, .75 + .12 * a)
    d[ARM2R] = (0, 0, .15 + .45 * a * a)
    d[HEAD] = (.05 * a, .08 * math.sin(f / 30 * 2 * math.pi * .7), 0)
    return d


def alegre(f=0):
    """Brazos arriba y saltito."""
    a = abs(math.sin(f / 30 * 2 * math.pi * 1.5))
    return {ARM1L: (0, 0, -2.5 + .25 * a), ARM1R: (0, 0, 2.5 - .25 * a), ARM2L: (0, 0, -.2), ARM2R: (0, 0, .2),
            LEG1L: (-.2 * a, 0, 0), LEG1R: (-.2 * a, 0, 0), HEAD: (-.1, 0, 0)}


def triste(f=0):
    """Hombros caídos y cabeza gacha."""
    a = .03 * math.sin(f / 30 * 2 * math.pi * .35)
    return {ARM1L: (0, 0, -1.42), ARM1R: (0, 0, 1.42), ARM2L: (0, 0, -.1), ARM2R: (0, 0, .1),
            CHEST: (.18 + a, 0, 0), HEAD: (.42 + a, 0, .05)}


def paga(f=0):
    """Extiende el brazo derecho hacia delante (entrega la moneda)."""
    return {ARM1R: (-1.2, 0, 1.0), ARM2R: (-.3, 0, .1), ARM1L: (0, 0, -1.3), ARM2L: (0, 0, -.12)}


class Jugador:
    """Actor para Plano.sprite: `frame(t)` devuelve la imagen RGBA del jugador en el instante t."""
    def __init__(self, rec, cuerpo, banco, cabeza, cara, zapatos=None, animacion=None, foto=None,
                 tamano=(360, 520), escala=19.0, giro=0.0, proyeccion=(-2.0, 2.0, -0.8, 2.2), fps=30,
                 fotograma=None, sombra=True, origen=None):
        g = _g()
        nit = lambda o: g.Nitro(rec.datos(o))
        self.cuerpo, self.cabeza, self.cara = nit(cuerpo), nit(cabeza), nit(cara)
        self.zapatos = nit(zapatos) if zapatos else None
        self.banco = nit(banco)
        self.anim = None
        if animacion:
            clips = nit(animacion).anims
            self.anim = clips[0] if clips else None
        self.fps, self.tamano, self.escala, self.giro, self.sombra = fps, tamano, escala, giro, sombra
        self.fotograma = fotograma
        self.origen = origen
        nits = [self.banco, self.cabeza, self.cara] + ([self.zapatos] if self.zapatos else [])
        rep = {}
        self.proyeccion = proyeccion
        if foto is not None:
            rep['face00'] = foto
        self.tex = _Textura(nits, rep)
        self._cache = {}

    def _rot(self, p, a):
        c, s = math.cos(a), math.sin(a)
        return (c * p[0] + s * p[2], p[1], -s * p[0] + c * p[2])

    def _tris(self, nit, anim, f, raiz=None):
        m = nit.models[0]
        tr = m.triangles(anim, f, root=raiz)
        return m, tr

    def _giro(self, tris):
        a = self.giro
        if not a:
            return tris
        out = []
        for mi, vs in tris:
            nv = []
            for v in vs:
                p = self._rot(v[:3], a)
                n = self._rot(v[6], a) if len(v) > 6 else None
                nv.append((*p, *v[3:6], *( (n,) if n is not None else ())))
            out.append((mi, nv))
        return out

    def _reproyectar(self, tris, locales, tam):
        """UV nuevas por proyección frontal de los vértices (en coordenadas del hueso de la cabeza)."""
        x0, x1, y0, y1 = self.proyeccion
        out = []
        for (mi, vs), (_, vl) in zip(tris, locales):
            nv = []
            for v, l in zip(vs, vl):
                u = (l[0] - x0) / (x1 - x0) * tam[1]
                w = (y1 - l[1]) / (y1 - y0) * tam[0]
                nv.append((v[0], v[1], v[2], u, w, *v[5:]))
            out.append((mi, nv))
        return out

    def render(self, f):
        g = _g()
        items = []
        mb, trb = self._tris(self.cuerpo, self.anim, f)
        mh, trh = self._tris(self.cabeza, self.anim, f)
        raiz = mh.last_stack[HUESO_CABEZA]
        mf, trf = self._tris(self.cara, None, 0, raiz=raiz)
        _, trf_local = self._tris(self.cara, None, 0)
        items.append((self._giro(trb), mb, None, 0))
        items.append((self._giro(trh), mh, None, 0))
        if 'face00' in self.tex.reemplazos:
            trf = self._reproyectar(trf, trf_local, self.tex.reemplazos['face00'].shape)
        items.append((self._giro(trf), mf, None, 0))
        if self.zapatos:
            ms, trs = self._tris(self.zapatos, self.anim, f)
            items.append((self._giro(trs), ms, None, 0))
        w, h = self.tamano
        rgba, _ = g.render_items(items, self.tex, scale=self.escala, size=self.tamano,
                                 origin=self.origen or (w // 2, h - 22), shade=True)
        im = Image.fromarray(rgba)
        return im

    def frame(self, t):
        f = self.fotograma(t) if self.fotograma else t * self.fps
        k = round(f * 2) / 2 if self.anim else 0
        if k not in self._cache:
            if len(self._cache) > 40:
                self._cache.pop(next(iter(self._cache)))
            self._cache[k] = self.render(k)
        return self._cache[k]
