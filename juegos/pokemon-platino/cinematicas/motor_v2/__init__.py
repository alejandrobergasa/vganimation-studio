"""Motor v2: el motor de siempre (motor/) con la sombra arreglada y los escenarios animados.

No sustituye a motor/: lo extiende por herencia, así que las escenas antiguas siguen funcionando igual.
Uso: `from motor_v2 import Escena, MapaReal` en vez de `from motor import ...`. API idéntica.
"""
from motor import TILE, ANCHO, ALTO, catalogo
from motor.mapa_real import ZONAS
from .escena import Escena, Personaje
from .mapa_real import MapaReal
