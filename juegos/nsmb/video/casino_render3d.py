"""Rasterizador de escena conjunta: perspectiva, profundidad, texturas DS y luz común."""
from pathlib import Path
import sys
import math

import numpy as np
from numba import njit
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'/'nsmb'))
import nitro3d as N

W,H=216,384


@njit(cache=True)
def project_clip(camera_points,uv,colors,mats,focal):
    """Recortar contra el plano cercano antes de proyectar, también para suelo y paredes grandes."""
    count=len(camera_points)
    points_out=np.zeros((count*2,3,3),np.float32)
    uv_out=np.zeros((count*2,3,2),np.float32)
    color_out=np.zeros((count*2,3,3),np.float32)
    mats_out=np.zeros(count*2,np.int32)
    used=0
    for k in range(count):
        source=np.zeros((3,8),np.float32)
        source[:,:3]=camera_points[k]
        source[:,3:5]=uv[k]
        source[:,5:8]=colors[k]
        polygon=np.zeros((5,8),np.float32)
        n=0
        for j in range(3):
            current=source[j];previous=source[(j+2)%3]
            inside=current[2]>=.25;before=previous[2]>=.25
            if inside!=before:
                q=(.25-previous[2])/(current[2]-previous[2])
                polygon[n]=previous+(current-previous)*q;n+=1
            if inside:
                polygon[n]=current;n+=1
        if n<3: continue
        for j in range(1,n-1):
            for corner,index in enumerate((0,j,j+1)):
                p=polygon[index];iz=1/p[2]
                points_out[used,corner,0]=108+p[0]*focal*iz
                points_out[used,corner,1]=195-p[1]*focal*iz
                points_out[used,corner,2]=iz
                uv_out[used,corner]=p[3:5]
                color_out[used,corner]=p[5:8]
            mats_out[used]=mats[k];used+=1
    return points_out[:used],uv_out[:used],color_out[:used],mats_out[:used]


@njit(cache=True)
def raster(vertices, uv, colors, mats, textures, sizes, repeats):
    image=np.zeros((H,W,3),np.uint8)
    image[:,:,0]=25;image[:,:,1]=7;image[:,:,2]=49
    depth=np.zeros((H,W),np.float32)
    for k in range(len(vertices)):
        a,b,c=vertices[k,0],vertices[k,1],vertices[k,2]
        if a[2]<=0 or b[2]<=0 or c[2]<=0: continue
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<.005: continue
        mi=mats[k]
        front=den<0
        if (front and repeats[mi,4]) or (not front and repeats[mi,5]): continue
        minx=max(0,int(math.floor(min(a[0],b[0],c[0]))))
        maxx=min(W-1,int(math.ceil(max(a[0],b[0],c[0]))))
        miny=max(0,int(math.floor(min(a[1],b[1],c[1]))))
        maxy=min(H-1,int(math.ceil(max(a[1],b[1],c[1]))))
        tw,th=sizes[mi]
        for y in range(miny,maxy+1):
            for x in range(minx,maxx+1):
                w0=((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/den
                w1=((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/den
                w2=1-w0-w1
                if w0<-.00001 or w1<-.00001 or w2<-.00001: continue
                z=w0*a[2]+w1*b[2]+w2*c[2]
                if z<=depth[y,x]: continue
                p0=w0*a[2]/z;p1=w1*b[2]/z;p2=w2*c[2]/z
                u=int(math.floor(p0*uv[k,0,0]+p1*uv[k,1,0]+p2*uv[k,2,0]))
                v=int(math.floor(p0*uv[k,0,1]+p1*uv[k,1,1]+p2*uv[k,2,1]))
                if repeats[mi,0]:
                    period=u//tw;u=u%tw
                    if repeats[mi,2] and period%2: u=tw-1-u
                else: u=min(tw-1,max(0,u))
                if repeats[mi,1]:
                    period=v//th;v=v%th
                    if repeats[mi,3] and period%2: v=th-1-v
                else: v=min(th-1,max(0,v))
                tex=textures[mi,v,u]
                if tex[3]<128: continue
                for j in range(3):
                    light=p0*colors[k,0,j]+p1*colors[k,1,j]+p2*colors[k,2,j]
                    image[y,x,j]=min(255,max(0,int(tex[j]*light)))
                depth[y,x]=z
    return image


@njit(cache=True)
def trace_particles(origins,velocities,environment,gravity=38.):
    """Primer choque de cada gota con la geometría real del casino."""
    count=len(origins)
    result=np.zeros((count,7),np.float64)
    for i in range(count):
        old=origins[i].copy(); found=False
        for step in range(1,151):
            t=step/60.
            new=origins[i]+velocities[i]*t
            new[1]-=.5*gravity*t*t
            direction=new-old
            for tri in environment:
                e1=tri[1]-tri[0];e2=tri[2]-tri[0]
                h=np.cross(direction,e2);det=np.dot(e1,h)
                if abs(det)<1e-9: continue
                inv=1/det;s=old-tri[0];u=inv*np.dot(s,h)
                if u<0 or u>1: continue
                q=np.cross(s,e1);v=inv*np.dot(direction,q)
                if v<0 or u+v>1: continue
                distance=inv*np.dot(e2,q)
                if distance<0 or distance>1: continue
                pos=old+distance*direction
                norm=np.cross(e1,e2);norm/=max(1e-8,np.sqrt(np.dot(norm,norm)))
                if np.dot(norm,direction)>0: norm=-norm
                result[i,0]=(step-1+distance)/60.
                result[i,1:4]=pos+norm*.025
                result[i,4:7]=norm
                found=True;break
            if found: break
            old=new
        if not found:
            result[i,0]=2.5
            result[i,1:4]=old
            result[i,4:7]=np.array([0.,1.,0.])
    return result


class Mesh:
    def __init__(self,xyz,uv,normal,color,mats):
        self.xyz=np.asarray(xyz,np.float32)
        self.uv=np.asarray(uv,np.float32)
        self.normal=np.asarray(normal,np.float32)
        self.color=np.asarray(color,np.float32)
        self.mats=np.asarray(mats,np.int32)


class Renderer:
    def __init__(self):
        self.tex=[];self.sizes=[];self.repeats=[];self.lookup={}

    def material(self,texture,repeat=False):
        a=np.asarray(texture,dtype=np.uint8)
        if a.shape[2]==3: a=np.concatenate((a,np.full((*a.shape[:2],1),255,np.uint8)),2)
        index=len(self.tex)
        canvas=np.zeros((256,256,4),np.uint8)
        canvas[:a.shape[0],:a.shape[1]]=a
        self.tex.append(canvas);self.sizes.append((a.shape[1],a.shape[0]))
        self.repeats.append((repeat,repeat,False,False,False,False))
        return index

    def solid(self,rgb):
        return self.material(np.array([[(*rgb,255)]],np.uint8))

    def from_items(self,items,texlook):
        xyz=[];uv=[];normals=[];color=[];mats=[]
        for tris,model,pattern,frame in items:
            for mi,tri in tris:
                m=model.materials[mi]
                texname,palname=m.tex,m.pal
                if pattern is not None:
                    selected=pattern.sample(m.name,frame)
                    if selected: texname,palname=selected
                key=(id(model),mi,texname,palname)
                if key not in self.lookup:
                    a=texlook.get(texname,palname) if texname else None
                    if texname and a is None:
                        raise ValueError('Textura sin resolver: %s / %s / %s'%(model.name,texname,palname))
                    if a is None: a=np.full((1,1,4),255,np.uint8)
                    a=a.copy();a[:,:,3]=(a[:,:,3]*m.alpha).astype(np.uint8)
                    idx=self.material(a)
                    self.repeats[idx]=(m.rep_s,m.rep_t,m.flip_s,m.flip_t,m.cull_front,m.cull_back)
                    self.lookup[key]=idx
                    if (id(model),mi) not in self.lookup: self.lookup[id(model),mi]=idx
                mats.append(self.lookup[key])
                xyz.append([v[:3] for v in tri]);uv.append([(v[3]*m.sx,v[4]*m.sy) for v in tri])
                normals.append([v[6] for v in tri]);color.append([(1,1,1)]*3)
        return Mesh(xyz,uv,normals,color,mats)

    def seal(self):
        self.textures=np.asarray(self.tex,np.uint8)
        self.tsizes=np.asarray(self.sizes,np.int32)
        self.trepeats=np.asarray(self.repeats,np.bool_)

    def frame(self,instances,camera):
        if len(self.tex)!=len(self.textures): self.seal()
        eye,target,focal=camera
        eye=np.asarray(eye,float);target=np.asarray(target,float)
        forward=target-eye;forward/=np.linalg.norm(forward)
        right=np.cross(forward,(0,1,0));right/=np.linalg.norm(right)
        up=np.cross(right,forward)
        view=np.array([right,up,forward])
        allp=[];allu=[];allc=[];allm=[]
        light=np.array([-.4,.85,.6]);light/=np.linalg.norm(light)
        for mesh,position,yaw,scale in instances:
            a=math.radians(yaw);s,c=math.sin(a),math.cos(a)
            rot=np.array([[c,0,s],[0,1,0],[-s,0,c]],np.float32)
            p=(mesh.xyz@rot.T)*scale+np.array(position)
            pc=(p-eye)@view.T
            normals=mesh.normal@rot.T
            nl=np.linalg.norm(normals,axis=2,keepdims=True)
            normals=normals/np.maximum(nl,1e-6)
            brightness=.72+.28*np.maximum(0,normals@light)
            colors=mesh.color*brightness[:,:,None]
            allp.append(pc);allu.append(mesh.uv);allc.append(colors);allm.append(mesh.mats)
        screen,uvs,colours,materials=project_clip(np.concatenate(allp).astype(np.float32),
                                                np.concatenate(allu),np.concatenate(allc).astype(np.float32),
                                                np.concatenate(allm),float(focal))
        arr=raster(screen,uvs,colours,materials,self.textures,self.tsizes,self.trepeats)
        return Image.fromarray(arr)


def mesh_triangles(tris,material,uvs=None):
    p=np.array(tris,np.float32)
    normals=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]);normals/=np.maximum(1e-8,np.linalg.norm(normals,axis=1,keepdims=True))
    normals=np.repeat(normals[:,None,:],3,1)
    return Mesh(p,np.zeros((len(p),3,2),np.float32) if uvs is None else uvs,
                normals,np.ones_like(p),np.full(len(p),material,np.int32))


def disc(material,radius=1,y=0,segments=20):
    tris=[];uvs=[]
    for i in range(segments):
        a=i*2*math.pi/segments;b=(i+1)*2*math.pi/segments
        pts=[(0,y,0),(radius*math.cos(a),y,radius*math.sin(a)),(radius*math.cos(b),y,radius*math.sin(b))]
        tris.append(pts);uvs.append([(.5,.5),(.5+.5*math.cos(a),.5+.5*math.sin(a)),(.5+.5*math.cos(b),.5+.5*math.sin(b))])
    mesh=mesh_triangles(tris,material,np.array(uvs,np.float32))
    mesh.normal[:]=(0,1,0)
    return mesh


def sphere(material,radius=1):
    v=[(0,radius,0),(radius,0,0),(0,0,radius),(-radius,0,0),(0,0,-radius),(0,-radius,0)]
    tris=[]
    for i in range(4):
        tris.append([v[0],v[1+i],v[1+(i+1)%4]])
        tris.append([v[5],v[1+(i+1)%4],v[1+i]])
    return mesh_triangles(tris,material)


def splat(position,normal,radius,material,seed):
    rng=np.random.default_rng(seed);normal=np.array(normal,float)
    tangent=np.cross(normal,(1,0,0) if abs(normal[0])<.8 else (0,0,1));tangent/=np.linalg.norm(tangent)
    other=np.cross(normal,tangent)
    p=np.array(position);tris=[]
    radii=rng.uniform(.5,1,12)*radius
    for i in range(12):
        a=i*math.pi/6;b=(i+1)*math.pi/6
        tris.append([p,p+(tangent*math.cos(a)+other*math.sin(a))*radii[i],
                      p+(tangent*math.cos(b)+other*math.sin(b))*radii[(i+1)%12]])
    return mesh_triangles(tris,material)
