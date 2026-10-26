"""REWINDLIMBO2 · tramo 4 (4:01-4:54). El robot.

Original: aparece el robot Valedores y le pide que no abra la caja (4:01-4:27); discuten; forcejean y el robot
suplica (4:27-4:37); El María lo lanza lejos (4:37-4:40), le dice «A cascarla» y se va con la caja
(4:40-4:49). Corte a un concierto: «Esta canción se llama No voy al Baige» (4:49-4:54).

Versión Platino: la misma hierba alta de la ruta 202 (zona 26,4) donde ha desenterrado la caja. El concierto
es una pantalla completa con un fondo de combate de noche y el guitarrista del juego.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import caja_proyecto, efecto, escenario, exportar, polvo, textos  # noqa
from motor import Escena, MapaReal

T0, T1 = 241.0, 294.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
maria = esc.personaje('el_maria_sudadera', 15, 14, mira='abajo')
robot = esc.personaje('robot_valedores', 8, 14, mira='derecha')
caja = esc.objeto(caja_proyecto(), 16, 14, visible=False)
esc.camara_fija(14, 14)
esc.subtitulos(textos.subtitulos(T0, T1))
ENFADO = efecto(11)[0]
NOTAS = efecto(29)


def enfado(p, frames=24):
    def acc():
        for f in range(frames):
            esc.efectos.append((ENFADO, p.x + 18, p.y - 22 - p.elevacion - (2 if f % 8 < 4 else 0)))
            p.empuje = ((1 if f % 2 else -1) if f < 12 else 0, 0)
            yield
        p.empuje = (0, 0)
    return acc()


def forcejeo(frames):
    """Los dos tiemblan agarrados, con polvo entre los pies."""
    def acc():
        for f in range(frames):
            a = 2 if f % 4 < 2 else -2
            maria.empuje = (a, 0)
            robot.empuje = (-a, 0)
            if f % 32 == 0:
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_KOUKA_L', 0.2))
            if f % 16 < 8:
                esc.efectos.append((polvo()[(f // 4) % 2].resize((12, 12)), maria.x - 6, maria.y + 10))
            yield
        maria.empuje = robot.empuje = (0, 0)
    return acc()


def concierto(frames):
    def acc():
        for f in range(frames):
            esc.capas['concierto'][0] = ESCENARIO[(f // 8) % 2]
            for i, (x, y) in enumerate(((60, 50), (196, 40), (80, 110), (180, 100))):
                if (f // 20 + i) % 2:
                    img = NOTAS[(f // 6 + i) % len(NOTAS)]
                    esc.efectos_pantalla.append((img, x - img.width // 2, y - (f % 20) - img.height // 2))
            yield
    return acc()


ESCENARIO = [escenario(0), escenario(1)]

# ---------------------------------------------------------------- 4:01 aparece el robot
esc.hacer(maria.llevar(caja_proyecto(), dy=-12))
esc.hacer(maria.mirar('izquierda'), robot.andar('derecha', 5))                     # (8,14) -> (13,14)
esc.hacer(esc.hasta(243.5))
esc.hacer(maria.emocion('!', 30), maria.saltar(6, 8))
esc.hacer(esc.hasta(246.3))
esc.hacer(enfado(maria, 30))
esc.hacer(esc.hasta(249.5))
esc.hacer(enfado(maria, 36), maria.saltar(4, 8))
esc.hacer(esc.hasta(252.7))
esc.hacer(robot.temblar(10, 1))
esc.hacer(esc.hasta(257.5))
esc.hacer(maria.saltar(4, 6), enfado(maria, 24))                                   # «Primo, cállate.»
esc.hacer(esc.hasta(261.3))
esc.hacer(robot.temblar(8, 1))
esc.hacer(esc.hasta(264.9))
esc.hacer(enfado(maria, 40))

# ---------------------------------------------------------------- 4:27 forcejeo
esc.hacer(esc.hasta(267.3))
esc.hacer(maria.mirar('derecha'))
esc.hacer(maria.posar(16), maria.llevar(None), caja.aparecer(), esc.sonido('SEQ_SE_DP_BOX01', 0.5))
esc.esperar(8)
esc.hacer(maria.posar(None), maria.mirar('izquierda'))
esc.hacer(maria.andar('izquierda', 1))                                             # -> (14,14), pegado al robot
esc.hacer(esc.en_paralelo(forcejeo(int((276.9 - 268.5) * 30))))
esc.hacer(esc.hasta(271.8))
esc.hacer(robot.posar(16))                          # suplica con los brazos arriba
for t in (272.6, 273.2, 274.3, 274.9, 276.1):
    esc.hacer(esc.hasta(t))
    esc.hacer(robot.posar(17 if t in (273.2, 274.9) else 16))
esc.hacer(esc.hasta(276.9))

# ---------------------------------------------------------------- 4:37 lo lanza
esc.hacer(robot.posar(None), maria.golpear(robot, 14, 'SEQ_SE_DP_KOUKA_H'))
esc.hacer(robot.mover(-150, -8, 24, arco=48), esc.sonido('SEQ_SE_DP_NAGERU', 0.7))
esc.hacer(robot.desaparecer(), esc.temblor_pantalla(10, 2), esc.sonido('SEQ_SE_DP_DANSA', 0.5))
esc.hacer(esc.hasta(279.6))
esc.hacer(maria.saltar(3, 6))                                                       # «A cascarla, Valedores.»
esc.hacer(esc.hasta(282.0))

# ---------------------------------------------------------------- 4:42 recoge la caja y se va
esc.hacer(maria.andar('derecha', 1))                                               # -> (15,14)
esc.hacer(maria.posar(16))
esc.esperar(10)
esc.hacer(caja.desaparecer(), maria.posar(None), maria.llevar(caja_proyecto(), dy=-12),
          esc.sonido('SEQ_SE_DP_BOX01', 0.4))
esc.hacer(esc.hasta(284.2))
esc.hacer(esc.camara_mover(15, 14, 12))
esc.hacer(esc.accion(lambda: esc.camara_sigue(maria)), maria.ruta(('abajo', 6), ('derecha', 3)))   # -> (18,20)
esc.hacer(esc.hasta(288.6))

# ---------------------------------------------------------------- 4:49 el concierto
esc.hacer(esc.fundido(entrada=False, frames=10))
esc.hacer(esc.mostrar('concierto', ESCENARIO[0], 0, 0, frames=1, efecto=None))
esc.hacer(esc.fundido(entrada=True, frames=8))
esc.hacer(concierto(int((293.4 - 289.25) * 30)))
esc.hacer(esc.fundido(entrada=False, frames=12))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't4_robot', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
