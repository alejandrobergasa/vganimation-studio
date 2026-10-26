"""Música original tocada con el banco de instrumentos de la ROM (BANK 50: bajo, acordes, melodía y batería).

`Partitura` acumula notas `(inicio_s, duración_s, tecla_MIDI, velocidad, programa, panorama, volumen)` y las renderiza con
`sonido.tocar_notas`. Programas del banco 50 (identificados por rango y espectro): 5 bajo, 3 acordes, 15 metales/cuerdas,
13 melodía, 16 melodía aguda, 4 campanilla, 14 pad, 17 percusión corta; kit 127: 36 bombo, 40 caja, 42 charles cerrado,
46 abierto, 59 platillo."""
import sonido
from . import audio as A

BANCO = 50
BAJO, ACORDE, METAL, LEAD, LEAD2, CAMP, PAD, TICK = 5, 3, 15, 13, 16, 4, 14, 17
BOMBO, CAJA, HAT, HAT_A, PLATO = 36, 40, 42, 46, 59


class Partitura:
    def __init__(self, dur):
        self.dur = dur
        self.notas = []

    def n(self, t, d, tecla, prog, vel=96, pan=64, vol=100):
        if 0 <= t < self.dur - 0.02:
            self.notas.append((float(t), float(min(d, self.dur - t)), int(tecla), int(vel), int(prog), int(pan), int(vol)))

    def bat(self, t, kind, vel=110):
        key, d = {'k': (BOMBO, .12), 's': (CAJA, .15), 'h': (HAT, .06), 'o': (HAT_A, .2), 'c': (PLATO, .9)}[kind]
        self.n(t, d, key, 127, vel, 64, 100)

    def render(self):
        return sonido.tocar_notas(A.son(), BANCO, self.notas, self.dur)
