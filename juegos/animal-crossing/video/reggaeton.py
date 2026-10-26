"""Instrumental de reggaeton (dembow) compuesta con los instrumentos del banco 12 del SDAT de Wild World.

Instrumentos (programas del banco 12, hallados midiendo espectro/ataque de cada uno):
  0 = bombo grave · 1 = caja/chasquido de ruido · 2 = hi-hat · 6 = bajo · 3 = punteo tonal · 13 = campanilla (suena una octava arriba)
Armonía La menor: Am - F - C - G. Compás 4/4 a 92 bpm, 16 pasos por compás; dembow = bombo a negras y caja en 3-6-11-14.
"""
import numpy as np

BANCO = 12
BPM = 92.0
PASO = 60.0 / BPM / 4
COMPAS = 16 * PASO
KICK, SNARE, HAT, BAJO, PUNTEO, CAMPANA = 0, 1, 2, 6, 3, 13

ACORDES = [(33, (57, 60, 64)), (29, (53, 57, 60)), (36, (55, 60, 64)), (31, (55, 59, 62))]   # (bajo, acorde)
# motivo de campanilla: (paso, nota, duración en pasos) por compás
MOTIVO = [
    [(0, 76, 3), (3, 76, 2), (6, 74, 2), (8, 72, 3), (11, 74, 3)],
    [(0, 72, 3), (3, 72, 2), (6, 69, 2), (8, 72, 4), (12, 74, 2)],
    [(0, 76, 3), (3, 79, 2), (6, 76, 2), (8, 74, 3), (11, 72, 3)],
    [(0, 74, 3), (3, 74, 2), (6, 71, 2), (8, 69, 4), (14, 71, 1)],
]
BAJO_PASOS = [(0, 3), (3, 2), (6, 1), (8, 3), (11, 2), (14, 1)]


def notas(duracion):
    """Lista de notas (inicio_s, dur_s, tecla, vel, programa, pan, volumen) para tocar_notas."""
    rng = np.random.RandomState(11)
    out = []
    n_compases = int(duracion / COMPAS) + 1
    for c in range(n_compases):
        t0 = c * COMPAS
        bajo, acorde = ACORDES[c % 4]
        intro = c < 2
        final = c >= n_compases - 2
        h = lambda: rng.uniform(-3, 3)
        def add(paso, dur, tecla, vel, prog, pan=64, vol=127):
            out.append((t0 + paso * PASO, dur * PASO, tecla, int(np.clip(vel + h(), 1, 127)), prog, pan, vol))
        # batería
        if not intro and not final:
            for s in (0, 4, 8, 12):
                add(s, 2, 36, 125, KICK, 64, 127)       # sub grave
                add(s, 1, 60, 110, KICK, 64, 110)       # clic del bombo
            for s in (3, 6, 11, 14):
                add(s, 2, 50, 112, SNARE, 64, 120)
            if c % 4 == 3:
                add(15, 1, 50, 80, SNARE, 64, 100)      # remate
        for s in range(0, 16, 2):
            add(s, 1, 60, 78 if s % 4 == 0 else 58, HAT, 78, 100)
        if not intro and not final and c % 2 == 1:
            for s in (5, 13):
                add(s, 1, 60, 40, HAT, 50, 90)
        # bajo
        if not intro and not final:
            for s, d in BAJO_PASOS:
                add(s, d, bajo + (12 if s == 14 else 0), 118, BAJO, 64, 127)
        # acordes a contratiempo
        for s in (3, 6, 11, 14):
            for k, n in enumerate(acorde):
                add(s, 1.2, n, 78 if not intro else 70, PUNTEO, 40 if s < 8 else 88, 105)
        # campanilla con el motivo (desde el compás 2)
        if c >= 2 and not final:
            for s, n, d in MOTIVO[c % 4]:
                add(s, d, n - 12, 96, CAMPANA, 64 + (14 if c % 2 else -14), 112)
        if final and c == n_compases - 2:
            add(0, 4, bajo, 110, BAJO, 64, 127)
            add(0, 2, 36, 120, KICK, 64, 127)
    return [n for n in out if n[0] < duracion]


def pista(audio_bank, duracion):
    return audio_bank.notes(notas(duracion), duracion, BANCO)
