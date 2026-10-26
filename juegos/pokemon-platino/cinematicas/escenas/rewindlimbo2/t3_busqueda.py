"""REWINDLIMBO2 · tramo 3 (2:30-4:01). La búsqueda.

Original: se prepara para el reto (2:30-2:43); atraviesa el sendero y una loma (2:43-2:57); recoge una rama
(2:57-3:10); busca entre la hierba y los árboles mirando el mapa (3:10-3:31); encuentra el sitio, excava con
la rama (3:31-3:57) y levanta la caja de EL PROYECTO (3:57-4:01).

Versión Platino: ruta 202 al oeste de Pueblo Arena (zona 26,4): camino de arena y la hierba alta.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import (rama, caja_grande, caja_proyecto, efecto, escalar, exportar, icono, inserto, mapa_dibujado,  # noqa
                   polvo, textos)
from motor import Escena, MapaReal

T0, T1 = 150.0, 241.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
maria = esc.personaje('el_maria_sudadera', 47, 24, mira='abajo')
caja = esc.objeto(caja_proyecto(), 15, 15, visible=False)
esc.camara_sigue(maria)
esc.subtitulos(textos.subtitulos(T0, T1))
PALO = rama().crop(rama().getbbox())
PALO_MANO = PALO.resize((PALO.width // 2, PALO.height // 2))


def excavar(frames):
    """Agachado, con polvo y ruido de arena cada poco."""
    def acc():
        for f in range(frames):
            if f % 40 == 0:                                   # espaciado: seguido se vuelve ruido
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_SUNA', 0.18))
            if f % 20 < 10:
                img = polvo()[(f // 5) % 2]
                esc.efectos.append((img.resize((20, 20)), maria.x - 2 + (f % 3), maria.y + 2 - maria.elevacion))
            maria.empuje = (0, 1 if f % 10 < 5 else 0)
            yield
        maria.empuje = (0, 0)
    return acc()


# ---------------------------------------------------------------- 2:30 se prepara para el reto
esc.hacer(maria.saltar(4, 8))
esc.hacer(esc.hasta(151.5))
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(152.3))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(153.1))
esc.hacer(maria.mirar('abajo'))
for t in (154.4, 155.4):                                          # calentamiento
    esc.hacer(esc.hasta(t))
    esc.hacer(maria.saltar(6, 10))
esc.hacer(esc.hasta(157.8))
esc.hacer(esc.mostrar('lata', inserto(icono('refresco'), 2), x=24, y=12, efecto='zoom', frames=8))
esc.hacer(esc.hasta(162.6))
esc.hacer(esc.ocultar('lata', 8))

# ---------------------------------------------------------------- 2:43 el sendero
esc.hacer(esc.fundido(entrada=False, frames=10))
esc.hacer(maria.teletransportar(29, 12), maria.mirar('izquierda'))
esc.hacer(esc.fundido(entrada=True, frames=10), maria.andar('izquierda', 1))
esc.hacer(maria.ruta(('izquierda', 6), ('abajo', 3)))                      # -> (23, 15)
esc.hacer(maria.mover(0, 32, 16, arco=10), esc.sonido('SEQ_SE_DP_DANSA', 0.6))   # salta el bordillo (la loma)
esc.hacer(maria.ruta(('abajo', 4), ('izquierda', 9)))                      # -> (14, 21)
esc.hacer(esc.hasta(176.6))

# ---------------------------------------------------------------- 2:57 la rama
esc.hacer(maria.mirar('abajo'))
esc.hacer(maria.emocion('!', 20))
esc.hacer(maria.posar(16), esc.sonido('SEQ_SE_DP_KUSA', 0.5))
esc.hacer(esc.mostrar('palo', inserto(rama(), 2), x=24, y=12, efecto='zoom', frames=8))
esc.hacer(esc.hasta(180.5))
esc.hacer(esc.ocultar('palo', 8), maria.posar(None))
esc.hacer(maria.llevar(PALO_MANO, dx=9, dy=14))
esc.hacer(esc.hasta(184.0))
esc.hacer(maria.andar('izquierda', 2))

# ---------------------------------------------------------------- 3:10 busca entre la hierba
esc.hacer(maria.andar('arriba', 4), esc.sonido('SEQ_SE_DP_KUSA', 0.3))     # (12,21) -> (12,17)
esc.hacer(esc.hasta(191.0))
esc.hacer(maria.mirar('izquierda'))
esc.hacer(esc.hasta(192.5))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(194.0))
esc.hacer(maria.ruta(('derecha', 3), ('arriba', 2)), esc.sonido('SEQ_SE_DP_KUSA', 0.3))   # -> (15,15)
esc.hacer(maria.mirar('abajo'))
esc.hacer(esc.hasta(198.0))
esc.hacer(esc.mostrar('mapa', mapa_dibujado(), y=10, efecto='subir', frames=12), esc.sonido('SEQ_SE_DP_KAMI', 0.5))
esc.hacer(esc.hasta(203.0))
esc.hacer(esc.ocultar('mapa', 10, 'bajar'))
esc.hacer(maria.ruta(('arriba', 2), ('izquierda', 2)), esc.sonido('SEQ_SE_DP_KUSA', 0.3))  # -> (13,13)
esc.hacer(maria.mirar('arriba'))
esc.hacer(esc.hasta(206.5))
esc.hacer(maria.mirar('derecha'))
esc.hacer(esc.hasta(208.0))
esc.hacer(maria.ruta(('derecha', 2), ('abajo', 1)), esc.sonido('SEQ_SE_DP_KUSA', 0.3))     # -> (15,14)
esc.hacer(maria.mirar('abajo'))
esc.hacer(esc.hasta(211.3))

# ---------------------------------------------------------------- 3:31 excava
esc.hacer(maria.emocion('!', 30), maria.saltar(6, 8), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.4))
esc.hacer(esc.hasta(213.4))
esc.hacer(maria.posar(16), maria.llevar(None))
esc.hacer(excavar(int((236.0 - 213.5) * 30)))
esc.hacer(caja.aparecer(), esc.animacion(efecto(19), caja.x + 8, caja.y + 6, 24, cada=4),
          esc.sonido('SEQ_SE_DP_KIRAKIRA2', 0.5))
esc.hacer(esc.hasta(237.6))
esc.hacer(esc.mostrar('caja', caja_grande(), y=14, efecto='zoom', frames=10))
esc.hacer(esc.hasta(239.8))
esc.hacer(esc.ocultar('caja', 6), caja.desaparecer(), maria.posar(None),
          maria.llevar(caja_proyecto(), dy=-12), maria.saltar(8, 10), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.5))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't3_busqueda', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
