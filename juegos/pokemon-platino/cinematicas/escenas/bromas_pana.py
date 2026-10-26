"""REWIND 2026 · BROMAS PARA EL PANA (~1 min).

Tres bromas sacadas de las notas del rewind, en la plaza de Pueblo Aromaflor:
  1. La tarta terrible del cumple del Pana, con Kinder Bueno.
  2. El Pana no sabe dónde está la biblioteca de Alejandría.
  3. El Pana con la IA.

Ejecutar desde cinematicas/:  python escenas/bromas_pana.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'rewindlimbo2'))
from PIL import Image  # noqa
from motor import Escena, MapaReal  # noqa
from motor.recursos import SALIDA, fuente  # noqa
from dibujo import Lienzo, ROJO, PAPEL, MADERA  # noqa
from comun import texto_img, escalar, inserto  # noqa

CREMA = ((255, 244, 214), (240, 218, 168), (206, 172, 120), (150, 112, 84))
CHOCO = ((150, 96, 64), (112, 66, 44), (78, 44, 32), (48, 28, 24))
NEGRO = ((70, 62, 66), (48, 42, 48), (34, 30, 38), (24, 20, 28))


def tarta(quemada=True):
    """Tarta torcida y quemada con tres Kinder Bueno clavados y una vela (24x22)."""
    c = Lienzo(24, 22)
    c.forma(lambda d: d.rectangle((2, 10, 21, 20), fill=255), NEGRO if quemada else CREMA)
    c.forma(lambda d: d.polygon([(2, 10), (21, 8), (21, 12), (2, 12)], fill=255), CREMA)
    for x in (5, 11, 17):                                   # Kinder Bueno: barritas oscuras con envoltorio blanco
        c.forma(lambda d, x=x: d.rectangle((x, 4, x + 3, 10), fill=255), CHOCO)
        c.plano(lambda d, x=x: d.rectangle((x + 1, 6, x + 2, 7), fill=255), (250, 250, 250))
    c.forma(lambda d: d.rectangle((11, 1, 12, 5), fill=255), ROJO)     # vela
    c.pixeles([(11, 0), (12, 0)], (255, 214, 64))
    c.pixeles([(4, 16), (9, 14), (15, 17), (19, 14)], (20, 16, 20))   # churretes de quemado
    return c.img


def signo(txt):
    return texto_img(txt, (255, 255, 255), (60, 60, 80), 2)


def titulo(lineas):
    f = fuente()
    w = max(f.ancho(l) for l in lineas) * 2 + 56
    h = 28 * len(lineas) + 12
    from motor.recursos import ventana_mensaje
    v = ventana_mensaje((w + 7) // 8 * 8, (h + 7) // 8 * 8, 1)
    for i, l in enumerate(lineas):
        t = texto_img(l, None, None, 2)
        v.alpha_composite(t, ((v.width - t.width) // 2, 8 + i * 28))
    return v


# ---------------------------------------------------------------- mapa y reparto
mapa = MapaReal('aromaflor', hora=17)
esc = Escena(mapa)
pana = esc.personaje('el_pana', 17, 48, mira='abajo')
santos = esc.personaje('santos', 26, 51, mira='izquierda')
chini = esc.personaje('chini', 8, 49, mira='derecha')
robot = esc.personaje('robot_valedores', 17, 54, mira='arriba')
for p in (santos, chini, robot):
    pass
esc.camara_fija(17, 49)

# ---------------------------------------------------------------- 0. Título
esc.musica('SEQ_TOWN01_D', volumen=0.5)
esc.hacer(esc.fundido(entrada=True, frames=20))
esc.hacer(esc.mostrar('titulo', titulo(['REWIND 2026', 'BROMAS PARA EL PANA']), efecto='zoom', frames=8))
esc.esperar(75)
esc.hacer(esc.ocultar('titulo', frames=8, efecto='fundido'))

# ---------------------------------------------------------------- 1. La tarta
esc.hacer(santos.andar('izquierda', 6), chini.andar('derecha', 4))
esc.hacer(santos.llevar(tarta(), dx=4, dy=-13))
esc.hacer(santos.andar('izquierda', 3), chini.andar('derecha', 3))
esc.hacer(pana.mirar(santos))
esc.hacer(pana.emocion('!', frames=20), pana.saltar(altura=5, frames=8))
esc.hacer(esc.dialogo('SANTOS: ¡Feliz cumple!\nTe hemos hecho tarta.'))
esc.hacer(santos.llevar(None), esc.mostrar('tarta', inserto(escalar(tarta(), 3), 1, 'TARTA DE KINDER BUENO'),
                                           efecto='zoom', frames=8))
esc.hacer(esc.dialogo('PANA: Está carbonizada.\n¿Eso son Kinder Bueno?', espera=50))
esc.hacer(esc.ocultar('tarta', frames=8, efecto='fundido'))
esc.hacer(chini.mirar(santos), esc.dialogo('CHINI: La tarta terrible\ndel cumple del Pana.'))
esc.hacer(pana.tenir((90, 200, 90), 0.5), pana.temblar(24, 1), esc.sonido('SEQ_SE_DP_BOWA3', volumen=0.6))
esc.hacer(esc.dialogo('PANA: Mmm... riquísima.\n...Me muero.', espera=50))
esc.hacer(pana.tenir(None))
esc.esperar(10)

# ---------------------------------------------------------------- 2. La biblioteca de Alejandría
esc.hacer(pana.mirar(chini), chini.mirar(pana))
esc.hacer(pana.llevar(signo('?'), dx=6, dy=-22), esc.dialogo('PANA: Chini, ¿dónde está\nla biblio de Alejandría?'))
esc.hacer(pana.llevar(None))
esc.hacer(chini.saltar(altura=5, frames=8), esc.dialogo('CHINI: En Egipto, pana.\nY ya no existe.', espera=50))
esc.hacer(pana.mirar('izquierda'), esc.dialogo('PANA: Vale, voy andando.'))
esc.hacer(pana.correr('izquierda', 4), esc.sonido('SEQ_SE_DP_NIGERU', volumen=0.5))
esc.esperar(10)
esc.hacer(pana.mirar('derecha'), santos.mirar('izquierda'))
esc.hacer(pana.llevar(signo('?'), dx=6, dy=-22), esc.dialogo('PANA: No la encuentro.\n¿Estará en la de aquí?', espera=50))
esc.hacer(pana.llevar(None), santos.saltar(altura=5, frames=8), chini.saltar(altura=5, frames=8))
esc.hacer(pana.correr('derecha', 4))

# ---------------------------------------------------------------- 3. El Pana con la IA
esc.musica('SEQ_TOWN02_D', volumen=0.5)
esc.hacer(robot.andar('arriba', 3), santos.mirar(robot), chini.mirar(robot))
esc.hacer(pana.mirar(robot))
esc.hacer(esc.dialogo('PANA: IA, ¿cómo hago una\ntarta que no esté quemada?', espera=50))
esc.hacer(robot.posar(16), esc.sonido('SEQ_SE_DP_PC_ON', volumen=0.5))
esc.hacer(esc.dialogo('IA: Paso 1: no uses\nKinder Bueno.', espera=50))
esc.hacer(robot.posar(None), pana.emocion('!', frames=20), pana.saltar(altura=5, frames=8))
esc.hacer(esc.dialogo('PANA: ¿Y la biblioteca de\nAlejandría? ¿Dónde está?', espera=50))
esc.hacer(robot.posar(17), robot.temblar(20, 2), esc.sonido('SEQ_SE_DP_BEEP', volumen=0.6))
esc.hacer(esc.dialogo('IA: ERROR 404.\nBiblioteca no encontrada.', espera=55))
esc.hacer(robot.posar(None), santos.saltar(altura=5, frames=8), chini.saltar(altura=5, frames=8))
esc.hacer(esc.dialogo('SANTOS: Feliz cumple, Pana.', espera=45))
esc.esperar(20)
esc.hacer(esc.mostrar('fin', titulo(['FELIZ CUMPLE,', 'PANA']), efecto='zoom', frames=8))
esc.esperar(110)
esc.parar_musica(frames=40)
esc.hacer(esc.fundido(entrada=False, frames=30))

if __name__ == '__main__':
    salida = os.path.join(SALIDA, 'bromas_pana')
    esc.renderizar(salida)
