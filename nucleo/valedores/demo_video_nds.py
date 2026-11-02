"""Pruebas reproducibles de los motores; todos los gráficos y sonidos salen de su ROM."""
import argparse
import math
from pathlib import Path

from . import rutas
from .activos_video_nds import Recursos
from .video_nds import Video, Clip, interpolar, Superposicion


def construir(juego, formato='horizontal', segundos=4, fps=30, personaje=None, animacion='quieto'):
    if segundos < 1:
        raise ValueError('La prueba debe durar al menos un segundo')
    recursos = Recursos(juego)
    video = Video(juego, formato=formato, fps=fps)
    w,h=video.tamano
    origenes=[]
    if juego == 'inazuma-eleven':
        from .recursos_nds import _modulo
        motor=_modulo('motor_ie_demo',Path(rutas.motor_dir(juego))/'motor.py')
        recursos=motor.Recursos()
        fondo=recursos.escenario('mr01b01')
        cx,cy=fondo.proyectar(0,-8)
        dx,dy=(64,0)
        mirada='este'
        if personaje:
            mirada=animacion.split('_',1)[1] if '_' in animacion else 'sur'
            vectores={'sur':(0,64),'sureste':(45,45),'este':(64,0),'noreste':(45,-45),
                      'norte':(0,-64),'noroeste':(-45,-45),'oeste':(-64,0),'suroeste':(-45,45)}
            dx,dy=vectores[mirada] if animacion.startswith('caminar_') else (0,0)
        ruta=motor.Recorrido([(0,cx-dx/2,cy-dy/2),(segundos,cx+dx/2,cy+dy/2)],mirada)
        actor=motor.ActorDireccional(recursos,personaje or 'Mark',ruta,personalizado=bool(personaje))
        escena=motor.EscenaRPG(fondo,video.tamano);escena.actor(actor,seguir=True)
        plano=video.plano(segundos)
        plano.sprite(escena,x=0,y=0,ancla=(0,0),pantalla=True)
        voces=recursos.buscar(tipo='audio SADL (pendiente)')
        voz=next((n for n in voces if recursos.registros[n]['bytes']>250000),voces[0])
        audio,fs=recursos.audio(voz,segundos)
        video.audio(audio,fs)
        origenes=fondo.origenes+['personaje personalizado: '+str(personaje) if personaje else 'data_iz/spr/char/{pcb,pch,ppb,pph}.pkb (Mark Evans)',voz]
    elif juego == 'profesor-layton':
        fondo='data/bg/choice_bg.arc'
        actor='data/ani/layton.arc'
        plano=video.plano(segundos,fondo=recursos.imagen(fondo))
        clip=recursos.clip(actor,'talk')
        escala=min(w*.55/clip.imagenes[0].width,h*.64/clip.imagenes[0].height)
        cara='data/ani/layton_e_face.arc'
        personaje=recursos.personaje_layton('layton','talk')
        plano.sprite(personaje,x=w*.5,y=h*.91,escala=escala)
        fuente=recursos.fuente()
        texto=fuente.texto('¡Qué aventura, señor Layton!',escala=3,color='#3b2210',ancho=w*.9)
        if texto.width>w*.9:
            raise ValueError('El rótulo de prueba excede el ancho')
        plano.sprite(texto,x=w*.5,y=h*.20,ancla=(.5,.5),pantalla=True)
        tema='data/stream/BGM_09.SAD'
        audio,fs=recursos.audio(tema,segundos)
        video.audio(audio,fs)
        origenes=[fondo,actor,cara,tema]
    elif juego == 'phoenix-wright-3':
        graficos=recursos.graficos_phoenix()
        fondo=graficos[412][1]
        # Las texturas tienen dimensiones potencia de dos; el margen alfa no
        # pertenece al escenario y no debe producir una banda negra en vertical.
        fondo=fondo.crop(fondo.getbbox())
        indice_pose=61 if formato=='vertical' else 78
        pose=recursos.personaje_personalizado(personaje,animacion) if personaje else graficos[indice_pose][1]
        imagen_pose=pose.frame(0) if personaje else pose.crop(pose.getbbox())
        if not personaje:pose=imagen_pose
        plano=video.plano(segundos,fondo=fondo)
        escala=min(w*.85/imagen_pose.width,h*.64/imagen_pose.height)
        plano.sprite(pose,x=interpolar(w*.45,w*.55,segundos),y=h*.96,escala=escala)
        tema=recursos.canciones()[0]
        audio,fs=recursos.musica(tema,segundos)
        video.audio(audio,fs)
        origenes=['data.bin@%x'%graficos[412][0],'personaje personalizado: '+str(personaje) if personaje else 'data.bin@%x'%graficos[indice_pose][0],tema]
    else:
        if juego == 'mario-party-ds':
            origen='data/p01_mario_LZ.bin::00019.bin'
        elif juego == 'super-mario-64-ds':
            origen='data/player/b_mario_all.bmd'
        else:
            raise ValueError('No hay prueba configurada para '+juego)
        modelo=recursos.modelo(origen,giro=lambda t: -.35+.7*t/segundos,tamano=(256,256))
        plano=video.plano(segundos,color=(29,39,59,255))
        escala=min(w*.82/256,h*.80/256)
        plano.sprite(modelo,x=w*.5,y=h*.91,escala=escala)
        tema='MU001' if juego == 'mario-party-ds' else 'NCS_BGM_CHIJOU'
        audio,fs=recursos.musica(tema,segundos)
        video.audio(audio,fs)
        origenes=[origen,tema]
    return video,origenes


def principal(juego,argv=None):
    ap=argparse.ArgumentParser(description='Prueba del motor de '+rutas.manifiesto(juego)['nombre'])
    ap.add_argument('--formato',choices=['horizontal','vertical'],default='horizontal')
    ap.add_argument('--segundos',type=float,default=4)
    ap.add_argument('--fps',type=int,default=30)
    ap.add_argument('--nombre',default='prueba_motor.mp4')
    ap.add_argument('--solo-frame',action='store_true')
    ap.add_argument('--personaje',help='Nombre en entrada/<proyecto>/personajes/ o ruta del personaje.json (Inazuma/Phoenix)')
    ap.add_argument('--animacion',default='quieto')
    args=ap.parse_args(argv)
    if args.personaje and juego not in ('inazuma-eleven','phoenix-wright-3'):
        ap.error('Esta prueba de personaje corresponde a Inazuma o Phoenix')
    video,origenes=construir(juego,args.formato,args.segundos,args.fps,args.personaje,args.animacion)
    p=Path(rutas.trabajo(juego))/'prueba_motor.png'
    video.frame(args.segundos/2).save(p)
    print('Recursos:',*origenes,sep='\n  ',flush=True)
    if args.solo_frame:
        print(p,flush=True)
    else:
        print(video.renderizar(args.nombre),flush=True)
    return 0
