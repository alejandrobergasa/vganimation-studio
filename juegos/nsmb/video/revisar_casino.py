"""Auditoría de materiales y continuidad de todos los personajes del casino."""
from pathlib import Path
import sys
import json

import numpy as np
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import casino_3d as C
import casino_motion as M
import casino_render3d as R
import casino_assets

OUT=C.CACHE/'pulido'


def single(f,name,pose,frame,loop=False):
    a=f.actors[name];anim=a.anims[casino_assets.POSES[name][pose]]
    if loop: anim=M.Loop(anim)
    base=a.parts[0].model
    tris=base.triangles(M.Mixer(anim,frame),0)
    stack=base.last_stack;items=[(tris,base,None,0)]
    for part in a.parts[1:]:
        root=stack[part.attach] if part.attach is not None else np.eye(4)
        items.append((part.model.triangles(None,0,root=root),part.model,None,0))
    mesh=f.r.from_items(items,a.tex);mesh.xyz[:,:,1]-=mesh.xyz[:,:,1].min()
    return mesh


def textures(f):
    names=list(C.HEIGHT)
    sheet=Image.new('RGB',(864,404*6),(25,7,49))
    comparison=Image.new('RGB',(432,404*6),(25,7,49))
    manifest=[]
    for row,name in enumerate(names):
        a=f.actors[name]
        for part in a.parts:
            for mat in part.model.materials:
                if mat.tex:
                    pixels=a.tex.get(mat.tex,mat.pal)
                    assert pixels is not None and pixels[:,:,3].max()>0,(name,mat.name)
                manifest.append({'personaje':name,'modelo':part.model.name,'material':mat.name,
                                 'textura':mat.tex,'paleta':mat.pal,'espejo':[mat.flip_s,mat.flip_t],
                                 'repeticion':[mat.rep_s,mat.rep_t],'UV':[mat.sx,mat.sy],
                                 'caras_ocultas':[mat.cull_front,mat.cull_back]})
        mesh=single(f,name,'wait',0)
        camera=((0,9,34),(0,7,0),250 if name=='bowser' else 320)
        for col,yaw in enumerate((0,80,180,280)):
            im=f.r.frame([(mesh,(0,0,0),yaw,f.scales[name])],camera)
            sheet.paste(im,(col*216,row*404))
            ImageDraw.Draw(sheet).text((col*216+4,row*404+384),name+' '+str(yaw))
            im.save(OUT/('%s_%s.png'%(name,yaw)))
            if col==0:
                corrected=im
                flags=f.r.trepeats.copy();f.r.trepeats[:,2:4]=False
                broken=f.r.frame([(mesh,(0,0,0),yaw,f.scales[name])],camera)
                f.r.trepeats=flags
                comparison.paste(broken,(0,row*404));comparison.paste(corrected,(216,row*404))
                d=ImageDraw.Draw(comparison)
                d.text((4,row*404+384),name+' antes');d.text((220,row*404+384),name+' corregido')
    sheet.save(OUT/'texturas_todos_los_angulos.png')
    comparison.save(OUT/'comparacion_UV.png')
    (OUT/'materiales.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print('Materiales revisados:',len(manifest),'Vistas:',len(names)*4,flush=True)


def verify(f):
    report={'transiciones':[],'ciclos':[],'costuras':[],'raster':[]}
    # Regresión del error real: el texel -1 se refleja a 0 y el 4 al 3, en un eje de ancho 4.
    texture=np.zeros((1,2,4,4),np.uint8)
    for v in range(2):
        for u in range(4): texture[0,v,u]=(40+u*50,50+v*100,0,255)
    points=np.array([[[90,160,1],[108,220,1],[125,160,1]]],np.float32)
    cols=np.ones((1,3,3),np.float32);mat=np.array([0],np.int32)
    sizes=np.array([[4,2]],np.int32);flags=np.array([[True,True,True,True,False,True]])
    for u,expected in [(-1,0),(0,0),(3,3),(4,3),(7,0),(8,0)]:
        uv=np.full((1,3,2),0,np.float32);uv[:,:,0]=u;uv[:,:,1]=-1
        image=R.raster(points,uv,cols,mat,texture,sizes,flags)
        assert tuple(image[180,108])==(40+expected*50,50,0),(u,image[180,108])
    back=R.raster(points[:,::-1].copy(),uv,cols,mat,texture,sizes,flags)
    assert tuple(back[180,108])==(25,7,49),'Cara posterior visible'
    report['raster']=['Espejo UV positivo y negativo','Culling original de materiales']
    for name in C.HEIGHT:
        identities=[(name,i) for i in range(3 if name=='toad' else 6)] if name in ('toad','koopa') else [name]
        for identity in identities:
            for at,pose in f.motion.timeline(name,identity)[1:]:
                before=f.motion.mesh(name,identity,at-.0001)
                after=f.motion.mesh(name,identity,at+.0001)
                error=float(np.linalg.norm(before.xyz-after.xyz,axis=2).max()*f.scales[name])
                assert error<.05,(name,identity,at,error)
                report['transiciones'].append({'personaje':str(identity),'segundo':at,'pose':pose,'salto_unidades':error})
        for pose,anim_name in casino_assets.POSES[name].items():
            a=single(f,name,pose,0)
            b=single(f,name,pose,f.actors[name].anims[anim_name].num_frames-1)
            assert a.xyz.shape==b.xyz.shape and np.isfinite(b.xyz).all()
            delta=float(np.linalg.norm(a.xyz-b.xyz,axis=2).max()*f.scales[name])
            loop=pose in ('wait','walk','run','hold') and not(name=='koopa' and pose=='wait')
            report['ciclos'].append({'personaje':name,'pose':pose,'diferencia_extremos':delta,'bucle':loop})
            if loop:
                end=f.actors[name].anims[anim_name].num_frames-1+M.Loop.bridge
                before=single(f,name,pose,end-.0001,True)
                after=single(f,name,pose,.0001,True)
                seam=float(np.linalg.norm(before.xyz-after.xyz,axis=2).max()*f.scales[name])
                assert seam<.02,(name,pose,seam)
                report['costuras'].append({'personaje':name,'pose':pose,'salto_unidades':seam})
    # Continuidad de la trayectoria entre persecuciones y al comenzar el ataque de los Koopas.
    for at in [24.7,26.33,28.53,30.63,31]:
        a=f.chase_state(max(24.7,at-.0001))[1]
        b=f.chase_state(at+.0001)[1]
        assert np.linalg.norm(a-b)<.02,(at,a,b)
    (OUT/'verificacion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print('Transiciones continuas:',len(report['transiciones']),flush=True)
    print('Clips completos:',len(report['ciclos']),flush=True)
    return report


def strips(f):
    # Secuencias que incluyen cada clase de cambio de animación y los tres agarres.
    centers=[2.5,6.4,7.4,9,14,15.9,22.4,25.68,27.88,29.98,33.1,34.7]
    for batch in range(3):
        sheet=Image.new('RGB',(864,4*404),(25,7,49))
        for row,at in enumerate(centers[batch*4:(batch+1)*4]):
            for col,dt in enumerate((-.10,.01,.09,.20)):
                t=at+dt;im=f.frame(t);sheet.paste(im,(col*216,row*404))
                ImageDraw.Draw(sheet).text((col*216+4,row*404+384),'%.2f s'%t)
        sheet.save(OUT/('continuidad_%d.png'%(batch+1)))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    f=C.Film(False)
    verify(f);textures(f);strips(f)
    print(OUT,flush=True)


if __name__=='__main__': main()
