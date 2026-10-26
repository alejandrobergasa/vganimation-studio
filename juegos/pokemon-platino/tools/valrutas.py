"""Enlace de los scripts de Pokémon Platino con `valedores.rutas` (ROM, biblioteca, salida, trabajo)."""
import os
import sys


def _repo():
    d = os.path.dirname(os.path.abspath(__file__))
    while not os.path.isfile(os.path.join(d, 'valedores.toml')):
        d = os.path.dirname(d)
    return d


sys.path.insert(0, os.path.join(_repo(), 'nucleo'))
from valedores import rutas  # noqa: E402

JUEGO = 'pokemon-platino'
SPR = rutas.extraidos(JUEGO)
CUSTOM = rutas.personalizados(JUEGO)
CACHE = rutas.cache(JUEGO)
TRABAJO = rutas.trabajo(JUEGO)
SALIDA = rutas.salida(JUEGO)


def rom():
    return rutas.rom(JUEGO)
