"""REWINDLIMBO2 · tramo 2 (1:10-2:30). El parque.

Original: señala el cartel pintado con WU-TANG y se queja (1:10-1:20); con la sudadera gris pasea entre árboles
y junto al lago sin dejar de quejarse (1:20-1:37); sube al porche de una cabaña cerrada, llama y nadie
contesta (1:37-1:54); va a un banco, se sienta, estudia el mapa, se desespera (1:54-2:26) y decide seguir
(2:26-2:30).

Versión Platino: Pueblo Arena y su playa (zona 26,4). El cartel es una ventana del juego sobre postes, la
cabaña es la casa pequeña del tejado azul y el banco está en el camino de arena.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import banco, cartel_pintado, efecto, escalar, exportar, inserto, mapa_dibujado, textos  # noqa
from motor import Escena, MapaReal

T0, T1 = 70.0, 150.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
letrero = esc.objeto(cartel_pintado(), 25, 10)
asiento = esc.objeto(banco(), 47, 23)
maria = esc.personaje('el_maria_sombrero', 25, 12, mira='arriba')
esc.camara_sigue(maria)
esc.subtitulos(textos.subtitulos(T0, T1))
ENFADO = efecto(11)[0]


def enfado(p, frames=24):
    """Símbolo de enfado del juego sobre la cabeza y un temblor."""
    def acc():
        for f in range(frames):
            esc.efectos.append((ENFADO, p.x + 18, p.y - 22 - p.elevacion - (2 if f % 8 < 4 else 0)))
            p.empuje = ((1 if f % 2 else -1) if f < 12 else 0, 0)
            yield
        p.empuje = (0, 0)
    return acc()


def corte(dur=8):
    """Corte rápido a negro (cambio de plano)."""
    return esc.fundido(entrada=False, frames=dur)


# ---------------------------------------------------------------- 1:10 el cartel pintado
esc.hacer(esc.mostrar('cartel', inserto(escalar(cartel_pintado(), 2), 1), y=8, efecto='zoom', frames=8))
esc.hacer(enfado(maria))
esc.hacer(esc.hasta(75.5))
esc.hacer(esc.ocultar('cartel', 8))
esc.hacer(maria.mirar('abajo'), enfado(maria))
esc.hacer(esc.hasta(77.6))

# ---------------------------------------------------------------- 1:18 sudadera, junto al lago
esc.hacer(corte())
esc.hacer(maria.cambiar_sprite('el_maria_sudadera'), maria.teletransportar(53, 26), maria.mirar('abajo'))
esc.hacer(esc.fundido(entrada=True, frames=8), maria.andar('abajo', 1))
esc.hacer(maria.ruta(('abajo', 7), ('izquierda', 3), ('abajo', 5)))     # por la playa, lejos de los pinos
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(86.9))
esc.hacer(maria.mirar('abajo'), enfado(maria))
esc.hacer(esc.hasta(91.0))
esc.hacer(enfado(maria, 30), maria.saltar(4, 8))
esc.hacer(esc.hasta(92.4))
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(93.9))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(95.1))
esc.hacer(maria.mirar('abajo'), enfado(maria, 30))
esc.hacer(esc.hasta(97.9))
esc.hacer(maria.mirar('arriba'))
esc.hacer(maria.andar('arriba', 4))
esc.hacer(esc.hasta(101.3))

# ---------------------------------------------------------------- 1:42 la cabaña cerrada
esc.hacer(corte())
esc.hacer(maria.teletransportar(39, 26), maria.mirar('arriba'))
esc.hacer(esc.fundido(entrada=True, frames=8), maria.andar('arriba', 1))
esc.hacer(maria.andar('arriba', 2))
for t in (102.6, 103.0, 103.4):                                   # llama a la puerta
    esc.hacer(esc.hasta(t))
    esc.hacer(esc.sonido('SEQ_SE_DP_KON', 0.7), maria.mover(0, -2, 2), maria.mover(0, 2, 2))
esc.hacer(esc.hasta(108.0))
esc.hacer(esc.sonido('SEQ_SE_DP_KON', 0.7), maria.mover(0, -2, 2), maria.mover(0, 2, 2))
esc.hacer(esc.hasta(109.6))
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(110.6))
esc.hacer(maria.mirar('abajo'), enfado(maria, 30))
esc.hacer(esc.hasta(114.0))
esc.hacer(maria.ruta(('abajo', 1), ('derecha', 8)))              # hacia el banco
esc.hacer(maria.mirar('abajo'))
esc.hacer(esc.hasta(119.0))
esc.hacer(maria.posar(17), maria.mover(0, -11, 6))               # se sienta en el banco
esc.hacer(esc.hasta(121.0))
esc.hacer(maria.mirar('izquierda'), maria.posar(17))
esc.hacer(esc.hasta(124.5))

# ---------------------------------------------------------------- 2:05 estudia el mapa y se desespera
esc.hacer(esc.mostrar('mapa', mapa_dibujado(), y=10, efecto='subir', frames=12), esc.sonido('SEQ_SE_DP_KAMI', 0.5))
esc.hacer(esc.hasta(129.3))
esc.hacer(esc.ocultar('mapa', 10, 'bajar'))
esc.hacer(enfado(maria, 30))
esc.hacer(esc.hasta(132.2))
esc.hacer(maria.temblar(16, 1))
esc.hacer(esc.hasta(136.6))
esc.hacer(enfado(maria, 36), maria.saltar(3, 8))
esc.hacer(esc.hasta(140.0))
esc.hacer(maria.temblar(20, 1))
esc.hacer(esc.hasta(143.0))
esc.hacer(enfado(maria, 36))
esc.hacer(esc.hasta(146.4))
esc.hacer(maria.emocion('!', 30), maria.saltar(6, 8), maria.posar(None), maria.mover(0, 11, 4))   # «Espera.»
esc.hacer(maria.mirar('abajo'))
esc.hacer(esc.hasta(148.4))
esc.hacer(maria.saltar(4, 8))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't2_parque', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
