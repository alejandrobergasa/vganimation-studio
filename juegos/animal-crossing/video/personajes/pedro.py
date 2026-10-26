"""Foto del usuario proyectada sobre el osezno cbr01 de la ROM."""
import os
import numpy as np
from PIL import Image
from motor import Asset, TexBank, build_mesh, draw_surface_texture, rutas


def cargar(rom, clips):
    asset=Asset(rom,'npc/model/24/29.nsbmd',['npc/model/24/29.nsbtx'],clips)
    cloth=next(p for p in rom.list('cloth/') if p.endswith('/cloth065.nsbtx'))
    asset.banks.insert(0,TexBank(rom.get(cloth)))
    path=os.path.join(rutas.personalizados('animal-crossing'),'pedro','cara_foto.png')
    image=Image.open(path).convert('RGBA')
    image=image.crop(image.getbbox())
    asset.photo=np.array(image.resize((64,64),Image.Resampling.LANCZOS))
    # UV de proyección en la pose de referencia. La misma topología se conserva al animar.
    asset.photo_uv={}
    asset.photo_mask={}
    for mat,p,uv,normals in build_mesh(asset.model):
        name=asset.model.materials[mat].name
        if name in ('e','m','b0'):
            if name=='b0':
                c=p.mean(axis=1)
                selected=(c[:,1]>1.10)&(c[:,2]>.04)&(np.abs(c[:,0])<.52)
            else:
                selected=np.ones(len(p),bool)
            coords=np.empty_like(uv)
            coords[...,0]=(p[...,0]+.72)/1.44*63
            coords[...,1]=(2.12-p[...,1])/1.34*63
            asset.photo_uv[mat]=coords[selected]
            asset.photo_mask[mat]=selected
    return asset


def dibujar_cara(canvas, asset, posed_mesh, world, view, proj, tint=(1,1,1)):
    surfaces=[(p[asset.photo_mask[mat]],asset.photo_uv[mat],n[asset.photo_mask[mat]])
              for mat,p,uv,n in posed_mesh if mat in asset.photo_uv]
    draw_surface_texture(canvas,asset.photo,surfaces,world,view,proj,tint)
