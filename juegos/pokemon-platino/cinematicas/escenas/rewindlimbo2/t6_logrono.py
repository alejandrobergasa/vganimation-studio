"""REWINDLIMBO2 · tramo 6 (5:15-5:30). Logroño ha cambiado.

Original: montaje de imágenes de archivo de Logroño con aspecto de tele vieja mientras el narrador dice que ha
llovido mucho desde el último Rewind (5:15-5:20) y enumera valedores muy casados y valedores con trabajo
(5:20-5:30).

Versión Platino: Ciudad Canal (zona 22,1) con el filtro CRT. Paneo por el canal; una pareja de boda (los trajes
de concurso del protagonista) con un bebé; y valedores trabajando: obrero, camarero y policía.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import exportar, textos  # noqa
from motor import Escena, MapaReal

T0, T1 = 315.0, 330.0
mapa = MapaReal(fila=22, col=1, filas=2, cols=1, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))
# plano 1: el canal
paseante = esc.personaje('man1', 19, 25, mira='abajo')
paseanta = esc.personaje('woman2', 10, 30, mira='arriba')
# plano 2: los casados
novio = esc.personaje('contesthero_heroe_traje', 2, 38, mira='derecha')
novia = esc.personaje('cont_heroine_heroina_vestido', 3, 38, mira='izquierda')
bebe = esc.personaje('babyboy1', 3, 39, mira='abajo')
# plano 3: los que trabajan
obrero = esc.personaje('workman', 26, 37, mira='abajo')
camarero = esc.personaje('waiter', 21, 39, mira='derecha')
poli = esc.personaje('policeman', 28, 40, mira='izquierda')
esc.camara_sigue(paseante)


def corte(fn, frames=6):
    """Salto de plano con un parpadeo a negro, como en un montaje de cintas."""
    def acc():
        yield from esc.fundido(entrada=False, frames=frames)
        fn()
        yield from esc.fundido(entrada=True, frames=frames)
    return acc()


esc.hacer(esc.poner_filtro('crt'), esc.fundido(entrada=True, frames=12))
# ---------------------------------------------------------------- 5:15 el canal
esc.hacer(esc.accion(lambda: esc.camara_sigue(paseante)), paseante.andar('abajo', 11), paseanta.andar('arriba', 2))
esc.hacer(esc.hasta(320.6))

# ---------------------------------------------------------------- 5:20 valedores muy casados
esc.hacer(corte(lambda: esc.camara_fija(5, 38)))
esc.hacer(novio.saltar(4, 8), novia.saltar(4, 8), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.4))
esc.hacer(esc.hasta(322.4))
esc.hacer(bebe.mirar('izquierda'))
esc.hacer(esc.hasta(323.2))
esc.hacer(bebe.mirar('derecha'), novio.saltar(3, 8))
esc.hacer(esc.hasta(325.4))

# ---------------------------------------------------------------- 5:25 valedores con trabajo
esc.hacer(corte(lambda: esc.camara_fija(25, 38)))
esc.hacer(camarero.andar('derecha', 3), obrero.temblar(30, 1), poli.andar('izquierda', 2))
esc.hacer(camarero.mirar('abajo'), poli.mirar('abajo'))
esc.hacer(esc.hasta(327.8))
esc.hacer(obrero.mirar('izquierda'), camarero.andar('derecha', 1))
esc.hacer(esc.hasta(329.4))
esc.hacer(esc.fundido(entrada=False, frames=18))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't6_logrono', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
