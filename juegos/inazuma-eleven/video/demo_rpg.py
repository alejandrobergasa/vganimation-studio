"""Ocho direcciones sobre el escenario real de Raimon, con seguimiento de cámara."""
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta/'valedores.toml').is_file():
        sys.path.insert(0,str(carpeta/'nucleo'))
        break
from valedores import rutas
sys.path.insert(0,rutas.motor_dir('inazuma-eleven'))
from motor import Video,Recursos,Recorrido,ActorDireccional


def construir(personaje='alega',personalizado=True,formato='vertical'):
    rec=Recursos();fondo=rec.escenario('mr01b01',pixeles_por_unidad=32)
    cx,cy=fondo.proyectar(0,-7)
    puntos=[(-32,0),(0,0),(23,23),(23,55),(0,78),(-32,78),(-55,55),(-55,23),(-32,0)]
    claves=[(i,cx+x,cy+y) for i,(x,y) in enumerate(puntos)]
    claves.append((8.6,cx-32,cy))
    actor=ActorDireccional(rec,personaje,Recorrido(claves),personalizado=personalizado)
    v=Video(formato=formato)
    p,escena=v.plano_rpg(8.6,fondo)
    escena.actor(actor,seguir=True)
    return v,fondo


if __name__=='__main__':
    v,f=construir()
    f.imagen.save(Path(rutas.trabajo('inazuma-eleven'))/'raimon-escenario-nativo.png')
    for i in range(8):v.frame(i+.5).save(Path(rutas.trabajo('inazuma-eleven'))/('direccion-%d.png'%i))
    print(v.renderizar('alega_ocho_direcciones_raimon.mp4'))
