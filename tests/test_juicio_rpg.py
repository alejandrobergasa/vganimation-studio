"""Orientación del movimiento, escala conjunta y golpes audiovisuales, sin ROMs."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'nucleo'))
from valedores import rutas
from valedores.video_nds import Clip,Plano


def modulo(juego,nombre):
    p=Path(rutas.motor_dir(juego))/(nombre+'.py')
    spec=importlib.util.spec_from_file_location('prueba_'+nombre,p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize('dx,dy,esperada',[(1,0,'este'),(1,1,'sureste'),(0,1,'sur'),(-1,1,'suroeste'),
                                       (-1,0,'oeste'),(-1,-1,'noroeste'),(0,-1,'norte'),(1,-1,'noreste')])
def test_direccion_sigue_vector_de_movimiento(dx,dy,esperada):
    assert modulo('inazuma-eleven','rpg').direccion(dx,dy)==esperada


def test_recorrido_conserva_mirada_al_parar():
    m=modulo('inazuma-eleven','rpg')
    r=m.Recorrido([(0,10,10),(1,20,10),(2,20,10),(3,20,0)])
    assert r.estado(.5)[:4]==(15,10,'este',True)
    assert r.estado(1.5)[:4]==(20,10,'este',False)
    assert r.estado(4)[:4]==(20,0,'norte',False)
    with pytest.raises(ValueError):m.Recorrido([(0,0,0),(0,1,1)])


def test_actor_cambia_clip_al_girar_y_al_parar():
    m=modulo('inazuma-eleven','rpg')
    def leer(nombre,direccion,accion,**kw):
        return Clip([Image.new('RGBA',(2,2),'red' if direccion=='este' and accion=='caminar' else 'blue')])
    a=m.ActorDireccional(SimpleNamespace(personaje=leer),'Mark',m.Recorrido([(0,0,0),(1,10,0),(2,10,0)]))
    assert a.frame(.5).getpixel((0,0))==(255,0,0,255)
    assert a.frame(1.5).getpixel((0,0))==(0,0,255,255)


def test_fondo_y_sprite_comparten_ampliacion_entera():
    m=modulo('inazuma-eleven','rpg')
    fondo=Image.new('RGBA',(16,16),'green')
    actor=SimpleNamespace(posicion=lambda t:(8,8),frame=lambda t:Image.new('RGBA',(2,2),'red'))
    e=m.EscenaRPG(fondo,tamano=(8,8),escala_salida=2);e.centro=(8,8);e.actor(actor)
    esperado=fondo.crop((6,6,10,10));esperado.paste('red',(1,0,3,2))
    assert np.array_equal(np.asarray(e.frame(0)),np.asarray(esperado.resize((8,8),Image.Resampling.NEAREST)))


def test_oclusiones_y_visibilidad_con_ancla_de_objeto():
    m=modulo('inazuma-eleven','rpg')
    fondo=Image.new('RGBA',(16,16),'green')
    a=SimpleNamespace(posicion=lambda t:(8,8),frame=lambda t:Image.new('RGBA',(2,2),'red'),
                      ancla=(0,0),visible=lambda t:t<1)
    e=m.EscenaRPG(fondo,tamano=(8,8),escala_salida=2);e.centro=lambda t:(8,8);e.actor(a)
    e.oclusion(Image.new('RGBA',(1,2),'blue'),(8,8))
    im=e.frame(0)
    assert im.getpixel((4,4))==(0,0,255,255)
    assert im.getpixel((6,4))==(255,0,0,255)
    assert e.frame(2).getpixel((6,4))==(0,128,0,255)


def test_impacto_es_breve_y_recupera_camara():
    m=modulo('phoenix-wright-3','juicio')
    p=Plano(2,color='red');p.camara_x=4
    m.impacto(p,(32,48),desde=.3,duracion=.4)
    assert p.camara_x(0)==p.camara_x(1)==4
    assert p.frame(.32,(32,48)).getpixel((16,24))[:3]!=(255,0,0)
    assert p.frame(1,(32,48)).getpixel((16,24))==(255,0,0)


def test_banda_sonora_respeta_pausas_y_reduce_musica_en_impactos():
    m=modulo('phoenix-wright-3','juicio');audios=[]
    rec=SimpleNamespace(musica=lambda pista,d:(np.ones((round(d*1000),2)),1000))
    v=SimpleNamespace(audio=lambda a,fs,**kw:audios.append((a,kw)))
    m.banda_sonora(v,rec,[(0,1,'tension',.4),(1,2,None,.4),(2,3,'replica',.3)],[(.5,'mazo',1)])
    assert len(audios)==2 and audios[1][1]['desde']==2
    assert audios[0][0][500,0]<audios[0][0][250,0]*.6
