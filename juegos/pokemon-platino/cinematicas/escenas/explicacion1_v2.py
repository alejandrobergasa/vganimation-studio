"""EXPLICACIÓN 1 v2: EL PANA le explica a EL MARÍA cómo ha montado ALEGA el programa que hace los vídeos de Pokémon.

Sitio: cuarto con PC (interior 313). Mientras habla, cada paso del programa sale en un plano detalle con
gráficos reales del juego: ROM -> sprites -> mapas 3D -> personajes propios -> guion -> música.
Música de fondo: base de reguetón (dembow, 90 bpm) tocada con el soundfont de Platino
(trabajo/explicacion1/musica.py). Sin ella la escena se renderiza sin música.

Ejecutar desde cinematicas/:  python escenas/explicacion1_v2.py
"""
import glob
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..'))
sys.path.insert(0, os.path.join(AQUI, 'rewindlimbo2'))
from PIL import Image  # noqa
from motor import Escena, MapaReal  # noqa
from motor.recursos import RAIZ, SPR, CUSTOM, TRABAJO, SALIDA, CACHE, fuente, imagen, ventana_mensaje  # noqa
from comun import texto_img, escalar  # noqa

WAV = os.path.join(TRABAJO, 'explicacion1', 'base_dembow_v2.wav')
BPM = 90
BEAT = 60 / BPM                      # 0,667 s = 20 frames a 30 fps


# ---------------------------------------------------------------- planos detalle (gráficos del juego)
def _sp(ruta):
    return imagen(os.path.join(SPR, ruta))


def _mapa(carpeta, i):
    return imagen(os.path.join(SPR, 'personajes_mapa', carpeta, 'frame_%02d.png' % i))


def _custom(nombre, i):
    return imagen(os.path.join(CUSTOM, nombre, 'mapa', 'frame_%02d.png' % i))


def panel(lineas, dibujo, w=224, tipo=1):
    """Ventana del juego con título arriba (texto grande), un dibujo en medio y un pie."""
    f = fuente()
    assert f.ancho(lineas[0]) * 2 <= w - 30 and all(f.ancho(l) <= w - 30 for l in lineas), lineas
    h = 112
    v = ventana_mensaje(w, h, tipo)
    t = texto_img(lineas[0], k=2)
    v.alpha_composite(t, ((w - t.width) // 2, 8))
    v.alpha_composite(dibujo, ((w - dibujo.width) // 2, 34 + (54 - dibujo.height) // 2))
    if len(lineas) > 1:
        p = texto_img(lineas[1])
        v.alpha_composite(p, ((w - p.width) // 2, h - 22))
    return v


def fila(imgs, hueco=4, k=1):
    imgs = [escalar(i, k) if k > 1 else i for i in imgs]
    W = sum(i.width for i in imgs) + hueco * (len(imgs) - 1)
    out = Image.new('RGBA', (W, max(i.height for i in imgs)), (0, 0, 0, 0))
    x = 0
    for i in imgs:
        out.alpha_composite(i, (x, out.height - i.height))
        x += i.width + hueco
    return out


def dib_rom():
    sprites = [_mapa(n, 4) for n in ('090_pl_boy01c_heroe_andar_correr', '000_babyboy1', '001_babygirl1')]
    caja = [imagen(os.path.join(SPR, 'objetos', 'iconos', '328_mt01.png')),
            imagen(os.path.join(SPR, 'objetos', 'iconos', '004_poke_ball.png'))]
    return fila(caja + sprites, hueco=3, k=1)


def dib_mapa():
    m = MapaReal('aromaflor', hora=12)
    # recorte con árboles, camino y arco: se localiza mirando salida/_panel_mapa.png
    r = m.fondo.crop(CORTE_MAPA)
    return r.resize((r.width, r.height), Image.NEAREST)


def dib_personajes():
    return fila([_custom('el_maria', i) for i in (4, 5, 6)] + [_custom('el_pana', i) for i in (4, 5, 6)], hueco=2)


def dib_codigo():
    c = Image.new('RGBA', (190, 52), (0, 0, 0, 0))
    for i, l in enumerate(('ANDAR   MIRAR   SALTAR', 'DIALOGO   MUSICA   FUNDIDO', 'UN GUION = UNA CINEMATICA')):
        c.alpha_composite(texto_img(l, (40, 40, 56), (200, 200, 216)), (4, 4 + i * 16))
    return c


def dib_musica():
    notas = [imagen(os.path.join(SPR, 'efectos_ataques', '29', 'celda_%02d.png' % i))
             for i in (0, 1, 2)]
    return fila(notas, hueco=14, k=1)


CORTE_MAPA = (130, 972, 290, 1026)       # se ajusta tras ver el plano


# ---------------------------------------------------------------- escena
mapa = MapaReal(land=313, hora=12)
esc = Escena(mapa)
alega = esc.personaje('el_pana', 7, 4, mira='arriba')        # ALEGA (EL PANA)
maria = esc.personaje('el_maria', 4, 8, mira='arriba')       # EL MARÍA
esc.camara_fija(5, 5)

ALEGA = 'ALEGA: '
MARIA = 'MARIA: '
f_ = fuente()


def d(texto, espera=50):
    for l in texto.split('\n'):
        assert f_.ancho(l) <= 200, (f_.ancho(l), l)
    return esc.dialogo(texto, espera=espera)


def plano(nombre, lineas, dibujo, y=8):
    p = panel(lineas, dibujo)
    return esc.mostrar(nombre, p, x=None, y=y, frames=10, efecto='zoom', orden=5)


esc.hacer(esc.fundido(entrada=True, frames=20), maria.andar('arriba', 4))
esc.hacer(maria.andar('derecha', 1))
esc.hacer(alega.mirar(maria), maria.mirar(alega))
esc.esperar(10)
esc.hacer(d('MARIA: PANA, ¿cómo hace Alega\nlos vídeos de Pokémon?'))
esc.hacer(alega.emocion('!', frames=20), alega.saltar(altura=5, frames=8))
esc.hacer(d('PANA: Fácil, María. Todo lo\nsaca del ROM de Platino.'))
esc.hacer(plano('p_rom', ('TODO SALE DEL ROM', 'POKEMON PLATINO'), dib_rom()))
esc.hacer(d('PANA: Alega hizo un programa\nque saca sprites y sonido.'))
esc.hacer(esc.ocultar('p_rom', frames=8, efecto='fundido'))
esc.hacer(d('MARIA: ¿Y los escenarios?\n¿Los dibuja a mano?'))
esc.hacer(plano('p_mapa', ('MAPAS 3D REALES', 'ARBOLES Y EDIFICIOS'), dib_mapa()))
esc.hacer(d('PANA: Qué va. Son modelos 3D\ndel juego, renderizados.'))
esc.hacer(d('PANA: Y su programa esconde a\nla gente tras los árboles.'))
esc.hacer(esc.ocultar('p_mapa', frames=8, efecto='fundido'))
esc.hacer(d('MARIA: ¿Y yo? ¡Que salgo yo\nen el vídeo!'))
esc.hacer(maria.saltar(altura=5, frames=8), maria.emocion('!', frames=20))
esc.hacer(plano('p_pj', ('SUS SPRITES', 'RECOLOREADOS DESDE FOTOS'), dib_personajes()))
esc.hacer(d('PANA: Te hizo a partir de un\nsprite del juego y fotos.'))
esc.hacer(esc.ocultar('p_pj', frames=8, efecto='fundido'))
esc.hacer(alega.mirar('arriba'))
esc.hacer(d('PANA: Luego Alega escribe el\nguion: andar, hablar, saltar...'))
esc.hacer(plano('p_guion', ('EL GUION', 'UNA ESCENA POR ARCHIVO'), dib_codigo()))
esc.hacer(d('PANA: Cada paso es una orden.\nLe da y sale el vídeo.'))
esc.hacer(esc.ocultar('p_guion', frames=8, efecto='fundido'))
esc.hacer(alega.mirar(maria))
esc.hacer(d('MARIA: ¿Y la música? ¡Suena\nmuy bien!'))
esc.hacer(plano('p_mus', ('LA MUSICA', 'SOUNDFONT DE PLATINO'), dib_musica()))
esc.hacer(d('PANA: Esa base de reguetón la\ntoca el soundfont de Platino.'))
esc.hacer(esc.ocultar('p_mus', frames=8, efecto='fundido'))
esc.hacer(d('MARIA: ¡Pues a bailar, que\nAlega se lo ha currado!'))
esc.hacer(esc.accion(lambda: print('FRAME BAILE', esc.t)))
for _ in range(4):
    esc.hacer(alega.saltar(altura=6, frames=10), maria.saltar(altura=6, frames=10))
    esc.esperar(10)
esc.hacer(alega.mirar(maria), maria.mirar(alega))
for _ in range(4):
    esc.hacer(alega.saltar(altura=6, frames=10), maria.saltar(altura=6, frames=10))
    esc.esperar(10)
esc.esperar(10)
esc.hacer(esc.fundido(entrada=False, frames=40))

if __name__ == '__main__':
    salida = os.path.join(SALIDA, 'explicacion1_v2')
    esc.exportar(salida, audio_base=WAV if os.path.exists(WAV) else None)
