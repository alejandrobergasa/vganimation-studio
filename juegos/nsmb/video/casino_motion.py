"""Clips continuos y mezclas de esqueleto para la cinemática. Evaluación sin estado previo."""
from collections import OrderedDict
import math

import numpy as np
from scipy.spatial.transform import Rotation

import casino_assets


def ease(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)


def rigid(r):
    if r is None: return np.eye(3)
    u,_,v=np.linalg.svd(r)
    if np.linalg.det(u@v)<0: u[:,-1]*=-1
    return u@v


def rotation_mix(a,b,q):
    qa=Rotation.from_matrix(rigid(a)).as_quat()
    qb=Rotation.from_matrix(rigid(b)).as_quat()
    if qa@qb<0: qb=-qb
    quat=qa*(1-q)+qb*q
    quat/=max(np.linalg.norm(quat),1e-8)
    return Rotation.from_quat(quat).as_matrix()


class Mixer:
    def __init__(self,a,fa,b=None,fb=0,weight=1):
        self.a,self.fa,self.b,self.fb,self.weight=a,fa,b,fb,weight

    def sample(self,i,frame,t,r,s):
        ta,ra,sa=self.a.sample(i,self.fa,t,r,s)
        if self.b is None:
            return ta,rigid(ra),sa
        tb,rb,sb=self.b.sample(i,self.fb,t,r,s)
        q=self.weight
        ta=np.zeros(3) if ta is None else ta;tb=np.zeros(3) if tb is None else tb
        sa=np.ones(3) if sa is None else sa;sb=np.ones(3) if sb is None else sb
        return ta*(1-q)+tb*q,rotation_mix(ra,rb,q),sa*(1-q)+sb*q


class Loop:
    """El tramo de cierre vuelve al primer fotograma sin reiniciar bruscamente las articulaciones."""
    bridge=5.

    def __init__(self,animation):
        self.animation=animation
        self.end=animation.num_frames-1

    def sample(self,i,frame,t,r,s):
        if frame<=self.end: return self.animation.sample(i,frame,t,r,s)
        q=ease((frame-self.end)/self.bridge)
        return Mixer(self.animation,self.end,self.animation,0,q).sample(i,0,t,r,s)


class Motion:
    def __init__(self,actors,renderer,hits):
        self.actors,self.r,self.hits=actors,renderer,hits
        self.cache=OrderedDict()

    @staticmethod
    def is_loop(name,pose):
        return pose in ('wait','walk','run','hold') and not(name=='koopa' and pose=='wait')

    def clip(self,name,pose):
        animation=self.actors[name].anims[casino_assets.POSES[name][pose]]
        return Loop(animation) if self.is_loop(name,pose) else animation

    def timeline(self,name,identity):
        # Cada entrada marca el inicio de una acción; las anteriores se mezclan durante 160 ms.
        if name=='mario':
            segments=[(0,'walk'),(2.3,'wait'),(6,'walk'),(6.4,'bet'),(7.4,'wait'),
                      (14,'mad'),(15.5,'wait'),(22.4,'shock'),(24.7,'run')]
            for i,(hit,_) in enumerate(self.hits):
                segments.extend([(hit-.42,'hold'),(hit-.12,'mad'),(hit+.23,'run')])
            segments.extend([(31,'run'),(32.2,'mad'),(33.1,'shock'),(34.7,'dead')])
        elif name=='luigi':
            segments=[(0,'walk'),(2.5,'shock'),(4.3,'wait'),(22.4,'fear')]
        elif name=='peach':
            segments=[(0,'wait'),(15.9,'spin'),(17,'wait'),(24.7,'shock')]
        elif name=='bowser':
            segments=[(0,'wait'),(9,'laugh'),(14,'wait')]
        elif name=='toad':
            i=identity[1];hit=self.hits[i][0]
            segments=[(0,'wait'),(hit-1.25,'run'),(hit-.42,'wait')]
        elif name=='koopa':
            i=identity[1];strike=33.25+i*.18
            segments=[(0,'walk'),(31+i*.075+1.9,'wait'),(strike-.15,'attack'),
                      (strike+.20,'recover'),(strike+.60,'wait')]
        ordered=[]
        for start,pose in sorted(segments):
            if ordered and ordered[-1][1]==pose: continue
            ordered.append((start,pose))
        return ordered

    def frame_number(self,name,pose,clock):
        a=self.actors[name]
        anim=a.anims[casino_assets.POSES[name][pose]]
        end=anim.num_frames-1
        if name=='bowser' and pose=='laugh':
            # Volver por la misma trayectoria elimina el salto del fotograma 69 al 30.
            return 30+39*(.5-.5*math.cos(math.tau*clock/1.6))
        if self.is_loop(name,pose):
            return (max(0,clock)*48)%max(1,end+Loop.bridge)
        rate=85 if name=='mario' and pose=='mad' and 24<getattr(self,'scene_time',0)<31 else 48
        return min(end,max(0,clock)*rate)

    def evaluate(self,name,identity,t):
        self.scene_time=t
        segments=self.timeline(name,identity)
        index=max(i for i,(start,_) in enumerate(segments) if start<=t)
        start,pose=segments[index]
        fb=self.frame_number(name,pose,t-start)
        anim_b=self.clip(name,pose)
        if index and t-start<.16:
            previous,old_pose=segments[index-1]
            fa=self.frame_number(name,old_pose,start-previous)
            anim_a=self.clip(name,old_pose)
            weight=ease((t-start)/.16)
            return Mixer(anim_a,fa,anim_b,fb,weight),(old_pose,round(fa,4),pose,round(fb,4),round(weight,5)),pose
        return Mixer(anim_b,fb),(pose,round(fb,4)),pose

    def mesh(self,name,identity,t):
        a=self.actors[name]
        mixer,key,pose=self.evaluate(name,identity,t)
        pattern=None;pframe=0
        if name in ('mario','luigi'):
            prefix='L_' if name=='luigi' else ''
            pattern=a.patterns.get(prefix+('tx_bkdwn' if pose=='dead' else 'tx_wait'))
            if pattern:
                pframe=(t*60)%max(1,pattern.num_frames)
        eyes=tuple((n,pattern.sample(n,pframe)) for n in pattern.tracks) if pattern else ()
        key=(name,key,eyes)
        if key in self.cache:
            mesh=self.cache.pop(key);self.cache[key]=mesh;return mesh
        base=a.parts[0].model
        tris=base.triangles(mixer,0)
        stack=base.last_stack
        items=[(tris,base,pattern,pframe)]
        for part in a.parts[1:]:
            anchor=stack[part.attach] if part.attach is not None else np.eye(4)
            items.append((part.model.triangles(None,0,root=anchor),part.model,pattern,pframe))
        mesh=self.r.from_items(items,a.tex)
        mesh.xyz[:,:,1]-=mesh.xyz[:,:,1].min()
        self.cache[key]=mesh
        if len(self.cache)>768: self.cache.popitem(last=False)
        return mesh
