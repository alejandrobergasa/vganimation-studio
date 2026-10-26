"""Lector de NKM (mapa de circuito de Mario Kart DS): salida, línea de carrera, puntos de control, cámaras.

Las posiciones del NKM están en fx32 (/4096) y a escala 16:1 respecto al modelo del circuito (validado: la altura
de cada punto de EPOI coincide con la del suelo del modelo con error < 0,004). Aquí se devuelven en unidades
del modelo (ya divididas entre 16)."""
import struct
import numpy as np

ESCALA = 16.0
SECCIONES = ['OBJI', 'PATH', 'POIT', 'STAG', 'KTPS', 'KTPJ', 'KTP2', 'KTPC', 'KTPM', 'CPOI', 'CPAT', 'IPOI',
             'IPAT', 'EPOI', 'EPAT', 'AREA', 'CAME']
TAM = {'OBJI': 0x3C, 'PATH': 4, 'POIT': 0x14, 'KTPS': 0x1C, 'KTPJ': 0x20, 'KTP2': 0x1C, 'KTPC': 0x1C, 'KTPM': 0x1C,
       'CPOI': 0x24, 'CPAT': 0x0C, 'IPOI': 0x14, 'IPAT': 0x0C, 'EPOI': 0x18, 'EPAT': 0x0C, 'AREA': 0x30, 'CAME': 0x4C}


def fx(d, o, n=3):
    return np.array(struct.unpack_from('<%di' % n, d, o), np.float64) / 4096.0


class Nkm:
    def __init__(self, data):
        self.d = d = bytes(data)
        assert d[:4] == b'NKMD', 'no es un NKM'
        hl = struct.unpack_from('<H', d, 6)[0]
        offs = struct.unpack_from('<%dI' % ((hl - 8) // 4), d, 8)
        self.sec = {}
        for n, o in zip(SECCIONES, offs):
            p = hl + o
            if p + 8 > len(d) or d[p:p + 4] != n.encode(): continue
            c = struct.unpack_from('<I', d, p + 4)[0]
            if n in TAM and c * TAM[n] + p + 8 <= len(d):
                self.sec[n] = (p + 8, c)

    def entradas(self, n):
        if n not in self.sec: return []
        p, c = self.sec[n]
        return [p + i * TAM[n] for i in range(c)]

    # -- salida
    def salida(self):
        """[(pos, yaw_grados)] de las parrillas de salida (KTPS); yaw con 0 = +z."""
        out = []
        for o in self.entradas('KTPS'):
            pos = fx(self.d, o) / ESCALA; rot = fx(self.d, o + 12)
            out.append((pos, float(rot[1])))
        return out

    def linea(self, indice=0):
        """Línea de carrera de los enemigos (EPOI): (n,3) posiciones y (n,) anchuras, en unidades del modelo."""
        pts = []; esc = []
        for o in self.entradas('EPOI'):
            pts.append(fx(self.d, o) / ESCALA); esc.append(fx(self.d, o + 12, 1)[0])
        pts = np.array(pts); esc = np.array(esc)
        paths = [struct.unpack_from('<HH', self.d, o) for o in self.entradas('EPAT')]
        # EPAT: u16 índice inicial, u16 longitud (en la ROM europea el primero cubre todos los puntos)
        if paths and paths[indice][1] > 0 and paths[indice][0] + paths[indice][1] <= len(pts):
            a, l = paths[indice]
            if l >= 4: return pts[a:a + l], esc[a:a + l]
        return pts, esc

    def puntos_control(self):
        """[(x1,z1,x2,z2)] de las puertas de checkpoint (CPOI)."""
        out = []
        for o in self.entradas('CPOI'):
            a = fx(self.d, o, 4) / ESCALA
            out.append(a)
        return np.array(out)

    def camaras(self):
        """Cámaras del circuito (CAME): lista de dicts. tipo 0..; las de intro (flyover) llevan ruta."""
        out = []
        for o in self.entradas('CAME'):
            pos = fx(self.d, o) / ESCALA
            rot = fx(self.d, o + 12)
            f = struct.unpack_from('<%di' % 13, self.d, o + 24)
            out.append({'pos': pos, 'rot': rot, 'crudo': [x / 4096 for x in f], 'off': o})
        return out

    def objetos(self):
        """Objetos de circuito (OBJI): [(id, pos, rot, escala, ruta)]."""
        out = []
        for o in self.entradas('OBJI'):
            pos = fx(self.d, o) / ESCALA
            rot = fx(self.d, o + 12); esc = fx(self.d, o + 24)
            oid, ruta = struct.unpack_from('<Hh', self.d, o + 36)
            out.append((oid, pos, rot, esc, ruta))
        return out
