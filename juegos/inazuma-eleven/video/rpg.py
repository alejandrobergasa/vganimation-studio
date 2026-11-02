"""Escenarios nativos, cámara en píxeles de juego y actores con ocho orientaciones."""
import math

from PIL import Image

from valedores.modelos_video_nds import lector

DIRECCIONES=('este','sureste','sur','suroeste','oeste','noroeste','norte','noreste')


def direccion(dx,dy):
    if not math.isfinite(dx) or not math.isfinite(dy) or (dx==dy==0):
        raise ValueError('La dirección necesita un vector finito distinto de cero')
    return DIRECCIONES[int(math.floor(math.atan2(dy,dx)/(math.pi/4)+.5))%8]


class Recorrido:
    """Claves (segundo,x,y) en píxeles de escenario; los tramos quietos mantienen la mirada."""
    def __init__(self, claves, mirada='sur'):
        self.claves=[tuple(float(n) for n in c) for c in claves]
        if len(self.claves)<2 or any(len(c)!=3 or not all(math.isfinite(n) for n in c) for c in self.claves):
            raise ValueError('El recorrido necesita dos o más claves finitas (t,x,y)')
        if self.claves[0][0]!=0 or any(b[0]<=a[0] for a,b in zip(self.claves,self.claves[1:])) or mirada not in DIRECCIONES:
            raise ValueError('Tiempos o mirada inicial del recorrido no válidos')
        self.mirada=mirada

    def estado(self,t):
        t=max(0,t);ultima=self.mirada
        for a,b in zip(self.claves,self.claves[1:]):
            dx,dy=b[1]-a[1],b[2]-a[2]
            mueve=abs(dx)+abs(dy)>1e-8
            d=direccion(dx,dy) if mueve else ultima
            if t<b[0]:
                u=max(0,(t-a[0])/(b[0]-a[0]))
                return (a[1]+dx*u,a[2]+dy*u,d,mueve,t-a[0])
            ultima=d
        return (*self.claves[-1][1:],ultima,False,0)


class ActorDireccional:
    def __init__(self,recursos,nombre,recorrido,personalizado=False,**opciones):
        self.recorrido=recorrido
        self.clips={}
        for d in DIRECCIONES:
            for accion in ('quieto','caminar'):
                self.clips[d,accion]=(recursos.personaje_personalizado(nombre,accion+'_'+d) if personalizado
                    else recursos.personaje(nombre,direccion=d,accion=accion,**opciones))
        tamanos={im.size for c in self.clips.values() for im in c.imagenes}
        if len(tamanos)!=1:
            raise ValueError('Todas las direcciones deben compartir lienzo y escala')

    def frame(self,t):
        x,y,d,mueve,fase=self.recorrido.estado(t)
        return self.clips[d,'caminar' if mueve else 'quieto'].frame(fase)

    def posicion(self,t):
        return self.recorrido.estado(t)[:2]


class FondoRPG:
    """Rasterización del escenario 3D real, a la escala lógica del sprite; no usa el minimapa."""
    def __init__(self,recursos,nombre='mr01b01',pixeles_por_unidad=32,separar_materiales=()):
        if not 1<=pixeles_por_unidad<=32:
            raise ValueError('Escala nativa de escenario fuera de límites')
        self.pixeles_por_unidad=pixeles_por_unidad
        g=lector();modelos=[];self.origenes=[]
        for n in recursos.buscar('data_iz/model/obj/sp/mr_nsbmd.pkb::'):
            if n.count('::')!=1:continue
            d=recursos.datos(n)
            if (nombre+'m').encode() not in d:continue
            for m in g.Nitro(d).models:
                if m.name.startswith(nombre+'m'):
                    modelos.append(m);self.origenes.append(n)
        if not modelos:raise ValueError('No hay modelos nativos para el escenario '+nombre)
        texturas={a.tex for m in modelos for a in m.materials if a.tex}
        bancos=[]
        for n in recursos.buscar('data_iz/model/obj/sp/mr_nsbtx.pkb::'):
            if n.count('::')!=1:continue
            d=recursos.datos(n)
            if not any(k.encode() in d for k in texturas):continue
            nit=g.Nitro(d);bancos.append(nit);self.origenes.append(n)
        lookup=g.TexLookup(*bancos)
        for m in modelos:
            for a in m.materials:
                if a.tex and lookup.get(a.tex,a.pal) is None:raise ValueError('Falta textura de escenario: '+a.tex)
        self.ortho=lambda x,y,z:(x,z*.7-y*.8)
        items=[(m.triangles(None,0),m,None,0) for m in modelos]
        rgba,self.origen=g.render_items(items,lookup,scale=pixeles_por_unidad,shade=False,ortho=self.ortho)
        self.imagen=Image.fromarray(rgba)
        self.objetos={}
        if separar_materiales:
            fondo=[]
            for tris,m,pat,frame in items:
                fondo.append(([(mi,vs) for mi,vs in tris if m.materials[mi].tex not in separar_materiales],m,pat,frame))
                for material in separar_materiales:
                    seleccion=[(mi,vs) for mi,vs in tris if m.materials[mi].tex==material]
                    if seleccion:self.objetos.setdefault(material,[]).append((seleccion,m,pat,frame))
            rgba,_=g.render_items(fondo,lookup,scale=pixeles_por_unidad,shade=False,ortho=self.ortho,
                                  size=self.imagen.size,origin=self.origen)
            self.imagen=Image.fromarray(rgba)
        self._texturas=lookup

    def suelo_bajo_objeto(self,material,desplazamiento=(0,96),muestra=None):
        """Reconstruye huecos alfa bajo objetos con suelo contiguo del mismo escenario.

        Algunos mapas omiten el suelo tapado por coches. Solo rellena píxeles
        transparentes dentro del rectángulo de cada mitad de la geometría aislada.
        No pinta superficies ni reutiliza la carrocería.
        """
        for lado in (-1,1):
            im,a,p=self.objeto(material,lambda vs:sum(v[0] for v in vs)*lado>0)
            x,y=round(p[0]-a[0])-12,round(p[1]-a[1])-12
            ancho,alto=im.width+24,im.height+24
            caja=(x,y,x+ancho,y+alto)
            dx,dy=desplazamiento
            suelo=self.imagen.crop((x+dx,y+dy,x+dx+ancho,y+dy+alto))
            if muestra is not None:
                pieza=self.imagen.crop(muestra)
                suelo=Image.new('RGBA',(ancho,alto))
                for ty in range(0,alto,pieza.height):
                    for tx in range(0,ancho,pieza.width):suelo.paste(pieza,(tx,ty))
            # La ROM también deja una silueta negra opaca bajo la carrocería.
            import numpy as np
            region=np.asarray(self.imagen.crop(caja))
            hueco=Image.fromarray(np.where((region[:,:,3]==0)|(region[:,:,:3].max(2)<8),255,0).astype('uint8'))
            self.imagen.paste(suelo,(x,y),hueco)

    def objeto(self,material,selector=lambda vs:True,giro=0):
        """Aísla geometría nativa por material y región, sin copiar suelo ni retocar texturas.

        Devuelve imagen y ancla en coordenadas del fondo. El giro es en radianes
        alrededor del centro de la pieza, conservando escala y proyección.
        """
        items=[];vertices=[]
        for tris,m,p,f in self.objetos[material]:
            elegidos=[(mi,vs) for mi,vs in tris if selector(vs)]
            items.append((elegidos,m,p,f))
            vertices.extend(v for _,vs in elegidos for v in vs)
        if not vertices:raise ValueError('La selección de geometría está vacía')
        cx=(min(v[0] for v in vertices)+max(v[0] for v in vertices))/2
        cz=(min(v[2] for v in vertices)+max(v[2] for v in vertices))/2
        c,s=math.cos(giro),math.sin(giro)
        transformados=[]
        for tris,m,p,f in items:
            nuevos=[]
            for mi,vs in tris:
                nuevos.append((mi,[(cx+(v[0]-cx)*c+(v[2]-cz)*s,v[1],
                                   cz-(v[0]-cx)*s+(v[2]-cz)*c,*v[3:]) for v in vs]))
            transformados.append((nuevos,m,p,f))
        rgba,origen=lector().render_items(transformados,self._texturas,scale=self.pixeles_por_unidad,
                                         shade=False,ortho=self.ortho)
        im=Image.fromarray(rgba)
        px,py=self.ortho(cx,0,cz)
        ancla=(origen[0]+px*self.pixeles_por_unidad,origen[1]+py*self.pixeles_por_unidad)
        return im,ancla,self.proyectar(cx,cz)

    def proyectar(self,x,z,y=0):
        px,py=self.ortho(x,y,z)
        return (self.origen[0]+px*self.pixeles_por_unidad,self.origen[1]+py*self.pixeles_por_unidad)


class EscenaRPG:
    """Mismo lienzo lógico para fondo y personajes; una única ampliación entera al final."""
    def __init__(self,fondo,tamano=(1080,1920),escala_salida=None):
        self.fondo=fondo.imagen if hasattr(fondo,'imagen') else fondo.convert('RGBA')
        self.tamano=tamano
        self.escala=escala_salida or math.ceil(max(tamano[0]/256,tamano[1]/192))
        if not isinstance(self.escala,int) or not 1<=self.escala<=32:
            raise ValueError('La ampliación de píxeles debe ser entera, entre 1 y 32')
        self.vista=tuple(math.ceil(n/self.escala) for n in tamano)
        if any(v>f for v,f in zip(self.vista,self.fondo.size)):
            raise ValueError('El escenario es menor que la vista de cámara')
        self.actores=[];self.seguir=None;self.centro=(self.fondo.width/2,self.fondo.height/2)
        self.oclusiones=[]

    def oclusion(self,imagen,posicion):
        """Pieza nativa en primer plano, en las mismas coordenadas lógicas del fondo."""
        self.oclusiones.append((imagen.convert('RGBA'),posicion))

    def actor(self,actor,seguir=False):
        self.actores.append(actor)
        if seguir:self.seguir=actor
        return actor

    def frame(self,t):
        vw,vh=self.vista
        cx,cy=self.seguir.posicion(t) if self.seguir else (self.centro(t) if callable(self.centro) else self.centro)
        x=round(max(0,min(self.fondo.width-vw,cx-vw/2)))
        y=round(max(0,min(self.fondo.height-vh,cy-vh*.60)))
        im=self.fondo.crop((x,y,x+vw,y+vh))
        for a in sorted(self.actores,key=lambda a:a.posicion(t)[1]):
            if hasattr(a,'visible') and not a.visible(t):continue
            px,py=a.posicion(t);sprite=a.frame(t)
            ax,ay=getattr(a,'ancla',(sprite.width/2,sprite.height))
            im.alpha_composite(sprite,(round(px-x-ax),round(py-y-ay)))
        for pieza,(px,py) in self.oclusiones:
            im.alpha_composite(pieza,(round(px-x),round(py-y)))
        # Nada de cover() separado para mapa y actor: se amplía la composición completa.
        return im.resize((vw*self.escala,vh*self.escala),Image.Resampling.NEAREST).crop((0,0,*self.tamano))
