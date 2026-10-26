"""Lectores y extracción DS con recursos sintéticos; no requieren ROMs comerciales."""
import hashlib
import json
from pathlib import Path
import struct
import sys

import ndspy.fnt
import ndspy.lz10
import ndspy.narc
import ndspy.rom
import ndspy.soundArchive
import ndspy.soundWave
import ndspy.soundWaveArchive
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'nucleo'))

from valedores import extraer, juegos, nitro, proyectos, recursos_nds, rutas  # noqa: E402

NUEVOS = {'inazuma-eleven': 'YEES', 'mario-party-ds': 'A8TP', 'phoenix-wright-3': 'YG3Y',
          'profesor-layton': 'A5FP', 'super-mario-64-ds': 'ASMP'}


@pytest.mark.parametrize('envoltorio', [b'', b'LZ77', struct.pack('<I', 2)])
def test_lz_y_envoltorios(envoltorio):
    original = b'Patrones de sprites y tiles' * 100
    datos, metodo = nitro.descomprimir(envoltorio + ndspy.lz10.compress(original), level5=True)
    assert datos == original and metodo.endswith('LZ10')


def test_rle_lz11_y_errores():
    assert nitro.descomprimir(b'\x30\x06\x00\x00\x80A\x02BCD')[0] == b'AAABCD'
    assert nitro.descomprimir(b'\x11\x06\x00\x00\x00ABCDEF')[0] == b'ABCDEF'
    for datos in (b'\x10\x20\x00\x00\x80\x00\x00', b'\x30\x05\x00\x00\x80',
                  b'\x10\xff\xff\xff\x80'):
        with pytest.raises(ValueError):
            nitro.descomprimir(datos)
    assert nitro.descomprimir(b'Sin compresion') == (b'Sin compresion', None)


def test_tablas_y_offsets():
    # PAC: offset absoluto; Mario Party: offset relativo al final del contador.
    pac = struct.pack('<IIIII', 2, 20, 3, 23, 2) + b'ABCDE'
    mp = struct.pack('<IIIII', 2, 16, 3, 19, 2) + b'ABCDE'
    assert [d for _, _, d in nitro.tabla_pares(pac)] == [b'ABC', b'DE']
    assert [d for _, _, d in nitro.tabla_pares(mp, relativo=4)] == [b'ABC', b'DE']
    assert nitro.tabla_pares(pac[:-1]) is None
    assert nitro.tabla_pares(struct.pack('<III', 1, 0, 4)) is None
    assert nitro.scripts_phoenix(pac) == nitro.tabla_pares(pac)


@pytest.mark.parametrize('tipo', [0, 2, 3])
def test_pkh_packnum(tipo):
    cab = bytearray(0x30)
    cab[:16] = b'PackNum 20080626'
    struct.pack_into('<H', cab, 0x12, tipo)
    struct.pack_into('<H', cab, 0x16, 2)
    struct.pack_into('<I', cab, 0x1C, 3)
    if tipo == 0:
        cab += struct.pack('<IIIIII', 9, 0, 3, 10, 3, 3)
    elif tipo == 2:
        cab += struct.pack('<IIII', 9, 0, 10, 0)
    else:
        cab += struct.pack('<II', 9, 10)
    assert [d for _, _, d in nitro.paquete_inazuma(cab, b'ABCDEF')] == [b'ABC', b'DEF']
    with pytest.raises(ValueError):
        nitro.paquete_inazuma(cab, b'A')


def _fondo():
    # Tile asimétrico: verde a la derecha, rojo a la izquierda.
    tile = np.zeros((8, 8), dtype='uint8')
    tile[:, 4:] = 1
    return (struct.pack('<IHHI', 2, 31, 31 << 5, 1) + tile.tobytes()
            + struct.pack('<HHHH', 2, 1, 0, 1024))


def test_fondo_y_flip():
    im = recursos_nds.fondo_layton(_fondo())
    assert im.size == (16, 8)
    assert im.getpixel((0, 0)) == (255, 0, 0, 255)
    assert im.getpixel((8, 0)) == (0, 255, 0, 255)
    with pytest.raises(ValueError):
        recursos_nds.fondo_layton(_fondo()[:-1])


def _rom(codigo='ASMP'):
    rom = ndspy.rom.NintendoDSRom()
    rom.idCode = codigo.encode('ascii')
    return rom


def test_extraccion_narc_trazable_y_repetible(tmp_path):
    rom = _rom()
    narc = ndspy.narc.NARC()
    contenido = ndspy.lz10.compress(b'Una muestra de un recurso' * 4)
    narc.files = [contenido]
    rom.files = [narc.save(), b'Archivo sin nombre']
    rom.filenames = ndspy.fnt.Folder(files=['caja.narc'])
    e = recursos_nds.Extractor('super-mario-64-ds', rom, tmp_path)
    assert e.ejecutar()
    cat = json.loads((tmp_path / 'catalogo.json').read_text('utf-8'))
    assert len(cat['recursos']) == 3 and cat['archivos_nitrofs_procesados'] == 2
    miembro = next(r for r in cat['recursos'] if '::' in r['origen'])
    assert miembro['sha256'] == hashlib.sha256(contenido).hexdigest()
    assert (tmp_path / miembro['derivados'][0]).read_bytes() == b'Una muestra de un recurso' * 4
    antes = (tmp_path / 'catalogo.json').read_bytes()
    assert recursos_nds.Extractor('super-mario-64-ds', rom, tmp_path).ejecutar()
    assert (tmp_path / 'catalogo.json').read_bytes() == antes


def test_sdat_exporta_muestras_y_no_inventa_canciones(tmp_path):
    sdat = ndspy.soundArchive.SDAT()
    ar = ndspy.soundWaveArchive.SWAR()
    ar.waves = [ndspy.soundWave.SWAV.fromData(b'\x00\x40\xc0\x00', sampleRate=8000,
                time=2095, totalLength=1)]
    sdat.waveArchives = [('instrumento', ar)]
    rom = _rom('A8TP')
    rom.files = [sdat.save()]
    rom.filenames = ndspy.fnt.Folder(files=['sonido.sdat'])
    assert recursos_nds.Extractor('mario-party-ds', rom, tmp_path).ejecutar()
    aud = json.loads(next(tmp_path.glob('archivos/*/audio/catalogo.json')).read_text('utf-8'))
    assert len(aud['wav']) == 1 and aud['wav'][0]['pico'] > 0
    assert aud['secuencias'] == []


def test_error_grafico_no_da_exito(tmp_path):
    rom = _rom('A5FP')
    rom.files = [struct.pack('<I', 2) + ndspy.lz10.compress('Fondo dañado'.encode('utf-8'))]
    rom.filenames = ndspy.fnt.Folder(files=['malo.arc'])
    e = recursos_nds.Extractor('profesor-layton', rom, tmp_path)
    # El origen dentro de bg identifica la estructura que debe leer el conversor.
    e.recurso('malo.arc', rom.files[0], 'archivos/00000', 'data/bg/malo.arc', rom.getFileByName)
    assert e.errores


def test_rapido_limita_y_etiqueta(tmp_path):
    rom = _rom()
    rom.files = [b'Original'] * 40
    rom.filenames = ndspy.fnt.Folder(files=['%03d.bin' % i for i in range(40)])
    assert recursos_nds.Extractor('super-mario-64-ds', rom, tmp_path, rapido=True).ejecutar()
    cat = json.loads((tmp_path / 'catalogo.json').read_text('utf-8'))
    assert cat['rapido'] and cat['archivos_nitrofs_procesados'] == 16


def test_manifiestos_de_extraccion_y_huella(monkeypatch, tmp_path):
    for juego, codigo in NUEVOS.items():
        m = rutas.manifiesto(juego)
        assert m['rom']['codigos'] == [codigo] and m['soporte'] == 'extraccion'
        assert not m['formatos'] and juegos.skills_del_juego(juego) == ['recursos-' + juego]
        assert all(Path(p).is_file() for p in juegos._archivos_extractor(juego))
        assert 'nucleo/valedores/nitro.py' in m['extractor']['fuentes']
        with pytest.raises(ValueError, match='motor de vídeo'):
            proyectos.crear('No hay motor', juego)
        monkeypatch.setattr(rutas, 'rom', lambda _: str(tmp_path / 'prueba.nds'))
        args = extraer.comandos(juego, rapido=True)[0]
        assert args[0] == 'tools/extraer.py' and args[-1] == '--rapido'


def test_rom_de_otro_juego_se_rechaza_sin_escribir(tmp_path):
    fichero = tmp_path / 'otra.nds'
    _rom('A2DP').saveToFile(str(fichero))
    destino = tmp_path / 'salida'
    with pytest.raises(SystemExit):
        recursos_nds.principal('super-mario-64-ds', ['--rom', str(fichero), '--salida', str(destino)])
    assert not destino.exists()


def test_cambios_en_lector_compartido_invalidan_huella(monkeypatch, tmp_path):
    (tmp_path / 'nucleo').mkdir()
    lector = tmp_path / 'nucleo' / 'lector.py'
    lector.write_text('# versión inicial\n', encoding='utf-8')
    monkeypatch.setattr(rutas, 'REPO', str(tmp_path))
    monkeypatch.setattr(rutas, 'JUEGOS', str(tmp_path / 'juegos'))
    monkeypatch.setattr(rutas, 'manifiesto', lambda _: {'extractor': {'fuentes': ['nucleo/lector.py']}})
    antes = juegos.hash_extractor('ejemplo')
    lector.write_text('# versión corregida\n', encoding='utf-8')
    assert juegos.hash_extractor('ejemplo') != antes


def test_compresion_no_compatible_queda_identificada(tmp_path):
    e = recursos_nds.Extractor('profesor-layton', _rom('A5FP'), tmp_path)
    e.recurso('bg.arc', struct.pack('<I', 3) + b'\x24\x08\x00\x00abcd',
              'archivos/00000', 'data/bg/bg.arc', lambda _: None)
    assert not e.errores and e.registros[0]['avisos']
    assert e.registros[0]['tipo'] == 'compresión pendiente o dañada'
