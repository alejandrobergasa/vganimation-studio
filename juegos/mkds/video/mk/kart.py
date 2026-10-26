"""Kart con piloto animado: cuerpo, cuatro ruedas independientes (giro y dirección) y piloto con pose de volante.

Las ruedas que lleva incrustadas el modelo del kart (material `kart_tire`) se separan en cuatro mallas centradas en
su eje, para poder girarlas (`giro`) y orientar las delanteras (`volante`) sin perder su textura original.
Convenciones: el kart mira a +z; +x es su izquierda; yaw 0 = hacia +z."""
import math
import numpy as np

import modelos as M
from . import escena as E

# desplazamiento del piloto respecto al kart (y, z), medido en el modelo de menú: clase a / b / c
ASIENTO = {'a': (0.20, -0.05), 'b': (0.30, -0.09), 'c': (0.31, -0.375)}
GRIS = ('mario', 'luigi', 'peach', 'yoshi', 'wario', 'donkey', 'koopa', 'daisy', 'waluigi', 'robo', 'karon', 'kinopio')


def _disponible(nombre, tipo):
    try:
        M.kart(nombre, tipo); return True
    except KeyError:
        return False


class Kart:
    def __init__(self, motor, piloto='mario', tipo='b', escala=5.0):
        if not _disponible(piloto, tipo): tipo = 'b'
        self.m, self.nombre, self.tipo, self.escala = motor, piloto, tipo, escala
        self.k = M.kart(piloto, tipo)
        self.p = M.piloto(piloto)
        mo = self.k.model
        self.cuerpo = motor.malla(self.k, omitir=('kart_tire',))
        # ruedas: triángulos del material kart_tire agrupados por lado y eje delantero/trasero
        mi = [i for i, mt in enumerate(mo.materials) if mt.name == 'kart_tire']
        self.ruedas = []
        if mi:
            full = motor.malla(self.k)
            tire_id = None
            todos = mo.triangles()
            tri = [(i, t) for i, t in todos if i == mi[0]]
            P = np.array([[v[:3] for v in t] for _, t in tri])
            cen = P.mean(1)
            zmed = (cen[:, 2].min() + cen[:, 2].max()) / 2
            grupos = {}
            for k, c in enumerate(cen):
                grupos.setdefault((c[0] > 0, c[2] > zmed), []).append(k)
            # reutiliza el material ya registrado por motor.malla para la rueda
            idx = motor._clave[(id(mo), mi[0], mo.materials[mi[0]].tex, mo.materials[mi[0]].pal)][0]
            for (izq, delante), ks in sorted(grupos.items()):
                Q = P[ks]
                c = (Q.reshape(-1, 3).min(0) + Q.reshape(-1, 3).max(0)) / 2
                uv = np.array([[(v[3] * mo.materials[mi[0]].sx, v[4] * mo.materials[mi[0]].sy) for v in tri[k][1]] for k in ks])
                nr = np.array([[v[6] for v in tri[k][1]] for k in ks])
                col = np.array([[v[5] for v in tri[k][1]] for k in ks])
                mesh = E.Malla(Q - c, uv, nr, col, np.full(len(ks), idx))
                self.ruedas.append({'izq': izq, 'delante': delante, 'centro': c, 'malla': mesh,
                                    'radio': float((Q.reshape(-1, 3).max(0) - Q.reshape(-1, 3).min(0))[1] / 2)})
        self.asiento = ASIENTO[tipo]
        self._cache = {}

    def radio_rueda(self):
        return self.ruedas[0]['radio'] * self.escala if self.ruedas else 1.0

    def piloto_malla(self, anim, frame):
        clave = (anim, round(frame * 2))
        if clave not in self._cache:
            if len(self._cache) > 400: self._cache.clear()
            a = self.p.anims[anim]
            self._cache[clave] = self.m.malla(self.p, a, min(max(frame, 0), a.num_frames - 1))
        return self._cache[clave]

    def instancias(self, pos, yaw=0.0, pitch=0.0, roll=0.0, giro=0.0, volante=0.0, pose='drive', frame_pose=None,
                   deriva=0.0, escala=None, **kw):
        """Instancias del kart completo. giro = ángulo de rodadura (grados), volante = -1 (derecha) .. 1 (izquierda),
        deriva = yaw extra del cuerpo respecto a la trayectoria (grados). Admite tinte/emision/alfa."""
        s = self.escala if escala is None else escala
        R = E.rotacion(yaw + deriva, pitch, roll)
        ins = [E.Instancia(self.cuerpo, pos=pos, rot=R, escala=s, **kw)]
        for r in self.ruedas:
            dirr = (volante * 28.0) if r['delante'] else 0.0
            Rl = R @ E.rotacion(dirr, 0, 0) @ E.rot_x(math.radians(giro))
            c = np.asarray(pos) + R @ (r['centro'] * s)
            ins.append(E.Instancia(r['malla'], pos=c, rot=Rl, escala=s, **kw))
        if frame_pose is None:
            frame_pose = 14 + 14 * (-volante)          # drive: 0 = izquierda, 14 = recto, 28 = derecha
        a, z = self.asiento
        offs = R @ (np.array([0, a, z]) * s)
        ins.append(E.Instancia(self.piloto_malla(pose, frame_pose), pos=np.asarray(pos) + offs, rot=R, escala=s, **kw))
        return ins
