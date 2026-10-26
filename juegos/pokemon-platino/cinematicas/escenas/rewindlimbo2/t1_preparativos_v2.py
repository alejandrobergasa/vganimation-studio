"""REWINDLIMBO2 · tramo 1 (0:00-1:10). Preparativos. VERSIÓN 2 (con iconos de objetos), sustituida por t1_preparativos.py.

Original: dentro del coche arranca y prepara la pipa (0:00-0:14); sale, se pone el sombrero y cierra la puerta
(0:14-0:24); llena, enciende y fuma la pipa (0:24-0:40); fuma y consulta el mapa dibujado a mano (0:40-0:59);
cruza la calzada y llega al cartel del parque (0:59-1:10).

Versión Platino: Pueblo Arena (zona 26,4). El coche no existe en el juego: el arranque y la pipa se cuentan con
insertos de objetos en ventanas del juego mientras EL MARÍA espera junto al Centro Pokémon.

Ejecutar desde cinematicas/:  python escenas/rewindlimbo2/t1_preparativos.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import (caja_proyecto, cartel, cartel_pintado, mapa_dibujado, efecto, escalar, exportar, humo, icono, inserto, pipa,  # noqa
                   textos)
from motor import Escena, MapaReal

T0, T1 = 0.0, 70.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
maria = esc.personaje('el_maria', 45, 12, mira='abajo')
letrero = esc.objeto(cartel_pintado(), 25, 10)
esc.camara_fija(45, 12)
esc.subtitulos(textos.subtitulos(T0, T1))


def fumar(desde, hasta, cada=2.2):
    """Bocanadas de humo sobre la cabeza entre dos segundos."""
    acc = []
    t = desde
    while t < hasta:
        acc.append(_bocanada(t))
        t += cada
    return acc


def _bocanada(t):
    def gen():
        yield from esc.hasta(t)
        yield from esc.animacion(humo(), maria.x + 16, maria.y - 14 - maria.elevacion, 24, cada=6)
    return gen()


# ---------------------------------------------------------------- 0:00 arranque y pipa (insertos)
esc.hacer(esc.fundido(entrada=True, frames=30))
esc.hacer(esc.hasta(1.0))
esc.hacer(esc.mostrar('obj', inserto(icono('llave_suite'), 2), x=24, y=12, efecto='zoom', frames=8),
          esc.sonido('SEQ_SE_DP_KASYA', 0.5))
esc.hacer(esc.hasta(4.6))
esc.hacer(esc.ocultar('obj', 6))
esc.hacer(esc.hasta(5.2))
esc.hacer(esc.mostrar('obj', inserto(pipa(), 2), x=24, y=12, efecto='zoom', frames=8),
          esc.mostrar('obj2', inserto(icono('hierba_rev'), 2), x=88, y=12, efecto='zoom', frames=8))
esc.hacer(esc.hasta(9.6))
esc.hacer(esc.ocultar('obj2', 6))
esc.hacer(esc.mostrar('obj2', inserto(icono('piedra_fuego'), 2), x=88, y=12, efecto='zoom', frames=8),
          esc.sonido('SEQ_SE_DP_KASYA', 0.4))
esc.hacer(esc.animacion(efecto(19), 122, 44, 30, cada=5, pantalla=True), esc.hasta(13.0))
esc.hacer(esc.ocultar('obj', 8), esc.ocultar('obj2', 8))

# ---------------------------------------------------------------- 0:14 sale y se pone el sombrero
esc.hacer(esc.hasta(15.0))
esc.hacer(maria.andar('abajo', 1))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(19.3))
esc.hacer(maria.mirar('abajo'), esc.animacion(humo(), maria.x + 16, maria.y - 6, 16, cada=4),
          esc.sonido('SEQ_SE_DP_BOX01', 0.4))
esc.hacer(maria.cambiar_sprite('el_maria_sombrero'), maria.saltar(4, 8))
esc.hacer(esc.hasta(22.4))
esc.hacer(maria.mirar('arriba'), esc.sonido('SEQ_SE_DP_DOOR_CLOSE', 0.6))       # cierra el coche
esc.hacer(esc.hasta(23.6))
esc.hacer(maria.mirar('abajo'))

# ---------------------------------------------------------------- 0:24 llena y enciende la pipa
esc.hacer(esc.hasta(25.0))
esc.hacer(maria.posar(16))                                      # agachado
esc.hacer(esc.mostrar('obj', inserto(pipa(), 2), x=24, y=12, efecto='zoom', frames=8))
esc.hacer(esc.hasta(29.5))
esc.hacer(esc.ocultar('obj', 6))
esc.hacer(esc.hasta(32.5))
esc.hacer(esc.mostrar('obj', inserto(icono('piedra_fuego'), 2), x=24, y=12, efecto='zoom', frames=8),
          esc.sonido('SEQ_SE_DP_KASYA', 0.4))
esc.hacer(esc.animacion(efecto(19), 58, 44, 40, cada=5, pantalla=True))
esc.hacer(esc.ocultar('obj', 6))
esc.hacer(esc.hasta(36.0))
esc.hacer(maria.posar(None), esc.en_paralelo(*fumar(36.5, 59.0)))   # el humo sigue mientras pasa lo demás

# ---------------------------------------------------------------- 0:40 consulta el mapa
esc.hacer(esc.hasta(42.0))
esc.hacer(esc.mostrar('mapa', mapa_dibujado(), y=12, efecto='subir', frames=12),
          esc.sonido('SEQ_SE_DP_KAMI', 0.5))
esc.hacer(esc.hasta(50.0))
esc.hacer(esc.ocultar('mapa', 10, 'bajar'))
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(52.0))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(54.0))
esc.hacer(maria.mirar('abajo'))
esc.hacer(esc.hasta(55.0))
esc.hacer(esc.mostrar('mapa', mapa_dibujado(), y=12, efecto='subir', frames=12),
          esc.sonido('SEQ_SE_DP_KAMI', 0.5))
esc.hacer(esc.hasta(58.6))
esc.hacer(esc.ocultar('mapa', 10, 'bajar'))

# ---------------------------------------------------------------- 0:59 cruza hacia el parque
esc.hacer(esc.hasta(59.5))
esc.hacer(maria.andar('arriba', 1))
esc.hacer(esc.accion(lambda: esc.camara_sigue(maria)), maria.andar('izquierda', 20))                         # (45,12) -> (25,12)
esc.hacer(maria.mirar('arriba'))
esc.hacer(esc.hasta(68.2))
esc.hacer(maria.emocion('!', 30), maria.saltar(5, 8))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't1_preparativos_v2', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
