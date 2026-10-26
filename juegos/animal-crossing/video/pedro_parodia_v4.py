"""Edición natural: Capitán cruza caminando, Pedro cae a llorar y la cámara final orbita.
python -I video/pedro_parodia_v4.py [--solo-frames .8,8,20.8,23.5,24.8,26,29,32,36,39,42,45]
"""
import os
import sys
import multiprocessing as mp
os.environ.setdefault('VIDEO_VERTICAL','1')
import numpy as np
from PIL import Image
HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
from motor import *
from gasto import rrect
from pesca import project
from personajes import pedro as PP
import pedro_parodia_v3 as BASE
import audio as AU
import reggaeton as RG
import sfx as SX

DURATION=46.4
CPS=22.0
INK=(.25,.12,.05)
K_START,K_END=20.8,34.0
SING_START,SING_END=23.4,31.4
FALL_START,FALL_END=24.25,25.45
SUNSET=35.4
FINAL_TEXT=41.4
G={}


class Costa(BASE.Costa):
    """Sol sobre el horizonte visible mientras la cámara rodea al personaje."""
    def sky(self,cv,t_day=.5):
        y=np.linspace(0,1,H)[:,None,None]
        cv.color[...,:3]=np.array([.27,.18,.47])*(1-y)+np.array([1,.60,.32])*y
        cv.color[...,3]=1

    def render(self,view,actors,**kwargs):
        cv=super().render(view,actors,**kwargs)
        proj=perspective(kwargs.get('fov',34),W/H,.5,200)
        direction=np.array([-view[2,0],0.,-view[2,2]])
        point=proj @ np.r_[view[:3,:3] @ direction,0.]
        horizon=(1-point[1]/point[3])*.5*H
        yy,xx=np.mgrid[:H,:W]
        sun=((xx-260)**2+(yy-horizon-3)**2<23**2)&(yy<horizon)&np.isinf(cv.depth)
        cv.color[sun,:3]=(1,.84,.46)
        return cv


def init():
    BASE.init()
    G.clear()
    G.update(BASE.G)
    G.pop('reactions',None)
    G['coast']=Costa(G['rom'])
    asset=G['P']
    build_mesh(asset.model)  # pose neutra para definir los ojos en coordenadas de cabeza
    neutral=asset.model.node_world[15].copy()
    G['eyes_local']=[np.linalg.solve(neutral,np.array([x,1.48,.76,1.])) for x in (-.23,.23)]


def active(t):
    return next((s for s in G['sched'] if s['t0']<=t<s['t_end']),None)


def center(img,text,y,scale=2,color=(1,.97,.83),alpha=1):
    f=G['font']
    assert f.measure(text,scale)<W-12,text
    f.draw(img,(W-f.measure(text,scale))//2,y,text,color,shadow=(.15,.12,.22),
           scale=scale,bold=True,alpha=alpha)


def camera(t,s):
    if t>=SUNSET:
        u=float(ease((t-SUNSET)/7.5))
        angle=np.pi*(1-u)
        radius=10.0*(1-u)+7.6*u
        target=np.array([-.15,.48,1.3])
        eye=target+np.array([radius*np.sin(angle),2.5-.5*u,radius*np.cos(angle)])
        return look_at(eye,target),34,'sunset',eye
    # Toma general continua: se ve al caminante entrar, cruzar y salir, y toda la caída.
    if K_START-.8<=t<34.2:
        eye=np.array([.1,3.6,19.8])
        return look_at(eye,(0,1.15,1.4)),34,'crossing',eye
    shot=s['shot'] if s else 'pedro'
    if t>=34.2:
        shot='wide'
    u=0 if s is None else float((t-s['t0'])/(s['t_end']-s['t0']))
    if shot=='pedro':
        eye=np.array([1.25+.08*u,1.95,7.8-.2*u])
        target=(1.25,1.38,1.)
    elif shot=='nook':
        eye=np.array([-1.25-.08*u,2.,8.4-.2*u])
        target=(-1.25,1.45,1.)
    else:
        eye=np.array([.12*np.sin(t*.12),3.4,17.5])
        target=(0,1.25,1.1)
    return look_at(eye,target),34,shot,eye


def rz(angle):
    c,s=np.cos(angle),np.sin(angle)
    m=np.eye(4)
    m[:2,:2]=((c,-s),(s,c))
    return m


def kappa_x(t):
    return -5.2+10.4*np.clip((t-K_START)/(K_END-K_START),0,1)


def actor(who,t,s):
    a=G[who]
    speaking=s is not None and s['who']==who and s['display_t0']<=t<s['t1']
    if who=='P' and t>=FALL_START:
        age=t-FALL_START
        first=a.anims['mr_naku1'].num_frames/30
        pose=pose_at(a,'mr_naku1',age,False) if age<first else pose_at(a,'mr_naku2',age-first)
        mesh=build_mesh(a.model,pose)
        fall=float(ease((t-FALL_START)/(FALL_END-FALL_START)))
        # Se tumba de lado con la animación de llorar. El suelo fija el apoyo en cada pose.
        rotation=ry(-.1*(1-fall)) @ rz(np.pi*.5*fall)
        points=np.concatenate([p.reshape(-1,3) for m,p,uv,n in mesh])
        lowest=(points @ rotation[:3,:3].T)[:,1].min()
        ground=-.18 if t>=SUNSET else 0.
        root_x=.8 if t>=SUNSET else 1.25
        world=world_matrix((root_x,ground-lowest,1.35)) @ rotation
        return a,world,pose,mesh,{'e':'e.3','m':'m.0'}
    if who=='K':
        # Camina por delante de ambos, mirando hacia su trayectoria.
        local=(t-K_START)*1.2
        pose=pose_layered(a,'walk1',local,'talk1',t) if SING_START<=t<SING_END else pose_at(a,'walk1',local)
        world=world_matrix((kappa_x(t),0.,2.8),yaw_facing(1,.10))
        tex={'e':'e.2' if (t+.7)%3.2<.12 else 'e.0',
             'm':'m.1' if SING_START<=t<SING_END and int(t*6)%2 else 'm.0'}
    elif who=='N':
        pose=pose_layered(a,'wait1',t,'talk1',t) if speaking else pose_at(a,'wait1',t)
        world=world_matrix((-1.25,0,1),.08)
        tex={'e':'e.2' if t%3.2<.12 else 'e.0'}
    else:
        pose=pose_layered(a,'wait1',t,'talk1',t) if speaking else pose_at(a,'mr_komari1',t)
        world=world_matrix((1.25,0,1),-.10)
        tex={'e':'e.0','m':'m.0'}
    return a,world,pose,build_mesh(a.model,pose),tex


def tears(img,t,world,head,view,proj,eye):
    if t<FALL_START+.3:
        return
    forward=(world @ head)[:3,2]
    for i,local in enumerate(G['eyes_local']):
        origin=(world @ head @ local)[:3]
        if np.dot(forward,eye-origin)<0:
            continue
        for j in range(2):
            phase=((t-FALL_START)*1.5+i*.32+j*.5)%1
            point=origin+np.array([.035*np.sin(i+t*5),-.34*phase,.025])
            q=project(point,view,proj)
            if q is not None and point[1]>(-.16 if t>=SUNSET else .01):
                x,y=q[:2]
                fill_rect(img,x-1,y-4,3,8,(.22,.62,.96),.9*(1-phase))
                fill_rect(img,x,y-4,1,5,(.82,.96,1),.9*(1-phase))


def frame(t):
    s=active(t)
    view,fov,shot,eye=camera(t,s)
    proj=perspective(fov,W/H,.5,200)
    sunset=t>=SUNSET
    env=G['coast'] if sunset else G['village']
    tint=(1,.80,.67) if sunset else (1,1,1)
    cv=env.render(view,[],fov=fov,tint=tint)
    actors=['P'] if sunset else ['N','P']
    if not sunset and K_START<=t<=K_END:
        actors.append('K')
    p_info=None
    for who in actors:
        a,world,pose,mesh,tex=actor(who,t,s)
        draw_model(cv,a.model,a.banks,world,view,proj,mesh=mesh,tex_override=tex,ambient=.85,tint=tint)
        if who=='P':
            PP.dibujar_cara(cv,a,mesh,world,view,proj,tint)
            p_info=(world,a.model.node_world[15].copy())
    img=cv.color[...,:3].copy()
    if p_info:
        tears(img,t,*p_info,view,proj,eye)
    rrect(img,12,24,162,23,(.18,.23,.27),4,.85)
    G['font'].draw(img,22,28,'PARODIA · FICCIÓN',(1,.97,.83),bold=True)
    if s and t>=s['display_t0']:
        bx,by=(W-G['bubble'].shape[1])//2,448
        blit(img,G['bubble'],bx,by)
        nx,ny=G['npos']; tx,ty=G['tpos']
        G['font'].draw(img,bx+nx+6,by+ny+3,BASE.NAMES[s['who']],(.1,.25,.5),bold=True)
        rem=len(s['text'])+3 if s['who']=='K' else int(max(0,t-s['display_t0'])*CPS)
        for i,line in enumerate(s['wrapped']):
            part=line[:max(0,rem)]; rem-=len(line)+1
            G['font'].draw(img,bx+tx,by+ty+i*30,part,INK,scale=2,bold=True)
    if t>=FINAL_TEXT:
        alpha=ease((t-FINAL_TEXT)/.6)
        rrect(img,12,463,336,108,(.14,.12,.22),6,.86*alpha)
        center(img,'que te vote',470,3,alpha=alpha)
        center(img,'txapote',518,3,alpha=alpha)
    # Un único fundido para el paso al atardecer; el resto son cortes normales.
    fade=min(1,t/.2,(DURATION-t)/1.3,abs(t-SUNSET)/.35)
    img*=np.clip(fade,0,1)
    return upscale((np.clip(img,0,1)*255+.5).astype(np.uint8))


def build_audio(path):
    A=AU.AudioBank(Rom())
    fx=SX.SFX(A)
    mix=AU.Mixer(DURATION)
    music=RG.pista(A,SUNSET)
    env=np.ones(len(music),np.float32)*.38
    for s in G['sched']:
        env[int(s['display_t0']*AU.SR):int(s['t1']*AU.SR)]*=.58
    env[int(SING_START*AU.SR):int(SING_END*AU.SR)]*=.70
    k=int(.15*AU.SR)
    env=np.convolve(env,np.ones(k,np.float32)/k,'same')
    music*=env[:,None]
    music[-int(.25*AU.SR):]*=np.linspace(1,0,int(.25*AU.SR))[:,None]
    mix.add(0,music)
    rng=np.random.RandomState(45)
    voices={'N':A.voice_set(18),'P':A.voice_set(19),'K':A.voice_set(17)}
    for s in G['sched']:
        who=s['who']
        if who=='K':
            syllables=[('PE',60,0),('DRO',60,.3),('SAN',64,.6),('CHEZ',64,.9),
                       ('HI',67,1.5),('JO',65,1.8),('DE',64,2.1),('PU',62,2.4),('TA',60,2.7)]
            for syll,note,dt in syllables:
                at=s['display_t0']+dt
                for d,w in AU.speech_blips(syll,voices['K'],.90*2**((note-60)/12),rng,10):
                    mix.add(at+d,w,gain=1.1,pan=float(np.clip(kappa_x(at)/5,-.65,.65)))
        else:
            for dt,w in AU.speech_blips(s['text'],voices[who],.78 if who=='N' else 1.1,rng,CPS):
                mix.add(s['display_t0']+dt,w,gain=1.,pan=-.12 if who=='N' else .12)
        mix.add(s['display_t0']-.04,fx.pop(79),gain=.10)
    # Pasos suaves ligados al ciclo real de walk1.
    step_period=G['K'].anims['walk1'].num_frames/30/1.2/2
    step=fx.nota(SX.SNARE,36,.04)[:int(.065*AU.SR)]
    for at in np.arange(K_START+.1,K_END,step_period):
        gain=.055*(1-abs(kappa_x(at))/7)
        mix.add(at,step,gain=gain,pan=float(np.clip(kappa_x(at)/5,-.65,.65)))
    mix.add(FALL_END-.1,fx.golpe(),gain=.16)
    # Sollozos de sílabas SDAT: dos impulsos por respiración, persistentes hasta el final.
    for at in np.arange(FALL_END+.15,DURATION-.6,1.35):
        for dt,w in AU.speech_blips('aa aa',voices['P'],.62,rng,12):
            mix.add(at+dt,w,gain=.16 if at<SUNSET else .23,pan=.12)
    notes=[]
    for bar,chord in enumerate([(45,57,60,64),(41,53,57,60),(38,50,53,57),(40,52,56,59)]):
        for j in range(8):
            note=chord[(0,1,2,3,2,1,2,1)[j]]
            notes.append((bar*3.1+j*.3875,.8,note,68,3,64,105))
        notes.append((bar*3.1,2.9,chord[0]-12,70,6,64,90))
    mix.add(SUNSET,A.notes(notes,13,12),gain=.65)
    mix.fade_out(DURATION-1.8,DURATION)
    raw_path=os.path.splitext(path)[0]+'_premaster.wav'
    mix.save(raw_path,DURATION)
    import subprocess
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-i',raw_path,
                    '-af','loudnorm=I=-16:TP=-1:LRA=9','-ar','44100',path],check=True)


def worker(i):
    return frame(i/FPS)


if __name__=='__main__':
    mp.freeze_support()
    sys.stdout.reconfigure(encoding='utf-8')
    init()
    out=rutas.salida('animal-crossing')
    temp=os.path.join(rutas.trabajo('animal-crossing'),'pedro_v4')
    os.makedirs(temp,exist_ok=True)
    if '--solo-frames' in sys.argv:
        for t in map(float,sys.argv[sys.argv.index('--solo-frames')+1].split(',')):
            Image.fromarray(frame(t)).save(os.path.join(temp,'p_%05.1f.png'%t))
        print('Fotogramas listos. Duración: 46,4 s')
    else:
        wav=os.path.join(rutas.trabajo('animal-crossing'),'_audio_pedro_v4.wav')
        build_audio(wav)
        with mp.Pool(min(8,max(1,mp.cpu_count()-1)),initializer=init) as pool:
            write_video(pool.imap(worker,range(round(DURATION*FPS)),chunksize=4),
                        os.path.join(out,'pedro_parodia_v4.mp4'),audio=wav)
        print('Vídeo terminado: salida/pedro_parodia_v4.mp4 (46,4 s)')
