"""Animaciones nativas ANMF de Mario Party DS (dentro de un contenedor HBDF).

Estructura, deducida de la ROM A8TP y comprobada al dibujar las poses (no hay documentación pública):

    HBDF + tamaño, ANMF + tamaño, base = byte 32
    +16 u32  n.º de palabras de la tabla de pistas << 12
    +24 u32  n.º de pistas
    +32      pistas: pares (u32 inicio, u32 nombre). inicio = índice<<12 | canales<<4 | banderas.
             Índice y nombre se cuentan desde la base: el índice en palabras, el nombre en bytes.
    canales: u32 = tipo<<24 | offset (desde la base).
             tipo 0-2 traslación XYZ, 3-5 rotación XYZ, 6-8 escala XYZ (9-14 no afectan a la pose).
    datos:   u32 modo; u32 reservado.
             modo 6: claves de 8 bytes (u16 modo<<12 | fotograma, s16 valor, s16 tangente de entrada,
             s16 tangente de salida), terminadas en una clave a cero. Modo de clave 5 = Hermite con
             tangentes por tramo (no por fotograma), 1 = lineal, 0 = escalón.
             modo 3: constante, s32 en +12.

Traslación y escala son punto fijo con 12 bits. En la rotación, 4096 = una vuelta en las claves y
65536 = una vuelta en las constantes.
"""
import math
import struct

import numpy as np

BASE = 32
UNIDAD_ANGULO = 2 * math.pi / 4096


class _Canal:
    __slots__ = ('tipo', 'constante', 'cuadros', 'valores', 'entrada', 'salida', 'modos')

    def __init__(self, tipo, constante=None, claves=None):
        self.tipo, self.constante = tipo, constante
        if claves:
            self.cuadros = np.array([c[0] for c in claves], np.float32)
            self.valores = np.array([c[1] for c in claves], np.float32)
            self.entrada = np.array([c[2] for c in claves], np.float32)
            self.salida = np.array([c[3] for c in claves], np.float32)
            self.modos = [c[4] for c in claves]
        else:
            self.cuadros = None

    @property
    def ultimo(self):
        return 0.0 if self.cuadros is None else float(self.cuadros[-1])

    def valor(self, f):
        if self.cuadros is None:
            return self.constante
        c = self.cuadros
        if f <= c[0]:
            return float(self.valores[0])
        if f >= c[-1]:
            return float(self.valores[-1])
        i = int(np.searchsorted(c, f, side='right')) - 1
        p0, p1 = float(self.valores[i]), float(self.valores[i + 1])
        modo = self.modos[i]
        if modo == 0:
            return p0
        u = (f - float(c[i])) / max(float(c[i + 1] - c[i]), 1e-6)
        if modo == 1:
            return p0 + (p1 - p0) * u
        u2, u3 = u * u, u * u * u
        return ((2 * u3 - 3 * u2 + 1) * p0 + (u3 - 2 * u2 + u) * float(self.salida[i])
                + (-2 * u3 + 3 * u2) * p1 + (u3 - u2) * float(self.entrada[i + 1]))


def _canal(datos, off, tipo):
    if off + 16 > len(datos):
        raise ValueError('Canal ANMF fuera de límites')
    modo = struct.unpack_from('<I', datos, off)[0]
    if modo == 6:
        claves, q = [], off + 8
        while q + 8 <= len(datos):
            f, v, a, b = struct.unpack_from('<Hhhh', datos, q)
            if f == 0 and q > off + 8:
                break
            claves.append((f & 0xFFF, v, a, b, f >> 12))
            q += 8
        if not claves:
            raise ValueError('Canal ANMF sin claves')
        return _Canal(tipo, claves=claves)
    if modo == 3:
        constante = struct.unpack_from('<i', datos, off + 12)[0]
        return _Canal(tipo, constante=constante / 16 if 3 <= tipo <= 5 else constante)
    return None


class AnimacionParty:
    """Curvas de una animación: `pistas[nombre del objeto][canal]` y `cuadros` (a 30 por segundo)."""

    FPS = 30

    def __init__(self, datos, nombre=None):
        if datos[:4] not in (b'HBDF', b'HSDF') or datos[8:12] != b'ANMF':
            raise ValueError('El archivo no contiene una animación ANMF')
        self.nombre = nombre
        n = struct.unpack_from('<I', datos, 24)[0]
        if not 0 < n <= 512:
            raise ValueError('Número de pistas ANMF fuera de límites')
        self.pistas = {}
        cuadros = 0.0
        for i in range(n):
            inicio, nom = struct.unpack_from('<II', datos, BASE + i * 8)
            fin = datos.find(b'\0', BASE + nom)
            if fin < 0:
                raise ValueError('Nombre de pista ANMF sin terminar')
            pista = datos[BASE + nom:fin].decode('ascii', 'replace')
            canales = {}
            for k in range((inicio >> 4) & 0xFF):
                c = struct.unpack_from('<I', datos, BASE + ((inicio >> 12) + k) * 4)[0]
                tipo = c >> 24
                if tipo > 8:
                    continue
                canal = _canal(datos, BASE + (c & 0xFFFFFF), tipo)
                if canal is not None:
                    canales[tipo] = canal
                    cuadros = max(cuadros, canal.ultimo)
            self.pistas[pista] = canales
        self.cuadros = max(cuadros, 1.0)

    @property
    def duracion(self):
        return self.cuadros / self.FPS

    def muestrear(self, cuadro):
        """Devuelve {objeto: (t | None, r | None, s | None)} con los canales absolutos de ese cuadro."""
        salida = {}
        for nombre, canales in self.pistas.items():
            t = [canales[k].valor(cuadro) / 4096 if k in canales else None for k in (0, 1, 2)]
            r = [canales[k].valor(cuadro) * UNIDAD_ANGULO if k in canales else None for k in (3, 4, 5)]
            s = [canales[k].valor(cuadro) / 4096 if k in canales else None for k in (6, 7, 8)]
            salida[nombre] = (t, r, s)
        return salida
