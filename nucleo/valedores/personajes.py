"""Importación de personajes adaptados desde fotos; la generación corresponde al agente.

Un manifiesto conserva identidad, referencia de la ROM y revisión visual. El lector
no convierte una fotografía en dibujo ni inventa poses: carga las ya generadas.
"""
import json
from pathlib import Path

from PIL import Image

from . import rutas
from .video_nds import Clip


PERFILES = {
    'inazuma-eleven': ('pixel_art', 'sprites RPG pequeños de spr/char; cabeza, cuerpo y paletas'),
    'phoenix-wright-3': ('anime', 'bustos y poses anime de data.bin a resolución DS'),
    'pokemon-platino': ('pixel_art', 'sprites de mapa; combate usa su propio formato'),
    'nsmb': ('textura_3d', 'modelo nativo con textura facial sobre sus UV'),
    'mkds': ('textura_3d', 'piloto nativo con textura facial sobre sus UV'),
    'animal-crossing': ('textura_3d', 'vecino o jugador nativo con textura facial sobre sus UV'),
    'mario-party-ds': ('textura_3d', 'modelo HBDF nativo con textura facial sobre sus UV'),
    'super-mario-64-ds': ('textura_3d', 'modelo BMD nativo con textura facial sobre sus UV'),
    'profesor-layton': ('anime', 'personaje dibujado en el estilo de los clips ARC'),
}


def perfil(juego):
    modo, referencia = PERFILES[juego]
    return {'modo': modo, 'referencia': referencia}


def _archivo(base, nombre):
    p = (base / nombre).resolve()
    if not p.is_relative_to(base.resolve()):
        raise ValueError('El asset debe estar dentro de la carpeta del personaje')
    return p


def manifiesto(juego, nombre, exigir_revision=True, permitir_foto=False):
    p = Path(nombre)
    if p.suffix != '.json':
        slug = rutas.proyecto_activo()
        if not slug or p.name != str(nombre) or str(nombre) in ('.', '..'):
            raise ValueError('Activa un proyecto o indica la ruta del personaje.json')
        p = Path(rutas.ENTRADA) / slug / 'personajes' / nombre / 'personaje.json'
    with p.open(encoding='utf-8') as f:
        m = json.load(f)
    if m.get('version') != 1 or m.get('juego') != juego:
        raise ValueError('Versión o juego del personaje incompatible')
    if m.get('modo') not in ('pixel_art', 'anime', 'textura_3d', 'foto_directa'):
        raise ValueError('Modo de personaje no válido')
    if m['modo'] == 'foto_directa' and not permitir_foto:
        raise ValueError('Una foto directa requiere una petición explícita y permitir_foto=True')
    if not m.get('referencia_identidad') or not m.get('referencia_rom'):
        raise ValueError('Documenta la foto de identidad y el asset de referencia de la ROM')
    if exigir_revision and m.get('revisado') is not True:
        raise ValueError('Abre y revisa el personaje junto al asset nativo antes de usarlo')
    return p, m


def cargar(juego, nombre, animacion='quieto', exigir_revision=True, permitir_foto=False):
    """Devuelve un Clip listo para Plano.sprite; lienzo y escala estables entre poses."""
    p, m = manifiesto(juego, nombre, exigir_revision, permitir_foto)
    if m['modo'] == 'textura_3d':
        raise ValueError('Una textura facial debe aplicarse al modelo con textura(); no es un sprite')
    try:a=m['animaciones'][animacion]
    except KeyError as exc:raise ValueError('Falta la pose o animación solicitada: '+animacion) from exc
    # Una pose complementaria puede vivir en otra hoja sin reemplazar la aprobada.
    cfg=dict(m)
    for clave in ('imagen','rejilla','lienzo','ajuste','tamano_visible','colores','cajas'):
        if clave in a:cfg[clave]=a[clave]
    m=cfg
    with Image.open(_archivo(p.parent, m['imagen'])) as im:
        atlas = im.convert('RGBA')
    cols, filas = m.get('rejilla', [1, 1])
    if not all(isinstance(n,int) and n > 0 for n in (cols,filas)):
        raise ValueError('El atlas debe contener celdas iguales en una rejilla exacta')
    if (atlas.width%cols or atlas.height%filas) and not m.get('ajustar_rejilla') and not m.get('cajas'):
        raise ValueError('El atlas debe contener celdas iguales en una rejilla exacta')
    cajas=m.get('cajas') or [(round(x*atlas.width/cols),round(y*atlas.height/filas),
                            round((x+1)*atlas.width/cols),round((y+1)*atlas.height/filas))
                           for y in range(filas) for x in range(cols)]
    if len(cajas)!=cols*filas or any(len(c)!=4 or not 0<=c[0]<c[2]<=atlas.width or not 0<=c[1]<c[3]<=atlas.height for c in cajas):
        raise ValueError('Cajas del atlas fuera de límites')
    celdas = [atlas.crop(c) for c in cajas]
    pixel = m['modo']=='pixel_art'
    muestreo=m.get('muestreo','vecino' if pixel else 'suave')
    if muestreo not in ('vecino','suave'):
        raise ValueError('Muestreo de personaje no válido')
    filtro = Image.Resampling.NEAREST if muestreo=='vecino' else Image.Resampling.LANCZOS
    if pixel or m.get('alfa_binario'):
        # Importación a la resolución y alfa binario del juego; no estiliza una foto.
        for im in celdas:
            im.putalpha(im.getchannel('A').point(lambda a:255 if a>=128 else 0))
    tamano = tuple(m['lienzo'])
    if len(tamano)!=2 or any(not isinstance(n,int) or not 0<n<=4096 for n in tamano):
        raise ValueError('Lienzo de personaje no válido')
    cajas = [im.getbbox() for im in celdas]
    if any(c is None for c in cajas):
        raise ValueError('El atlas contiene una celda vacía')
    if m.get('ajuste')=='pies':
        vw,vh=m.get('tamano_visible',tamano)
        if not 0<vw<=tamano[0] or not 0<vh<=tamano[1]:
            raise ValueError('El tamaño visible debe caber en el lienzo')
        escala=min(vw/max(c[2]-c[0] for c in cajas),vh/max(c[3]-c[1] for c in cajas))
        frames=[]
        for im,c in zip(celdas,cajas):
            pieza=im.crop(c)
            pieza=pieza.resize((max(1,round(pieza.width*escala)),max(1,round(pieza.height*escala))),filtro)
            frame=Image.new('RGBA',tamano)
            frame.alpha_composite(pieza,((tamano[0]-pieza.width)//2,tamano[1]-pieza.height))
            frames.append(frame)
    else:
        frames=[im.resize(tamano,filtro) for im in celdas]
    if m.get('paleta'):
        colores=m['paleta']
        if not 1<=len(colores)<=256 or any(len(c)!=3 or any(not isinstance(v,int) or not 0<=v<=255 for v in c) for c in colores):
            raise ValueError('Paleta RGB de personaje no válida')
        pal=Image.new('P',(1,1))
        pal.putpalette([v for i in range(256) for v in colores[i%len(colores)]])
        nuevos=[]
        for im in frames:
            convertido=im.convert('RGB').quantize(palette=pal,dither=Image.Dither.NONE).convert('RGBA')
            convertido.putalpha(im.getchannel('A'));nuevos.append(convertido)
        frames=nuevos
    elif m.get('colores'):
        n=m['colores']
        if not isinstance(n,int) or not 2<=n<=256:
            raise ValueError('La paleta debe tener entre 2 y 256 colores')
        # Una sola paleta para todos los frames evita parpadeos de color.
        tira=Image.new('RGBA',(tamano[0]*len(frames),tamano[1]))
        for i,im in enumerate(frames):tira.paste(im,(i*tamano[0],0))
        tira=tira.quantize(colors=n,method=Image.Quantize.FASTOCTREE,dither=Image.Dither.NONE).convert('RGBA')
        frames=[tira.crop((i*tamano[0],0,(i+1)*tamano[0],tamano[1])) for i in range(len(frames))]
    indices=a['frames']
    if not indices or any(not isinstance(i,int) or not 0<=i<len(frames) for i in indices):
        raise ValueError('Animación fuera de la rejilla del atlas')
    elegidos=[frames[i] for i in indices]
    if a.get('reflejar'):
        elegidos=[im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) for im in elegidos]
    clip=Clip(elegidos,a.get('duraciones',[]),a.get('repetir',True))
    clip.procedencia=m
    return clip


def textura(juego, nombre, exigir_revision=True):
    """Textura UV ya preparada, para reemplazar el material facial del modelo nativo."""
    p,m=manifiesto(juego,nombre,exigir_revision)
    if m['modo']!='textura_3d' or not m.get('material'):
        raise ValueError('Se necesita modo textura_3d y el nombre real del material facial')
    with Image.open(_archivo(p.parent,m['imagen'])) as im:
        return m['material'],im.convert('RGBA')
