"""[v2: sombra arreglada y escenario animado] Demo: Lucas pasea por Pueblo Aromaflor, saluda a un niño, el niño se asusta y sale corriendo.

Ejecutar desde cinematicas/:  python escenas/demo_parque_v2.py
Plano de la zona con la rejilla de tiles:  python herramientas.py mapa aromaflor
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from motor_v2 import Escena, MapaReal
from motor.recursos import SALIDA

# ---------------------------------------------------------------- mapa real del juego
mapa = MapaReal('aromaflor', hora=12)          # 32 x 64 tiles; el pueblo ocupa las filas 32-63

# ---------------------------------------------------------------- reparto
esc = Escena(mapa)
lucas = esc.personaje('heroe_andar_correr', 11, 63, mira='arriba')   # 090: Lucas (Platino)
nino = esc.personaje('babyboy1', 19, 51, mira='arriba')              # 000: niño pequeño
esc.camara_sigue(lucas)

# ---------------------------------------------------------------- guion
esc.hacer(esc.fundido(entrada=True), lucas.andar('arriba', 2))
esc.hacer(lucas.andar('arriba', 10))           # cruza el arco de flores y sube por el camino
esc.hacer(lucas.andar('derecha', 6))           # llega junto al niño
esc.esperar(12)
esc.hacer(nino.mirar(lucas))                     # el niño se gira
esc.esperar(8)
esc.hacer(esc.dialogo('¡HOLA! ¿QUÉ TAL?'))
esc.hacer(nino.emocion('!', frames=24), nino.saltar(altura=6, frames=8))
esc.esperar(6)
esc.hacer(nino.mirar('derecha'))
esc.hacer(nino.correr('derecha', 12))            # sale corriendo por la salida del este
esc.hacer(nino.desaparecer())
esc.esperar(20)
esc.hacer(lucas.mirar('abajo'))
esc.esperar(20)
esc.hacer(esc.fundido(entrada=False, frames=20))

if __name__ == '__main__':
    salida = os.path.join(SALIDA, 'demo_parque_v2')
    esc.renderizar(salida)
