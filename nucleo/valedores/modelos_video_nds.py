"""Adaptadores de modelos nativos a la rasterización DS del repositorio."""
from functools import lru_cache
import math
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image

from . import nitro, rutas
from .activos_video_nds import textura, cadena, texturas_party


@lru_cache(maxsize=1)
def lector():
    sys.path.insert(0, str(Path(rutas.juego_dir('nsmb')) / 'tools' / 'nsmb'))
    import nitro3d
    return nitro3d


class ModeloSM64:
    """Geometría BMD en pose de reposo, con huesos, materiales y texturas propios."""
    def __init__(self, datos):
        self.datos = datos
        self.materials, self.texturas, self.tris = [], {}, []
        g = lector()
        nb, ob, npoly, opoly, nt, ot, npal, opal, nm, om, mapa = struct.unpack_from('<11I', datos, 4)
        if max(nb, npoly, nt, npal, nm) > 4096:
            raise ValueError('Tablas BMD fuera de límites')
        matrices = []
        self.huesos = {}
        for i in range(nb):
            p = ob + i * 64
            s = np.array(struct.unpack_from('<3i', datos, p + 16)) / 4096
            rx, ry, rz = np.array(struct.unpack_from('<3h', datos, p + 28)) * math.pi / 2048
            t = np.array(struct.unpack_from('<3i', datos, p + 36)) / 4096
            cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
            rot = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @ np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @ np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
            m = g.Model.trs_matrix(t, rot, s)
            padre = struct.unpack_from('<h', datos, p + 8)[0]
            if padre < 0:
                if i + padre < 0:
                    raise ValueError('Padre de hueso BMD fuera de límites')
                m = matrices[i + padre] @ m
            matrices.append(m)
            self.huesos[cadena(datos, nitro.u32(datos, p + 4))] = m
        for i in range(nm):
            p = om + 48 * i
            no, ti, pi = struct.unpack_from('<3I', datos, p)
            param, poli, color = struct.unpack_from('<3I', datos, p + 32)
            nombre = cadena(datos, no)
            tex = None
            if ti != 0xFFFFFFFF:
                if ti >= nt:
                    raise ValueError('Textura BMD fuera de límites')
                tex = 't%d_p%d' % (ti, pi)
                no, off, tam, wh, texpar = struct.unpack_from('<5I', datos, ot + ti * 20)
                paleta = b''
                if pi != 0xFFFFFFFF:
                    _, po, pl = struct.unpack_from('<3I', datos, opal + pi * 16)
                    paleta = datos[po:po + pl]
                tipo = texpar >> 26 & 7
                im = textura(datos[off:off + tam], paleta, tipo, 8 << (texpar >> 20 & 7),
                             8 << (texpar >> 23 & 7), bool(texpar >> 29 & 1),
                             datos[off + tam:off + tam + tam // 2] if tipo == 5 else b'')
                self.texturas[tex] = np.asarray(im)
                param |= texpar
            dif = tuple((color >> b & 31) / 31 for b in (0,5,10))
            esc = struct.unpack_from('<2i', datos, p + 12)
            self.materials.append(SimpleNamespace(name=nombre, tex=tex, pal=None,
                alpha=(poli >> 16 & 31) / 31, cull_front=not bool(poli & 128), cull_back=not bool(poli & 64),
                sx=esc[0] / 4096 if param >> 30 else 1, sy=esc[1] / 4096 if param >> 30 else 1,
                rep_s=bool(param >> 16 & 1), rep_t=bool(param >> 17 & 1),
                flip_s=bool(param >> 18 & 1), flip_t=bool(param >> 19 & 1),
                light_mask=poli & 15, diffuse=dif, diffuse_vtx=not bool(color & 32768)))
        for i in range(nb):
            p = ob + i * 64
            n, mat, pol = struct.unpack_from('<3I', datos, p + 48)
            for k in range(n):
                mi, polid = datos[mat + k], datos[pol + k]
                off = nitro.u32(datos, opoly + polid * 8 + 4)
                nh, oh, tam, dl = struct.unpack_from('<4I', datos, off)
                pila = []
                for h in range(nh):
                    indice = struct.unpack_from('<H', datos, mapa + 2 * datos[oh + h])[0]
                    pila.append(matrices[indice])
                pila += [matrices[i]] * (32 - len(pila))
                tris = g.run_dl(datos[dl:dl + tam], matrices[i], pila)
                self.tris.extend((mi, tri) for tri in tris)
        if not self.tris:
            raise ValueError('El BMD no contiene geometría renderizable')

    def get(self, tex, pal):
        return self.texturas.get(tex)


def _rotacion_euler(r):
    """Matriz de rotación XYZ usada por los objetos HBDF y los huesos BMD."""
    rx, ry, rz = r
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    return (np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
            @ np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            @ np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]]))


def _normales_suaves(p, obj):
    """Normales por vértice calculadas de la geometría, orientadas hacia fuera de cada objeto.

    Las listas GX de los HBDF no traen normales útiles (todas iguales): iluminar con ellas da un sombreado
    plano y erróneo. Se promedian las de los triángulos que comparten posición dentro del mismo objeto."""
    salida = np.zeros_like(p)
    for o in np.unique(obj):
        i = np.flatnonzero(obj == o)
        q = p[i]
        f = np.cross(q[:, 1] - q[:, 0], q[:, 2] - q[:, 0])
        centro = q.reshape(-1, 3).mean(0)
        hacia_fuera = q.mean(1) - centro
        f = np.where(((f * hacia_fuera).sum(1) < 0)[:, None], -f, f)
        claves = np.round(q.reshape(-1, 3) * 64).astype(np.int64)
        _, inv = np.unique(claves, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        acumulado = np.zeros((inv.max() + 1, 3), np.float32)
        np.add.at(acumulado, inv, np.repeat(f, 3, axis=0))
        n = acumulado[inv]
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-6)
        salida[i] = n.reshape(-1, 3, 3)
    return salida


class ModeloParty:
    """Geometría HBDF; materiales, jerarquía, display lists GX y poses por objeto.

    La pose de reposo se guarda en `tris`. `pose(rotaciones, traslaciones)` devuelve una lista
    de triángulos nueva sin tocar la de reposo: cada objeto se mueve con su matriz local y las
    mallas se transforman con la diferencia entre la matriz animada y la de reposo. Sirve para
    animar brazos, piernas y el cuerpo sin leer todavía las curvas ANMF.
    """
    def __init__(self, datos, bancos=()):
        if datos[:4] not in (b'HBDF', b'HSDF'):
            raise ValueError('El archivo no es HBDF/HSDF')
        self.tris, self.materials = [], []
        self.texturas = {n: np.asarray(im) for d in (datos, *bancos) for n, im in texturas_party(d)}
        g = lector()
        md = datos.find(b'MDLF')
        if md < 0:
            raise ValueError('El HBDF no tiene modelo MDLF')
        inicio = md + 8
        no, nm, na, nmat = struct.unpack_from('<4H', datos, inicio + 40)
        if max(no,nm,na,nmat)>4096:
            raise ValueError('Tablas HBDF fuera de límites')
        p = inicio + 48
        materiales = [struct.unpack_from('<4I4h', datos, p+i*24) for i in range(nm)]
        p += nm*24
        atributos = [struct.unpack_from('<11I2H', datos, p+i*48) for i in range(na)]
        p += na*48 + nmat*40
        objetos = []
        self.objetos_party = []
        for i in range(no):
            if datos[p:p+4] != b'OBJO':
                raise ValueError('Objeto HBDF sin bloque OBJO')
            tam = nitro.u32(datos,p+4)
            q = p+8
            tipo,padre = struct.unpack_from('<Hh',datos,q)
            nombre_obj = struct.unpack_from('<I',datos,q+8)[0]
            valores = np.array(struct.unpack_from('<9i',datos,q+12),dtype=float)
            t,r,s = valores[:3]/4096,valores[3:6]/16384,valores[6:]/4096
            rot = _rotacion_euler(r)
            transformacion=g.Model.trs_matrix(t,rot,s)
            objetos.append((transformacion,q+48 if tipo==2 else None,padre))
            self.objetos_party.append({
                't': t.astype(float), 'r': r.astype(float), 's': s.astype(float),
                'padre': padre, 'tipo': tipo, 'global': None, 'global_inv': None, 'nombre_off': nombre_obj,
            })
            p+=8+tam
        # STRB guarda las cadenas referenciadas por materiales, atributos y objetos.
        sb=datos.find(b'STRB',p)
        cadenas=datos[sb+8:sb+8+nitro.u32(datos,sb+4)] if sb>=0 else b''
        for info in self.objetos_party:
            off=info.pop('nombre_off')
            info['nombre']=cadena(cadenas,off) if off<len(cadenas) else ''
        self.indice_objeto={info['nombre']:i for i,info in enumerate(self.objetos_party) if info['nombre']}
        for mat in materiales:
            nombre_off,col1,col2,hilite,ai,unk,unk2,luz=mat
            tex=None
            flags=0
            escala_uv=(1,1)
            if ai>=0 and ai<len(atributos):
                flags=atributos[ai][1]
                escala_uv=(atributos[ai][8]/4096,atributos[ai][9]/4096)
                off=atributos[ai][-1]
                if off<len(cadenas):tex=cadena(cadenas,off)
            self.materials.append(SimpleNamespace(name=str(nombre_off),tex=tex,pal=None,alpha=1,
                cull_front=False,cull_back=False,sx=escala_uv[0],sy=escala_uv[1],
                rep_s=bool(flags>>16&1),rep_t=bool(flags>>17&1),flip_s=bool(flags>>18&1),flip_t=bool(flags>>19&1),
                light_mask=luz,diffuse=tuple((col1>>b&31)/31 for b in (0,5,10)),diffuse_vtx=False))
        def global_objeto(i, visitados=()):
            local, _, padre = objetos[i]
            if padre < 0 or padre == i:
                return local
            if padre >= len(objetos) or i in visitados:
                raise ValueError('Jerarquía HBDF fuera de límites o cíclica')
            return global_objeto(padre, visitados+(i,)) @ local
        self.tris_objeto = []
        # Todos los objetos, con malla o sin ella, tienen matriz global: los enganches (itemhook) y
        # los huesos sin geometría también se pueden seguir con la cámara.
        for indice in range(len(objetos)):
            transformacion=global_objeto(indice)
            self.objetos_party[indice]['global'] = transformacion
            self.objetos_party[indice]['global_inv'] = np.linalg.inv(transformacion)
        for indice, (local,q,padre) in enumerate(objetos):
            if q is None:continue
            transformacion=self.objetos_party[indice]['global']
            if datos[q:q+4]!=b'MESH':raise ValueError('Falta MESH en objeto HBDF')
            q+=8
            escala=np.array(struct.unpack_from('<3i',datos,q))/4096
            ng,tam=struct.unpack_from('<HH',datos,q+28)
            grupos=[struct.unpack_from('<4H',datos,q+32+i*8) for i in range(ng)]
            q+=32+ng*8
            base=transformacion@np.diag([*escala,1])
            for mi,unk,primero,cantidad in grupos:
                if mi>=len(self.materials):raise ValueError('Material HBDF fuera de límites')
                # Los grupos referencian palabras de 32 bits del flujo GX,
                # no índices de triángulos. Cada grupo reinicia sus comandos.
                a,b=primero*4,(primero+cantidad)*4
                if b>tam:raise ValueError('Grupo GX de HBDF fuera de límites')
                for tri in g.run_dl(datos[q+a:q+b],base):
                    self.tris.append((mi,tri))
                    self.tris_objeto.append((mi,tri,indice))
        if not self.tris:
            raise ValueError('Modelo HBDF sin geometría renderizable')

    def paquete(self):
        """Malla en reposo como arrays: posiciones, normales, UV en téxeles, objeto y material por triángulo."""
        if getattr(self, '_paquete', None) is None:
            mats = self.materials
            p = np.array([[v[:3] for v in tri] for _, tri, _i in self.tris_objeto], np.float32)
            obj = np.array([i for _, _t, i in self.tris_objeto], np.int32)
            self._paquete = SimpleNamespace(
                p=p,
                n=_normales_suaves(p, obj),
                uv=np.array([[(v[3] * mats[mi].sx, v[4] * mats[mi].sy) for v in tri]
                             for mi, tri, _i in self.tris_objeto], np.float32),
                obj=obj,
                mat=np.array([mi for mi, _t, _i in self.tris_objeto], np.int32))
        return self._paquete

    def locales_reposo(self):
        """Matriz (objetos, 9) con traslación, rotación y escala locales de la pose de reposo."""
        return np.array([[*o['t'], *o['r'], *o['s']] for o in self.objetos_party], np.float64)

    def globales(self, locales):
        """Matrices globales de todos los objetos a partir de sus valores locales (objetos, 9)."""
        n = len(self.objetos_party)
        salida = [None] * n
        trs = lector().Model.trs_matrix
        pendientes = list(range(n))
        while pendientes:
            resto = []
            for i in pendientes:
                padre = self.objetos_party[i]['padre']
                if padre >= 0 and padre != i and salida[padre] is None:
                    resto.append(i)
                    continue
                v = locales[i]
                m = trs(v[:3], _rotacion_euler(v[3:6]), v[6:9])
                salida[i] = m if padre < 0 or padre == i else salida[padre] @ m
            if len(resto) == len(pendientes):
                raise ValueError('Jerarquía HBDF cíclica')
            pendientes = resto
        return np.array(salida)

    def pose(self, rotaciones=None, traslaciones=None):
        """Triángulos en una pose nueva: {objeto: (dx,dy,dz)} en radianes y unidades locales."""
        rotaciones = dict(rotaciones or {})
        traslaciones = dict(traslaciones or {})
        g = lector()
        locales = []
        for i, info in enumerate(self.objetos_party):
            dr = np.asarray(rotaciones.get(i, (0, 0, 0)), dtype=float)
            dt = np.asarray(traslaciones.get(i, (0, 0, 0)), dtype=float)
            locales.append(g.Model.trs_matrix(info['t'] + dt, _rotacion_euler(info['r'] + dr), info['s']))
        globales = [None] * len(locales)

        def global_de(i, visitados=()):
            if globales[i] is not None:
                return globales[i]
            padre = self.objetos_party[i]['padre']
            if padre < 0 or padre == i:
                m = locales[i]
            else:
                if padre >= len(locales) or i in visitados:
                    raise ValueError('Jerarquía HBDF fuera de límites o cíclica')
                m = global_de(padre, visitados + (i,)) @ locales[i]
            globales[i] = m
            return m

        salida = []
        for mi, tri, indice in self.tris_objeto:
            info = self.objetos_party[indice]
            delta = global_de(indice) @ info['global_inv']
            r3 = delta[:3, :3]
            vs = []
            for v in tri:
                p = r3 @ np.asarray(v[:3]) + delta[:3, 3]
                n = r3 @ np.asarray(v[6])
                vs.append((*p, v[3], v[4], v[5], tuple(n)))
            salida.append((mi, vs))
        return salida

    def get(self,tex,pal):
        return self.texturas.get(tex)


class TexturasPersonalizadas:
    """Sustituye texturas en memoria, sin alterar bancos nativos ni UV."""
    def __init__(self, base):
        self.base, self.reemplazos = base, {}

    def get(self, tex, pal):
        return self.reemplazos[tex] if tex in self.reemplazos else self.base.get(tex,pal)


class VistaModelo:
    """Actor 3D para Plano.sprite; giro/cámara ortográfica y encuadre constante."""
    def __init__(self, modelo, texturas, animacion=None, tamano=(256,256), giro=0, inclinacion=0):
        self.modelo, self.texturas, self.animacion = modelo, texturas, animacion
        self.tamano, self.giro, self.inclinacion = tamano, giro, inclinacion
        tris = modelo.tris if hasattr(modelo, 'tris') else modelo.triangles(animacion, 0)
        puntos = np.array([v[:3] for _, tri in tris for v in tri])
        if not len(puntos):
            raise ValueError('Modelo sin vértices')
        self.centro = (puntos.max(0) + puntos.min(0)) / 2
        self.escala = min(tamano) * 0.84 / max(float(np.linalg.norm(puntos - self.centro, axis=1).max()) * 2, 1e-6)

    def reemplazar_textura(self, nombre, imagen, escala=1):
        """Aplica un atlas facial ya ajustado a las UV del material, con su resolución nativa.

        `escala` multiplica la resolución del atlas y las UV del material: un atlas 4× permite que
        una cara de foto se reconozca sin cambiar el reparto de UV ni la geometría. Debe ser entero.
        """
        if not isinstance(escala,int) or escala<1 or escala>8:
            raise ValueError('La escala de la textura debe ser un entero entre 1 y 8')
        materiales=[m for m in self.modelo.materials if m.tex==nombre]
        if not materiales:
            raise ValueError('La textura no pertenece al modelo: '+nombre)
        original=self.texturas.get(nombre,materiales[0].pal)
        if original is None:
            raise ValueError('No se pudo leer la textura nativa: '+nombre)
        if not isinstance(self.texturas,TexturasPersonalizadas):
            self.texturas=TexturasPersonalizadas(self.texturas)
        alto,ancho=original.shape[:2]
        if escala!=1:
            for m in materiales:
                if not getattr(m,'_escala_personalizada',False):
                    m.sx*=escala
                    m.sy*=escala
                    m._escala_personalizada=True
        self.texturas.reemplazos[nombre]=np.asarray(imagen.convert('RGBA').resize((ancho*escala,alto*escala),Image.Resampling.NEAREST))
        return self

    def frame(self, t):
        angulo = self.giro(t) if callable(self.giro) else self.giro
        c, s, ci, si = math.cos(angulo), math.sin(angulo), math.cos(self.inclinacion), math.sin(self.inclinacion)
        rot = np.array([[c,0,s],[si*s,ci,-si*c],[-ci*s,si,ci*c]])
        tris = self.modelo.tris if hasattr(self.modelo, 'tris') else self.modelo.triangles(self.animacion, t * 30)
        nuevos = []
        for mi, tri in tris:
            vertices = []
            for v in tri:
                p = rot @ (np.array(v[:3]) - self.centro)
                vertices.append((*p, *v[3:6], tuple(rot @ np.asarray(v[6]))))
            nuevos.append((mi, vertices))
        rgba, _ = lector().render(nuevos, self.modelo, self.texturas, scale=self.escala,
            size=self.tamano, origin=(self.tamano[0]//2,self.tamano[1]//2), shade=True)
        return Image.fromarray(rgba)


def modelo_sm64(datos, **kw):
    m = ModeloSM64(datos)
    return VistaModelo(m, m, **kw)


def modelo_party(datos,bancos=(),**kw):
    m=ModeloParty(datos,bancos)
    return VistaModelo(m,m,**kw)


def modelo_nitro(datos, bancos=(), animacion=None, **kw):
    g = lector()
    n = g.Nitro(datos)
    if not n.models:
        raise ValueError('El contenedor no tiene modelos Nitro')
    clips = g.Nitro(animacion).anims if animacion else []
    lookup = g.TexLookup(n, *(g.Nitro(b) for b in bancos))
    for material in n.models[0].materials:
        if material.tex and lookup.get(material.tex,material.pal) is None:
            raise ValueError('Falta el banco de la textura %s; indícalo en bancos=()' % material.tex)
    return VistaModelo(n.models[0], lookup, clips[0] if clips else None, **kw)
