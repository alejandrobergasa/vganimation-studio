"""Música simpática para el vídeo del salmón: pasacalles saltarín en Do mayor, con los instrumentos del banco 12 del SDAT.

Instrumentos (ver CONOCIMIENTO.md): 0 = bombo · 1 = caja · 2 = hi-hat · 6 = bajo · 3 = punteo tonal · 13 = campanilla (suena una octava arriba).
Compás 4/4 a 116 bpm, 16 pasos por compás. Armonía C - Am - F - G; bombo a 1 y 3, caja suave a 2 y 4, acordes a contratiempo,
melodía de campanilla en dos frases de 4 compases (A: tonada; B: respuesta que resuelve en Do).
"""
import numpy as np

BANCO = 12
BPM = 116.0
PASO = 60.0 / BPM / 4
COMPAS = 16 * PASO
KICK, SNARE, HAT, BAJO, PUNTEO, CAMPANA = 0, 1, 2, 6, 3, 13

ACORDES = [(36, (60, 64, 67)), (33, (57, 60, 64)), (29, (57, 60, 65)), (31, (55, 59, 62))]   # (bajo, acorde)
# (paso, nota escrita, duración en pasos); la campanilla suena una octava arriba, así que se resta 12 al tocar
FRASE_A = [
    [(0, 76, 2), (2, 79, 2), (4, 76, 2), (6, 72, 2), (8, 74, 2), (10, 76, 2), (12, 72, 4)],
    [(0, 72, 2), (2, 76, 2), (4, 81, 2), (6, 76, 2), (8, 72, 2), (10, 69, 2), (12, 72, 4)],
    [(0, 77, 2), (2, 81, 2), (4, 77, 2), (6, 72, 2), (8, 74, 2), (10, 77, 2), (12, 81, 4)],
    [(0, 79, 2), (2, 83, 2), (4, 79, 2), (6, 74, 2), (8, 71, 2), (10, 74, 2), (12, 79, 3)],
]
FRASE_B = [
    [(0, 84, 3), (3, 79, 1), (4, 76, 2), (6, 79, 2), (8, 84, 3), (11, 79, 1), (12, 76, 4)],
    [(0, 81, 3), (3, 76, 1), (4, 72, 2), (6, 76, 2), (8, 81, 3), (11, 76, 1), (12, 72, 4)],
    [(0, 77, 3), (3, 81, 1), (4, 84, 2), (6, 81, 2), (8, 77, 3), (11, 74, 1), (12, 77, 4)],
    [(0, 83, 2), (2, 79, 2), (4, 74, 2), (6, 71, 2), (8, 72, 8)],
]


def notas(duracion):
    """Lista de notas (inicio_s, dur_s, tecla, vel, programa, pan, volumen) para tocar_notas."""
    rng = np.random.RandomState(5)
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
        if not intro and not final:
            for s in (0, 8):
                add(s, 2, 36, 122, KICK, 64, 127)
                add(s, 1, 60, 100, KICK, 64, 105)
            for s in (4, 12):
                add(s, 2, 50, 92, SNARE, 64, 110)
            if c % 4 == 3:
                add(14, 1, 50, 80, SNARE, 64, 100)      # remate
                add(15, 1, 50, 90, SNARE, 64, 100)
        for s in range(0, 16, 2):
            add(s, 1, 60, 76 if s % 4 == 0 else 54, HAT, 76, 95)
        # bajo saltarín: fundamental, quinta, nota de paso
        if not intro and not final:
            for s, d, up in ((0, 3, 0), (4, 2, 7), (8, 3, 0), (12, 2, 7), (14, 1, 12)):
                add(s, d, bajo + up, 116, BAJO, 64, 127)
        # acordes a contratiempo
        for s in (2, 6, 10, 14):
            for n in acorde:
                add(s, 1.2, n, 70 if intro else 80, PUNTEO, 42 if s < 8 else 86, 100)
        # melodía de campanilla (desde el compás 2): frase A y frase B alternas
        if c >= 2 and not final:
            frase = FRASE_A if ((c - 2) // 4) % 2 == 0 else FRASE_B
            for s, n, d in frase[c % 4]:
                add(s, d, n - 12, 98, CAMPANA, 64 + (12 if c % 2 else -12), 112)
        if final and c == n_compases - 2:
            add(0, 6, bajo, 112, BAJO, 64, 127)
            add(0, 3, 36, 120, KICK, 64, 127)
            for n in (72, 76, 79):
                add(0, 8, n - 12, 100, CAMPANA, 64, 112)
    return [n for n in out if n[0] < duracion]


def pista(audio_bank, duracion):
    return audio_bank.notes(notas(duracion), duracion, BANCO)
