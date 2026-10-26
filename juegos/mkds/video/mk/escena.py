"""Escena 3D: mallas con texturas DS, instancias, cámara y render a float32 (H,W,3).

Uso básico:
    m = Motor(1080, 1920, ss=1)
    malla = m.malla(conjunto, anim, frame)                  # modelo + animación NSBCA -> triángulos
    img = m.render([Instancia(malla, pos=(0, 0, 0), yaw=30)], Camara((0, 5, 20), (0, 2, 0), fov=50), Entorno())
"""
import math
import numpy as np
from PIL import Image
from . import raster as R

import nitro3d as N


# ------------------------------------------------------------------ matemáticas

def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)


def rotacion(yaw=0.0, pitch=0.0, roll=0.0):
    """Ángulos en grados. Orden: roll (Z) -> pitch (X) -> yaw (Y). Un modelo que mira a +z con yaw=0."""
    return rot_y(math.radians(yaw)) @ rot_x(math.radians(pitch)) @ rot_z(math.radians(roll))


def normaliza(v):
    v = np.asarray(v, np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


# ------------------------------------------------------------------ datos

class Malla:
    """Triángulos en espacio del modelo. xyz (n,3,3), uv (n,3,2) en texels, nrm (n,3,3), col (n,3,3), mat (n,)."""
    def __init__(self, xyz, uv, nrm, col, mat, alfa=None):
        self.xyz = np.ascontiguousarray(xyz, np.float32)
        self.uv = np.ascontiguousarray(uv, np.float32)
        self.nrm = np.ascontiguousarray(nrm, np.float32)
        self.col = np.ascontiguousarray(col, np.float32)
        self.mat = np.ascontiguousarray(mat, np.int32)
        self.alfa = np.ones((len(self.xyz), 3), np.float32) if alfa is None else np.ascontiguousarray(alfa, np.float32)

    def __len__(self):
        return len(self.xyz)

    @staticmethod
    def une(mallas):
        mallas = [m for m in mallas if m is not None and len(m)]
        if not mallas: return Malla(np.zeros((0, 3, 3)), np.zeros((0, 3, 2)), np.zeros((0, 3, 3)), np.zeros((0, 3, 3)), np.zeros(0))
        return Malla(*[np.concatenate([getattr(m, c) for m in mallas]) for c in ('xyz', 'uv', 'nrm', 'col', 'mat', 'alfa')])

    def transformada(self, pos=(0, 0, 0), rot=None, escala=1.0):
        rot = np.eye(3, dtype=np.float32) if rot is None else rot
        esc = np.asarray(escala, np.float32)
        xyz = (self.xyz * esc) @ rot.T + np.asarray(pos, np.float32)
        return Malla(xyz, self.uv, self.nrm @ rot.T, self.col, self.mat, self.alfa)


class Instancia:
    """Una malla colocada en el mundo.
    luz: 'normal' = iluminada con las normales; 'baked' = sólo color de vértice (circuitos); 'plana' = sin luz.
    tinte multiplica el color, emision se suma (0..1), alfa multiplica la opacidad."""
    def __init__(self, malla, pos=(0, 0, 0), rot=None, yaw=0.0, pitch=0.0, roll=0.0, escala=1.0,
                 luz='normal', tinte=(1, 1, 1), emision=(0, 0, 0), alfa=1.0, capa=0, brillo=1.0):
        self.malla = malla
        self.pos = np.asarray(pos, np.float32)
        self.rot = rotacion(yaw, pitch, roll) if rot is None else np.asarray(rot, np.float32)
        self.escala = escala
        self.luz = luz
        self.tinte = np.asarray(tinte, np.float32)
        self.emision = np.asarray(emision, np.float32)
        self.alfa = alfa
        self.capa = capa
        self.brillo = brillo


class Camara:
    def __init__(self, ojo, objetivo, fov=55.0, roll=0.0, near=0.3, arriba=(0, 1, 0)):
        self.ojo = np.asarray(ojo, np.float64)
        self.objetivo = np.asarray(objetivo, np.float64)
        self.fov = fov            # vertical, grados
        self.roll = roll
        self.near = near
        self.arriba = np.asarray(arriba, np.float64)

    def base(self):
        f = normaliza(self.objetivo - self.ojo)
        r = normaliza(np.cross(f, self.arriba))
        u = np.cross(r, f)
        if self.roll:
            a = math.radians(self.roll); c, s = math.cos(a), math.sin(a)
            r, u = r * c + u * s, u * c - r * s
        return np.array([r, u, f], np.float64)


class Entorno:
    """Luz, niebla y color de fondo."""
    def __init__(self, cielo=(0.45, 0.65, 0.95), cielo_bajo=None, niebla=(0.62, 0.78, 0.95), niebla_ini=120.0, niebla_fin=900.0,
                 niebla_fuerza=1.0, luz_dir=(-0.45, 0.8, 0.4), luz_color=(1.0, 0.97, 0.9), ambiente=(0.58, 0.60, 0.68)):
        self.cielo = np.asarray(cielo, np.float32)
        self.cielo_bajo = np.asarray(cielo if cielo_bajo is None else cielo_bajo, np.float32)
        self.niebla = np.asarray(niebla, np.float32)
        self.niebla_ini, self.niebla_fin, self.niebla_fuerza = niebla_ini, niebla_fin, niebla_fuerza
        self.luz_dir = normaliza(luz_dir).astype(np.float32)
        self.luz_color = np.asarray(luz_color, np.float32)
        self.ambiente = np.asarray(ambiente, np.float32)


# ------------------------------------------------------------------ motor

class Motor:
    def __init__(self, w=1080, h=1920, ss=1.0, filtro=1):
        self.w, self.h, self.ss, self.filtro = w, h, ss, filtro
        self._mats = []        # (mips, tamaños, flags, modo)
        self._clave = {}
        self._tex = None

    # -- materiales
    def material(self, rgba, modo=None, flags=(0, 0, 0, 0, 0, 0)):
        """Registra una textura (h,w,4) uint8 ya decodificada. Devuelve el id de material."""
        a = np.asarray(rgba, np.uint8)
        if a.ndim == 2: a = np.stack([a] * 3, -1)
        if a.shape[2] == 3: a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], 2)
        if a.shape[0] > 256 or a.shape[1] > 256:
            a = np.array(Image.fromarray(a).resize((min(256, a.shape[1]), min(256, a.shape[0])), Image.BILINEAR))
        if modo is None:
            al = a[:, :, 3]
            modo = R.OPACO if al.min() == 255 else (R.RECORTE if np.isin(al, (0, 255)).all() else R.ALFA)
        mips, tam = R.construir_mips(a)
        self._mats.append((mips, tam, np.array(flags, np.bool_), modo))
        self._tex = None
        return len(self._mats) - 1

    def solido(self, rgb, modo=R.OPACO):
        return self.material(np.array([[(*[int(c * 255) for c in rgb], 255)]], np.uint8), modo)

    def _sellar(self):
        if self._tex is not None and len(self._tex[0]) == len(self._mats): return
        self._tex = (np.stack([m[0] for m in self._mats]), np.stack([m[1] for m in self._mats]),
                     np.stack([m[2] for m in self._mats]), np.array([m[3] for m in self._mats], np.int32))

    # -- mallas desde modelos Nitro
    def malla(self, conjunto, anim=None, frame=0, pattern=None, pframe=0, modelo=None, root=None, omitir=()):
        """Hornea un Conjunto (tools/mkds/modelos.py) con una animación en `frame`.
        anim puede ser Anim o un mezclador; omitir = nombres de material que no se dibujan."""
        model = conjunto.model if modelo is None else modelo
        tris = model.triangles(anim, frame, root)
        xyz, uv, nrm, col, mat, alfa = [], [], [], [], [], []
        for mi, tri in tris:
            m = model.materials[mi]
            if m.name in omitir: continue
            texname, palname = m.tex, m.pal
            if pattern is not None:
                sel = pattern.sample(m.name, pframe)
                if sel: texname, palname = sel
            clave = (id(model), mi, texname, palname)
            if clave not in self._clave:
                a = conjunto.texlook.get(texname, palname) if texname else None
                if texname and a is None:
                    raise ValueError('Textura sin resolver: %s / %s / %s' % (model.name, texname, palname))
                if a is None: a = np.full((1, 1, 4), 255, np.uint8)
                a = np.asarray(a, np.uint8)
                if a.shape[2] == 3: a = np.concatenate([a, np.full(a.shape[:2] + (1,), 255, np.uint8)], 2)
                # los materiales con alfa de polígono parcial (< 31) se mezclan; el resto según el alfa de la textura
                modo = None
                if m.alpha < 0.99: modo = R.ALFA
                idx = self.material(a, modo, (m.rep_s, m.rep_t, m.flip_s, m.flip_t, m.cull_front, m.cull_back))
                self._clave[clave] = (idx, m.alpha)
            idx, pa = self._clave[clave]
            xyz.append([v[:3] for v in tri]); uv.append([(v[3] * m.sx, v[4] * m.sy) for v in tri])
            nrm.append([v[6] for v in tri]); col.append([v[5] for v in tri]); mat.append(idx)
            alfa.append([pa] * 3)
        if not xyz:
            return Malla.une([])
        return Malla(xyz, uv, nrm, col, mat, alfa)

    # -- render
    def render(self, instancias, camara, entorno=None, fondo=None, dibujar_fondo=True):
        """-> imagen float32 (h, w, 3) en [0, ~]. `fondo` = callable(img, camara, entorno) que pinta el cielo."""
        entorno = entorno or Entorno()
        self._sellar()
        tex, tsz, flags, modo = self._tex
        W, H = int(self.w * self.ss), int(self.h * self.ss)
        img = np.zeros((H, W, 3), np.float32)
        if dibujar_fondo:
            t = np.linspace(0, 1, H, dtype=np.float32)[:, None]
            img[:] = (entorno.cielo * (1 - t) + entorno.cielo_bajo * t)[:, None, :]
        if fondo is not None: fondo(img, camara, entorno)
        depth = np.zeros((H, W), np.float32)
        base = camara.base().astype(np.float32)
        foco = (H / 2.0) / math.tan(math.radians(camara.fov) / 2.0)
        ojo = camara.ojo.astype(np.float32)
        luz = entorno.luz_dir
        capas = sorted({i.capa for i in instancias})
        for capa in capas:
            grupos = [i for i in instancias if i.capa == capa and len(i.malla)]
            if not grupos: continue
            P, U, C, M = [], [], [], []
            for ins in grupos:
                mal = ins.malla
                p = (mal.xyz * ins.escala) @ ins.rot.T + (ojo if capa < 0 else ins.pos)   # capa < 0: cielo anclado a la cámara
                pc = (p - ojo) @ base.T
                nrm = mal.nrm @ ins.rot.T
                if ins.luz == 'plana':
                    col = np.ones_like(mal.col)
                elif ins.luz == 'baked':
                    col = mal.col.copy()
                else:
                    ln = np.maximum(0, nrm @ luz)
                    col = (entorno.ambiente + entorno.luz_color * ln[:, :, None]) * 0.62 + 0.38
                    blanco = (mal.col > 0.99).all(2, keepdims=True)
                    col = col * np.where(blanco, 1.0, mal.col)
                col = col * ins.tinte * ins.brillo + ins.emision
                rgba = np.concatenate([col, mal.alfa[:, :, None] * ins.alfa], 2)
                P.append(pc); U.append(mal.uv); C.append(rgba); M.append(mal.mat)
            sc, uv, co, ma, zm = R.proyectar(np.concatenate(P).astype(np.float32), np.concatenate(U).astype(np.float32),
                                             np.concatenate(C).astype(np.float32), np.concatenate(M), float(foco),
                                             W / 2.0, H / 2.0, float(camara.near))
            if capa < 0: depth[:] = 0
            nf = 1.0 if entorno.niebla_fuerza > 0 and capa >= 0 else 0.0
            for pasada in (0, 1):
                if pasada == 1:
                    orden = np.argsort(-zm, kind='stable')
                    sc, uv, co, ma = sc[orden], uv[orden], co[orden], ma[orden]
                R.dibujar(img, depth, sc, uv, co, ma, tex, tsz, flags, modo, self.filtro,
                          float(entorno.niebla_fuerza * nf), entorno.niebla, float(entorno.niebla_ini),
                          float(entorno.niebla_fin), pasada)
            if capa < 0: depth[:] = 0
        if self.ss != 1.0:
            img = self.reducir(img)
        return img

    def reducir(self, img):
        """Reduce el supermuestreo conservando el rango HDR (para el bloom)."""
        k = int(round(self.ss))
        if abs(self.ss - k) < 1e-6 and k >= 1:
            h, w = self.h, self.w
            return img[:h * k, :w * k].reshape(h, k, w, k, 3).mean((1, 3))
        return np.stack([np.asarray(Image.fromarray(img[:, :, c]).resize((self.w, self.h), Image.BOX)) for c in range(3)], 2)
