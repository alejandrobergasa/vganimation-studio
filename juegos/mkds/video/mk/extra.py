"""Piezas propias para cinemáticas con personajes a medida: mallas de cajas, texturas sustituidas y pasajeros.

- `caja` / `cilindro`: mallas sencillas (cigarro, huesos, luces de policía, aparato de alcoholemia...).
- `Pasajero`: un piloto de la ROM con texturas cambiadas (p. ej. la cara de Ábalos sobre el modelo de Mario) y pose libre.
- `cara_abalos`: textura 128x128 de media cara (centro en x=0, como las caras del juego) a partir de abalos.jpg."""
import os
import math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

import modelos as M
from . import escena as E, rutas


# ------------------------------------------------------------------ mallas simples

_CARAS = [  # (normal, cuatro esquinas en sentido antihorario visto desde fuera)
    ((0, 0, 1), [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)]),
    ((0, 0, -1), [(1, -1, -1), (-1, -1, -1), (-1, 1, -1), (1, 1, -1)]),
    ((1, 0, 0), [(1, -1, 1), (1, -1, -1), (1, 1, -1), (1, 1, 1)]),
    ((-1, 0, 0), [(-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1)]),
    ((0, 1, 0), [(-1, 1, 1), (1, 1, 1), (1, 1, -1), (-1, 1, -1)]),
    ((0, -1, 0), [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)]),
]


def caja(mat, ancho=1.0, alto=1.0, largo=1.0, centro=(0, 0, 0), tam_tex=(1, 1), uv_caras=None):
    """Caja con un material. ancho = x, alto = y, largo = z. uv_caras: dict cara(0..5) -> (u0, v0, u1, v1) en texels."""
    xyz, uv, nrm = [], [], []
    h = np.array([ancho, alto, largo], np.float64) / 2
    c = np.asarray(centro, np.float64)
    for k, (n, q) in enumerate(_CARAS):
        q = [c + np.array(v) * h for v in q]
        u0, v0, u1, v1 = (uv_caras or {}).get(k, (0, 0, tam_tex[0], tam_tex[1]))
        t = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
        for a, b, d in ((0, 1, 2), (0, 2, 3)):
            xyz.append([q[a], q[b], q[d]]); uv.append([t[a], t[b], t[d]]); nrm.append([n] * 3)
    n = len(xyz)
    return E.Malla(xyz, uv, nrm, np.ones((n, 3, 3)), np.full(n, mat))


def cilindro(mat, radio=0.5, largo=1.0, lados=8, eje='z', centro=(0, 0, 0)):
    xyz, nrm = [], []
    c = np.asarray(centro, np.float64)
    ang = np.linspace(0, 2 * math.pi, lados + 1)
    def pt(a, z):
        v = {'z': (math.cos(a) * radio, math.sin(a) * radio, z), 'x': (z, math.cos(a) * radio, math.sin(a) * radio),
             'y': (math.cos(a) * radio, z, math.sin(a) * radio)}[eje]
        return c + np.array(v)
    for i in range(lados):
        a0, a1 = ang[i], ang[i + 1]
        z0, z1 = -largo / 2, largo / 2
        p = [pt(a0, z0), pt(a1, z0), pt(a1, z1), pt(a0, z1)]
        nm = [p[0] - c, p[1] - c, p[2] - c, p[3] - c]
        for a, b, d in ((0, 1, 2), (0, 2, 3)):
            xyz.append([p[a], p[b], p[d]]); nrm.append([nm[a] / (np.linalg.norm(nm[a]) + 1e-9), nm[b] / (np.linalg.norm(nm[b]) + 1e-9),
                                                      nm[d] / (np.linalg.norm(nm[d]) + 1e-9)])
        for a, b, d, nz in ((None, None, None, 0),):
            pass
    n = len(xyz)
    return E.Malla(xyz, np.zeros((n, 3, 2)), nrm, np.ones((n, 3, 3)), np.full(n, mat))


def textura_texto(s, ancho, alto, fondo, tinta, fuente_px=None):
    """Imagen RGBA uint8 con texto (PIL, para pantallas de aparatos). El texto del vídeo usa la fuente del juego en `texto.py`."""
    from PIL import ImageDraw
    im = Image.new('RGBA', (ancho, alto), fondo)
    return im


# ------------------------------------------------------------------ texturas de Ábalos

FOTO = os.path.join(rutas.personalizados('mkds'), 'abalos.jpg')


def cara_abalos(tam=128):
    """Media cara (derecha de la foto) con el centro de la cara en x = 0. Reajuste vertical para que ojos, nariz y boca queden
    donde los dibuja el modelo de los pilotos (ojos hacia la fila 11/32, boca 26/32, barbilla 31/32)."""
    im = Image.open(FOTO).convert('RGB')
    a = np.asarray(im, np.float32) / 255.0
    H, W = a.shape[:2]
    sx, sy = W / 830.0, H / 1242.0
    cx = 418 * sx
    # filas destino (0..32) -> filas de la foto
    destino = np.array([0, 3, 11, 20, 26, 31.5, 32.0])
    origen = np.array([360, 410, 485, 640, 728, 905, 925]) * sy
    ys = np.interp((np.arange(tam) + .5) / tam * 32, destino, origen)
    xs = cx + (np.arange(tam) + .5) / tam * (745 * sx - cx)
    gy, gx = np.meshgrid(ys, xs, indexing='ij')
    out = np.stack([map_coordinates(a[..., c], [gy, gx], order=1, mode='nearest') for c in range(3)], -1)
    # un poco de contraste y saturación: las texturas del juego son planas y vivas
    lum = out @ np.array([.299, .587, .114], np.float32)
    out = lum[..., None] + (out - lum[..., None]) * 1.25
    out = (out - .5) * 1.18 + .5 + .02
    out = np.clip(out, 0, 1)
    rgba = np.concatenate([out, np.ones(out.shape[:2] + (1,))], -1)
    rgba = (rgba * 255).astype(np.uint8)
    k = tam // 32
    rgba[int(28.6 * k):, int(28.2 * k):, :3] = PIEL          # la nariz del modelo usa la esquina inferior de la textura
    return rgba


PIEL = np.array([222, 168, 130], np.uint8)
PELO = np.array([118, 104, 96], np.float32)
TRAJE = np.array([38, 42, 58], np.float32)
CAMISA = np.array([236, 238, 244], np.float32)
CORBATA = np.array([86, 98, 128], np.float32)


def main_abalos(base):
    """P_main de Mario (64x32): gorra -> pelo, mono azul -> traje oscuro, camisa roja -> camisa blanca, botones grises."""
    a = np.array(base, np.uint8).copy()
    f = a[..., :3].astype(np.float32)
    h, w = a.shape[:2]
    rojo = (f[..., 0] > 120) & (f[..., 1] < 110) & (f[..., 2] < 110)
    azul = (f[..., 2] > 110) & (f[..., 0] < 60)
    amar = (f[..., 0] > 180) & (f[..., 1] > 150) & (f[..., 2] < 140)
    yy, xx = np.mgrid[0:h, 0:w]
    gorra = (xx >= 16) & (xx < 48) & (yy >= 16)
    lum = f.mean(-1) / 255.0
    rng = np.random.default_rng(3)
    pelo = PELO * (0.92 + 0.16 * rng.random((h, w, 1)))
    out = f.copy()
    out[gorra] = pelo[gorra]                                                         # gorra entera -> pelo
    flequillo = (xx < 17) & (yy < 9)
    out[flequillo] = pelo[flequillo]
    oreja = np.zeros_like(flequillo)
    out[oreja] = PIEL.astype(np.float32) * 0.92
    rojo = rojo & ~flequillo & ~oreja
    pecho = rojo & ~gorra & (xx < 16) & (yy >= 6)
    out[pecho] = CAMISA * (0.82 + 0.18 * lum[pecho][:, None] * 1.0)
    resto_rojo = rojo & ~gorra & ~pecho
    out[resto_rojo] = TRAJE * (0.8 + 0.4 * lum[resto_rojo][:, None])
    out[azul] = TRAJE * (0.72 + 0.5 * lum[azul][:, None])
    out[amar] = CORBATA
    a[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    return a


# ------------------------------------------------------------------ pasajeros con pose

class _Ov:
    def __init__(self, base, d):
        self.b, self.d = base, d

    def get(self, t, p):
        return self.d[t] if t in self.d else self.b.get(t, p)


class Pasajero:
    """Piloto de la ROM (sin kart) con texturas a medida. `malla(anim, frame)` -> Malla horneada (con caché)."""
    def __init__(self, motor, piloto='mario', abalos=False):
        self.m = motor
        self.c = M.piloto(piloto)
        self.abalos = abalos
        self.escala_uv = {}
        if abalos:
            base = M.piloto('mario')
            # conjunto propio: mismas mallas, otras texturas (el motor cachea materiales por id del modelo + nombre,
            # así que se registra con un nombre de textura distinto)
            ov = {'ABALOS_face': cara_abalos(128), 'ABALOS_main': main_abalos(base.texlook.get('P_main', 'P_main_pl'))}
            self.c = M.Conjunto(base.nitro, None, base.anims, nombre='abalos')
            self.c.texlook = _Ov(base.texlook, ov)
            self.renombre = {'P_face.1': 'ABALOS_face', 'P_main': 'ABALOS_main'}
        else:
            self.renombre = {}
        self._cache = {}
        self._pre = None

    def _hornear(self, anim, frame):
        c = self.c; mo = c.model
        if self.abalos:
            # parche temporal de nombres de textura en los materiales del modelo
            guardado = [(m, m.tex, m.pal) for m in mo.materials]
            for m in mo.materials:
                if m.tex in self.renombre: m.tex = self.renombre[m.tex]; m.pal = None
            try:
                mal = self._malla(anim, frame)
            finally:
                for m, t, p in guardado: m.tex, m.pal = t, p
            return mal
        return self._malla(anim, frame)

    def _malla(self, anim, frame):
        c = self.c
        a = c.anims[anim] if anim else None
        mal = self.m.malla(c, a, min(max(frame, 0), a.num_frames - 1) if a else 0)
        if self.abalos:
            tris = c.model.triangles(a, min(max(frame, 0), a.num_frames - 1))
            # reconstruir filtrando la visera (triángulos de la gorra que sobresalen) y ampliando los uv de la cara
            return self._filtrar(mal, tris)
        return mal

    def _filtrar(self, mal, tris):
        mo = self.c.model
        # los triángulos salen en el mismo orden que en m.malla
        keep, uvm, xyz = [], mal.uv.copy(), mal.xyz.copy()
        n = 0
        for mi, tri in tris:
            U = np.array([v[3:5] for v in tri]); P = np.array([v[:3] for v in tri])
            mt = mo.materials[mi]
            um, vm = U[:, 0].mean(), U[:, 1].mean()
            visera = mt.name == 'P_main' and vm <= 3 and 8 <= um <= 13
            if visera:                                  # la visera pasa a ser un flequillo pegado a la frente
                xyz[n, :, 2] = 0.05 + (xyz[n, :, 2] - 0.05) * 0.75
            keep.append(True)
            if mt.name == 'P_face': uvm[n] = uvm[n] * 4.0
            n += 1
        keep = np.array(keep)
        return E.Malla(xyz[keep], uvm[keep], mal.nrm[keep], mal.col[keep], mal.mat[keep], mal.alfa[keep])

    def malla(self, anim, frame):
        clave = (anim, round(frame * 2))
        if clave not in self._cache:
            if len(self._cache) > 300: self._cache.clear()
            self._cache[clave] = self._hornear(anim, frame)
        return self._cache[clave]


# ------------------------------------------------------------------ más piezas

def plano(mat, ancho, largo, centro=(0, 0, 0)):
    """Rectángulo horizontal (normal +y) de ancho (x) por largo (z)."""
    return caja(mat, ancho, 0.0, largo, centro)


def disco(mat, radio=1.0, lados=14):
    """Disco horizontal (para charcos de sangre, manchas)."""
    xyz = []
    a = np.linspace(0, 2 * math.pi, lados + 1)
    for i in range(lados):
        xyz.append([(0, 0, 0), (math.sin(a[i]) * radio, 0, math.cos(a[i]) * radio), (math.sin(a[i + 1]) * radio, 0, math.cos(a[i + 1]) * radio)])
    n = len(xyz)
    return E.Malla(xyz, np.zeros((n, 3, 2)), np.tile([[0, 1, 0]], (n, 3, 1)), np.ones((n, 3, 3)), np.full(n, mat))


def cinta(mat, puntos, ancho):
    """Cinta plana siguiendo una polilínea (n,3): marcas de frenada."""
    puntos = np.asarray(puntos, np.float64)
    d = np.gradient(puntos, axis=0); d[:, 1] = 0
    d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
    n = np.stack([d[:, 2], np.zeros(len(d)), -d[:, 0]], 1) * ancho / 2
    xyz = []
    for i in range(len(puntos) - 1):
        a, b, c, e = puntos[i] - n[i], puntos[i] + n[i], puntos[i + 1] + n[i + 1], puntos[i + 1] - n[i + 1]
        xyz.append([a, b, c]); xyz.append([a, c, e])
    k = len(xyz)
    return E.Malla(xyz, np.zeros((k, 3, 2)), np.tile([[0, 1, 0]], (k, 3, 1)), np.ones((k, 3, 3)), np.full(k, mat))


def cuerpo_kart(kart, pos, yaw=0.0, pitch=0.0, roll=0.0, giro=0.0, volante=0.0, deriva=0.0, escala=None, **kw):
    """Instancias del kart (carrocería + 4 ruedas) sin piloto."""
    s = kart.escala if escala is None else escala
    R = E.rotacion(yaw + deriva, pitch, roll)
    ins = [E.Instancia(kart.cuerpo, pos=pos, rot=R, escala=s, **kw)]
    for r in kart.ruedas:
        dirr = (volante * 28.0) if r['delante'] else 0.0
        Rl = R @ E.rotacion(dirr, 0, 0) @ E.rot_x(math.radians(giro))
        c = np.asarray(pos) + R @ (r['centro'] * s)
        ins.append(E.Instancia(r['malla'], pos=c, rot=Rl, escala=s, **kw))
    return ins


class Peaton:
    """Busto de piloto con piernas (caminar / correr) para personajes a pie."""
    def __init__(self, motor, piloto, piel=(0.93, 0.72, 0.55), pantalon=None, zapato=(0.45, 0.25, 0.1), largo=1.5, escala=5.0):
        self.p = Pasajero(motor, piloto)
        self.largo, self.escala = largo, escala
        mp = motor.solido(piel); mz = motor.solido(zapato)
        pierna = caja(mp, 0.62, largo, 0.62, centro=(0, -largo / 2, 0))
        zap = caja(mz, 0.7, 0.4, 1.15, centro=(0, -largo - 0.0, 0.25))
        self.pierna = E.Malla.une([pierna, zap]) if pantalon is None else None
        if pantalon is not None:
            mt = motor.solido(pantalon)
            self.pierna = E.Malla.une([caja(mt, 0.66, largo, 0.66, centro=(0, -largo / 2, 0)), zap])

    def instancias(self, pos, yaw, fase=0.0, amp=35.0, anim='drive', frame=14, inclina=0.0, rebote=0.0, escala_v=1.0, **kw):
        """pos = suelo bajo los pies. fase en radianes (paso); amp = amplitud de las piernas en grados."""
        R = E.rotacion(yaw, inclina, 0)
        s = self.escala
        cadera = np.array([0, self.largo + 0.25 + rebote, 0])
        ins = []
        for lado in (-1, 1):
            a = math.sin(fase + (0 if lado < 0 else math.pi)) * amp
            Rl = R @ E.rot_x(math.radians(a))
            ins.append(E.Instancia(self.pierna, pos=np.asarray(pos) + R @ (cadera + [lado * 0.5, 0, 0]), rot=Rl, escala=1.0, **kw))
        ins.append(E.Instancia(self.p.malla(anim, frame), pos=np.asarray(pos) + R @ (cadera + [0, 0, 0]), rot=R, escala=s * escala_v, **kw))
        return ins


def parchear_cielo(nombre_tex='Mmc_sky1', fila=86):
    """El cielo de Mario Circuit trae bajo el horizonte una franja negra con puntos azules (la parte que en el juego queda tapada
    por el terreno). Se sustituye por un degradado de campo lejano para que no asome en planos con cámara baja."""
    orig = M.Circuito.conjunto_cielo
    if getattr(orig, '_parcheado', False): return

    def nuevo(self):
        c = orig(self)
        if c is not None and not isinstance(c.texlook, _Ov):
            base = c.texlook
            mt = c.model.materials[0]
            a = np.array(base.get(mt.tex, mt.pal), np.uint8)
            if mt.tex == nombre_tex and a.shape[0] >= 100:
                h = a.shape[0]
                f = int(fila / 128 * h)
                arriba = a[f - 2, :, :3].astype(np.float32).mean(0)
                rng = np.random.default_rng(5)
                for y in range(f, h):
                    u = (y - f) / max(1, h - f)
                    col = np.array([150, 190, 160], np.float32) * (1 - u) + np.array([60, 140, 70], np.float32) * u
                    a[y, :, :3] = np.clip(col + rng.normal(size=(a.shape[1], 3)) * 4, 0, 255).astype(np.uint8)
                a[..., 3] = 255
                c.texlook = _Ov(base, {mt.tex: a})
        return c
    nuevo._parcheado = True
    M.Circuito.conjunto_cielo = nuevo
