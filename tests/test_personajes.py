"""Importación de personajes, anclas y lectura de sprites RPG sin ROM comercial."""
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
from valedores.personajes import cargar, textura, perfil
from valedores.modelos_video_nds import VistaModelo


def archivo_personaje(tmp_path, **opciones):
    im=Image.new('RGBA',(32,16))
    im.paste('red',(3,1,9,15))
    im.paste('blue',(19,4,25,15))
    im.save(tmp_path/'atlas.png')
    m=dict(version=1,juego='inazuma-eleven',modo='pixel_art',referencia_identidad='foto.jpg',
           referencia_rom='spr/char',imagen='atlas.png',rejilla=[2,1],lienzo=[16,24],
           ajuste='pies',tamano_visible=[8,14],revisado=True,
           animaciones={'caminar':dict(frames=[0,1],duraciones=[.1,.2])})
    m.update(opciones)
    p=tmp_path/'personaje.json'
    p.write_text(json.dumps(m),encoding='utf-8')
    return p


def test_atlas_mantiene_escala_ancla_y_tiempos(tmp_path):
    c=cargar('inazuma-eleven',archivo_personaje(tmp_path),'caminar')
    a,b=c.imagenes
    assert a.size==b.size==(16,24)
    assert a.getbbox()==(5,10,11,24) and b.getbbox()==(5,13,11,24)
    assert c.frame(.15).getpixel((6,20))==(0,0,255,255)
    assert c.frame(.31).getpixel((6,20))==(255,0,0,255)


def test_carga_exige_revision_juego_y_optin_de_foto(tmp_path):
    p=archivo_personaje(tmp_path,revisado=False)
    with pytest.raises(ValueError,match='revisa'):cargar('inazuma-eleven',p,'caminar')
    assert cargar('inazuma-eleven',p,'caminar',exigir_revision=False)
    with pytest.raises(ValueError,match='juego'):cargar('phoenix-wright-3',p,'caminar')
    p=archivo_personaje(tmp_path,modo='foto_directa')
    with pytest.raises(ValueError,match='explícita'):cargar('inazuma-eleven',p,'caminar')
    assert cargar('inazuma-eleven',p,'caminar',permitir_foto=True)


def test_no_carga_imagen_fuera_del_personaje_ni_rejilla_inexacta(tmp_path):
    p=archivo_personaje(tmp_path,imagen='../foto.jpg')
    with pytest.raises(ValueError,match='dentro'):cargar('inazuma-eleven',p,'caminar')
    p=archivo_personaje(tmp_path,rejilla=[3,1])
    with pytest.raises(ValueError,match='rejilla'):cargar('inazuma-eleven',p,'caminar')


def test_textura_no_se_presenta_como_sprite(tmp_path):
    p=archivo_personaje(tmp_path,modo='textura_3d',material='cara')
    with pytest.raises(ValueError,match='modelo'):cargar('inazuma-eleven',p)
    nombre,im=textura('inazuma-eleven',p)
    assert nombre=='cara' and im.size==(32,16)
    assert perfil('inazuma-eleven')['modo']=='pixel_art'
    assert perfil('phoenix-wright-3')['modo']=='anime'
    assert perfil('mkds')['modo']=='textura_3d'


def test_pose_complementaria_no_reemplaza_la_imagen_aprobada(tmp_path):
    Image.new('RGBA',(16,16),'yellow').save(tmp_path/'otra-pose.png')
    p=archivo_personaje(tmp_path,animaciones={'quieto':{'frames':[0]},'objecion':{
        'imagen':'otra-pose.png','rejilla':[1,1],'frames':[0]}})
    assert cargar('inazuma-eleven',p,'quieto').frame(0).getpixel((6,20))==(255,0,0,255)
    assert cargar('inazuma-eleven',p,'objecion').frame(0).getpixel((6,20))==(255,255,0,255)


def test_atlas_con_cajas_y_vista_reflejada(tmp_path):
    p=archivo_personaje(tmp_path,cajas=[[0,0,16,16],[16,0,32,16]],animaciones={
        'quieto':{'frames':[0]},'oeste':{'frames':[0],'reflejar':True}})
    a=cargar('inazuma-eleven',p).frame(0)
    b=cargar('inazuma-eleven',p,'oeste').frame(0)
    assert np.array_equal(np.asarray(b),np.asarray(a.transpose(Image.Transpose.FLIP_LEFT_RIGHT)))
    p=archivo_personaje(tmp_path,cajas=[[0,0,40,16],[16,0,32,16]])
    with pytest.raises(ValueError,match='Cajas'):cargar('inazuma-eleven',p,'caminar')


def test_paleta_comun_preserva_transparencia(tmp_path):
    p=archivo_personaje(tmp_path,paleta=[[255,0,0],[0,0,255]])
    c=cargar('inazuma-eleven',p,'caminar')
    for im in c.imagenes:
        assert {rgba[:3] for n,rgba in im.getcolors(100) if rgba[3]}<={(255,0,0),(0,0,255)}
        assert im.getpixel((0,0))[3]==0


def test_textura_personalizada_conserva_uv_banco_y_resolucion():
    original=np.zeros((8,16,4),dtype=np.uint8)
    banco=SimpleNamespace(get=lambda tex,pal:original)
    v=VistaModelo.__new__(VistaModelo)
    v.modelo=SimpleNamespace(materials=[SimpleNamespace(tex='cara',pal='piel')])
    v.texturas=banco
    assert v.reemplazar_textura('cara',Image.new('RGBA',(64,64),'red')) is v
    assert v.texturas.get('cara','piel').shape==(8,16,4)
    assert v.texturas.get('cara','piel')[0,0].tolist()==[255,0,0,255]
    assert not original.any() and v.texturas.get('otra',None) is original
    with pytest.raises(ValueError,match='pertenece'):v.reemplazar_textura('inexistente',Image.new('RGBA',(1,1)))


def test_sprite_rpg_decodifica_pixeles_lineales_y_paleta():
    p=Path(rutas.motor_dir('inazuma-eleven'))/'sprites.py'
    spec=importlib.util.spec_from_file_location('sprites_prueba',p)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    meta=struct.pack('<4I',16,16,52,0)+struct.pack('<HHI',1,3,24)
    meta+=struct.pack('<6H',16,31,8,8,1,0)+struct.pack('<6HI',8,7,0,0,0,0,0)
    pix=bytes([0x21,0,0,0,0x11]+[0]*27)
    pac=struct.pack('<5I',2,20,len(meta),20+len(meta),len(pix))+meta+pix
    pal=struct.pack('<16H',0,31,31<<5,*([0]*13))
    im=mod.Pieza(pac).frame(0,pal)
    assert im.getpixel((24,24))==(255,0,0,255)
    assert im.getpixel((25,24))==(0,255,0,255)
    assert im.getpixel((24,25))==(255,0,0,255)
    assert im.getpixel((26,24))[3]==0
    with pytest.raises(ValueError,match='límites'):mod.Pieza(pac).frame(1,pal)


def test_estudio_transmite_adaptacion_de_identidad(tmp_path,monkeypatch):
    monkeypatch.setattr(rutas,'PROYECTOS',str(tmp_path/'proyectos'))
    monkeypatch.setattr(rutas,'ENTRADA',str(tmp_path/'entrada'))
    p=proyectos.crear('Adaptación','inazuma-eleven',formato='vertical')
    t=proyectos.contexto(p['slug'])
    assert 'referencias de identidad' in t and 'personajes-desde-fotos.md' in t
