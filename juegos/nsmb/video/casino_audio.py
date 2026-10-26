"""Partitura propia de casino, suspense, caos y derrota con SBNK/SWAR de la ROM."""
from pathlib import Path
import sys
import json
import re

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'nsmb'))
import sonido
import rom
from rom import rutas
from renfe_audio import effect, fade, normal, put

FS = sonido.FS
DURATION = 40
CACHE = Path(rutas.cache('nsmb')) / 'casino_3d'
PAGES = [
    (2.5, 6, 'LUIGI', 'Mario, me da miedo apostar. Vámonos.'),
    (6, 9, 'MARIO', '¡Todas mis monedas al rojo!'),
    (9.4, 11.7, 'BOWSER', 'Lo que a la rule le das,'),
    (11.7, 14, 'BOWSER', 'la rule te lo quita.'),
    (14, 15.7, 'MARIO', 'LET IT RIDE!'),
    (15.7, 17, 'PEACH', '¡No va más!'),
    (22, 23.1, 'PEACH', 'Negro.'),
    (23.1, 24.7, 'MARIO', '¡MIS MONEDAS!'),
    (36.6, 39.7, 'LUIGI', 'Te dije que nos fuéramos.'),
]
CPS = 23

# Tiempo, personaje, clip original, duración, nivel, panorama, cambio de tono en semitonos.
VOICE_CUES=[
    (.30,'Mario','SE_VOC_OPDM_YES',.40,.26,.42,0),
    (1.10,'Luigi','SE_VOC_LU_HOH',.30,.21,.25,0),
    (2.65,'Luigi','SE_VOC_L_HOEE',.44,.28,.28,0),
    (4.82,'Luigi','SE_VOC_LU_OTOTO',.32,.24,.26,0),
    (6.38,'Mario','SE_VOC_MA_HOH',.24,.23,.45,0),
    (6.72,'Mario','SE_VOC_MA_THROW_1',.34,.29,.48,0),
    (9.05,'Bowser','SE_EMY_KOOPA_LAUGH',.80,.37,.62,0),
    (12.05,'Bowser','SE_EMY_KOOPA_LAUGH',.65,.29,.61,-1),
    (14.05,'Mario','SE_VOC_MA_THROW',.45,.34,.48,0),
    (15.76,'Peach','SE_VOC_OPDM_PEACH_OH',.38,.28,.52,0),
    (18.10,'Mario','SE_VOC_MA_HOH',.19,.14,.40,0),
    (19.10,'Luigi','SE_VOC_LU_DANGLE',.25,.20,.28,0),
    (20.10,'Mario','SE_VOC_MA_HOH',.21,.17,.43,1),
    (21.10,'Luigi','SE_VOC_OPDM_UN_02_L',.22,.18,.29,0),
    (21.78,'Peach','SE_VOC_OPDM_PEACH_OH',.22,.19,.53,0),
    (23.12,'Mario','SE_VOC_OPDM_HOEE',.42,.33,.48,0),
    (24.72,'Mario','SE_VOC_MA_WOOO',.42,.34,.49,0),
    (25.43,'Mario','SE_VOC_MA_HOH',.21,.22,.45,0),
    (25.83,'Toad 1','SE_VOC_OPDM_AWAWA_01',.25,.28,.47,3),
    (25.98,'Mario','SE_VOC_MA_THROW_1',.24,.31,.46,0),
    (26.55,'Luigi','SE_VOC_L_HOEE',.40,.25,.25,0),
    (27.72,'Mario','SE_VOC_MA_THROW',.24,.29,.54,0),
    (28.02,'Toad 2','SE_VOC_OPDM_AWAWA_02',.25,.28,.55,3),
    (28.18,'Mario','SE_VOC_MA_THROW_1',.24,.31,.55,1),
    (29.10,'Peach','SE_VOC_JRDM_PEACH_CRY',.33,.23,.62,0),
    (30.14,'Toad 3','SE_VOC_OPDM_AWAWA_03',.25,.29,.62,3),
    (30.28,'Mario','SE_VOC_MA_THROW',.24,.31,.61,0),
    (30.72,'Bowser','SE_EMY_OLKP_BARK',.45,.29,.65,0),
    (31.35,'Luigi','SE_VOC_LU_OTOTO',.32,.24,.23,0),
    (33.25,'Mario','SE_VOC_BIRI',.26,.28,.52,0),
    (33.80,'Mario','SE_VOC_BIRI',.26,.27,.52,-1),
    (34.30,'Mario','SE_VOC_OPDM_HOEE',.24,.28,.51,0),
    (34.75,'Mario','SE_VOC_M_HOEE',.60,.33,.50,0),
    (36.68,'Luigi','SE_VOC_LU_HOH',.24,.23,.45,0),
    (38.40,'Luigi','SE_VOC_OPDM_UN_02_L',.20,.21,.45,0),
]


def character_voices():
    """Clips completos breves, sin silencio inicial, con voces de la ROM y panorama moderado."""
    track=np.zeros((round(DURATION*FS),2),np.float32)
    manifest=[]
    for at,who,name,duration,level,pan,semitones in VOICE_CUES:
        a=effect(name,min(1.3,duration+.4),1)
        activity=np.max(np.abs(a),axis=1)
        active=np.flatnonzero(activity>max(float(activity.max())*.055,.0001))
        assert len(active),'Clip de personaje mudo: '+name
        first=max(0,int(active[0]) - round(.008*FS))
        a=a[first:]
        if semitones:
            ratio=2**(semitones/12)
            p=np.arange(max(1,round(len(a)/ratio)))*ratio
            a=np.stack([np.interp(p,np.arange(len(a)),a[:,c]) for c in range(2)],1)
        a=a[:round(duration*FS)]
        a=fade(normal(a,level),.012)
        a[:,0]*=np.sqrt(2*(1-pan));a[:,1]*=np.sqrt(2*pan)
        put(track,a,at)
        manifest.append({'segundo':at,'personaje':who,'clip':name,'duracion':len(a)/FS,
                         'tono_semitonos':semitones,'pico':float(np.abs(a).max())})
    sonido.guardar_wav(str(CACHE/'voces_personajes.wav'),track)
    (CACHE/'voces_personajes.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('Vocalizaciones originales sincronizadas:',len(manifest),flush=True)
    return track


def score(kind, duration):
    notes = []
    def n(t, d, key, prog=13, vel=92, pan=64, vol=100):
        if t < duration - .02:
            notes.append((float(t), float(min(d, duration-t)), int(key), vel, prog, pan, vol))
    if kind == 'casino':
        beat = 60/128
        melody = [76, 79, 82, 81, 79, 76, 74, 75, 76, 0, 79, 81, 82, 79, 76, 74,
                  77, 81, 84, 83, 81, 77, 75, 76, 79, 0, 78, 77, 74, 71, 74, 79]
        roots = [48, 53, 50, 55]
        for i in range(int(duration/beat)+1):
            t = i*beat
            root = roots[(i//4)%4]
            n(t, beat*.7, root + [0,4,7,9][i%4], 11, 98, 57)
            for d, key in [(0, melody[(i*2)%32]), (beat*.64, melody[(i*2+1)%32])]:
                if key:
                    n(t+d, beat*.25, key, 13, 90, 73)
            if i%2:
                for k in (root+12, root+16, root+22):
                    n(t+.03, beat*.28, k, 14, 72, 43, 84)
            n(t, .06, 36 if i%2==0 else 38, 125, 70, 65, 80)
            n(t+beat*.64, .04, 42, 125, 55, 82, 74)
    elif kind == 'reto':
        beat = .48
        for i in range(int(duration/beat)+1):
            t=i*beat
            n(t,.28,[48,51,54,55][i%4],11,100,60)
            if i%2==0:
                for k in (60,63,66): n(t,.14,k,14,75,45)
            n(t+.31,.12,[79,78,75,73][i%4],18,82,75)
    elif kind == 'suspense':
        for i in range(int(duration/.24)+1):
            t=i*.24
            n(t,.13,[60,61,67,66,60,63,67,70][i%8],17,66+i%4*4,55+i%2*24,82)
            if i%4==0: n(t,.6,36+(i//8)%2,11,88,64,90)
    elif kind == 'caos':
        beat=60/176
        for i in range(int(duration/(beat/2))+1):
            t=i*beat/2
            root=[45,48,44,47][(i//8)%4]
            n(t,.12,[root+24,root+27,root+31,root+30][i%4],18,108,55+i%2*20)
            if i%2==0: n(t,.22,root,11,110,64)
            n(t,.07,36 if i%4==0 else 38 if i%4==2 else 42,125,100,64,100)
    elif kind == 'tropas':
        for i in range(int(duration/.34)+1):
            t=i*.34
            n(t,.18,38,125,103,64)
            n(t,.23,[43,43,46,48,43,43,50,46][i%8],11,106,55)
            if i%2==0:
                for k in (55,58,62): n(t,.26,k,15,85,75)
    elif kind == 'derrota':
        for t,d,k in [(0,.18,76),(.23,.17,72),(.45,.18,67),(.7,.3,63),(1.2,.5,59),(2,.9,48)]:
            n(t,d,k,18,106)
        for k in (48,51,55): n(2,.95,k,14,70,55)
    return notes


def dialogue():
    out=np.zeros((round(DURATION*FS),2),np.float32)
    samples={'MARIO':'SE_VOC_OPDM_UN_01','LUIGI':'SE_VOC_OPDM_UN_01_L',
             'PEACH':'SE_VOC_OPDM_PEACH_OH','BOWSER':'SE_EMY_KOOPA_LAUGH'}
    grains={}
    for who,name in samples.items():
        a=effect(name,.65,1)
        power=np.convolve(a.mean(1)**2,np.ones(300)/300,'same')
        peak=int(np.argmax(power)); start=max(0,peak-int(.025*FS))
        grains[who]=a[start:start+int(.085*FS)]
    for start,end,who,line in PAGES:
        syll=list(re.finditer(r'[aeiouáéíóúü]+',line,re.I))
        for j,m in enumerate(syll):
            ratio=2**(([-2,1,0,3,-1][j%5]+(-5 if who=='BOWSER' else 0))/12)
            grain=grains[who]; p=np.arange(round(len(grain)/ratio))*ratio
            a=np.stack([np.interp(p,np.arange(len(grain)),grain[:,c]) for c in range(2)],1)
            a=fade(normal(a,.21 if who!='BOWSER' else .24),.012)
            put(out,a,start+.12+m.start()/CPS)
    return out


def build():
    CACHE.mkdir(parents=True,exist_ok=True)
    son=sonido.Sonido(rom.find_rom())
    mix=np.zeros((round(DURATION*FS),2),np.float32)
    music=np.zeros_like(mix)
    manifest=[]
    for kind,start,end,level in [('casino',0,9,.26),('reto',9,15.7,.23),
                                ('suspense',15.7,21.85,.22),('caos',24.7,31,.30),
                                ('tropas',31,34.7,.28),('derrota',36.6,39.7,.30)]:
        print('Partitura:',kind,flush=True)
        notes=score(kind,end-start)
        a=fade(normal(sonido.tocar_notas(son,'BANK_CHIJO_BGM',notes,end-start),level),.08)
        put(music,a,start)
        sonido.guardar_wav(str(CACHE/('musica_'+kind+'.wav')),a)
        manifest.append({'escena':kind,'inicio':start,'fin':end,'banco':'BANK_CHIJO_BGM','notas':notes})
    duck=np.ones(len(mix),np.float32)
    for start,end,who,line in PAGES:
        a=round(start*FS); b=min(len(mix),round((start+len(line)/CPS+.38)*FS))
        duck[a:b]=.48
    for at,who,name,duration,level,pan,semitones in VOICE_CUES:
        a=max(0,round((at-.035)*FS));b=min(len(mix),round((at+duration+.08)*FS))
        duck[a:b]=np.minimum(duck[a:b],.55)
    # Suavizar la envolvente a 20 ms para evitar saltos en la música.
    step=round(.02*FS)
    small=np.convolve(duck[::step],np.ones(5)/5,'same')
    duck=np.interp(np.arange(len(mix)),np.arange(len(small))*step,small)
    mix+=music*duck[:,None]
    cues=[(0,'SE_SYS_COURSE_IN',.4,.15),(9.05,'SE_EMY_KOOPA_LAUGH',.65,.40),
          (14.05,'SE_VOC_MA_THROW',.45,.30),(15.75,'SE_VOC_OPDM_PEACH_OH',.4,.22),
          (16.7,'SE_OBJ_COIN_BOUND',.3,.26),(22,'SE_OBJ_TEKKYU_CRASH',.5,.42),
          (23.2,'SE_VOC_MA_OTOTO',.5,.31),(24.7,'SE_VOC_MA_WOOO',.4,.37),
          (31,'SE_SYS_WARNING',.35,.31),(34.7,'SE_PLY_DOWN',.8,.44),
          (34.75,'SE_VOC_M_HOEE',.55,.34),(36.6,'SE_SYS_ONE_DOWN',.7,.24)]
    for t in np.arange(.15,2.4,.22): cues.append((float(t),'SE_PLY_FOOTNOTE',.09,.07))
    for i,t in enumerate(np.arange(6.4,7.8,.09)): cues.append((float(t),'SE_OBJ_GET_COIN',.2,.20))
    # Clics de bola que se espacian con la desaceleración de la rueda.
    t=17.0
    while t<21.85:
        cues.append((t,'SE_SYS_CURSOR',.055,.10))
        t+=.055+.055*(t-17)**1.25
    for t in (26.1,28.3,30.4,33.25,33.8,34.35):
        cues.append((t,'SE_OBJ_BLOCK_BREAK',.26,.40))
        cues.append((t,'SE_PLY_HIT_BLOCK',.15,.28))
    for t in (26.1,28.3,30.4):
        cues.append((t+.035,'SE_PLY_LAND_WATER',.23,.28))
    for i in range(6):
        cues.append((33.25+i*.18,'SE_EMY_KAME_HIT_%d'%(i+1),.17,.24))
    for t in np.arange(24.8,31,.14): cues.append((float(t),'SE_PLY_FOOTNOTE',.08,.08))
    for t in np.arange(31,34.5,.27): cues.append((float(t),'SE_EMY_OLKP_FOOT',.13,.17))
    loaded={}
    # Las voces se mezclan en una pista propia para recortarlas y sincronizarlas sin duplicados.
    cues=[c for c in cues if not c[1].startswith('SE_VOC_') and c[1]!='SE_EMY_KOOPA_LAUGH']
    for t,name,dur,level in cues:
        key=(name,dur,level)
        if key not in loaded: loaded[key]=effect(name,dur,level)
        put(mix,loaded[key],t)
    speech=dialogue()
    sonido.guardar_wav(str(CACHE/'dialogos.wav'),speech)
    mix+=speech
    mix+=character_voices()
    peak=float(np.abs(mix).max())
    if peak>.78: mix*=.78/peak
    mix=fade(mix,.04)
    assert np.isfinite(mix).all() and np.abs(mix).max()<.99
    sonido.guardar_wav(str(CACHE/'mezcla.wav'),mix)
    (CACHE/'partitura.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('Pico mezcla: %.2f dBFS'%(20*np.log10(np.abs(mix).max())),flush=True)
    return CACHE/'mezcla.wav'


if __name__=='__main__':
    build()
