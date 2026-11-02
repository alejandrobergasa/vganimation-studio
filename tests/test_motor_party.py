"""Piezas del motor 3D de Mario Party DS, sin ROMs comerciales."""
from pathlib import Path
import math
import struct
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'nucleo'))
from valedores.anmf_party import AnimacionParty
from valedores.caras_foto import CaraFoto, Hitos
from valedores.efectos_video import TRANSICIONES, transicion
from valedores.escena3d import Camara, ENCUADRES
from valedores.video_nds import Pista


def _anmf(canales):
    """ANMF de una pista 'spin' con canales [(tipo, bytes de datos)]."""
    tabla = 8 + 4 * len(canales)
    nombre = b'spin\0\0\0\0'
    cuerpo, datos, off = b'', b'', tabla + len(nombre)
    for tipo, d in canales:
        cuerpo += struct.pack('<I', tipo << 24 | off)
        datos += d
        off += len(d)
    pista = struct.pack('<II', 2 << 12 | len(canales) << 4, tabla)
    base = pista + cuerpo + nombre + datos
    cab = b'HBDF' + struct.pack('<I', 32 + len(base)) + b'ANMF' + struct.pack('<IIIII', len(base), 0, 0, 1, 0)
    return cab + base


def _claves(*claves):
    return struct.pack('<II', 6, 0) + b''.join(struct.pack('<Hhhh', 5 << 12 | f, v, a, b) for f, v, a, b in claves) + bytes(8)


def _constante(valor):
    return struct.pack('<IIIi', 3, 0, 0, valor)


def test_anmf_rotacion_de_claves_y_de_constante_usan_su_escala():
    a = AnimacionParty(_anmf([(3, _claves((0, 1024, 0, 0), (30, 2048, 0, 0))), (4, _constante(16384)), (1, _constante(8192))]))
    assert a.cuadros == 30 and a.duracion == 1
    t, r, s = a.muestrear(0)['spin']
    assert r[0] == pytest.approx(math.pi / 2)    # claves: 4096 = una vuelta
    assert r[1] == pytest.approx(math.pi / 2)    # constante: 65536 = una vuelta
    assert t[1] == pytest.approx(2)              # traslación en punto fijo de 12 bits
    assert s == [None, None, None]
    assert a.muestrear(30)['spin'][1][0] == pytest.approx(math.pi)
    assert a.muestrear(15)['spin'][1][0] == pytest.approx(math.pi * 0.75, abs=1e-3)


def test_anmf_rechaza_otros_archivos():
    with pytest.raises(ValueError):
        AnimacionParty(b'HBDF\0\0\0\0MDLF' + bytes(40))


def test_pista_interpola_y_sostiene_extremos():
    p = Pista([(1, 0), (3, 10)], curva='recta')
    assert p(0) == 0 and p(2) == pytest.approx(5) and p(9) == 10


@pytest.mark.parametrize('tipo', TRANSICIONES)
def test_transiciones_llegan_de_una_imagen_a_otra(tipo):
    a, b = Image.new('RGB', (64, 36), (255, 0, 0)), Image.new('RGB', (64, 36), (0, 0, 255))
    assert transicion(tipo, a, b, 0.5).size == (64, 36)
    assert transicion(tipo, a, b, 0).convert('RGB').getpixel((32, 18)) == (255, 0, 0)
    assert transicion(tipo, a, b, 1).convert('RGB').getpixel((32, 18)) == (0, 0, 255)


def test_transicion_desconocida():
    a = Image.new('RGB', (4, 4))
    with pytest.raises(ValueError):
        transicion('nada', a, a, .5)


class _Actor:
    giro = 0.0

    def altura(self):
        return 10.0

    def posicion(self, t):
        return np.zeros(3)


@pytest.mark.parametrize('tipo', ENCUADRES)
def test_encuadre_se_aleja_en_vertical(tipo):
    c = Camara()
    c.encuadre(tipo, _Actor(), 0, corte=True)
    ancho = np.linalg.norm(np.asarray(c.estado(1)[0]) - np.asarray(c.estado(1)[1]))
    c.aspecto = 9 / 16
    alto = np.linalg.norm(np.asarray(c.estado(1)[0]) - np.asarray(c.estado(1)[1]))
    assert alto > ancho * 1.4


def test_encuadre_desconocido():
    with pytest.raises(ValueError):
        Camara().encuadre('nada', _Actor())


def test_cara_de_foto_alinea_y_compone_expresiones(tmp_path):
    # Foto sintética: piel lisa con ojos y boca oscuros en sitios conocidos.
    im = np.full((300, 300, 3), (225, 180, 150), np.uint8)
    for x, y in ((110, 120), (190, 120), (150, 200)):
        im[y - 5:y + 5, x - 12:x + 12] = (30, 20, 20)
    ruta = tmp_path / 'foto.png'
    Image.fromarray(im).save(ruta)
    cara = CaraFoto(str(ruta), Hitos((110, 120), (190, 120), (150, 200), (150, 250)))
    neutra, abierta = cara.imagen('neutra'), cara.imagen('alegria+boca2')
    assert neutra.shape == abierta.shape and neutra.shape[0] == neutra.shape[1]
    assert not np.array_equal(neutra, abierta)
    assert 0.7 < cara.piel[0] <= 1 and cara.piel[0] > cara.piel[2]
    with pytest.raises((ValueError, KeyError)):
        cara.imagen('nada')
