"""Base de reguetón (dembow, 90 bpm, La menor: Am F C G) tocada con el banco BANK_BGM_FIELD de Platino.
Uso: python musica.py [duracion_s] [desfase_s]   -> base_dembow.wav (el desfase deja silencio al inicio para
que el compás caiga con el baile)."""
import glob
import os
import sys

import numpy as np

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import valrutas
import sonido  # noqa

BPM = 90
BEAT = 60 / BPM
ST = BEAT / 4                      # semicorchea
BARRA = BEAT * 4
RAICES = [33, 29, 36, 31]          # A1 F1 C2 G1
ACORDES = [(57, 60, 64), (53, 57, 60), (55, 60, 64), (55, 59, 62)]     # Am F C G (voicings medios)
# (paso, nota, duración en pasos) por compás de las 4 del ciclo
HOOK = [
    [(0, 76, 3), (3, 79, 1), (4, 76, 2), (6, 72, 2), (8, 74, 4)],
    [(0, 72, 3), (3, 76, 1), (4, 72, 2), (6, 69, 2), (8, 72, 4)],
    [(0, 76, 3), (3, 79, 1), (4, 84, 2), (6, 79, 2), (8, 76, 4)],
    [(0, 74, 3), (3, 71, 1), (4, 74, 2), (6, 79, 2), (8, 74, 2), (11, 71, 1), (12, 67, 4)],
]


def notas(n_barras):
    out = []
    P = lambda t, d, k, v, prog, pan=64, vol=127: out.append((t, d, k, v, prog, pan, vol))  # noqa
    for b in range(n_barras):
        t0 = b * BARRA
        c = b % 4
        seccion = b // 4                           # 0-1: solo ritmo y bajo; luego entra el resto
        for s in range(16):
            t = t0 + s * ST
            if s % 4 == 0:
                P(t, 0.2, 36, 120, 1)                                 # bombo a negras
            if s in (3, 6, 11, 14):
                P(t, 0.15, 38, 112 if s in (3, 11) else 96, 1)        # caja del dembow 3-3-2
            if s % 2 == 0:
                P(t, 0.08, 42, 80 if s % 4 == 0 else 58, 1, 80, 100)  # charles a corcheas
            if s == 14 and b % 2 == 1:
                P(t, 0.2, 46, 70, 1, 80, 100)
            if s == 0 and b % 4 == 0:
                P(t, 0.8, 49, 90, 1, 50, 90)                          # plato al inicio de frase
        for s in (0, 3, 6, 8, 11, 14):                                # bajo en tresillo
            P(t0 + s * ST, 0.17, RAICES[c] + (12 if s in (6, 14) else 0), 118, 33, 64, 127)
        if seccion >= 1:
            for s in (3, 6, 11, 14):                                   # acordes cortados (piano eléctrico)
                for k in ACORDES[c]:
                    P(t0 + s * ST, 0.11, k, 70, 4, 40, 110)
            for k in ACORDES[c]:                                       # colchón de cuerdas
                P(t0, BARRA * 0.97, k + 12, 52, 48, 88, 100)
        if seccion >= 1:
            for s, k, dur in HOOK[c]:                                  # estribillo en marimba
                P(t0 + s * ST, dur * ST * 0.9, k, 108, 12, 64, 127)
        if seccion >= 2:
            for s, k, dur in HOOK[c]:                                  # y trompeta una octava... a la par
                P(t0 + s * ST, dur * ST * 0.8, k + 12 if k < 80 else k, 78, 56, 90, 110)
    return out


if __name__ == '__main__':
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60
    des = float(sys.argv[2]) if len(sys.argv) > 2 else 0
    nb = int(np.ceil(dur / BARRA)) + 1
    son = sonido.Sonido(valrutas.rom())
    a = sonido.tocar_notas(son, 'BANK_BGM_FIELD', notas(nb), nb * BARRA + 1)
    if des >= 0:
        a = np.concatenate([np.zeros((int(des * sonido.FS), 2), np.float32), a])
    else:
        a = a[int(-des * sonido.FS):]            # empieza a mitad de compás
    a = a[:int((dur + 1) * sonido.FS)]
    # fundido de salida de 3 s al final y pico a 0,85
    n = int(3 * sonido.FS)
    a[-n:] *= np.linspace(1, 0, n, dtype=np.float32)[:, None]
    a = a / max(float(np.abs(a).max()), 1e-6) * 0.85
    sonido.guardar_wav(os.path.join(AQUI, (sys.argv[3] if len(sys.argv) > 3 else 'base_dembow.wav')), a)
    print('base_dembow.wav %.1f s' % (len(a) / sonido.FS))
