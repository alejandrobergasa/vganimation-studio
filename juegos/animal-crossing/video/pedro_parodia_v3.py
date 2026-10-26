"""Parodia v3: arranque inmediato, ritmo de montaje, reacciones y efectos de cómic.
python -I video/pedro_parodia_v3.py [--solo-frames 1.8,5,10,14,18,22,25,29,33,39,44].
"""
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
from pesca import pop_text, speed_lines, shift_xy, confetti, sunburst, back
from personajes import pedro as PP
import audio as AU
import reggaeton as RG
import sfx as SX

DURATION = 46.4
CPS = 22.0
INK = (0.25, 0.12, 0.05)
# Cada página contiene una frase o una cláusula con sentido completo.
LINES = [
    (2, 5.5, 'P', 'BRO, AYUDA POR FAVOR.', 'pedro'),
    (5.5, 11, 'P', 'VOY JODIDO CON LAS ELECCIONES ESTAS.', 'wide'),
    (11, 17, 'N', 'Estás en un lío de la ostia, primo.', 'nook'),
    (17, 20.5, 'N', 'Lo de Ábalos para empezar,', 'nook'),
    (20.5, 24, 'N', 'lo de tu hermano para seguir,', 'pedro'),
    (24, 28, 'N', 'y lo de tu mujer para culminar.', 'nook'),
    (28, 32, 'K', 'PEDRO SANCHEZ, HIJO DE PUTA,', 'kappa'),
    (32, 36, 'K', 'PEDRO SANCHEZ, HIJO DE PUTA', 'kappa_wide'),
    (36, 40, 'N', 'Vas a ir a la cárcel, mano.', 'nook'),
]
CUTS=[(2,'zoom'),(5.5,'whip'),(7.8,'zoom'),(11,'bars'),(14.2,'zoom'),
      (17,'whip'),(20.5,'bars'),(24,'whip'),(28,'iris'),(32,'whip'),(36,'zoom'),(40,'fade')]
IMPACTS=[2.28,11.28,17.28,20.78,24.28,28.28,36.28]
TAGS=[(2.28,'¡BRO!',1.3),(6.9,'ELECCIONES',1.5),(11.5,'VAYA LÍO',1.6),
      (17.7,'ÁBALOS',1.5),(21.3,'TU HERMANO',1.5),(24.9,'TU MUJER',1.6),
      (28.3,'¡ENTRA CAPITÁN!',1.6),(30.05,'HIJO DE PUTA',1.5),
      (32.35,'PEDRO SÁNCHEZ',1.1),(33.8,'HIJO DE PUTA',1.5),(37.25,'LA CÁRCEL',1.8)]
NAMES = {'P': 'Pedro Sánchez', 'N': 'Tom Nook', 'K': 'Capitán'}
G = {}


def T(old):
    """Reedición temporal: elimina esperas conservando voz y frases completas."""
    return float(np.interp(old,[0,2,5.5,11,17,20.5,24,28,32,36,40,46,53],
                           [0,.25,3.3,7.7,12.4,16,19.6,23.4,27.4,31.4,35.4,41.4,46.4]))


LINES=[(T(a),T(b),who,text,shot) for a,b,who,text,shot in LINES]
CUTS=[(T(a),kind) for a,kind in CUTS]
IMPACTS=[T(a) for a in IMPACTS]
TAGS=[(T(a),text,duration) for a,text,duration in TAGS]
MAJORCUTS=CUTS.copy()
# Microcortes de reacción; el texto permanece en la misma página durante cada uno.
MICROCUTS=[(1.95,'wide'),(5.8,'pedro'),(6.9,'nook'),(9.9,'pedro'),(11.2,'wide'),
           (14.25,'pedro'),(17.8,'wide'),(21.3,'pedro'),(24.9,'kappa_wide'),
           (26.25,'kappa'),(28.9,'kappa'),(30.1,'kappa_wide'),(33.25,'pedro'),(34.1,'nook')]
MICRO_TRANSITIONS=[(a,'zoom' if i%2 else 'whip') for i,(a,name) in enumerate(MICROCUTS)]
CUTS+=MICRO_TRANSITIONS
CUTS.sort()


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
    G['P'] = PP.cargar(rom,clips)
    G['font'] = Font(rom)
    G['bubble'],G['tpos'],G['npos'] = make_bubble(rom,13,extra_rows=5)
    G['sched'] = []
    for t0,tend,who,text,shot in LINES:
        lines = wrap(G['font'],text, G['bubble'].shape[1]-G['tpos'][0]-25,2)
        assert len(lines)<=3,(text,lines)
        speech_start=t0+.26
        speech_end=speech_start+len(text)/CPS
        assert tend-speech_end>=.9,(text,'falta pausa de lectura')
        G['sched'].append(dict(t0=t0,display_t0=speech_start,t_end=tend,who=who,text=text,
                               shot=shot,wrapped=lines,t1=speech_end))
    G['reactions']=[]
    for tt in (.12,.48):
        cv=Canvas(88,100,bg=(255,246,218,255))
        view=look_at((0,1.5,3.7),(0,1.38,0))
        proj=perspective(38,88/100,.4,50)
        asset=G['P']
        mesh=build_mesh(asset.model,pose_at(asset,'mr_aseru1',tt,False))
        world=world_matrix((0,0,0))
        draw_model(cv,asset.model,asset.banks,world,view,proj,mesh=mesh,ambient=.9)
        PP.dibujar_cara(cv,asset,mesh,world,view,proj)
        G['reactions'].append(cv.to_image())


def active(t):
    return next((s for s in G['sched'] if s['t0']<=t<s['t_end']),None)


def center(img,text,y,scale=2,color=(1,.97,.83),alpha=1):
    f=G['font']
    assert f.measure(text,scale)<W-12, text
    f.draw(img,(W-f.measure(text,scale))//2,y,text,color,shadow=(.15,.12,.22),scale=scale,bold=True,alpha=alpha)


def camera(t,s):
    shot=s['shot'] if s else 'pedro'
    u=0 if s is None else (t-s['t0'])/(s['t_end']-s['t0'])
    if s:
        for tc,name in MICROCUTS:
            if s['t0']<tc<=t:
                shot=name
    punch=max((max(0,1-(t-t0)/.45) if t>=t0 else 0) for t0 in IMPACTS)
    fov=34-2.7*punch
    if t>=T(40):
        u=ease((t-T(40))/10)
        return look_at((3.3+u*.8,2.1,9.8+u),(0,.7,-1)),34,'sunset'
    if shot=='pedro':
        return look_at((1.25+.15*u,1.9,7.2-.4*u),(1.25,1.35,1)),fov,shot
    if shot=='nook':
        return look_at((-1.25-.15*u,2.0,8.1-.4*u),(-1.25,1.45,1)),fov,shot
    if shot=='kappa':
        return look_at((.2,1.9,7.8-.4*u),(0,1.45,1.3)),fov,shot
    return look_at((.2*np.sin(t*.2),3.1,16.0-.5*u),(0,1.6,.8)),fov,shot


def actor(who,t,s,shot):
    a=G[who]
    speaking=s is not None and s['who']==who and s['display_t0']<=t<s['t1']
    if who=='P':
        pos=np.array([1.25,0.,1.])
        yaw=-.10+.06*np.sin(t*1.2)
        clip='mr_aseru1' if t<T(11) else 'mr_komari1'
        if t>=T(40):
            clip='ft_sitdown_wait1'
            pos=np.array([0.,-1.22,1.4])
            yaw=np.pi
    elif who=='N':
        pos=np.array([-1.25,0.,1.])
        yaw=.08
        clip='wait1'
    else:
        enter=ease((t-T(28.05))/.48)
        pos=np.array([0.,.09*abs(np.sin((t-T(28))*np.pi*2)),1.3])
        pos[0]=4*(1-enter)
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


def frame(t):
    s=active(t)
    view,fov,shot=camera(t,s)
    proj=perspective(fov,W/H,.5,200)
    sunset=t>=T(40)
    env=G['coast'] if sunset else G['village']
    cv=env.render(view,[],fov=fov,tint=(1,.8,.65) if sunset else (1,1,1))
    actors=['P'] if sunset else (['N','P','K'] if T(28)<=t<T(36) else ['N','P'])
    for who in actors:
        a,world,pose,tex=actor(who,t,s,shot)
        mesh=build_mesh(a.model,pose)
        draw_model(cv,a.model,a.banks,world,view,proj,mesh=mesh,tex_override=tex,ambient=.85,
                   tint=(1,.80,.67) if sunset else (1,1,1))
        if who=='P':
            PP.dibujar_cara(cv,a,mesh,world,view,proj,(1,.80,.67) if sunset else (1,1,1))
    img=cv.color[...,:3].copy()
    impact=max((max(0,1-(t-t0)/.38) if t>=t0 else 0) for t0 in IMPACTS)
    if impact>0:
        img=speed_lines(img,t,.45*impact,cy=H*.43)
        img=shift_xy(img,int(4*impact*np.sin(t*75)),int(3*impact*np.cos(t*61)))
        img=chromatic_shift(img,int(4*impact))
    if T(28)<=t<T(36):
        img=sunburst(img,180,260,t,.55)
        confetti(img,t,T(28.18))
        confetti(img,t,T(32.18))
        # Cinta de color que pulsa con el canto, siempre fuera del bocadillo.
        pulse=(.5+.5*np.sin((t-T(28))*2*np.pi/ .6))**4
        fill_rect(img,0,62,6,370,(.96,.27,.38),.8*pulse)
        fill_rect(img,W-6,62,6,370,(.30,.75,.94),.8*pulse)
    if T(36)<=t<T(36)+.75:
        gray=img.mean(axis=2,keepdims=True)
        img=np.clip(gray*1.24-.10,0,1)*.85+img*.15
    if T(28)-.15<=t<T(28):
        for row in range(6):
            y=80+row*57
            dx=int(10*np.sin(row*2.7+t*80))
            img[y:y+9]=np.roll(img[y:y+9],dx,axis=1)
        img=chromatic_shift(img,5)
    img=screen_transition(img,t,MICRO_TRANSITIONS,half_duration=.12)
    rrect(img,62,24,236,28,(.18,.23,.27),5,.9)
    center(img,'PARODIA · FICCIÓN',24,2)
    for t0,label,dur in TAGS:
        pop_text(img,G['font'],label,94,t-t0,dur)
    if T(17)<=t<T(28):
        number=1 if t<T(20.5) else (2 if t<T(24) else 3)
        # Contador de la enumeración y ventana de reacción real del mismo vecino.
        rrect(img,16,166,58,53,(.17,.22,.3),5,.94)
        G['font'].draw(img,23,171,str(number)+'/3',(1,.85,.30),scale=2,bold=True)
        if shot=='nook' or shot=='wide':
            phase=t-(T(17) if number==1 else T(20.5) if number==2 else T(24))
            y=172+int(10*(1-back(min(phase/.3,1))))
            rrect(img,260,y-3,94,124,(1,.94,.76),4)
            blit(img,G['reactions'][int(t*3)%2],263,y)
            G['font'].draw(img,273,y+103,'¡AYUDA!',(.5,.15,.13),bold=True)
    if T(28)<=t<T(36):
        # Notas pixeladas que ascienden al ritmo de la entrada musical.
        for k in range(5):
            phase=(t*.7+k*.19)%1
            x,y=25+k*67,270-phase*130
            fill_rect(img,x,y,3,18,(1,.83,.2))
            fill_rect(img,x,y,10,3,(1,.83,.2))
            fill_rect(img,x-4,y+15,7,5,(1,.83,.2))
    if s and t>=s['display_t0']-.08:
        age=max(0,t-s['display_t0']+.08)
        bx=(W-G['bubble'].shape[1])//2
        by=448+int(18*(1-back(age/.24)))
        blit(img,G['bubble'],bx,by)
        nx,ny=G['npos']; tx,ty=G['tpos']
        G['font'].draw(img,bx+nx+6,by+ny+3,NAMES[s['who']],(.1,.25,.5),bold=True)
        # Canto: letra completa y barra de ritmo; diálogo: texto tecleado.
        rem=len(s['text'])+3 if s['who']=='K' else int(max(0,t-s['display_t0'])*CPS)
        for i,line in enumerate(s['wrapped']):
            part=line[:max(0,rem)]; rem-=len(line)+1
            G['font'].draw(img,bx+tx,by+ty+i*30,part,INK,scale=2,bold=True)
        if s['who']=='K':
            fill_rect(img,30,580,300*((t-s['t0'])/4),3,(1,.80,.20))
    if t>=T(46):
        a=ease((t-T(46))/.6)
        rrect(img,12,463,336,108,(.14,.12,.22),6,.88*a)
        center(img,'que te vote',470,3,alpha=a)
        center(img,'txapote',518,3,alpha=a)
    img=screen_transition(img,t,MAJORCUTS)
    if t<.45:
        yy,xx=np.mgrid[:H,:W]
        radius=np.hypot(H,W)*ease(t/.45)
        img[np.hypot(xx-W/2,yy-H*.43)>radius]=(.10,.18,.23)
    fade=min(1,t/.12,(DURATION-t)/1.3)
    img*=np.clip(fade,0,1)
    return upscale((np.clip(img,0,1)*255+.5).astype(np.uint8))


def build_audio(path):
    A=AU.AudioBank(Rom())
    fx=SX.SFX(A)
    mix=AU.Mixer(DURATION)
    music=RG.pista(A,T(40))
    env=np.ones(len(music),np.float32)*.45
    for s in G['sched']:
        env[int(s['display_t0']*AU.SR):int(s['t1']*AU.SR)]*=.55
    env[int(T(28)*AU.SR):int(T(36)*AU.SR)]*=.70
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
                    mix.add(s['display_t0']+dt+d,w,gain=1.1,pan=.05)
        else:
            for dt,w in AU.speech_blips(s['text'],voices[who],.78 if who=='N' else 1.1,rng,CPS):
                mix.add(s['display_t0']+dt,w,gain=1.0,pan=-.12 if who=='N' else .12)
    # Barridos y pops sincronizados; las voces entran después de cada transición.
    mix.add(.03,fx.whoosh(.42),gain=.32)
    mix.add(.42,fx.pop(),gain=.25)
    for i,(tc,kind) in enumerate(CUTS):
        gain=.12 if (tc,kind) in MICRO_TRANSITIONS else (.18 if kind=='fade' else .27)
        mix.add(tc-.20,fx.whoosh(.40,up=i%2==0),gain=gain,pan=(-.3 if i%2 else .3))
    for s in G['sched']:
        mix.add(s['display_t0']-.06,fx.pop(79 if s['who']=='N' else 84),gain=.22)
    mix.add(T(2.25),fx.alerta(),gain=.29)
    for tc in (11.3,17.7,21.3,24.9,37.25):
        mix.add(T(tc),fx.golpe(),gain=.30)
    mix.add(T(27.3),fx.trino(.65),gain=.22)
    mix.add(T(28)-.14,fx.tick(),gain=.2)
    mix.add(T(28)-.06,fx.tick(),gain=.15)
    mix.add(T(28.22),fx.fanfarria(),gain=.26)
    for tc in (29.9,31.4,33.9,35.4):
        mix.add(T(tc),fx.tick(),gain=.21,pan=.25)
    # Frenazo tonal antes de la réplica de Nook, hecho con el punteo del SDAT.
    scratch=fx._glide(fx.nota(SX.PUNTEO,72,.4)[:int(.38*AU.SR)],1.9,.20)
    mix.add(T(35.62),scratch,gain=.25)
    mix.add(T(38.6),fx.sting_rey(),gain=.24)
    mix.add(T(46.2),fx.ding(72),gain=.17)
    # Coda original en La menor, punteo suave del banco 12 ya caracterizado.
    notes=[]
    for bar,chord in enumerate([(45,57,60,64),(41,53,57,60),(38,50,53,57),(40,52,56,59)]):
        for j in range(8):
            n=chord[(0,1,2,3,2,1,2,1)[j]]
            notes.append((bar*3.1+j*.3875,.8,n,68,3,64,105))
        notes.append((bar*3.1,2.9,chord[0]-12,70,6,64,90))
    sad=A.notes(notes,13,12)
    mix.add(T(40),sad,gain=.65)
    mix.fade_out(DURATION-1.8,DURATION)
    raw_path=os.path.splitext(path)[0]+'_premaster.wav'
    mix.save(raw_path,DURATION)
    # Volumen para móvil sin picos excesivos; remuestreo explícito tras loudnorm.
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
    temp=os.path.join(rutas.trabajo('animal-crossing'),'pedro_v3')
    os.makedirs(temp,exist_ok=True)
    if '--solo-frames' in sys.argv:
        for t in map(float,sys.argv[sys.argv.index('--solo-frames')+1].split(',')):
            Image.fromarray(frame(t)).save(os.path.join(temp,'p_%05.1f.png'%t))
        print('Fotogramas listos. Duración: 46,4 s')
    else:
        wav=os.path.join(rutas.trabajo('animal-crossing'),'_audio_pedro_v3.wav')
        build_audio(wav)
        with mp.Pool(min(8,max(1,mp.cpu_count()-1)),initializer=init) as pool:
            write_video(pool.imap(worker,range(int(DURATION*FPS)),chunksize=4),os.path.join(out,'pedro_parodia_v3.mp4'),audio=wav)
        print('Vídeo terminado: salida/pedro_parodia_v3.mp4 (46,4 s)')
