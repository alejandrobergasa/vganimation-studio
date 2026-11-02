"""Personajes de Mario Party DS: actores 3D con sus animaciones nativas y caras de foto.

`personaje(rec, 'mario', foto=..., ...)` devuelve un `Actor3D` listo para una `Escena3D`, con las 27
animaciones ANMF del juego por nombre (`ANIMACIONES`), mezcla entre clips y boca/parpadeo animados.
El modelo `data/pNN_<personaje>_LZ.bin::00019.bin` es el personaje completo, con 23 objetos.

La segunda parte (`preparar`, `clip`, `poses`...) es la vía anterior, con poses a mano en un sprite
ortográfico; se conserva para los proyectos que ya la usan.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image

from valedores import rutas
from valedores.anmf_party import AnimacionParty
from valedores.caras_foto import CaraFoto, Hitos, poner_cara
from valedores.caras_video import atlas_cara, vestir
from valedores.escena3d import Actor3D
from valedores.modelos_video_nds import ModeloParty, VistaModelo
from valedores.video_nds import Clip

CLAVES = {'mario': 'p01_mario', 'luigi': 'p02_luigi', 'wario': 'p03_wario', 'yoshi': 'p04_yoshi',
          'peach': 'p05_peach', 'daisy': 'p06_daisy', 'waluigi': 'p07_waluigi', 'toad': 'p08_kinopio'}

# Miembros ANMF de cada personaje: ('p', n) en pNN_<personaje>_LZ.bin y ('b', n) en bmap_pNNmotion.bin.
# Los nombres describen lo que se ve al dibujarlas (la ROM no los guarda): consulta `hoja_animaciones`.
ANIMACIONES = {
    'quieto': ('p', 0), 'andar': ('p', 1), 'voltereta': ('p', 2), 'correr': ('p', 3), 'esprintar': ('p', 4),
    'girar': ('p', 5), 'caer_de_cabeza': ('p', 6), 'mirar_alrededor': ('p', 7), 'dudar': ('p', 8),
    'encogido': ('p', 9), 'celebrar': ('p', 10), 'tropezar': ('p', 11), 'caer_de_frente': ('p', 12),
    'aterrizar': ('p', 13), 'volar': ('p', 14), 'boca_abajo': ('p', 15), 'temblar': ('p', 16),
    'de_espaldas': ('p', 17), 'mirar_arriba': ('p', 18),
    'saludar': ('b', 0), 'paso': ('b', 1), 'preparado': ('b', 2), 'girar_cabeza': ('b', 3),
    'esperar_tablero': ('b', 4), 'saltar_alegre': ('b', 5), 'asentir': ('b', 6), 'inclinarse': ('b', 7),
}

# Rectángulo de la cara en cada cabeza, medido sobre el modelo en reposo.
AJUSTE_CARA = {
    'mario':   dict(ojos=11.04, barbilla=9.0, frente=12.2, ancho=2.05),
    'luigi':   dict(ojos=12.18, barbilla=9.9, frente=13.0, ancho=1.45),
    'wario':   dict(ojos=10.8, barbilla=7.4, frente=12.0, ancho=2.5, alfa_x=1.7, ancho_liso=1.9),
    'yoshi':   dict(ojos=14.2, barbilla=10.3, frente=15.8, ancho=2.5),
    'peach':   dict(ojos=15.1, barbilla=13.55, frente=16.2, ancho=1.2),
    'daisy':   dict(ojos=14.9, barbilla=13.45, frente=16.0, ancho=1.25),
    'waluigi': dict(ojos=19.6, barbilla=16.1, frente=20.5, ancho=1.55, alfa_x=1.7),
    'toad':    dict(ojos=6.8, barbilla=5.0, frente=7.7, ancho=2.0),
}


def _origen_animacion(nombre_personaje, grupo, n):
    clave = CLAVES[nombre_personaje]
    return ('data/%s_LZ.bin::%05d.bin' % (clave, n) if grupo == 'p'
            else 'data/bmap_%smotion.bin::%05d.bin' % (clave[:3], n))


def animaciones(rec, nombre_personaje):
    """{nombre: AnimacionParty} del personaje."""
    if nombre_personaje not in CLAVES:
        raise ValueError('Personaje desconocido; hay: ' + ', '.join(CLAVES))
    return {n: AnimacionParty(rec.datos(_origen_animacion(nombre_personaje, g, i)), n)
            for n, (g, i) in ANIMACIONES.items()}


def personaje(rec, nombre, foto=None, hitos=None, gorra=True, pelo=None, brillo=1.0, contraste=1.0,
              ajuste=None, aplanar=1.0, sombra=True, cara=None, **actor):
    """Actor de un personaje del juego, con la cara de `foto` si se indica.

    `hitos`: `Hitos(ojo_i, ojo_d, boca, barbilla)` en píxeles; sin ellos se detectan con OpenCV.
    `gorra=False` quita la gorra y usa `pelo` (RGB 0..1, None = calvo) en la parte alta de la cabeza.
    Devuelve el actor; si tiene foto, `actor.cara` anima boca y expresión (`hablar`, `expresion`...).
    """
    if nombre not in CLAVES:
        raise ValueError('Personaje desconocido; hay: ' + ', '.join(CLAVES))
    # Modelo propio de este actor: la cara cambia sus texturas y la malla de su cabeza.
    modelo = ModeloParty(rec.datos('data/%s_LZ.bin::00019.bin' % CLAVES[nombre]))
    a = Actor3D(modelo, animaciones=animaciones(rec, nombre), nombre=nombre, sombra=sombra, **actor)
    a.cara = None
    if foto is not None or cara is not None:
        cara = cara or CaraFoto(foto, hitos, brillo=brillo, contraste=contraste, nombre=nombre)
        a.foto = cara
        a.cara = poner_cara(a, cara, {**AJUSTE_CARA[nombre], **(ajuste or {})}, gorra=gorra, pelo=pelo, aplanar=aplanar)
    a.anim('quieto')
    return a


def hoja_animaciones(rec, nombre='mario', columnas=6, tamano=(150, 170), angulo=0.55):
    """Hoja de contactos con todas las animaciones, para elegir por lo que se ve."""
    from PIL import ImageDraw
    from valedores.escena3d import Camara, Escena3D
    nombres = list(ANIMACIONES)
    hoja = Image.new('RGB', (tamano[0] * columnas, tamano[1] * len(nombres)), (40, 48, 74))
    a = personaje(rec, nombre)
    alto = a.altura()
    d = alto * 2.1
    esc = Escena3D(tamano=tamano, fondo=(70, 86, 130), camara=Camara((math.sin(angulo) * d, alto * .7, math.cos(angulo) * d), (0, alto * .48, 0), 36))
    esc.actor(a)
    dib = ImageDraw.Draw(hoja)
    for k, n in enumerate(nombres):
        an = a.animaciones[n]
        a.linea = []
        a.anim(n, mezcla=0)
        for j in range(columnas):
            hoja.paste(esc.frame(an.duracion * j / columnas).convert('RGB'), (j * tamano[0], k * tamano[1]))
        dib.text((3, k * tamano[1] + 2), '%s (%.1f s)' % (n, an.duracion), fill=(255, 255, 160))
    return hoja


def retrato(cara, tamano=48, borde=(255, 255, 255)):
    """Icono cuadrado, a resolución DS, de una `CaraFoto`: para diálogos y marcadores."""
    a = cara.imagen('neutra')
    n = a.shape[0]
    x0, y0, x1, y1 = int(.14 * n), int(.14 * n), int(.86 * n), int(.98 * n)
    im = Image.fromarray((a[y0:y1, x0:x1] * 255).astype(np.uint8)).resize((tamano - 4, tamano - 4), Image.Resampling.BILINEAR)
    salida = Image.new('RGBA', (tamano, tamano), (*borde, 255))
    salida.paste(im, (2, 2))
    return salida


# ------------------------------------------------------------------- vía anterior (sprite ortográfico)

# Objetos del esqueleto HBDF (mismo orden en todos los jugadores de Mario Party DS).
CARA, BRAZO_I, BRAZO_D, CUERPO, PIERNA_I, PIERNA_D = 0, 4, 8, 10, 14, 18


def cargar(rec, clave):
    """Carga el modelo principal y devuelve (modelo, material de cabeza, material de ojos)."""
    origen = 'data/%s_LZ.bin::00019.bin' % clave
    modelo = ModeloParty(rec.datos(origen))
    cabeza = next((m for m in modelo.materials if m.tex and 'head' in m.tex.lower()), None)
    ojos = next((m for m in modelo.materials if m.tex and 'eye' in m.tex.lower()), None)
    if cabeza is None:
        raise ValueError('El modelo no tiene material de cabeza: ' + clave)
    return modelo, cabeza, ojos


def parametros_cara(modelo, cabeza):
    """Rectángulo de proyección de la cara a partir de la malla frontal del material."""
    mi = next(i for i, m in enumerate(modelo.materials) if m is cabeza)
    tris = [t for i, t in modelo.tris if i == mi]
    if not tris:
        raise ValueError('El material de cabeza no tiene geometría')
    pts = np.array([v[:3] for t in tris for v in t])
    front = np.array([v[:3] for t in tris
                      if sum(v[2] for v in t) / 3 > np.percentile(pts[:, 2], 70) for v in t])
    if not len(front):
        raise ValueError('No hay triángulos frontales en la cabeza')
    fx0, fx1 = front[:, 0].min(), front[:, 0].max()
    fy0, fy1 = front[:, 1].min(), front[:, 1].max()
    fz0, fz1 = front[:, 2].min(), front[:, 2].max()
    alto = fy1 - fy0
    return dict(mx=0.85 * max(abs(fx0), abs(fx1)), my0=fy0 + 0.03 * alto,
                my1=fy0 + 0.52 * alto, zmin=fz0 + 0.10 * (fz1 - fz0))


def preparar(rec, clave, foto, hitos, escala=4, brillo=1.25):
    """Modelo con la cara aplicada y listo para posar.

    El `VistaModelo` se encuadra con la pose de reposo del personaje (brazos bajados), no con
    la T-pose del HBDF: así el cuerpo ocupa el lienzo y no queda pequeño entre los brazos.
    """
    modelo, cabeza, ojos = cargar(rec, clave)
    opciones = parametros_cara(modelo, cabeza)
    atlas = atlas_cara(modelo, cabeza.name, foto, hitos, pelo=None, escala=escala,
                       tener_pelo=False, brillo=brillo, **opciones)
    rot, tras = poses('quieto', 1)[0]
    modelo.tris = modelo.pose(rot, tras)
    vista = VistaModelo(modelo, modelo, giro=0.0, tamano=(512, 512))
    vestir(vista, cabeza.name, atlas, escala=escala, ocultar=(ojos.name,) if ojos else (), sin_gorra=False)
    return modelo, vista


def _pose_ciclo(modo, fase):
    """Rotaciones y traslaciones de los objetos para un instante del ciclo."""
    rot, tras = {}, {}
    # Brazos bajados: es la pose base de todos los ciclos.
    rot[BRAZO_I] = [0.0, 0.0, -1.05]
    rot[BRAZO_D] = [0.0, 0.0, 1.05]
    if modo == 'quieto':
        tras[CUERPO] = (0.0, 0.025 * math.sin(fase), 0.0)
        rot[CARA] = (0.03 * math.sin(fase + 0.5), 0.0, 0.02 * math.sin(fase * 0.5))
    elif modo == 'hablar':
        tras[CUERPO] = (0.0, 0.02 * math.sin(fase * 2), 0.0)
        rot[CARA] = (0.05 * math.sin(fase * 2), 0.0, 0.04 * math.sin(fase))
        rot[BRAZO_D] = [0.10 * math.sin(fase), 0.0, 1.15 + 0.25 * math.sin(fase * 2)]
        rot[BRAZO_I] = [0.0, 0.0, -1.05]
    elif modo == 'andar':
        s, c = math.sin(fase), math.cos(fase)
        rot[PIERNA_I] = (0.36 * s, 0.0, 0.0)
        rot[PIERNA_D] = (-0.36 * s, 0.0, 0.0)
        rot[BRAZO_I] = [0.0, 0.0, -1.05 - 0.12 * s]
        rot[BRAZO_D] = [0.0, 0.0, 1.05 + 0.12 * s]
        rot[CUERPO] = (0.025, 0.0, 0.0)
        tras[CUERPO] = (0.0, 0.035 * abs(c), 0.0)
        rot[CARA] = (0.02 * math.sin(fase * 2), 0.0, 0.0)
    elif modo == 'correr':
        s, c = math.sin(fase), math.cos(fase)
        rot[PIERNA_I] = (0.62 * s, 0.0, 0.0)
        rot[PIERNA_D] = (-0.62 * s, 0.0, 0.0)
        rot[BRAZO_I] = [0.0, 0.0, -1.05 - 0.28 * s]
        rot[BRAZO_D] = [0.0, 0.0, 1.05 + 0.28 * s]
        rot[CUERPO] = (0.14, 0.0, 0.04 * s)
        tras[CUERPO] = (0.0, 0.06 * abs(c), 0.0)
        rot[CARA] = (-0.04, 0.0, 0.03 * s)
    elif modo == 'enfado':
        rot[BRAZO_I] = [0.0, 0.0, -0.82]
        rot[BRAZO_D] = [0.0, 0.0, 0.82]
        rot[CUERPO] = (0.06, 0.0, 0.0)
        rot[CARA] = (-0.06, 0.0, 0.05 * math.sin(fase * 6))
        tras[CUERPO] = (0.0, 0.02 * math.sin(fase * 6), 0.0)
    elif modo == 'encogerse':
        rot[BRAZO_I] = [0.0, 0.0, -0.55]
        rot[BRAZO_D] = [0.0, 0.0, 0.55]
        rot[CUERPO] = (0.04, 0.0, 0.06)
        rot[CARA] = (0.05, 0.0, -0.08)
        tras[CUERPO] = (0.0, -0.03, 0.0)
    else:
        raise ValueError('Modo de animación desconocido: ' + modo)
    return ({i: tuple(v) for i, v in rot.items()}, tras)


def poses(modo, n=12):
    return [_pose_ciclo(modo, 2 * math.pi * i / n) for i in range(n)]


def ancla(vista):
    """Punto de anclaje en la base del personaje, como fracción del lienzo de `VistaModelo`."""
    b = vista.frame(0).getbbox()
    if b is None:
        raise ValueError('El personaje no generó píxeles')
    return (0.5, b[3] / vista.tamano[1])


def clip_preparado(modelo, vista, modo, n=12, fps=12, ancla_personaje=None):
    """Clip de n poses sobre un modelo ya vestido; conserva el lienzo completo de VistaModelo."""
    rest = modelo.tris
    imagenes = []
    for rot, tras in poses(modo, n):
        modelo.tris = modelo.pose(rot, tras)
        imagenes.append(vista.frame(0))
    modelo.tris = rest
    clip = Clip(imagenes, [1 / fps] * n, repetir=True)
    clip.ancla = ancla_personaje or ancla(vista)
    return clip


def clip(rec, clave, foto, hitos, modo, n=12, escala=4, fps=12):
    """Clip RGBA de n poses del personaje, con la cara ya aplicada y su anclaje de pies."""
    modelo, vista = preparar(rec, clave, foto, hitos, escala=escala)
    return clip_preparado(modelo, vista, modo, n=n, fps=fps)
