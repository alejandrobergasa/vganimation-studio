"""Sátira ficticia solicitada. python -I video/pedro_parodia.py [--solo-frames 2,12,30,44,49]."""
import os
import sys
import multiprocessing as mp
os.environ.setdefault('VIDEO_VERTICAL', '1')
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from motor import *
from escena import Village
from gasto import wrap, panel, rrect
import audio as AU
import reggaeton as RG

DURATION = 53.0
CPS = 22.0
INK = (0.25, 0.12, 0.05)
# Frases exactas del encargo, repartidas para lectura móvil.
LINES = [
    (2, 5, 'P', 'BRO AYUDA POR FAVOR', 'pedro'),
    (5, 8, 'P', 'VOY JODIDO CON LAS', 'wide'),
    (8, 11, 'P', 'ELECCIONES ESTAS', 'pedro'),
    (11, 14, 'N', 'estás es un lío de', 'nook'),
    (14, 17, 'N', 'la ostia primo,', 'wide'),
    (17, 20.5, 'N', 'lo de Ábalos para empezar,', 'nook'),
    (20.5, 24, 'N', 'lo de tu hermano para seguir', 'pedro'),
    (24, 28, 'N', 'y lo de tu mujer para culminar', 'nook'),
    (28, 32, 'K', 'PEDRO SANCHEZ, HIJO DE PUTA,', 'kappa'),
    (32, 36, 'K', 'PEDRO SANCHEZ, HIJO DE PUTA', 'kappa_wide'),
    (36, 40, 'N', 'vas a ir a la cárcel mano', 'nook'),
]
NAMES = {'P': 'Pedro Sánchez', 'N': 'Tom Nook', 'K': 'Capitán'}
G = {}


class Costa(Village):
    """Orilla al atardecer: arena y cáusticas del banco de suelo de la ROM."""
    def __init__(self, rom):
        self.rom = rom
        self.static = []
        b = TexBank(rom.get('bg/ct0/grd_set0a.nsbtx'))
        self.sand = b.decode('grd_ssa', 'grd_pl')
        self.water = b.decode('grd_riv.0', 'grd_riv_pl')

    def sky(self, cv, t_day=.5):
        y = np.linspace(0, 1, H)[:, None, None]
        cv.color[..., :3] = np.array([.27,.18,.47])*(1-y) + np.array([1,.60,.32])*y
        cv.color[..., 3] = 1
        yy, xx = np.mgrid[:H,:W]
        sun = (xx-252)**2 + (yy-211)**2 < 31**2
        cv.color[sun,:3] = (1,.83,.44)

    def draw_ground(self, cv, view, proj):
        from pesca import Rio
        vp = proj @ view
        # Rio._quads tilea en X/Z; aquí la orilla queda detrás de Pedro (z < -1).
        Rio._quads(self, cv, vp, -40,40,-4,28,-.18,-.18,self.sand,4,.83)
        Rio._quads(self, cv, vp, -40,40,-70,-4,-.26,-.26,self.water,5,.80)


def init():
    rom = Rom()
    G['rom'] = rom
    G['village'] = Village(rom)
    G['coast'] = Costa(rom)
    clips = {}
    for p in rom.list('anm/'):
        if p.endswith('.nsbca'):
            clips.update(load_clips(rom,[p]))
    G['N'] = Asset(rom,'npc_sp/model/rcn.nsbmd',['npc_sp/model/rcn_tex.nsbtx'],clips)
    G['K'] = Asset(rom,'npc_sp/model/wip.nsbmd',['npc_sp/model/wip_tex.nsbtx'],clips)
    G['P'] = Asset(rom,'PBody/boy.nsbmd',['cloth/0/cloth012.nsbtx'],clips)
    G['hair'] = Asset(rom,'PHead/0/0.nsbmd',['PPal/0/0.nsbtx','PFcTx/0/0.nsbtx'])
    # El cuerpo humano de la ROM no lleva cabeza. Se acopla el decal al nodo head.
    G['P'].model.materials[0].diffuse = (.92,.65,.46)
    G['P'].model.materials[1].diffuse = (.16,.18,.24)
    face = Image.open(os.path.join(rutas.personalizados('animal-crossing'),'pedro','cara.png')).convert('RGBA')
    G['face'] = np.array(face.resize((128,128),Image.Resampling.NEAREST))
    G['font'] = Font(rom)
    G['bubble'],G['tpos'],G['npos'] = make_bubble(rom,13,extra_rows=5)
    G['sched'] = []
    for t0,tend,who,text,shot in LINES:
        lines = wrap(G['font'],text, G['bubble'].shape[1]-G['tpos'][0]-25,2)
        assert len(lines)<=3,(text,lines)
        G['sched'].append(dict(t0=t0,t_end=tend,who=who,text=text,shot=shot,wrapped=lines,t1=t0+len(text)/CPS))


def active(t):
    return next((s for s in G['sched'] if s['t0']<=t<s['t_end']),None)


def center(img,text,y,scale=2,color=(1,.97,.83),alpha=1):
    f=G['font']
    assert f.measure(text,scale)<W-12, text
    f.draw(img,(W-f.measure(text,scale))//2,y,text,color,shadow=(.15,.12,.22),scale=scale,bold=True,alpha=alpha)


def camera(t,s):
    shot=s['shot'] if s else 'wide'
    u=0 if s is None else (t-s['t0'])/(s['t_end']-s['t0'])
    if t>=40:
        u=ease((t-40)/10)
        return look_at((3.3+u*.8,2.1,9.8+u),(0,.7,-1)),34,'sunset'
    if shot=='pedro':
        return look_at((1.25+.15*u,1.9,7.8-.4*u),(1.25,1.6,1)),34,shot
    if shot=='nook':
        return look_at((-1.25-.15*u,2.0,7.8-.4*u),(-1.25,1.45,1)),34,shot
    if shot=='kappa':
        return look_at((.2,1.9,7.3-.4*u),(0,1.45,1.3)),34,shot
    return look_at((.2*np.sin(t*.2),3.1,17.0-.5*u),(0,1.6,.8)),34,shot


def actor(who,t,s,shot):
    a=G[who]
    speaking=s is not None and s['who']==who and t<s['t1']
    if who=='P':
        pos=np.array([1.25,0.,1.])
        yaw=-.07
        clip='mr_aseru1' if t<11 else 'mr_komari1'
        if t>=40:
            clip='ft_sitdown_wait1'
            pos=np.array([0.,-1.14,1.4])
            yaw=np.pi
    elif who=='N':
        pos=np.array([-1.25,0.,1.])
        yaw=.08
        clip='wait1'
    else:
        pos=np.array([0., .08*abs(np.sin((t-28)*np.pi*2)),1.3])
        yaw=.12*np.sin(t*3)
        clip='mr_happy1'
    if speaking and who!='K':
        pose=pose_layered(a,'wait1',t,'talk1',t)
    else:
        pose=pose_at(a,clip,t)
    tex={'e':'e.2' if (t+(.9 if who=='K' else 0))%3.2<.13 else 'e.0'}
    if who=='K':
        tex['m']='m.1' if int(t*5)%2 else 'm.0'
    return a,world_matrix(pos,yaw),pose,tex


def draw_pedro_face(cv,asset,pose,world,view,proj,t):
    # node_world se recalcula para cada fotograma, nunca se integra estado en t.
    asset.model.pose(pose)
    anchor=asset.model.node_world[15][:3,3]
    x,y,z=anchor
    # El decal conserva la perspectiva y la profundidad; no es un rótulo sobre la pantalla.
    corners=[(x-.66,y-.05,z+.26),(x+.66,y-.05,z+.26),(x+.66,y+1.53,z+.26),(x-.66,y+1.53,z+.26)]
    draw_textured_quad(cv,G['face'],corners,world,view,proj,tint=(1,.95,.88) if t>=40 else (1,1,1))


def frame(t):
    s=active(t)
    view,fov,shot=camera(t,s)
    proj=perspective(fov,W/H,.5,200)
    sunset=t>=40
    env=G['coast'] if sunset else G['village']
    cv=env.render(view,[],fov=fov,tint=(1,.8,.65) if sunset else (1,1,1))
    actors=['P'] if sunset else (['N','P','K'] if 28<=t<36 else ['N','P'])
    for who in actors:
        a,world,pose,tex=actor(who,t,s,shot)
        draw_model(cv,a.model,a.banks,world,view,proj,override=pose,tex_override=tex,ambient=.85,
                   tint=(1,.80,.67) if sunset else (1,1,1))
        if who=='P':
            if sunset:
                a.model.pose(pose)
                draw_model(cv,G['hair'].model,G['hair'].banks,world @ a.model.node_world[15],view,proj,
                           tint=(1,.8,.67),ambient=.85)
            else:
                draw_pedro_face(cv,a,pose,world,view,proj,t)
    img=cv.color[...,:3].copy()
    rrect(img,62,24,236,28,(.18,.23,.27),5,.9)
    center(img,'PARODIA · FICCIÓN',24,2)
    if t<2:
        panel(img,22,76,316,105)
        center(img,'PEDRO EN',83,3,(.22,.4,.32))
        center(img,'ANIMAL CROSSING',128,2,(.24,.38,.30))
    if 28<=t<36:
        # Notas pixeladas que ascienden al ritmo de la entrada musical.
        for k in range(5):
            phase=(t*.7+k*.19)%1
            G['font'].draw(img,25+k*67,270-phase*130,'♪',(.95,.78,.2),scale=2,shadow=(.2,.3,.2))
        center(img,'CANTA CAPITÁN',86,2)
    if s:
        bx,by=(W-G['bubble'].shape[1])//2,448
        blit(img,G['bubble'],bx,by)
        nx,ny=G['npos']; tx,ty=G['tpos']
        G['font'].draw(img,bx+nx+6,by+ny+3,NAMES[s['who']],(.1,.25,.5),bold=True)
        # Canto: letra completa y barra de ritmo; diálogo: texto tecleado.
        rem=len(s['text'])+3 if s['who']=='K' else int(max(0,t-s['t0'])*CPS)
        for i,line in enumerate(s['wrapped']):
            part=line[:max(0,rem)]; rem-=len(line)+1
            G['font'].draw(img,bx+tx,by+ty+i*30,part,INK,scale=2,bold=True)
        if s['who']=='K':
            fill_rect(img,30,586,300*((t-s['t0'])/4),4,(1,.80,.20))
    if t>=46:
        a=ease((t-46)/.6)
        rrect(img,12,463,336,108,(.14,.12,.22),6,.88*a)
        center(img,'que te vote',470,3,alpha=a)
        center(img,'txapote',518,3,alpha=a)
    fade=min(1,t/.35,(DURATION-t)/1.3)
    img*=np.clip(fade,0,1)
    return upscale((np.clip(img,0,1)*255+.5).astype(np.uint8))


def build_audio(path):
    A=AU.AudioBank(Rom())
    mix=AU.Mixer(DURATION)
    music=RG.pista(A,40)
    env=np.ones(len(music),np.float32)*.45
    for s in G['sched']:
        env[int(s['t0']*AU.SR):int(s['t1']*AU.SR)]*=.62
    k=int(.15*AU.SR)
    env=np.convolve(env,np.ones(k,dtype=np.float32)/k,'same')
    music*=env[:,None]
    # Corte de comedia a la sección triste, con cola suave de 0,25 s.
    music[-int(.25*AU.SR):]*=np.linspace(1,0,int(.25*AU.SR))[:,None]
    mix.add(0,music)
    rng=np.random.RandomState(45)
    voices={'N':A.voice_set(18),'P':A.voice_set(19),'K':A.voice_set(17)}
    for s in G['sched']:
        who=s['who']
        if who=='K':
            # Sílaba, nota MIDI, desplazamiento. Melodía y texto repetidos dos veces.
            syllables=[('PE',60,0),('DRO',60,.3),('SAN',64,.6),('CHEZ',64,.9),
                       ('HI',67,1.5),('JO',65,1.8),('DE',64,2.1),('PU',62,2.4),('TA',60,2.7)]
            for syll,note,dt in syllables:
                for d,w in AU.speech_blips(syll,voices['K'],.90*2**((note-60)/12),rng,10):
                    mix.add(s['t0']+dt+d,w,gain=1.2,pan=.05)
        else:
            for dt,w in AU.speech_blips(s['text'],voices[who],.78 if who=='N' else 1.1,rng,CPS):
                mix.add(s['t0']+dt,w,gain=1.0,pan=-.12 if who=='N' else .12)
    # Coda original en La menor, punteo suave del banco 12 ya caracterizado.
    notes=[]
    for bar,chord in enumerate([(45,57,60,64),(41,53,57,60),(38,50,53,57),(40,52,56,59)]):
        for j in range(8):
            n=chord[(0,1,2,3,2,1,2,1)[j]]
            notes.append((bar*3.1+j*.3875,.8,n,68,3,64,105))
        notes.append((bar*3.1,2.9,chord[0]-12,70,6,64,90))
    sad=A.notes(notes,13,12)
    mix.add(40,sad,gain=.65)
    mix.fade_out(DURATION-1.8,DURATION)
    mix.save(path,DURATION)


def worker(i):
    return frame(i/FPS)


if __name__=='__main__':
    mp.freeze_support()
    sys.stdout.reconfigure(encoding='utf-8')
    init()
    out=rutas.salida('animal-crossing')
    temp=os.path.join(rutas.trabajo('animal-crossing'),'pedro')
    os.makedirs(temp,exist_ok=True)
    if '--solo-frames' in sys.argv:
        for t in map(float,sys.argv[sys.argv.index('--solo-frames')+1].split(',')):
            Image.fromarray(frame(t)).save(os.path.join(temp,'p_%05.1f.png'%t))
        print('Fotogramas listos. Duración: 53 s')
    else:
        wav=os.path.join(rutas.trabajo('animal-crossing'),'_audio_pedro.wav')
        build_audio(wav)
        with mp.Pool(min(8,max(1,mp.cpu_count()-1)),initializer=init) as pool:
            write_video(pool.imap(worker,range(int(DURATION*FPS)),chunksize=4),os.path.join(out,'pedro_parodia.mp4'),audio=wav)
        print('Vídeo terminado: salida/pedro_parodia.mp4 (53 s)')
