"""Revisión 3D del casino: una escena, escalas constantes y montaje de 40 segundos."""
from pathlib import Path
from functools import lru_cache
import math
import sys
import json
import time
import subprocess
import shutil

import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'tools'/'nsmb'))
import chars
import nitro3d as N
from rom import rutas
import casino_assets
import casino as anterior
import casino_audio
import casino_render3d as R
import casino_motion

W,H,FPS,TOTAL=216,384,30,40
CACHE=Path(rutas.cache('nsmb'))/'casino_3d'
FINAL=Path(rutas.salida('nsmb'))/'mario_casino_vertical.mp4'
TABLE=np.array([24.,6.94,-34.])
HITS=[(26.1,(11.,-9.)),(28.3,(29.,1.)),(30.4,(39.,-17.))]
STAND={'mario':(7.,0.,-22.),'luigi':(-2.,0.,-18.),
       'peach':(27.,0.,-52.),'bowser':(44.,0.,-37.)}
HEIGHT={'mario':13.,'luigi':13.5,'peach':14.,'bowser':19.,'toad':8.6,'koopa':10.5}


def ease(x):
    x=max(0,min(1,x));return x*x*(3-2*x)
def mix(a,b,q): return np.array(a)*(1-q)+np.array(b)*q
def yawto(a,b): return math.degrees(math.atan2(b[0]-a[0],b[2]-a[2]))
def angle_mix(a,b,q): return a+((b-a+180)%360-180)*ease(q)


class Film:
    def __init__(self,blood=True):
        CACHE.mkdir(parents=True,exist_ok=True)
        self.r=R.Renderer()
        native=casino_assets.extraer_casino.load()
        model=native.models[0]
        self.room=self.r.from_items([(model.triangles(),model,None,0)],N.TexLookup(native))
        # Continuar las superficies originales fuera del encuadre DS evita ver el borde del decorado.
        # Se conserva la misma proyección UV, textura y escala del suelo extraído.
        floor_id=next(i for i,m in enumerate(model.materials) if m.name=='mat_floor')
        table_id=next(i for i,m in enumerate(model.materials) if m.name=='mat_wall')
        floor_mat=self.r.lookup[id(model),floor_id]
        wall_mat=self.r.lookup[id(model),table_id]
        selected=self.room.mats==floor_mat
        floor_xyz=self.room.xyz[selected];floor_uv=self.room.uv[selected]
        areas=np.linalg.norm(np.cross(floor_xyz[:,1]-floor_xyz[:,0],floor_xyz[:,2]-floor_xyz[:,0]),axis=1)
        largest=int(np.argmax(areas));p=floor_xyz[largest];uv=floor_uv[largest]
        mapping=np.linalg.solve(np.column_stack((p[:,0],p[:,2],np.ones(3))),uv)
        tris=np.array([[(-180,-.035,-180),(180,-.035,-180),(180,-.035,130)],
                       [(-180,-.035,-180),(180,-.035,130),(-180,-.035,130)]],np.float32)
        tris=tris[:,[0,2,1]]
        uvs=np.column_stack((tris[:,:,0].ravel(),tris[:,:,2].ravel(),np.ones(6)))@mapping
        self.floor=R.mesh_triangles(tris,floor_mat,uvs.reshape(2,3,2))
        self.floor.normal[:]=(0,1,0)
        self.room.normal[selected]=(0,1,0)
        walls=[((-115,0,-145),(115,0,-145),(115,100,-145),(-115,100,-145)),
               ((85,0,-145),(85,0,120),(85,100,120),(85,100,-145)),
               ((-100,0,120),(-100,0,-145),(-100,100,-145),(-100,100,120))]
        walltris=[];walluv=[]
        for a,b,c,d in walls:
            walltris.extend([[a,b,c],[a,c,d]])
            width=np.linalg.norm(np.array(b)-a)*2
            walluv.extend([[(0,0),(width,0),(width,200)],[(0,0),(width,200),(0,200)]])
        self.walls=R.mesh_triangles(walltris,wall_mat,np.array(walluv,np.float32))
        self.actors={name:casino_assets.actor(name) for name in HEIGHT}
        self.scales={};self.local_cache={}
        for name,a in self.actors.items():
            pose=casino_assets.POSES[name].get('wait',next(iter(casino_assets.POSES[name].values())))
            items=a._items(pose,0,0)
            raw=self.r.from_items(items,a.tex)
            self.scales[name]=HEIGHT[name]/np.ptp(raw.xyz[:,:,1])
            # Registrar también las texturas de todas las partes antes de cerrar el atlas.
        self.motion=casino_motion.Motion(self.actors,self.r,HITS)
        self.approaches=[]
        begin=np.array([12.,0.,-22.])
        for _,(x,z) in HITS:
            target=np.array([x,0.,z]);direction=target-begin
            direction/=np.linalg.norm(direction)
            end=target-direction*2.6
            self.approaches.append((begin.copy(),end.copy(),yawto(begin,target)))
            begin=end
        texdir=Path(rutas.extraidos('nsmb'))/'casino'
        dummy=anterior.Film.__new__(anterior.Film)
        dummy.a=type('Texturas',(),{'tex':{p.stem:Image.open(p).convert('RGBA') for p in texdir.glob('*.png')}})()
        wheel=anterior.Film.wheel_texture(dummy)
        wi=self.r.material(wheel)
        self.wheel=R.disc(wi,8.2,0,64)
        self.wheel.uv*=240
        self.wood=self.r.solid((125,55,21))
        self.gold=self.r.solid((255,207,72))
        self.white=self.r.solid((255,255,232))
        self.red=self.r.solid((191,12,27))
        self.darkred=self.r.solid((128,5,17))
        self.shadowmat=self.r.solid((87,36,17))
        self.ball=R.sphere(self.white,.58)
        self.coin=R.sphere(self.gold,.32)
        self.rim=R.disc(self.wood,8.6,0,48)
        self.hub=R.sphere(self.gold,.75)
        self.shadow=R.disc(self.shadowmat,1,.025,20)
        bet=Image.new('RGBA',(64,32),(181,18,32,255))
        d=ImageDraw.Draw(bet);d.rectangle((1,1,62,30),outline=(255,207,72),width=2)
        lettering=anterior.lettering('ROJO',anterior.GOLD)
        bet.alpha_composite(lettering,((64-lettering.width)//2,6))
        mat=self.r.material(bet)
        self.bet=R.mesh_triangles([[(-3,0,-1.4),(3,0,-1.4),(3,0,1.4)],[(-3,0,-1.4),(3,0,1.4),(-3,0,1.4)]],mat,
                                  np.array([[(0,0),(63,0),(63,31)],[(0,0),(63,31),(0,31)]],np.float32))
        self.bet.normal[:]=(0,1,0)
        self.droplet=R.sphere(self.red,.22)
        self.blood_cloud=R.sphere(self.red,1)
        self.blood_events=[]
        if blood: self.prepare_blood()
        self.r.seal()
        self.instances=[]
        (CACHE/'escena.json').write_text(json.dumps({
            'duracion':TOTAL,'resolucion_logica':[W,H],'fps':FPS,
            'alturas_mundiales':HEIGHT,'posiciones_iniciales':STAND,
            'impactos':HITS,'casino':'ARCHIVE/casino.narc/casino/casino_back.nsbmd',
            'personajes':'Modelos y animaciones originales de la ROM; sin escala individual por plano',
            'render':'Perspectiva, recorte cercano, profundidad conjunta y UV sin suavizado',
            'sangre':'Partículas y manchas estilizadas autorizadas en la revisión, con colisión y persistencia',
            'musica':'Partitura propia con BANK_CHIJO_BGM y muestras SBNK/SWAR de la ROM'
        },ensure_ascii=False,indent=2),encoding='utf8')
        print('Escena 3D preparada; escala Mario %.3f.'%self.scales['mario'],flush=True)

    def local(self,name,pose,t):
        a=self.actors[name]
        anim=casino_assets.POSES[name][pose]
        frames=a.anims[anim].num_frames
        tick=int(max(0,t)*48)%frames
        if name=='bowser' and pose=='laugh': tick=30+int(max(0,t)*22)%40
        key=name,pose,tick
        if key not in self.local_cache:
            m=self.r.from_items(a._items(anim,tick,0),a.tex)
            # El origen se fija bajo los pies: la animación no altera la escala mundial.
            m.xyz[:,:,1]-=m.xyz[:,:,1].min()
            self.local_cache[key]=m
        return self.local_cache[key]

    def add(self,mesh,position=(0,0,0),yaw=0,scale=1):
        self.instances.append((mesh,position,yaw,scale))

    def actor(self,name,pos,pose='wait',t=0,yaw=0,shadow=True,identity=None):
        if shadow:
            radius=HEIGHT[name]*.22*max(.6,1-pos[1]*.035)
            self.add(self.shadow,(pos[0],.02,pos[2]),scale=radius)
        mesh=self.motion.mesh(name,identity or name,getattr(self,'scene_t',0))
        if name=='mario' and getattr(self,'scene_t',0)>=26.1:
            # La sangre sobre los guantes acompaña al esqueleto en los siguientes planos.
            color=mesh.color.copy()
            gloves=(np.abs(mesh.xyz[:,:,0])>3.2)&(mesh.xyz[:,:,1]>6)&(mesh.xyz[:,:,1]<12.5)
            color[gloves]*=(1,.13,.16)
            mesh=R.Mesh(mesh.xyz,mesh.uv,mesh.normal,color,mesh.mats)
        self.add(mesh,pos,yaw,self.scales[name])

    def prepare_blood(self):
        collision=np.concatenate((self.room.xyz,self.floor.xyz,self.walls.xyz)).astype(np.float64)
        for i,(at,(x,z)) in enumerate(HITS):
            rng=np.random.default_rng(720+i)
            count=145
            origins=np.repeat(np.array([[x,9.6,z]],np.float64),count,0)
            angles=rng.uniform(0,math.tau,count)
            speed=rng.uniform(12,52,count)
            velocities=np.stack((np.cos(angles)*speed,rng.uniform(1,24,count),np.sin(angles)*speed),1)
            hits=R.trace_particles(origins,velocities,collision)
            stains=[]
            for j,hit in enumerate(hits):
                radius=rng.uniform(.25,1.15)*(1.5 if abs(hit[5])<.5 else 1)
                stains.append(R.splat(hit[1:4],hit[4:7],radius,self.red if j%3 else self.darkred,j+700*i))
            pools=[R.splat((x+dx,.045,z+dz),(0,1,0),radius,self.darkred,42+i*100+j)
                   for j,(dx,dz,radius) in enumerate([(0,0,5.1),(2,1,2.7),(-2,-1.5,3.2)])]
            self.blood_events.append((at,origins,velocities,hits,stains,pools))
        print('Salpicaduras calculadas contra suelo, paredes y mobiliario reales.',flush=True)

    def blood(self,t):
        for at,origins,velocity,hits,stains,pools in self.blood_events:
            age=t-at
            if age<0: continue
            if age<.14:
                self.add(self.blood_cloud,origins[0],scale=1.4+age*17)
            for j,hit in enumerate(hits):
                if age<hit[0]:
                    p=origins[j]+velocity[j]*age
                    p[1]-=19*age*age
                    # Partículas tridimensionales, ocultas por los objetos cuando pasan detrás.
                    self.add(self.droplet,p,scale=1+(j%4)*.35)
                else:
                    self.add(stains[j])
            if age>.60:
                for pool in pools: self.add(pool)

    def roulette(self,t):
        self.add(self.rim,TABLE+np.array([0,.02,0]))
        q=max(0,min(1,(t-17)/5))
        angle=360*5*(1-(1-q)**3) if t>=17 else 0
        self.add(self.wheel,TABLE+np.array([0,.10,0]),yaw=angle)
        self.add(self.hub,TABLE+np.array([0,.65,0]))
        final=math.radians(-90+2*360/37)
        theta=final+math.tau*7*(1-q)**2.3
        radius=7.4-.8*ease((q-.65)/.35)
        ball=TABLE+np.array([math.cos(theta)*radius,.52,math.sin(theta)*radius])
        if 16.15<t<17:
            q2=(t-16.15)/.85
            ball=mix((28,10.2,-47),ball,q2)
            ball[1]+=math.sin(q2*math.pi)*2
        if t>=16.15: self.add(self.ball,ball)
        self.add(self.bet,(18.3,7.03,-24))
        if 6.4<t<22.6:
            for i in range(16):
                end=(16.6+i%4*.85,7.45+i//4*.43,-24.5+(i%3)*.5)
                q2=ease((t-6.4-i*.045)/.65)
                if q2<=0: continue
                p=mix((14.4,8.2,-23.6),end,q2)
                p[1]+=math.sin(q2*math.pi)*2
                self.add(self.coin,p,yaw=i*30)
        elif 22.6<=t<23.1:
            q2=ease((t-22.6)/.5)
            for i in range(16):
                p=mix((16.6+i%4*.85,7.45+i//4*.43,-24.5+i%3*.5),(27,9,-50),q2)
                self.add(self.coin,p)

    def fixed_cast(self,t):
        # El reparto mantiene estas posiciones mundiales en todos los planos de la apuesta.
        mario=np.array(STAND['mario']);luigi=np.array(STAND['luigi'])
        if t<2.5:
            mario=mix((15,0,8),mario,ease(t/2.3))
            luigi=mix((8,0,12),luigi,ease(max(0,t-.25)/2.25))
        if t>=6:
            mario=mix(STAND['mario'],(12,0,-22),ease((t-6)/.4))
        if 2.5<t<6:
            luigi+=np.array([-2*ease((t-2.5)/2),0,2*ease((t-2.5)/2)])
        if t>=6: luigi+=(-2,0,2)
        mp='walk' if t<2.2 or 6<t<6.4 else 'bet' if 6.45<t<7.4 else 'mad' if 14<t<15.5 else 'shock' if t>=22.4 else 'wait'
        lp='walk' if t<2.5 else 'shock' if t<4.3 else 'fear' if t>=22.4 else 'wait'
        myaw=yawto(mario,TABLE)
        if 2.5<t<5.8: myaw=angle_mix(myaw,yawto(mario,luigi),(t-2.5)/.25)
        elif 5.8<=t<6.2: myaw=angle_mix(yawto(mario,luigi),myaw,(t-5.8)/.4)
        self.actor('mario',mario,mp,t if mp not in ('bet','shock') else t-(6.45 if mp=='bet' else 22.4),myaw)
        lyaw=yawto(luigi,mario)
        if 4.6<t<5.8: lyaw=angle_mix(lyaw,yawto(luigi,(0,0,10)),(t-4.6)/.25)
        elif 5.8<=t<6.2: lyaw=angle_mix(yawto(luigi,(0,0,10)),lyaw,(t-5.8)/.4)
        if t>17: lyaw=angle_mix(lyaw,yawto(luigi,TABLE),(t-17)/.3)
        self.actor('luigi',luigi,lp,t,lyaw)
        self.actor('peach',STAND['peach'],'spin' if 15.9<t<17 else 'wait',t-15.9 if 15.9<t<17 else t,
                   yawto(STAND['peach'],TABLE))
        byaw=angle_mix(yawto(STAND['bowser'],mario),yawto(STAND['bowser'],TABLE),(t-17)/.3)
        self.actor('bowser',STAND['bowser'],'laugh' if 9<t<14 else 'wait',t-9 if 9<t<14 else t,byaw)

    def chase_state(self,t):
        for i,(hit,(x,z)) in enumerate(HITS):
            start=24.7 if i==0 else HITS[i-1][0]+.23
            if t<=hit+.23 or i==2:
                begin,target,heading=self.approaches[i]
                previous=yawto((12,0,-22),TABLE) if i==0 else self.approaches[i-1][2]
                heading=angle_mix(previous,heading,(t-start)/.2)
                if i==2 and t>hit+.23:
                    p=mix(target,(28,0,-5),ease((t-hit-.23)/1.57))
                    heading=angle_mix(heading,yawto(target,(28,0,-5)),(t-hit-.23)/.2)
                    return i,p,'run',heading,None
                if t<hit-.42:
                    p=mix(begin,target,ease((t-start)/(hit-.42-start)))
                    return i,p,'run',heading,None
                p=np.array(target)
                pose='hold' if t<hit-.12 else 'mad'
                if t<hit:
                    q=ease((t-hit+.42)/.42)
                    held=(x,4.8*q,z)
                else: held=None
                return i,p,pose,heading,held

    def combat(self,t):
        watching=self.chase_state(t)[1] if t<31 else mix(self.approaches[-1][1],(28,0,-5),ease((t-30.63)/1.57))
        pyaw=angle_mix(yawto(STAND['peach'],TABLE),yawto(STAND['peach'],watching),(t-24.7)/.3)
        byaw=angle_mix(yawto(STAND['bowser'],TABLE),yawto(STAND['bowser'],watching),(t-24.7)/.3)
        lyaw=angle_mix(yawto((-4,0,-16),TABLE),yawto((-4,0,-16),watching),(t-24.7)/.3)
        self.actor('peach',STAND['peach'],'shock',t,pyaw)
        self.actor('bowser',STAND['bowser'],'wait',t,byaw)
        self.actor('luigi',(-4,0,-16),'fear',t,lyaw)
        if t<31:
            active,pos,pose,yaw,held=self.chase_state(t)
            self.actor('mario',pos,pose,t,yaw)
            for i,(hit,(x,z)) in enumerate(HITS):
                if t>=hit: continue
                if i==active and held is not None:
                    tyaw=angle_mix(45+i*90,yaw+180,(t-hit+.42)/.2)
                    self.actor('toad',held,'wait',t,tyaw,identity=('toad',i))
                else:
                    # Intento de huida visible antes del agarre, sin teletransportarse de encuentro.
                    panic=ease((t-(hit-1.25))/.8)
                    jitter=math.sin(t*8)*.15*panic*(1-ease((t-hit+.55)/.13))
                    tyaw=angle_mix(60+i*70,45+i*90,(t-hit+1.25)/.18)
                    self.actor('toad',(x+jitter,0,z),'run' if panic else 'wait',t,tyaw,identity=('toad',i))
        else:
            pos=mix(self.approaches[-1][1],(28,0,-5),ease((t-30.63)/1.57))
            if t<34.7:
                aiming=angle_mix(yawto(self.approaches[-1][1],(28,0,-5)),yawto(pos,(22,0,9)),(t-31)/.25)
                self.actor('mario',pos,'run' if t<32.1 else 'mad' if t<33.1 else 'shock',t,
                           aiming)
            else:
                age=t-34.7
                p=np.array([28.,max(0,10*age-13*age*age),-5.])
                # Animación de derrota del juego, con un salto y caída controlados en el mundo.
                falling=angle_mix(yawto((28,0,-5),(22,0,9)),150,age/.28)
                self.actor('mario',p,'dead',age,falling)
            ring=[(20,-1),(35,-1),(20,-10),(35,-10),(27,3),(28,-15)]
            starts=[(13,17),(43,17),(15,12),(45,9),(26,18),(40,12)]
            for i,((x,z),(sx,sz)) in enumerate(zip(ring,starts)):
                q=ease((t-31-i*.075)/1.9)
                p=mix((sx,0,sz),(x,0,z),q)
                strike=33.25+i*.18
                if strike-.2<t<strike+.28:
                    phase=math.sin(math.pi*(t-strike+.2)/.48)**2
                    p=mix(p,pos,phase*.55)
                self.actor('koopa',p,'walk' if t<33 else 'attack',t,yawto(p,pos),identity=('koopa',i))
        self.blood(t)

    def camera(self,t):
        wide=((55,31,20),(20,5,-30),280)
        if t<2.5:
            return tuple(mix((76,42,39),wide[0],ease(t/2.5))),wide[1],238
        if t<6:
            return (33,20,5),(2.5,7,-18),300
        if t<9:
            return (43,22,-1),(13,6.7,-26),315
        if t<14:
            return (16,23,-7),(43,10,-37),275
        if t<15.7:
            return (37,17,-5),(12,7,-22),300
        if t<17:
            return (12,22,-17),(27,9,-49),305
        if t<19.8:
            return (24,20,-27),(24,7,-34),137
        if t<20.55:
            return wide
        if t<22.6:
            return (10,23,-33),(24,7,-34),210
        if t<24.7:
            return (38,19,-1),(12,7,-22),290
        if t<31:
            _,p,_,_,_=self.chase_state(t)
            target=mix((23,5,-8),(p[0],6,p[2]),.7)
            return (54,25,24),tuple(target),325
        if t<36.6:
            return (55,29,25),(27,5,-5),315
        return wide

    def frame(self,t):
        self.scene_t=t
        self.instances=[]
        self.add(self.walls)
        self.add(self.floor)
        self.add(self.room)
        self.roulette(t)
        if t<24.7:
            self.fixed_cast(t)
            for i,(hit,(x,z)) in enumerate(HITS): self.actor('toad',(x,0,z),'wait',t,60+i*70,identity=('toad',i))
        else: self.combat(min(t,36.59))
        im=self.r.frame(self.instances,self.camera(t)).convert('RGBA')
        # Breves sacudidas nacen de los impactos, siempre con decorado y reparto juntos.
        impact=max([0]+[max(0,1-(t-hit)/.12) for hit,_ in HITS if 0<=t-hit<.12])
        if impact:
            im=im.transform((W,H),Image.Transform.AFFINE,(1,0,int(math.sin(t*93)*3*impact),0,1,int(math.cos(t*71)*2*impact)),resample=Image.Resampling.NEAREST)
        if 36<t<36.6:
            q=ease((t-36)/.6);r=350*(1-q)
            mask=Image.new('L',(W,H),255)
            ImageDraw.Draw(mask).ellipse((108-r,220-r,108+r,220+r),fill=0)
            im.paste((20,6,31),(0,0,W,H),mask)
        if t>=36.6:
            im=Image.new('RGBA',(W,H),(20,6,31,255))
            anterior.label(im,'GAME',100,color=(255,97,78),scale=2)
            anterior.label(im,'OVER',137,color=(255,97,78),scale=2)
        anterior.dialogue(im,t)
        if t<.2: im=Image.blend(Image.new('RGBA',(W,H),(20,6,31,255)),im,ease(t/.2))
        if t>39.7: im=Image.blend(im,Image.new('RGBA',(W,H),(20,6,31,255)),ease((t-39.7)/.3))
        return im.convert('RGB')


def preview():
    film=Film()
    times=[1.5,3.8,7.7,11.8,14.8,16.5,18.5,20.2,21.95,22.8,24.2,25.75,26.2,27.3,28.4,30.5,32.5,34,35.1,38]
    sheet=Image.new('RGB',(W*5,(H+22)*4),(20,6,31))
    for i,t in enumerate(times):
        start=time.perf_counter();fr=film.frame(t)
        print('Plano %.2f: %.2fs'%(t,time.perf_counter()-start),flush=True)
        fr.save(CACHE/('previo_%s.png'%t))
        x=i%5*W;y=i//5*(H+22)
        sheet.paste(fr,(x,y));sheet.paste(anterior.lettering('%.2f s'%t).convert('RGB'),(x+3,y+H))
    sheet.save(CACHE/'storyboard_visual.png')
    print(CACHE/'storyboard_visual.png',flush=True)


def main():
    FINAL.parent.mkdir(parents=True,exist_ok=True)
    film=Film();silent=CACHE/'imagen.mp4'
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}',
         '-r',str(FPS),'-i','-','-vf','scale=1080:1920:flags=neighbor','-an','-c:v','libx264',
         '-preset','fast','-crf','17','-pix_fmt','yuv420p',str(silent)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(TOTAL*FPS):
            p.stdin.write(film.frame(i/FPS).tobytes())
            if i%90==0: print('3D: %d / %d s'%(i/FPS,TOTAL),flush=True)
    finally:
        p.stdin.close();code=p.wait()
    if code: raise RuntimeError('No se pudo renderizar el casino 3D')
    wav=casino_audio.build()
    subprocess.check_call(['ffmpeg','-y','-loglevel','error','-i',str(silent),'-i',str(wav),'-c:v','copy',
                           '-c:a','aac','-b:a','192k','-ar','48000','-af','loudnorm=I=-16:TP=-1.5:LRA=8',
                           '-t',str(TOTAL),'-movflags','+faststart',str(FINAL)])
    shutil.copyfile(FINAL,FINAL.with_name('mario_casino_vertical_v3.mp4'))
    print(FINAL,flush=True)


if __name__=='__main__':
    preview() if '--preview' in sys.argv else main()
