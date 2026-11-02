"""Actuación 2D, impactos de juicio y montaje musical con bancos de la ROM."""
import math
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image,ImageDraw
from valedores import rutas


class Busto:
    def __init__(self,recursos,nombre,pose='quieto',hablar='hablar'):
        self.quieto=recursos.personaje_personalizado(nombre,pose)
        self.habla=recursos.personaje_personalizado(nombre,hablar) if hablar else self.quieto

    def frame(self,t):
        return self.quieto.frame(t)

    def conversando(self,segundos):
        base=self
        class Conversacion:
            def frame(self,t):
                return (base.habla if t<segundos else base.quieto).frame(t)
        return Conversacion()


class LineasVelocidad:
    def __init__(self,tamano,color=(235,235,255,220)):
        self.tamano,self.color=tamano,color

    def frame(self,t):
        w,h=self.tamano;im=Image.new('RGBA',self.tamano);d=ImageDraw.Draw(im)
        cx,cy=w*.5,h*.48
        for i in range(22):
            a=i*math.tau/22+math.sin(t*8)*.025
            r=min(w,h)*(.34+.07*math.sin(i*13+t*12))
            d.line((cx+math.cos(a)*r,cy+math.sin(a)*r,cx+math.cos(a)*h,cy+math.sin(a)*h),
                   fill=self.color,width=1+i%3)
        return im


def impacto(plano,tamano,desde=0,duracion=.45,intensidad=1,color=(255,248,220,255)):
    """Un golpe breve: destello, líneas de velocidad y sacudida amortiguada."""
    w,h=tamano;escala=w/270
    plano.sprite(LineasVelocidad((270,round(h/escala))),x=0,y=0,ancla=(0,0),escala=escala,
                 desde=desde,hasta=desde+duracion,pantalla=True,opacidad=lambda t:max(0,1-t/duracion)*.85)
    blanco=Image.new('RGBA',tamano,color)
    plano.sprite(blanco,x=0,y=0,ancla=(0,0),pantalla=True,desde=desde,hasta=desde+.10,
                 opacidad=lambda t:max(0,1-t/.10)*.85)
    for eje,fase in [('camara_x',0),('camara_y',1.4)]:
        anterior=getattr(plano,eje)
        def mover(t,anterior=anterior,fase=fase):
            u=t-desde
            extra=math.sin(u*73+fase)*w*.006*intensidad*(1-u/duracion) if 0<=u<=duracion else 0
            return (anterior(t) if callable(anterior) else anterior)+extra
        setattr(plano,eje,mover)


def rotulo_impacto(plano,imagen,tamano,desde=0,duracion=1.0):
    w,h=tamano
    base=min(w*.90/imagen.width,h*.22/imagen.height)
    def escala(t):
        u=min(1,t/.15)
        return base*(.4+.7*(1-(1-u)**3)-.1*min(1,max(0,t-.15)/.15))
    plano.sprite(imagen,x=w*.5,y=h*.27,ancla=(.5,.5),pantalla=True,desde=desde,hasta=desde+duracion,
                 escala=escala,giro=lambda t:-5*max(0,1-t/.18))


def banda_sonora(video,recursos,programa,efectos):
    """Música por escena, cortes dramáticos y ducking alrededor de impactos (todo SDAT)."""
    for inicio,fin,pista,volumen in programa:
        if not pista or fin<=inicio:continue
        a,fs=recursos.musica(pista,fin-inicio+.05)
        a=a.copy();n=min(len(a),round((fin-inicio)*fs));a=a[:n]
        t=np.arange(n)/fs
        envolvente=np.minimum(1,t/.12)*np.minimum(1,(fin-inicio-t)/.2)
        for instante,nombre,vol in efectos:
            if nombre=='blip':continue
            envolvente*=1-.62*np.exp(-((t-(instante-inicio))/.17)**2)
        video.audio(a*np.clip(envolvente,0,1)[:,None],fs,desde=inicio,volumen=volumen)


def normalizar_audio_redes(archivo,objetivo=-16,pico=-2):
    """Dos pasadas EBU R128; conserva el vídeo y deja margen para la codificación AAC."""
    archivo=Path(archivo)
    trabajo=Path(rutas.trabajo('phoenix-wright-3'))
    filtro='loudnorm=I=%s:TP=%s:LRA=8'%(objetivo,pico)
    analisis=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(archivo),'-vn','-af',
        filtro+':print_format=json','-f','null','NUL'],capture_output=True,text=True,check=True)
    medidas=json.loads(analisis.stderr[analisis.stderr.rfind('{'):analisis.stderr.rfind('}')+1])
    ajuste=filtro+':measured_I={input_i}:measured_TP={input_tp}:measured_LRA={input_lra}:measured_thresh={input_thresh}:offset={target_offset}:linear=true'.format(**medidas)
    temporal=trabajo/(archivo.stem+'_audio_redes.mp4')
    subprocess.run(['ffmpeg','-y','-v','error','-i',str(archivo),'-map','0:v:0','-map','0:a:0',
        '-c:v','copy','-af',ajuste,'-ar','48000','-c:a','aac','-b:a','192k','-movflags','+faststart',str(temporal)],check=True)
    temporal.replace(archivo)
    (trabajo/'normalizacion_audio.json').write_text(json.dumps(medidas,indent=2),encoding='utf-8')
    return str(archivo)
