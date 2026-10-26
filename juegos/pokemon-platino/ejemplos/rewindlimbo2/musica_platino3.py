"""Música de REWINDLIMBO2 v3: la canción ORIGINAL tocada nota a nota con los instrumentos de Pokémon Platino.

La v1 (musica_platino.py) tocaba las notas de basic-pitch tal cual y se trababa; la v2 (musica_platino2.py) las
cambiaba por un arreglo de acordes y dejaba de reconocerse la canción. Aquí se tocan las notas de verdad, pero
limpias:
  - rejilla de pulsos de cada corte (analizar() de la v2) y notas ajustadas a la semicorchea cuando caen cerca;
  - fuera los armónicos falsos (octava, 12.ª y doble octava de una nota más fuerte que empieza a la vez) y las
    notas débiles del corte;
  - los trozos seguidos de la misma nota se unen y las notas cortadas se alargan hasta la siguiente (legato);
  - la melodía (la voz más aguda, una sola nota a la vez) va con el instrumento principal, el resto de notas
    con un acompañamiento suave de como mucho 3 voces, y el bajo con su línea monofónica;
  - batería del original golpe a golpe, pero sobre la rejilla de semicorcheas;
  - volumen constante por corte (sin bombeo) y limitador.

  python musica_platino3.py            -> audio/musica_platino.wav y audio/mezcla_final.wav
  python musica_platino3.py comparar   -> parecido (croma) de v1, v2 y v3 con la música original
"""
import glob
import json
import os
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import valrutas  # noqa: E402
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy import signal

from musica_platino2 import (AQUI, BANCO, CORTES, FS_OUT, SEP, SR, HOP, analizar, leer, limitar, sonido,  # noqa
                             volumen, RAIZ)

P_BATERIA, P_BAJO, P_MELODIA, P_CORTA, P_LARGA = 1, 33, 2, 4, 48
KICK, CAJA, CHARLES = 36, 38, 42


# ============================================================ limpieza de notas

def ajustar(t, rejilla, paso, tol=0.4):
    """Lleva t a la semicorchea más cercana si está a menos de tol pasos."""
    i = np.searchsorted(rejilla, t)
    cands = [rejilla[k] for k in (i - 1, i) if 0 <= k < len(rejilla)]
    if not cands:
        return t
    g = min(cands, key=lambda g: abs(g - t))
    return g if abs(g - t) < tol * paso else t


def limpiar(notas, rejilla, paso, umbral_vel):
    """notas: [a, b, tono, vel] en segundos absolutos. Devuelve la lista ajustada y limpia."""
    ns = [[ajustar(a, rejilla, paso), ajustar(b, rejilla, paso), int(p), v] for a, b, p, v in notas if v >= umbral_vel]
    for n in ns:
        n[1] = max(n[1], n[0] + paso * 0.9)
    # armónicos falsos: misma salida que una nota más fuerte 12, 19 o 24 semitonos por debajo
    ns.sort(key=lambda n: n[0])
    fuera = set()
    for i, n in enumerate(ns):
        for j in range(i - 1, -1, -1):
            m = ns[j]
            if n[0] - m[0] > paso * 0.6:
                break
            if n[2] - m[2] in (12, 24) and n[3] <= m[3] * 0.8:
                fuera.add(i)
        for j in range(i + 1, len(ns)):
            m = ns[j]
            if m[0] - n[0] > paso * 0.6:
                break
            if n[2] - m[2] in (12, 24) and n[3] <= m[3] * 0.8:
                fuera.add(i)
    ns = [n for i, n in enumerate(ns) if i not in fuera]
    # une trozos seguidos de la misma nota
    ns.sort(key=lambda n: (n[2], n[0]))
    unidas = []
    for n in ns:
        u = unidas[-1] if unidas else None
        if u and u[2] == n[2] and n[0] - u[1] < paso * 0.6:
            u[1] = max(u[1], n[1])
            u[3] = max(u[3], n[3])
        else:
            unidas.append(list(n))
    return sorted(unidas, key=lambda n: (n[0], -n[2]))


def monofonica(ns, paso, prefiere='agudo'):
    """Una sola nota a la vez: en cada inicio gana la más aguda (melodía) o la más fuerte (bajo); cada nota dura
    hasta la siguiente si el hueco es pequeño (legato) y nunca se solapa."""
    porinicio = {}
    for n in ns:
        k = round(n[0], 3)
        if k not in porinicio or (n[2] if prefiere == 'agudo' else n[3]) > \
                (porinicio[k][2] if prefiere == 'agudo' else porinicio[k][3]):
            porinicio[k] = list(n)
    out = sorted(porinicio.values())
    for i in range(len(out) - 1):
        sig = out[i + 1][0]
        if sig - out[i][1] < paso * 1.1:
            out[i][1] = sig
        out[i][1] = min(out[i][1], sig)
    return [n for n in out if n[1] - n[0] > paso * 0.45]


def polifonia(ns, maximo):
    out, sonando = [], []
    for n in sorted(ns, key=lambda n: (n[0], -n[3])):
        sonando = [s for s in sonando if s[1] > n[0] + 1e-3]
        if len(sonando) >= maximo:
            peor = min(sonando, key=lambda s: s[3])
            if peor[3] >= n[3]:
                continue
            peor[1] = n[0]
            sonando.remove(peor)
        sonando.append(n)
        out.append(n)
    return [n for n in out if n[1] - n[0] > 0.03]


def melodia_y_resto(ns, paso):
    """Separa la línea de arriba (la que se canta/silba) del acompañamiento."""
    candidatas = [n for n in ns if n[2] >= 60]
    if not candidatas:
        return [], ns
    vmin = np.percentile([n[3] for n in candidatas], 25)
    mel = monofonica([n for n in candidatas if n[3] >= vmin], paso, 'agudo')
    claves = {(round(n[0], 3), n[2]) for n in mel}
    resto = [n for n in ns if (round(n[0], 3), n[2]) not in claves]
    return mel, resto


# ============================================================ batería sobre la rejilla

def bateria_rejilla(datos, A):
    t0, t1 = A['t0'], A['t1']
    d = datos['drums'][int(t0 * SR):int(t1 * SR)]
    S = np.abs(librosa.stft(d, n_fft=1024, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    tm = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
    rms = 20 * np.log10(librosa.feature.rms(y=d, hop_length=HOP)[0] + 1e-6)
    semis = A['semis']
    out = []
    for tecla, (a, b), umbral in ((KICK, (30, 140), 0.42), (CAJA, (900, 4000), 0.45), (CHARLES, (6000, 11000), 0.4)):
        e = np.log1p(S[(f >= a) & (f < b)].sum(0))
        flujo = np.maximum(0, np.diff(e, prepend=e[0]))
        v = np.zeros(len(semis))
        nivel = np.full(len(semis), -99.0)
        for i, t in enumerate(semis):
            s = (tm >= t - 0.03) & (tm < t + 0.03)
            if s.any():
                v[i] = flujo[s].max()
                nivel[i] = rms[s].max()
        v = v / (np.percentile(v, 95) + 1e-9)
        for i, t in enumerate(semis):
            if v[i] > umbral and nivel[i] > -42:
                out.append((t0 + t, 0.12, tecla, int(np.clip(55 + 55 * min(1.0, v[i]), 55, 115)), P_BATERIA, 64, 105))
    return out


# ============================================================ notas de cada corte

def notas_corte(A, otro, bajo):
    t0, t1 = A['t0'], A['t1']
    rejilla = t0 + A['semis']
    paso = A['per'] / 4
    dentro = lambda ns: [n for n in ns if t0 <= n[0] < t1]
    o = dentro(otro)
    b = dentro(bajo)
    out = []
    if o:
        uo = max(30, np.percentile([n[3] for n in o], 12))
        lo = limpiar([n for n in o if 40 <= n[2] <= 96], rejilla, paso, uo)
        mel, resto = melodia_y_resto(lo, paso)
        for a, z, p, v in mel:
            out.append((a, z - a, p, int(min(120, 50 + v * 0.7)), P_MELODIA, 64, 100))
        for a, z, p, v in polifonia([n for n in resto if 40 <= n[2] <= 90], 4):
            d = z - a
            if d < A['per'] * 0.9:
                out.append((a, d, p, int(min(110, 35 + v * 0.6)), P_CORTA, 48, 80))
            else:
                out.append((a, d, p, int(min(105, 30 + v * 0.6)), P_LARGA, 80, 72))
    if b:
        ub = max(28, np.percentile([n[3] for n in b], 10))
        lb = monofonica(limpiar(b, rejilla, paso, ub), paso, 'fuerte')
        for a, z, p, v in lb:
            while p > 52:
                p -= 12
            while p < 28:
                p += 12
            out.append((a, (z - a) * 0.95, p, int(min(120, 55 + v * 0.6)), P_BAJO, 64, 110))
    return out


def cargar_notas(nombre):
    return [list(n) for n in json.load(open(os.path.join(AQUI, 'audio', nombre)))]


# ============================================================ comparar con la original

def parecido(ruta, original, fs):
    """Correlación media del croma (por corte) entre una versión y la música original."""
    a, fa = sf.read(ruta, dtype='float32')
    a = a.mean(1) if a.ndim == 2 else a
    res = []
    for t0, t1, _ in CORTES:
        x = librosa.resample(a[int(t0 * fa):int(t1 * fa)], orig_sr=fa, target_sr=SR)
        y = librosa.resample(original[int(t0 * fs):int(t1 * fs)], orig_sr=fs, target_sr=SR)
        cx = librosa.feature.chroma_cqt(y=x, sr=SR, hop_length=1024)
        cy = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=1024)
        n = min(cx.shape[1], cy.shape[1])
        cx, cy = cx[:, :n], cy[:, :n]
        e = librosa.feature.rms(y=y, hop_length=1024)[0][:n]
        ok = e > 10 ** (-45 / 20)
        num = (cx * cy).sum(0)
        den = np.linalg.norm(cx, axis=0) * np.linalg.norm(cy, axis=0) + 1e-9
        res.append(float((num / den)[ok].mean()) if ok.any() else float('nan'))
    return res


def comparar():
    original = sum(sf.read(os.path.join(SEP, n + '.wav'), dtype='float32')[0].mean(1) for n in ('bass', 'other'))
    fs = 44100
    vs = [('v1', 'musica_platino_v1.wav'), ('v2', 'musica_platino_v2.wav'), ('v3', 'musica_platino.wav')]
    tabla = {v: parecido(os.path.join(AQUI, 'audio', r), original, fs) for v, r in vs
             if os.path.exists(os.path.join(AQUI, 'audio', r))}
    print('corte          ' + '  '.join('%5s' % v for v in tabla))
    for i, (t0, t1, _) in enumerate(CORTES):
        print('%6.1f-%6.1f  ' % (t0, t1) + '  '.join('%5.2f' % tabla[v][i] for v in tabla))
    print('media          ' + '  '.join('%5.2f' % np.nanmean(tabla[v]) for v in tabla))


# ============================================================ principal

def main():
    datos = {n: leer(n) for n in ('drums', 'bass', 'other')}
    otro, bajo = cargar_notas('notas_other.json'), cargar_notas('notas_bass.json')
    notas = []
    for t0, t1, bpm in CORTES:
        A = analizar(datos, t0, t1, bpm)
        nc = notas_corte(A, otro, bajo)
        nb = bateria_rejilla(datos, A)
        print('%6.1f-%6.1f  %5.1f bpm  melodía %d  acomp. %d  bajo %d  batería %d' % (
            t0, t1, 60 / A['per'], sum(n[4] == P_MELODIA for n in nc), sum(n[4] in (P_CORTA, P_LARGA) for n in nc),
            sum(n[4] == P_BAJO for n in nc), len(nb)), flush=True)
        notas += nc + nb
    voz, fs = sf.read(os.path.join(SEP, 'vocals.wav'), dtype='float32')
    son = sonido.Sonido(valrutas.rom())
    a = sonido.tocar_notas(son, BANCO, notas, len(voz) / fs + 1)
    a = signal.resample_poly(a, FS_OUT, sonido.FS, axis=0).astype(np.float32)[:len(voz)]
    if len(a) < len(voz):
        a = np.pad(a, ((0, len(voz) - len(a)), (0, 0)))
    original = sum(sf.read(os.path.join(SEP, n + '.wav'), dtype='float32')[0].mean(1) for n in ('drums', 'bass', 'other'))
    a = limitar(a * volumen(a, original, fs)[:, None], 0.7, fs)
    sf.write(os.path.join(AQUI, 'audio', 'musica_platino.wav'), a, fs, subtype='FLOAT')
    mezcla = limitar(voz + a * 0.85, 0.95, fs)
    sf.write(os.path.join(AQUI, 'audio', 'mezcla_final.wav'), mezcla, fs, subtype='FLOAT')
    print('->', os.path.join(AQUI, 'audio', 'mezcla_final.wav'))


if __name__ == '__main__':
    comparar() if len(sys.argv) > 1 and sys.argv[1] == 'comparar' else main()
