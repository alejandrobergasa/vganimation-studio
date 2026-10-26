"""Música de «BOLAS NEGRAS»: pieza original tocada con el banco 50 de Mario Kart DS (ver mk/musica.py), en 5 secciones
ligadas al guion. Genera `musica/muestra.wav` (pieza completa, solo música: sin voces ni efectos) y `musica/partitura.json`.
    python valedores.py ejecutar bolas_negras -- python -I proyectos/bolas_negras/musica_bn.py"""
import os, sys, json
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'nucleo'))
from valedores import rutas
JUEGO = 'mkds'
sys.path.insert(0, rutas.motor_dir(JUEGO))
import numpy as np
import mk                                  # deja en el path la librería Nitro (sonido, nftr...)
import sonido
from mk import audio as A
from mk.musica import *

DIR = os.path.dirname(os.path.abspath(__file__))
DUR = 36.0
# instantes del guion (s)
T_CINE, T_PEDRO, T_PAGAN, T_ENTRAN, T_SANTOS, T_ZOOM, T_BUSCAN = 12.0, 16.0, 19.0, 24.0, 24.0, 28.0, 32.5


def acorde(base, mayor=True):
    return [base, base + (4 if mayor else 3), base + 7]


# ---------------------------------------------------------------- 1. carretera (0–12 s) y 2. aparcamiento (12–16 s)
def carretera(dur, bpm=120, raiz=45, con_lead=True, ligera=False):
    """La mayor, progresión I–IV–V–IV; 4 compases = un ciclo. `ligera` quita bombo/caja y deja el pulso."""
    p = Partitura(dur)
    b = 60.0 / bpm
    prog = [0, 5, 7, 5]                                           # A  D  E  D
    lead = [   # por compás: (pulso, duración en pulsos, tecla)
        [(0, 1, 76), (1, .5, 73), (1.5, .5, 76), (2, 1, 78), (3, 1, 76)],
        [(0, 1, 74), (1, .5, 78), (1.5, .5, 74), (2, 1, 73), (3, 1, 71)],
        [(0, 1, 76), (1, .5, 80), (1.5, .5, 76), (2, 1, 71), (3, 1, 68)],
        [(0, 1.5, 69), (1.5, .5, 74), (2, 1, 73), (3, 1, 69)],
    ]
    for bar in range(int(dur / (4 * b)) + 1):
        t0 = bar * 4 * b
        r = raiz + prog[bar % 4]
        for i, o in enumerate([0, 0, 12, 0, 7, 12, 7, 12]):
            p.n(t0 + i * b / 2, b * 0.42, r + o, BAJO, 104 if i % 4 == 0 else 86, 58)
        for beat in (1, 3):
            for k in acorde(r + 24):
                p.n(t0 + beat * b + b * 0.5, b * 0.28, k, ACORDE, 82, 78)
        if con_lead:
            oct_ = 12 if (bar // 4) % 2 else 0                    # el segundo ciclo, una octava arriba
            for (pu, d, k) in lead[bar % 4]:
                p.n(t0 + pu * b, d * b * 0.9, k + oct_, LEAD, 88, 70)
        if not ligera:
            for i in range(4):
                p.bat(t0 + i * b, 'k' if i % 2 == 0 else 's', 118 if i % 2 == 0 else 108)
        for i in range(8):
            p.bat(t0 + i * b / 2, 'h', 64 + (16 if i % 2 == 0 else 0))
    p.bat(0, 'c', 100)
    return p


# ---------------------------------------------------------------- 3. portero (16–24 s): suspense cómico en La menor
def portero(dur, bpm=92, raiz=33):
    p = Partitura(dur)
    b = 60.0 / bpm
    for i in range(int(dur / b) + 1):
        t = i * b
        p.n(t, b * 0.95, raiz + [0, 0, 0, 7, 0, 0, 3, 5][i % 8], BAJO, 92, 56)
        if i % 4 == 0:
            for k in acorde(raiz + 24, False): p.n(t, b * 4.1, k, PAD, 60, 70, 90)
        if i % 2 == 1: p.bat(t + b / 2, 'h', 56)
        if i % 4 == 0: p.bat(t, 'k', 86)
    # «moneda»: arpegio ascendente cuando pagan (T_PAGAN - 16 y +1,2 s)
    for t0 in (T_PAGAN - T_PEDRO, T_PAGAN - T_PEDRO + 1.9):
        for j, k in enumerate((81, 85, 88, 93)):
            p.n(t0 + j * 0.07, 0.5, k, CAMP, 100, 64 + (j - 2) * 10)
    # «pasen, pasen»: cadencia corta y brillante al entrar
    t = 22.0 - T_PEDRO
    for j, k in enumerate((57, 61, 64, 69)):
        p.n(t + j * 0.12, 0.8, k, METAL, 96, 64)
    return p


# ---------------------------------------------------------------- 4. Santos (24–32,5 s): lamento en La menor, 60 bpm
def santos(dur, bpm=60, raiz=45):
    p = Partitura(dur)
    b = 60.0 / bpm
    prog = [(0, False), (-4, True), (-9, True), (-5, True)]       # Am  F  C  E (F, C y E mayores; Am menor)
    for bar in range(int(dur / (4 * b)) + 1):
        t0 = bar * 4 * b
        off, may = prog[bar % 4]
        r = raiz + off
        for k in acorde(r + 12, may): p.n(t0, b * 3.9, k, PAD, 70, 64, 92)
        p.n(t0, b * 3.9, r - 12, BAJO, 84, 60)
        p.n(t0 + 2 * b, b * 1.8, r - 12 + 7, BAJO, 70, 60)
    # melodía descendente y triste (tecla, inicio en pulsos, duración)
    mel = [(76, 1, 2), (74, 3, 2), (72, 5, 2), (71, 7, 1), (69, 8, 3)]
    for k, tb, d in mel:
        p.n(tb * b, d * b * 0.95, k, LEAD, 82, 70)
    # latido grave que acompaña al zoom hacia la cara
    for i in range(int((dur - (T_ZOOM - T_SANTOS)) / (b / 2))):
        t = (T_ZOOM - T_SANTOS) + i * b / 2
        p.bat(t, 'k', int(60 + 5 * i))
    return p


# ---------------------------------------------------------------- 5. «¿QUÉ BUSCAN?» (32,5–36 s): golpe seco + cola
def golpe_final(dur):
    p = Partitura(dur)
    for k in (45, 52, 57, 60, 64): p.n(0, 3.2, k, METAL, 120, 64)   # La menor con novena sin resolver
    p.n(0, 3.2, 33, BAJO, 118, 64)
    p.bat(0, 'c', 120); p.bat(0, 'k', 120)
    return p


SECCIONES = [   # (nombre, inicio, partitura, ganancia, fundido de entrada, fundido de salida)
    ('carretera', 0.0, carretera(T_CINE, 120), 0.85, 0.0, 0.0),
    ('aparcar', T_CINE, carretera(T_PEDRO - T_CINE, 120, con_lead=False, ligera=True), 0.7, 0.0, 0.0),
    ('portero', T_PEDRO, portero(T_SANTOS - T_PEDRO), 0.8, 0.0, 0.05),
    ('santos', T_SANTOS, santos(T_BUSCAN - T_SANTOS), 0.85, 0.05, 0.0),
    ('golpe', T_BUSCAN, golpe_final(DUR - T_BUSCAN), 0.9, 0.0, 1.5),
]


def componer():
    m = A.Mezcla(DUR)
    for nombre, t0, part, g, f_in, f_out in SECCIONES:
        a = part.render()
        m.musica(a, t=t0, ganancia=g, entrada=f_in, salida=f_out, hasta=min(DUR, t0 + part.dur))
    return m


if __name__ == '__main__':
    os.makedirs(os.path.join(DIR, 'musica'), exist_ok=True)
    m = componer()
    sonido.guardar_wav(os.path.join(DIR, 'musica', 'muestra.wav'), m.final())
    json.dump({n: {'inicio': t0, 'dur': p.dur, 'notas': p.notas} for n, t0, p, *_ in SECCIONES},
              open(os.path.join(DIR, 'musica', 'partitura.json'), 'w'))
    x = m.final()
    print('duración %.2f s · pico %.3f · rms %.4f' % (len(x) / A.FS, np.abs(x).max(), np.sqrt((x ** 2).mean())))
