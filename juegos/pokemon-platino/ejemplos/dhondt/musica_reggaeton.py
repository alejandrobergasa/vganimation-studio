"""Instrumental de reggaetón (dembow, 94 bpm, La menor) tocada con los instrumentos de BANK_BGM_FIELD de Platino.

Uso: python musica_reggaeton.py <segundos> <salida.wav>
Programas del banco: 1 batería GM (36 bombo, 38 caja, 42/46 charles, 39 palmas), 33 bajo, 4 piano eléctrico,
12 marimba, 73 flauta, 48 cuerdas, 46 arpa.
"""
import glob
import os
import sys

import numpy as np

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import valrutas
import sonido  # noqa

BPM = 94
PASO = 60 / BPM / 4                         # una semicorchea
BATERIA, BAJO, PIANO, MARIMBA, FLAUTA, CUERDAS, ARPA = 1, 33, 4, 12, 73, 48, 46

# Am - F - C - G
RAICES = [33, 29, 36, 31]                   # bajo (A1, F1, C2, G1)
ACORDES = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62)]
# melodía de 4 compases: (paso del compás, duración en pasos, nota)
MELODIA = [
    [(0, 2, 76), (3, 1, 76), (4, 2, 74), (8, 2, 72), (11, 3, 69)],
    [(0, 2, 72), (3, 1, 72), (4, 2, 69), (8, 2, 72), (11, 3, 77)],
    [(0, 2, 76), (3, 1, 79), (4, 2, 76), (8, 2, 72), (11, 3, 76)],
    [(0, 2, 74), (3, 1, 74), (4, 2, 71), (8, 2, 74), (11, 5, 67)],
]
DEMBOW_CAJA = (3, 6, 11, 14)                # 3+3+2 de cada medio compás
BAJO_PASOS = (0, 3, 6, 8, 11, 14)

# secciones: (nombre, compases)
SECCIONES = [('intro', 4)] + [('verso', 8), ('estribillo', 8), ('puente', 4), ('estribillo', 8)] * 40


def compases(total):
    out, n = [], 0
    for nombre, cs in SECCIONES:
        for k in range(cs):
            if n >= total:
                return out
            out.append((nombre, k, cs))
            n += 1
    return out


def generar(segundos):
    total = int(np.ceil(segundos / (PASO * 16))) + 1
    notas = []

    def n(t, dur, tecla, vel, prog, pan=64, vol=100):
        notas.append((t, dur, tecla, vel, prog, pan, vol))

    cs = compases(total)
    for i, (sec, k, longitud) in enumerate(cs):
        t0 = i * 16 * PASO
        acorde, raiz = ACORDES[i % 4], RAICES[i % 4]
        ultimo = (i == len(cs) - 1)
        base = sec in ('verso', 'estribillo')
        # batería
        if sec == 'intro':
            for p in range(0, 16, 2):
                n(t0 + p * PASO, PASO, 42, 50 + 14 * (p % 4 == 0), BATERIA, 80, 90)
            if k >= 2:
                for p in (0, 4, 8, 12):
                    n(t0 + p * PASO, PASO * 2, 36, 100, BATERIA, 64, 110)
        elif sec == 'puente':
            for p in (0, 8):
                n(t0 + p * PASO, PASO * 2, 36, 112, BATERIA, 64, 112)
            if k == longitud - 1:                         # redoble hacia el estribillo
                for p in range(8, 16):
                    n(t0 + p * PASO, PASO, 38, 60 + p * 5, BATERIA, 64, 105)
        else:
            for p in (0, 4, 8, 12):
                n(t0 + p * PASO, PASO * 2, 36, 120, BATERIA, 64, 118)
            for p in DEMBOW_CAJA:
                n(t0 + p * PASO, PASO, 38, 112 if p in (3, 11) else 96, BATERIA, 64, 112)
            for p in range(0, 16, 2):
                n(t0 + p * PASO, PASO, 42, 78 if p % 4 else 98, BATERIA, 84, 88)
            n(t0 + 14 * PASO, PASO * 2, 46, 70, BATERIA, 84, 82)
        # bajo
        if sec != 'intro' or k >= 2:
            pasos = BAJO_PASOS if base else (0, 8)
            for p in pasos:
                n(t0 + p * PASO, PASO * (2 if p in (0, 8) else 1.4), raiz + (12 if p == 14 else 0), 118, BAJO, 64, 118)
        # piano eléctrico: acordes sincopados
        if base or k >= 1:
            for p in ((0, 3, 6, 8, 11, 14) if sec == 'estribillo' else (3, 6, 11, 14)):
                for tecla in acorde:
                    n(t0 + p * PASO, PASO * 1.6, tecla, 70, PIANO, 40, 92)
        # cuerdas largas en el puente y el verso
        if sec in ('puente', 'verso', 'intro'):
            for tecla in acorde:
                n(t0, PASO * 15, tecla + 12, 60, CUERDAS, 90, 80)
        # arpa en la intro
        if sec == 'intro':
            for j, tecla in enumerate(acorde * 2):
                n(t0 + j * 2 * PASO, PASO * 3, tecla + 12, 80, ARPA, 64, 100)
        # melodía
        if sec == 'estribillo' or (sec == 'verso' and k >= 4):
            prog = MARIMBA if sec == 'verso' else FLAUTA
            for p, d, tecla in MELODIA[i % 4]:
                n(t0 + p * PASO, d * PASO * 0.95, tecla, 105, prog, 64, 108)
                if sec == 'estribillo':
                    n(t0 + p * PASO, d * PASO * 0.95, tecla - 12, 80, MARIMBA, 40, 96)
        if ultimo:
            n(t0 + 16 * PASO, 1.2, 36, 120, BATERIA, 64, 118)
            for tecla in ACORDES[0]:
                n(t0 + 16 * PASO, 1.5, tecla, 100, PIANO, 64, 100)
    return notas


def main():
    seg = float(sys.argv[1])
    salida = sys.argv[2]
    notas = [x for x in generar(seg) if x[0] < seg]
    son = sonido.Sonido(valrutas.rom())
    a = sonido.tocar_notas(son, 'BANK_BGM_FIELD', notas, seg)
    a = a[:int(seg * sonido.FS)]
    pico = float(np.abs(a).max()) or 1.0
    a = a / pico * 0.85
    fade = int(2.5 * sonido.FS)
    a[-fade:] *= np.linspace(1, 0, fade)[:, None]
    sonido.guardar_wav(salida, a)
    print('%.1f s -> %s' % (len(a) / sonido.FS, salida))


if __name__ == '__main__':
    main()
