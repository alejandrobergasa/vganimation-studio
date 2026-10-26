"""FORMIGAL. Une los vídeos casaformigal y fiestaformigal (buzon/).

Acto 1 (casa): cuatro colegas en el piso. GRIS come patatas y juega con un cochecito; VERDE descubre que
ya no quedan nuggets «porque no hay macarrones con tomate», abre la nevera («aquí tenemos birra») y
pregunta dónde están los espaguetis o las lasañas.
Acto 2 (fiesta de après-ski, de noche): GAFAS (gorro, gafas de sol y braga roja) y ROJO (chaqueta roja con
capucha) entre la multitud: «menudo campo de nabos», «¡Formigal!», «¡tala, tala!», «¡ocho pavos!» y «primo,
quítate ya las gafas».
(Transcripción hecha con Whisper; las frases dudosas se han dejado como suenan.)

Ejecutar desde cinematicas/:  python escenas/formigal.py
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..'))
sys.path.insert(0, os.path.join(AQUI, 'rewindlimbo2'))
from motor import Escena, MapaReal  # noqa
from motor.recursos import CACHE, SALIDA, fuente, ventana_mensaje  # noqa
from dibujo import Lienzo, ROJO, PAPEL, MADERA, PLATA, NEGRO  # noqa
from comun import texto_img  # noqa

BLANCO = ((250, 250, 250), (226, 230, 236), (196, 202, 212), (150, 158, 172))
LATA = ((236, 168, 96), (204, 120, 56), (156, 82, 40), (104, 52, 30))
MORADO = ((140, 120, 232), (96, 72, 200), (64, 44, 150), (40, 28, 96))
PATATA = ((255, 226, 120), (240, 190, 70), (200, 140, 48), (140, 90, 36))


def titulo(lineas):
    f = fuente()
    w = max(f.ancho(l) for l in lineas) * 2 + 56
    h = 28 * len(lineas) + 12
    v = ventana_mensaje((w + 7) // 8 * 8, (h + 7) // 8 * 8, 1)
    for i, l in enumerate(lineas):
        t = texto_img(l, None, None, 2)
        v.alpha_composite(t, ((v.width - t.width) // 2, 8 + i * 28))
    return v


# V2: en la fiesta suena la canción del vídeo original tocada con el banco de Platino (trabajo/formigal).
V2 = os.environ.get('FORMIGAL_V2') == '1'
MARCAS = {}


# ---------------------------------------------------------------- gráficos propios
def nevera(abierta=False):
    """Nevera baja de cocina, 20x26. Abierta enseña las latas (el interior naranja del vídeo)."""
    c = Lienzo(20, 26)
    c.forma(lambda d: d.rectangle((1, 2, 18, 24), fill=255), BLANCO)
    if abierta:
        c.plano(lambda d: d.rectangle((3, 4, 16, 22), fill=255), (255, 190, 120), (120, 70, 40))
        for y in (9, 16):
            c.plano(lambda d, y=y: d.rectangle((3, y, 16, y), fill=255), (255, 240, 220))
            for x in (4, 8, 12):
                c.forma(lambda d, x=x, y=y: d.rectangle((x, y - 4, x + 2, y - 1), fill=255), LATA)
        c.forma(lambda d: d.polygon([(18, 3), (19, 5), (19, 23), (18, 24)], fill=255), BLANCO)
    else:
        c.plano(lambda d: d.rectangle((2, 11, 17, 11), fill=255), (150, 158, 172))
        c.plano(lambda d: d.rectangle((15, 4, 16, 8), fill=255), (130, 138, 152))
        c.plano(lambda d: d.rectangle((15, 14, 16, 18), fill=255), (130, 138, 152))
    return c.img


def mesa():
    """Mesa blanca con patatas fritas rojas y una botella, 28x22."""
    c = Lienzo(28, 22)
    c.forma(lambda d: d.rectangle((1, 9, 26, 13), fill=255), BLANCO)
    c.forma(lambda d: d.rectangle((3, 14, 5, 20), fill=255), PLATA)
    c.forma(lambda d: d.rectangle((22, 14, 24, 20), fill=255), PLATA)
    c.forma(lambda d: d.polygon([(4, 3), (11, 3), (10, 9), (5, 9)], fill=255), ROJO)
    for x in (5, 7, 9):
        c.plano(lambda d, x=x: d.rectangle((x, 0, x + 1, 4), fill=255), PATATA[1], (140, 90, 36))
    c.forma(lambda d: d.rectangle((18, 2, 21, 9), fill=255), ((200, 228, 250), (150, 190, 232), (110, 150, 200), (80, 110, 160)))
    c.plano(lambda d: d.rectangle((19, 0, 20, 2), fill=255), (60, 90, 190), (30, 40, 90))
    return c.img


def cochecito():
    c = Lienzo(10, 7)
    c.forma(lambda d: d.rectangle((1, 2, 8, 4), fill=255), MORADO)
    c.forma(lambda d: d.rectangle((3, 0, 6, 2), fill=255), MORADO)
    c.pixeles([(2, 5), (3, 5), (6, 5), (7, 5)], (20, 20, 28))
    return c.img


def vaso():
    """Cono de papel de la fiesta (8x10)."""
    c = Lienzo(8, 10)
    c.forma(lambda d: d.polygon([(0, 0), (7, 0), (5, 9), (2, 9)], fill=255), BLANCO)
    c.plano(lambda d: d.polygon([(2, 3), (5, 3), (4, 7), (3, 7)], fill=255), (50, 50, 60))
    return c.img


def signo(txt):
    return texto_img(txt, (255, 255, 255), (60, 60, 80), 2)


def d(texto, espera=50):
    """Diálogo con comprobación de ancho (26 caracteres por línea, 2 líneas)."""
    for l in texto.split('\n'):
        if len(l) > 26:
            print('LINEA LARGA (%d): %s' % (len(l), l))
    assert len(texto.split('\n')) <= 2, 'demasiadas líneas: ' + texto
    return esc.dialogo(texto, espera=espera)


# ---------------------------------------------------------------- mapas y reparto
casa = MapaReal(land=313)                      # cuarto de suelo de madera
calle = MapaReal('jubileo', hora=22)           # avenida de noche: la fiesta

esc = Escena(casa)
fri = esc.objeto(nevera(False), 5, 3)
mes = esc.objeto(mesa(), 7, 5)
coche = esc.objeto(cochecito(), 7, 5)
gris = esc.personaje('maria_gris', 8, 5, mira='izquierda')
verde = esc.personaje('chini_verde', 4, 6, mira='derecha')
esc.camara_fija(6, 5)

# Fiesta: se colocan al cambiar de mapa
gafas = esc.personaje('chini_gafas', 46, 14, mira='abajo')
rojo = esc.personaje('maria_rojo', 47, 14, mira='abajo')
GENTE = [(44, 12, 'skierm'), (46, 12, 'skierw'), (49, 11, 'skierw'), (48, 13, 'skierm'), (44, 14, 'skierw'),
         (45, 15, 'skierm'), (48, 15, 'skierw'), (49, 14, 'skierm'), (46, 16, 'skierm'), (47, 16, 'skierw'),
         (45, 17, 'skierw'), (49, 17, 'skierm'), (44, 10, 'skierm'), (48, 10, 'skierw')]
for p in (gafas, rojo):
    p.visible = False
multitud = []
for x, y, s in GENTE:
    p = esc.personaje(s, x, y, mira='abajo')
    p.visible = False
    multitud.append(p)


def saltan(alt=5, fr=8):
    return [p.saltar(altura=alt, frames=fr) for p in multitud + [gafas, rojo]]


# ---------------------------------------------------------------- ACTO 1: la casa
esc.hacer(esc.musica('SEQ_TOWN01_D', volumen=0.45))
esc.hacer(esc.fundido(entrada=True, frames=20), coche.mover(0, -9, 1))
esc.hacer(esc.mostrar('titulo', titulo(['FORMIGAL']), efecto='zoom', frames=8))
esc.esperar(70)
esc.hacer(esc.ocultar('titulo', frames=8, efecto='fundido'))
esc.esperar(6)
esc.hacer(d('MARÍA: Mira, con el\ncochecito, ahí.'), coche.mover(-14, 0, 20), gris.mirar('izquierda'))
esc.hacer(coche.mover(14, 0, 20), esc.sonido('SEQ_SE_DP_SELECT', volumen=0.4))
esc.hacer(gris.saltar(altura=4, frames=8), d('MARÍA: Otro nugget.', espera=40))
esc.hacer(verde.andar('derecha', 1))
esc.hacer(verde.mirar(gris), d('CHINI: Ya se acabaron\nlos nuggets.'))
esc.hacer(gris.emocion('!', frames=22), gris.saltar(altura=5, frames=8))
esc.hacer(d('CHINI: Porque no hay\nmacarrones con tomate.', espera=55))
esc.hacer(gris.mirar('abajo'))
esc.hacer(d('MARÍA: Abre la nevera,\nque se ve lo que hay.', espera=55))
esc.hacer(verde.andar('arriba', 1), gris.mirar(verde))
esc.hacer(verde.mirar('arriba'))
esc.esperar(10)
esc.hacer(fri.posar(nevera(True)), esc.sonido('SEQ_SE_DP_DOOR_OPEN', volumen=0.6))
esc.hacer(verde.saltar(altura=4, frames=8))
esc.hacer(d('CHINI: Aquí tenemos\nbirra.', espera=50))
esc.hacer(gris.saltar(altura=5, frames=8), gris.emocion('!', frames=20))
esc.hacer(d('MARÍA: ¿Dónde están los\nespaguetis o lasañas?', espera=55))
esc.hacer(verde.mirar(gris))
esc.hacer(d('CHINI: Por gusto no se\nle dice.', espera=50))
esc.hacer(d('CHINI: Por gusto no es\nbirra.', espera=50))
esc.esperar(14)
esc.hacer(esc.parar_musica(frames=25))
esc.hacer(esc.fundido(entrada=False, frames=25))

# ---------------------------------------------------------------- ACTO 2: la fiesta
esc.hacer(*[o.desaparecer() for o in (fri, mes, coche, gris, verde)])
esc.hacer(esc.cambiar_mapa(calle, fija=(46, 14)))
esc.hacer(*[p.aparecer() for p in multitud + [gafas, rojo]])
if V2:
    esc.hacer(esc.accion(lambda: MARCAS.update(fiesta=esc.t)))      # la canción del vídeo entra aquí (trabajo/formigal/montaje.py)
else:
    esc.hacer(esc.musica('SEQ_SLOT', volumen=0.5))
esc.hacer(esc.fundido(entrada=True, frames=20))
esc.hacer(esc.tenir_pantalla((40, 255, 120), 0.08, 12))
esc.hacer(esc.mostrar('lugar', titulo(['ESA NOCHE...']), y=24, efecto='fundido', frames=8))
esc.esperar(55)
esc.hacer(esc.ocultar('lugar', frames=8, efecto='fundido'))
esc.hacer(gafas.mirar(rojo), rojo.mirar(gafas))
esc.hacer(d('CHINI: Menudo campo de\nnabos.', espera=50))
esc.hacer(multitud[3].saltar(altura=4, frames=8), multitud[4].saltar(altura=4, frames=8))
esc.hacer(d('CHINI: No ya le habría\nhablado a un atleti.', espera=55))
esc.hacer(rojo.saltar(altura=5, frames=8), rojo.emocion('!', frames=20))
esc.hacer(gafas.llevar(vaso(), dx=-10, dy=2))
esc.hacer(gafas.saltar(altura=6, frames=8), esc.destello((60, 255, 140), 10, 0.5))
esc.hacer(d('CHINI: ¡FORMIGAL!', espera=45), *saltan(5, 8))
esc.hacer(esc.tenir_pantalla((255, 60, 80), 0.1, 8))
esc.hacer(*saltan(6, 8))
esc.hacer(d('TODOS: ¡TALA, TALA, TALA,\nTALA, TALA!', espera=50), esc.temblor_pantalla(30, 1))
esc.hacer(*saltan(5, 6), esc.tenir_pantalla((40, 255, 120), 0.1, 8))
esc.hacer(*saltan(5, 6), esc.tenir_pantalla((80, 120, 255), 0.1, 8))
esc.hacer(*saltan(5, 6), esc.tenir_pantalla((40, 255, 120), 0.1, 8))
esc.esperar(6)
esc.hacer(rojo.mirar('derecha'), rojo.saltar(altura=5, frames=8))
esc.hacer(d('MARÍA: ¡OCHO PAVOS!', espera=45), *saltan(4, 8))
esc.hacer(multitud[2].saltar(altura=6, frames=8))
esc.hacer(d('¡MAESTRO!', espera=40), *saltan(5, 8))
esc.esperar(10)
esc.hacer(rojo.mirar(gafas), gafas.mirar(rojo))
esc.hacer(d('MARÍA: Primo, quítate ya\nlas gafas.', espera=55))
esc.hacer(gafas.temblar(10, 1))
esc.hacer(d('MARÍA: Primo, ya basta.', espera=50))
esc.hacer(gafas.emocion('!', frames=20), gafas.saltar(altura=5, frames=8))
esc.esperar(30)
esc.hacer(esc.parar_musica(frames=35))
esc.hacer(esc.fundido(entrada=False, frames=30))

if __name__ == '__main__':
    if V2:
        esc.renderizar(os.path.join(SALIDA, 'formigal_v2_sinmusica'), gif=False, hoja_contacto=False)
        json.dump(MARCAS, open(os.path.join(CACHE, 'formigal_marcas.json'), 'w'))
    else:
        esc.renderizar(os.path.join(SALIDA, 'formigal'))
