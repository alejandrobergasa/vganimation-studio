"""Cinemática vertical «Todo al rojo». ROM intacta; ruleta nueva autorizada.

python -I video/make_video.py --casino
python -I video/casino.py --preview
"""
from pathlib import Path
from functools import lru_cache
import sys
import math
import json
import subprocess

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT/'tools'/'nsmb'))
import text
import nitro3d as N
from rom import rutas
import casino_assets
import casino_audio

W,H,FPS=216,384,30
TOTAL=casino_audio.DURATION
CACHE=Path(rutas.cache('nsmb'))/'casino'
FINAL=Path(rutas.salida('nsmb'))/'mario_casino_vertical.mp4'
NEAREST=Image.Resampling.NEAREST
INK=(21,10,34)
GOLD=(255,214,74)
WHITE=(255,247,222)
RED=(197,25,42)
BLACK=(23,22,29)
NUMBERS=[0,32,15,19,4,21,2,25,17,34,6,27,13,36,11,30,8,23,10,5,24,16,33,1,20,14,31,9,22,18,29,7,28,12,35,3,26]
REDS={1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}


def clamp(x): return max(0,min(1,x))
def ease(x):
    x=clamp(x)
    return x*x*(3-2*x)
def lerp(a,b,q): return a+(b-a)*q


@lru_cache(maxsize=512)
def lettering(s,color=WHITE,scale=1):
    im=text.render(s,color=color,outline=INK)
    if scale!=1: im=im.resize((im.width*scale,im.height*scale),NEAREST)
    return im


def label(im,s,y,x=None,color=WHITE,scale=1):
    t=lettering(s,color,scale)
    im.alpha_composite(t,(round((W-t.width)/2 if x is None else x),round(y)))


@lru_cache(maxsize=64)
def wrap(s,width=170):
    lines=['']
    for word in s.split():
        trial=(lines[-1]+' '+word).strip()
        if lettering(trial).width>width:
            lines.append(word)
        else: lines[-1]=trial
    return lines


def dialogue(im,t):
    for start,end,who,line in casino_audio.PAGES:
        if not start<=t<end: continue
        colors={'MARIO':(255,109,90),'LUIGI':(123,236,121),'BOWSER':GOLD,'PEACH':(255,159,209)}
        lines=wrap(line)
        top=331-len(lines)*18
        d=ImageDraw.Draw(im)
        d.rectangle((10,top-22,194,346),fill=(17,10,32),outline=GOLD,width=1)
        d.line((12,top-20,192,top-20),fill=(129,73,41))
        label(im,who,top-21,x=17,color=colors[who])
        count=int(max(0,t-start-.06)*casino_audio.CPS)
        for j,s in enumerate(lines):
            visible=s[:max(0,count)]
            if visible: label(im,visible,top+j*18,x=17)
            count-=len(s)+1
        break


class Film:
    def __init__(self):
        CACHE.mkdir(parents=True,exist_ok=True)
        self.a=casino_assets.Assets()
        self.a.contacts()
        self.base=self.room()
        self.wheel_source=self.wheel_texture()
        self.coin=self.coin_texture()
        self.room_wide=self.base.copy()
        (CACHE/'procedencia.json').write_text(json.dumps({
            'casino':'ARCHIVE/casino.narc/casino/casino_back.nsbmd',
            'mario':'player/mario_model_LZ.bin + mario_head_cap_LZ.bin',
            'luigi':'player/luigi_model_LZ.bin + luigi_head_cap_LZ.bin',
            'bowser':'enemy/koopa_new.nsbmd + koopa_new.nsbca',
            'peach':'enemy/peach.nsbmd + peach.nsbca',
            'toads':'ARCHIVE/luigi_model_mg.narc/kino_d.nsbmd + kino_wait/kino_walk',
            'tropas':'enemy/nokonoko.nsbmd + nokonoko.nsbca',
            'fuente':'font_a.NFTR',
            'musica':'partitura propia, BANK_CHIJO_BGM, SBNK/SWAR de sound_data.sdat',
            'excepcion_autorizada':'geometría nueva de ruleta roja y negra y bola, con texturas y paleta del casino',
            'violencia':'golpes, destellos, estrellas y desapariciones sin gore',
            'formato':'216x384 -> 1080x1920, nearest, 30 fps, 59 s'
        },ensure_ascii=False,indent=2),encoding='utf8')
        print('Decorado preparado.',flush=True)

    def room(self):
        """Casino 3D original con continuación de sus texturas fuera del campo DS."""
        wall=np.asarray(self.a.tex['wall'])
        floor=np.asarray(self.a.tex['floor'])
        yy,xx=np.mgrid[0:H,0:W]
        arr=wall[yy%wall.shape[0],xx%wall.shape[1]].copy()
        # La misma proyección que usa el modelo para extender el suelo hasta el primer plano.
        mask=yy>=174
        fx=((xx-108)*.65+(yy-174)*.23).astype(int)%32
        fy=((yy-174)*1.12).astype(int)%32
        arr[mask]=floor[fy[mask],fx[mask]]
        im=Image.fromarray(arr)
        n=casino_assets.extraer_casino.load()
        m=n.models[0]
        # Las paredes originales son de una cara; desde dentro se mantienen los materiales.
        rendered,_=N.render(m.triangles(),m,N.TexLookup(n),scale=2.65,size=(W,H),
                             origin=(108,235),ortho=lambda x,y,z:(x,-y*.9+z*.4),ambient=.86)
        im.alpha_composite(Image.fromarray(rendered))
        # Oscurecimiento superior: hace legibles las siluetas y conserva la textura del decorado.
        shade=np.zeros((H,W,4),np.uint8)
        shade[...,:3]=(13,4,25)
        shade[...,3]=np.clip(70*(1-yy/170),0,70).astype(np.uint8)
        im.alpha_composite(Image.fromarray(shade))
        return im

    def coin_texture(self):
        # Moneda auténtica del nivel, ya extraída por el motor del proyecto.
        import world
        return world.get().coin_img.convert('RGBA')

    def wheel_texture(self):
        """Ruleta autorizada. Aro y cubeta usan texturas del casino; 37 casillas europeas."""
        size=240; c=120
        im=Image.new('RGBA',(size,size))
        # La madera se toma de la maceta y el metal del marco del taburete original.
        wood=self.a.tex['flower_pot'].resize((size,size),NEAREST)
        mask=Image.new('L',(size,size));ImageDraw.Draw(mask).ellipse((2,2,237,237),fill=255)
        im.paste(wood,(0,0),mask)
        d=ImageDraw.Draw(im)
        d.ellipse((3,3,236,236),outline=(77,28,12),width=4)
        d.ellipse((10,10,229,229),fill=(92,45,17),outline=GOLD,width=3)
        for i,num in enumerate(NUMBERS):
            # Centro de la primera casilla en -90 grados.
            a0=-90+(i-.5)*360/37
            a1=-90+(i+.5)*360/37
            color=(25,116,51) if num==0 else RED if num in REDS else BLACK
            pts=[(c,c)]+[(c+99*math.cos(math.radians(a)),c+99*math.sin(math.radians(a)))
                         for a in np.linspace(a0,a1,5)]
            d.polygon(pts,fill=color)
            d.line((c,c,*pts[1]),fill=(235,184,64),width=1)
            # Números diminutos de la misma fuente NFTR, escalados sólo aquí a resolución de mesa.
            numim=lettering(str(num))
            numim=numim.resize((max(4,round(numim.width*.55)),9),NEAREST)
            a=math.radians(-90+i*360/37)
            im.alpha_composite(numim,(round(c+85*math.cos(a)-numim.width/2),round(c+85*math.sin(a)-5)))
        # Núcleo de madera con los colores de la textura original.
        d.ellipse((57,57,183,183),fill=(132,62,26),outline=(239,175,60),width=2)
        d.ellipse((69,69,171,171),fill=(171,90,39),outline=(108,43,18),width=2)
        for a in range(0,360,90):
            r=math.radians(a)
            d.line((c,c,c+41*math.cos(r),c+41*math.sin(r)),fill=GOLD,width=5)
        d.ellipse((110,110,130,130),fill=GOLD,outline=(98,56,19),width=3)
        im.save(CACHE/'ruleta_textura.png')
        return im

    def wheel(self,im,t,x=108,y=222,r=84,tilt=.60,close=False):
        # Integración analítica: velocidad inicial alta y frenada cúbica, sin saltos temporales.
        q=clamp((t-29)/9)
        angle=360*7*(1-(1-q)**3) if t>=29 else 0
        d=ImageDraw.Draw(im)
        ry=r*tilt
        d.ellipse((x-r,y-ry+9,x+r,y+ry+13),fill=(64,24,10),outline=(224,153,43),width=2)
        d.ellipse((x-r+2,y-ry+6,x+r-2,y+ry+8),fill=(145,65,24))
        disc=self.wheel_source.rotate(angle,resample=NEAREST)
        disc=disc.resize((round(r*2),round(r*2*tilt)),NEAREST)
        im.alpha_composite(disc,(round(x-r),round(y-ry)))
        # La bola termina en 15: casilla negra del orden europeo, con la rueda parada.
        final=-90+2*360/37
        ballangle=final+360*9*(1-q)**2.25
        rad=r*(.88-.12*ease((q-.65)/.35))
        if t<29:
            ballangle=-78;rad=r*.86
        theta=math.radians(ballangle)
        bx=x+rad*math.cos(theta);by=y+rad*tilt*math.sin(theta)
        br=2.3 if not close else 3.1
        d=ImageDraw.Draw(im)
        d.ellipse((bx-br+1,by-br+2,bx+br+1,by+br+2),fill=(52,28,18))
        d.ellipse((bx-br,by-br,bx+br,by+br),fill=(255,255,238),outline=(159,160,147))
        d.point((round(bx-1),round(by-1)),fill=(255,255,255))
        # Relieve central independiente del giro.
        d.ellipse((x-5,y-9,x+5,y+2),fill=(236,178,58),outline=(95,52,19))
        d.ellipse((x-3,y-10,x+3,y-5),fill=(255,228,121))

    def table(self,im,t,y=228,coins=False):
        d=ImageDraw.Draw(im)
        # Perfil de mesa remuestreado directamente del material table.
        tex=self.a.tex['table'].resize((200,44),NEAREST)
        im.alpha_composite(tex,(8,y+30))
        d.ellipse((5,y-22,211,y+55),fill=(81,35,14),outline=GOLD,width=2)
        d.ellipse((10,y-26,206,y+44),fill=(19,94,43),outline=(223,166,56),width=2)
        self.wheel(im,t,79,y+3,62,.48)
        d.polygon([(143,y-17),(190,y-12),(199,y+31),(146,y+27)],fill=RED,outline=GOLD)
        stamp=lettering('ROJO',GOLD)
        im.alpha_composite(stamp,(145,y-8))
        if coins:
            for i in range(12):
                c=self.coin.resize((8,10),NEAREST)
                im.alpha_composite(c,(153+i%4*8,y+9-i//4*4))

    def main_room(self,t,bet=False):
        im=self.base.copy()
        self.a.draw(im,'toad',23,180,'wait',t,.9,angle=65)
        self.a.draw(im,'toad',187,191,'wait',t+.3,.9,facing=-1,angle=65)
        self.a.draw(im,'peach',105,202,'wait',t,1.6)
        self.a.draw(im,'bowser',176,224,'laugh' if 15<=t<23 else 'wait',t,1.5,facing=-1)
        self.table(im,t,229,coins=bet and t<38)
        self.a.draw(im,'luigi',40,287,'shock' if t>=29 else 'wait',t,1.85)
        self.a.draw(im,'mario',114,297,'shock' if t>=38 else 'wait',t,2.1,angle=65)
        return im

    def close_room(self):
        # Planos cercanos conservan el casino detrás, con la cuadrícula de píxel intacta.
        return self.base.crop((16,50,200,330)).resize((W,H),NEAREST)

    def coin_cascade(self,im,t):
        d=ImageDraw.Draw(im)
        # Bolsa sugerida por monedas en la mano y el gesto real de lanzamiento.
        for i in range(20):
            q=clamp((t-10.8-i*.065)/.6)
            if q<=0: continue
            x=lerp(85,160+(i%4)*4,q)
            y=lerp(256,252-(i//4)*3,q)-math.sin(q*math.pi)*34
            c=self.coin.resize((8 if i%2 else 6,10),NEAREST)
            im.alpha_composite(c,(round(x),round(y)))

    def burst(self,im,age,x,y,seed=0):
        """Impacto arcade rojo: estrellas opacas; no sangre, gotas ni anatomía."""
        if not 0<=age<.5: return
        d=ImageDraw.Draw(im)
        if age<.15:
            pts=[]
            for i in range(16):
                r=(24 if i%2==0 else 10)*(1+age)
                a=i*math.pi/8
                pts.append((x+r*math.cos(a),y+r*math.sin(a)))
            d.polygon(pts,fill=(255,65,40),outline=(255,212,74))
        for i in range(9):
            a=(i*2.4+seed)
            r=age*(48+i*4)
            px=x+math.cos(a)*r;py=y+math.sin(a)*r+age*age*38
            color=(255,83,46) if i%2 else GOLD
            rr=max(1,3-age*4)
            d.polygon([(px,py-rr*2),(px+rr,py),(px,py+rr*2),(px-rr,py)],fill=color)

    def chaos(self,t):
        im=self.base.copy()
        tt=t-42.5
        # Tres encuentros: carrera, agarre visible, lanzamiento y destello de desaparición.
        hits=(43.9,45.7,47.5)
        stage=min(2,max(0,int((t-42.5)/1.8)))
        hit=hits[stage]
        left=stage%2==0
        start,end=(-20,143) if left else (236,67)
        q=ease((t-(hit-1.4))/1.08)
        x=lerp(start,end,q)
        self.a.draw(im,'luigi',23,200,'fear',t,1.1)
        for i,h in enumerate(hits):
            tx=(164,49,164)[i]
            if t<h-.35:
                self.a.draw(im,'toad',tx+math.sin(t*3+i)*2,278-i*4,'run',t,1.5,facing=-1 if i%2 else 1,angle=65)
        pose='run' if t<hit-.42 else 'hold' if t<hit-.12 else 'mad'
        self.a.draw(im,'mario',x,286,pose,t if pose=='run' else t-(hit-.42),2.15,
                     facing=1 if left else -1,angle=65)
        if hit-.42<=t<hit:
            # Toad entero delante de las manos; el destello arcade oculta su desaparición.
            self.a.draw(im,'toad',x+(26 if left else -26),251-10*ease((t-hit+.42)/.42),'wait',t,1.4,
                         facing=-1 if left else 1)
        for i,h in enumerate(hits): self.burst(im,t-h,(164,49,164)[i],244,seed=i)
        # Coupe et travelling latéral discret, pas de texte ajouté au combat.
        if any(0<=t-h<.12 for h in hits):
            im=im.transform((W,H),Image.Transform.AFFINE,(1,0,round(math.sin(t*120)*3),0,1,round(math.cos(t*93)*2)),resample=NEAREST)
        return im

    def troops(self,t):
        im=self.base.copy()
        self.a.draw(im,'luigi',23,204,'fear',t,1.2)
        q=ease((t-49)/2.2)
        spots=[(lerp(-20,51,q),247),(lerp(236,172,q),250),
               (lerp(-40,40,q),286),(lerp(250,181,q),288),
               (lerp(-65,68,q),321),(lerp(280,157,q),325)]
        for x,y in spots[:2]: self.a.draw(im,'koopa',x,y,'walk',t,1.7,facing=1 if x<108 else -1,angle=65)
        if t<53.1:
            self.a.draw(im,'mario',108+math.sin(t*34)*(.7 if t<51 else 3),287,
                         'mad' if t<51 else 'shock',t,2.2,angle=20)
        else:
            age=t-53.1
            y=287-110*age+110*age*age
            self.a.draw(im,'mario',108,y,'dead',age,2.2,once=True)
        for x,y in spots[2:]: self.a.draw(im,'koopa',x,y,'walk' if t<51.2 else 'attack',t,1.9,
                                       facing=1 if x<108 else -1,angle=65)
        for h in (51.4,52.1,52.8): self.burst(im,t-h,108,248,2)
        if t>=54.2:
            mask=Image.new('L',(W,H),255);r=350*(1-ease((t-54.2)/.8))
            ImageDraw.Draw(mask).ellipse((108-r,252-r,108+r,252+r),fill=0)
            im.paste(INK,(0,0,W,H),mask)
        return im

    def frame(self,t):
        if t<5:
            im=self.base.copy()
            self.a.draw(im,'peach',105,203,'wait',t,1.55)
            self.a.draw(im,'bowser',174,226,'wait',t,1.5,facing=-1)
            self.a.draw(im,'toad',29,181,'wait',t,1.0)
            self.table(im,0,229)
            q=ease(t/4.2)
            self.a.draw(im,'mario',lerp(-36,110,q),lerp(321,294,q),'walk' if t<4.2 else 'wait',t,2.05,angle=65)
            self.a.draw(im,'luigi',lerp(-72,38,q),lerp(331,291,q),'walk' if t<4.2 else 'wait',t,1.9,angle=65)
            if t<.35:
                im=Image.blend(Image.new('RGBA',(W,H),INK+(255,)),im,ease(t/.35))
        elif t<10:
            im=self.close_room()
            self.a.draw(im,'bowser',186,193,'wait',t,1.2,facing=-1)
            self.a.draw(im,'mario',169,282,'wait',t,2.0,facing=-1,angle=65)
            # Luigi recula y dirige la mirada hacia la salida.
            self.a.draw(im,'luigi',lerp(85,66,ease((t-5)/3)),282,'shock' if t<7 else 'fear',t-5,3.6,
                         facing=-1 if t>8 else 1,angle=20)
        elif t<15:
            im=self.close_room()
            self.a.draw(im,'peach',167,194,'wait',t,1.7)
            self.table(im,0,244,coins=t>12.4)
            self.a.draw(im,'mario',52,322,'bet' if 10.9<t<12 else 'wait',t-10.9,4.8,angle=20,once=10.9<t<12)
            self.coin_cascade(im,t)
        elif t<23:
            im=self.close_room()
            self.a.draw(im,'bowser',115,274,'laugh',t-15,3.5,facing=-1)
            self.a.draw(im,'mario',32,294,'wait',t,1.4,angle=65)
            self.wheel(im,0,185,286,49,.48)
        elif t<26:
            im=self.close_room()
            # Mario tiende la mano a la mesa y celebra antes del giro.
            self.a.draw(im,'mario',105,289,'mad',t-23,4.0,angle=20)
            if t<23.25:
                self.burst(im,t-23,105,170,5)
        elif t<29:
            im=self.close_room()
            self.a.draw(im,'peach',108,245,'spin' if t>27 else 'wait',t-27,3.3,once=t>27)
            self.table(im,0,263,coins=True)
            if 28.15<t<28.9:
                q=(t-28.15)/.75
                bx=lerp(132,79,q);by=lerp(174,257,q)-math.sin(q*math.pi)*23
                ImageDraw.Draw(im).ellipse((bx-2,by-2,bx+2,by+2),fill=WHITE)
        elif t<38:
            if 31.8<=t<33.1 or 34.8<=t<35.9:
                im=self.main_room(t,True)
                # Todos miran la mesa: movimiento contenido y sin diálogos sobre la bola.
            else:
                im=self.close_room()
                # Los personajes se recortan en el borde superior durante el primer plano.
                self.a.draw(im,'peach',108,162,'wait',t,1.6)
                self.a.draw(im,'bowser',182,189,'wait',t,1.15,facing=-1)
                self.a.draw(im,'luigi',31,197,'shock',t,1.5)
                self.a.draw(im,'mario',80,199,'wait',t,1.6,angle=65)
                self.wheel(im,t,108,251,101,lerp(.67,.83,ease((t-35.9)/2.1)),True)
        elif t<40.2:
            im=self.close_room()
            self.wheel(im,38,108,213,102,.87,True)
            if t>38.5: label(im,'15',114,color=GOLD,scale=2)
        elif t<42.5:
            im=self.close_room()
            self.a.draw(im,'luigi',181,246,'fear',t,1.7,facing=-1)
            self.a.draw(im,'mario',106,289,'shock',t-40.2,4,once=True)
        elif t<49:
            im=self.chaos(t)
        elif t<55:
            im=self.troops(t)
        else:
            im=Image.new('RGBA',(W,H),INK+(255,))
            # Fondo del propio casino bajo la tarjeta final.
            stars=self.a.tex['wall']
            for y in range(0,H,64):
                for x in range(0,W,64): im.alpha_composite(stars,(x,y))
            im.alpha_composite(Image.new('RGBA',(W,H),(10,3,24,150)))
            label(im,'GAME',87,color=(255,116,86),scale=2)
            label(im,'OVER',122,color=(255,116,86),scale=2)
            self.a.draw(im,'luigi',108,254,'fear',t-55,2.5)
            if t>58.5: im=Image.blend(im,Image.new('RGBA',(W,H),INK+(255,)),ease((t-58.5)/.5))
        dialogue(im,t)
        return im.convert('RGB')


def preview():
    f=Film()
    times=[1.5,4.7,7.1,12.8,17.8,21,24.6,28.5,30.5,32.4,36.7,38.8,41.5,43.7,44.03,45.5,47.63,50.5,52.2,53.5,54.6,56.9]
    rows=math.ceil(len(times)/5)
    sheet=Image.new('RGB',(W*5,(H+22)*rows),INK)
    for i,t in enumerate(times):
        fr=f.frame(t)
        fr.save(CACHE/('previo_%s.png'%t))
        x=i%5*W;y=i//5*(H+22)
        sheet.paste(fr,(x,y))
        sheet.paste(lettering('%.2f s'%t).convert('RGB'),(x+5,y+H))
    sheet.save(CACHE/'storyboard_visual.png')
    print(CACHE/'storyboard_visual.png',flush=True)


def main():
    FINAL.parent.mkdir(parents=True,exist_ok=True)
    film=Film()
    silent=CACHE/'imagen.mp4'
    cmd=['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
         '-s',f'{W}x{H}','-r',str(FPS),'-i','-','-vf','scale=1080:1920:flags=neighbor',
         '-an','-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(silent)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for i in range(TOTAL*FPS):
            p.stdin.write(film.frame(i/FPS).tobytes())
            if i%150==0: print('Imagen: %d / %d s'%(i/FPS,TOTAL),flush=True)
    finally:
        p.stdin.close()
        code=p.wait()
    if code: raise RuntimeError('ffmpeg no pudo completar el casino')
    wav=casino_audio.build()
    subprocess.check_call(['ffmpeg','-y','-loglevel','error','-i',str(silent),'-i',str(wav),
                           '-c:v','copy','-c:a','aac','-b:a','192k','-ar','48000',
                           '-af','loudnorm=I=-16:TP=-1.5:LRA=8','-t',str(TOTAL),
                           '-movflags','+faststart',str(FINAL)])
    print(FINAL,flush=True)


if __name__=='__main__':
    # Conservar estas utilidades de texto y textura; la entrada pública usa la escena 3D revisada.
    import casino_3d
    casino_3d.preview() if '--preview' in sys.argv else casino_3d.main()
