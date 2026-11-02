"""Composición, tiempos y audio de los motores nuevos, sin ROMs comerciales."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'nucleo'))
from valedores import rutas, proyectos
from valedores.video_nds import Video, Plano, Clip, Fuente, Superposicion, interpolar
from valedores.activos_video_nds import textura, imagenes_phoenix, imagen_pac_inazuma, texturas_sm64
from valedores.sonido_video_nds import sadl

JUEGOS=['inazuma-eleven','mario-party-ds','phoenix-wright-3','profesor-layton','super-mario-64-ds']


def test_clip_respeta_tiempos_y_final():
    a,b=Image.new('RGBA',(2,2),'red'),Image.new('RGBA',(2,2),'blue')
    c=Clip([a,b],[.1,.3])
    assert c.frame(.09).getpixel((0,0))==(255,0,0,255)
    assert c.frame(.11).getpixel((0,0))==(0,0,255,255)
    assert c.frame(.41).getpixel((0,0))==(255,0,0,255)
    c.repetir=False
    assert c.frame(8).getpixel((0,0))==(0,0,255,255)


def test_movimiento_camara_y_capa_de_pantalla():
    p=Plano(1)
    actor=Image.new('RGBA',(2,2),'red')
    p.sprite(actor,x=interpolar(2,6,1),y=2,ancla=(0,0))
    p.sprite(Image.new('RGBA',(1,1),'green'),x=7,y=7,pantalla=True,ancla=(0,0))
    p.camara_x=1
    assert p.frame(0,(8,8)).getpixel((1,2))==(255,0,0)
    assert p.frame(1,(8,8)).getpixel((5,2))==(255,0,0)
    assert p.frame(1,(8,8)).getpixel((7,7))==(0,128,0)


def test_superposicion_conserva_el_original():
    base=Clip([Image.new('RGBA',(4,4),'red')])
    ojos=Clip([Image.new('RGBA',(1,1),'blue')])
    combinado=Superposicion(base,ojos,(2,1))
    assert combinado.frame(0).getpixel((2,1))==(0,0,255,255)
    assert base.frame(0).getpixel((2,1))==(255,0,0,255)


def test_audio_remuestreo_mono_y_validacion():
    v=Video('profesor-layton',tamano=(64,64))
    v.audio(np.ones((800,1),dtype='float32'),8000,desde=.5)
    assert v.audios[0][2].shape==(3277,2)
    with pytest.raises(ValueError):v.audio(np.array([float('nan')]))
    with pytest.raises(ValueError):v.audio(np.ones(10),desde=-1)
    v.plano(1)
    with pytest.raises(ValueError):v.renderizar('../fuera.mp4')


def test_zoom_mantiene_el_actor_en_el_centro():
    p=Plano(1)
    p.zoom=2
    p.sprite(Image.new('RGBA',(2,2),'red'),x=5,y=5,ancla=(.5,.5))
    assert p.frame(0,(10,10)).getbbox()==(3,3,7,7)


def test_fuente_por_defecto_prioriza_el_espanol(monkeypatch):
    from valedores import activos_video_nds as activos
    r=activos.Recursos.__new__(activos.Recursos)
    r.juego='animal-crossing'
    r.buscar=lambda **kw:['japonesa','latina']
    r.datos=lambda n:n.encode('ascii')
    def leer(d):
        return SimpleNamespace(enc=2 if d==b'japonesa' else 3,
            cmap={ord(c):i for i,c in enumerate('ABC' if d==b'japonesa' else '¡¿ñÑáéíóú')})
    monkeypatch.setattr(activos,'lectores',lambda:(None,SimpleNamespace(Font=leer),None))
    monkeypatch.setattr(activos,'Fuente',lambda d,**kw:SimpleNamespace(origen=d))
    assert r.fuente().origen==b'latina'


def test_cortes_usan_el_plano_correcto():
    v=Video('profesor-layton',tamano=(4,4))
    v.plano(.25,color='red');v.plano(.75,color='blue')
    assert v.frame(.24).getpixel((0,0))==(255,0,0)
    assert v.frame(.25).getpixel((0,0))==(0,0,255)
    assert v.frame(2).getpixel((0,0))==(0,0,255)


def test_cabecera_phoenix_conserva_transparencia_y_procedencia():
    cab=bytes([3,0,0,0])+struct.pack('<4I',20,32,52,32)
    d=cab+bytes([0x10]*32)+struct.pack('<16H',0,31,*([0]*14))
    imgs=imagenes_phoenix(d)
    assert len(imgs)==1 and imgs[0][0]==0
    im=imgs[0][1]
    assert im.getpixel((0,0))[3]==0 and im.getpixel((1,0))==(255,0,0,255)
    assert imagenes_phoenix(d[:-1])==[]


@pytest.mark.parametrize('codigo',[0x72,0xB2])
def test_sadl_sintetico_y_limites(codigo):
    d=bytearray(256+16)
    d[:4]=b'sadl';d[0x32]=1;d[0x33]=codigo
    struct.pack_into('<I',d,0x40,len(d))
    if codigo==0xB2:d[-1]=128
    audio,fs=sadl(d)
    assert audio.shape[1]==1 and fs==16364 and np.all(np.isfinite(audio))
    struct.pack_into('<I',d,0x40,len(d)+32)
    with pytest.raises(ValueError):sadl(d)


@pytest.mark.parametrize('juego',JUEGOS)
def test_cada_motor_se_importa_y_crea_video(juego,tmp_path,monkeypatch):
    p=Path(rutas.motor_dir(juego))/'motor.py'
    spec=importlib.util.spec_from_file_location('motor_'+juego.replace('-','_'),p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    v=mod.Video(formato='vertical')
    assert v.juego==juego and v.tamano==(1080,1920)
    monkeypatch.setattr(rutas,'PROYECTOS',str(tmp_path/'proyectos'))
    monkeypatch.setattr(rutas,'ENTRADA',str(tmp_path/'entrada'))
    proyecto=proyectos.crear('Prueba',juego,formato='vertical')
    assert proyecto['juego']==juego and proyecto['formato']=='vertical'


def _fuente_sintetica(glifos,espacio=3):
    """Fuente mínima: cada glifo es (margen, ancho, avance, bitmap) y ' ' no tiene tinta."""
    f=SimpleNamespace(height=2,depth=1,rot=0,enc=0,dleft=0,dwidth=1,dadv=1,
        cmap={ord(c):i for i,c in enumerate(glifos)},
        widths=[g[:3] for g in glifos.values()],
        glyph=lambda i:np.array(list(glifos.values())[i][3],dtype='uint8'))
    fuente=Fuente.__new__(Fuente)
    fuente.f,fuente.extra,fuente.espaciado=f,{},0
    return fuente


def test_fuente_espaciado_por_tinta_ignora_margenes_y_avances_irregulares():
    # 'a' sin margen ni hueco (avance == tinta) y 'y' con margen propio de 1 px.
    glifos={'a':(0,3,3,[[1,1,1],[1,1,1]]),'y':(1,3,5,[[1,1,1],[1,1,1]]),' ':(0,0,4,[[0,0,0],[0,0,0]])}
    fuente=_fuente_sintetica(glifos)
    assert fuente.texto('aa').width==6          # sin espaciado: pegadas
    fuente.espaciado=1
    for texto in ('aa','ay','ya'):
        im=fuente.texto(texto)
        assert im.width==7                     # 3 + 1 de hueco + 3, sea cual sea el margen
        columnas=[x for x in range(im.width) if im.getchannel('A').crop((x,0,x+1,2)).getbbox()]
        assert columnas==[0,1,2,4,5,6]
    assert fuente.texto('a a').width==3+1+4+3  # el espacio conserva su avance


def test_alinear_cara_layton_encuentra_el_encaje_exacto():
    from valedores.activos_video_nds import alinear_cara_layton
    rng=np.random.default_rng(1)
    cuerpo=Image.fromarray(rng.integers(0,255,(40,30,4),dtype='uint8')).convert('RGBA')
    cuerpo.putalpha(255)
    parche=cuerpo.crop((7,21,16,27))             # la cara sale del propio cuerpo
    otro=Image.fromarray(rng.integers(0,255,(6,9,4),dtype='uint8')).convert('RGBA')
    otro.putalpha(255)
    assert alinear_cara_layton([cuerpo],[otro,parche])==((7,21),0.0)
    with pytest.raises(ValueError):
        alinear_cara_layton([cuerpo],[otro])
