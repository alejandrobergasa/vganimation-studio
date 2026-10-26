"""Música de fondo de REWINDLIMBO2 rehecha como un ARREGLO con los instrumentos de Pokémon Platino.

La versión 1 (musica_platino.py) copiaba nota a nota lo que basic-pitch sacaba de las pistas separadas: miles de
notas cortas y sueltas (también de los ruidos del montaje original), golpes de batería sueltos y un volumen que
bombeaba cada 0,5 s. Sonaba entrecortado y con racimos de ruido.

Aquí, para cada canción (corte musical) del original:
  1. rejilla de pulsos (beat tracking) y primer tiempo de cada compás (4/4);
  2. acordes pulso a pulso (plantillas de tríadas + Viterbi, con la tonalidad del corte como preferencia);
  3. bajo: en los golpes del bajo original, con su nota si encaja con el acorde (si no, la fundamental);
  4. cuerdas sostenidas con el acorde (conducción de voces suave) y un arpegio de arpa en corcheas;
  5. melodía: notas de basic-pitch cuadradas a semicorcheas, una sola voz, sólo las de la escala;
  6. batería: un patrón de 16 semicorcheas por corte (lo que se repite compás a compás en la batería original),
     tocado sólo en los compases en los que la batería original suena;
  7. volumen: constante por corte, igualado al de la música original, con fundidos suaves al cambiar de corte.
Banco BANK_BGM_FIELD (el de rutas y pueblos); los programas siguen la numeración General MIDI.

  python trabajo/rewindlimbo2/musica_platino2.py           -> audio/musica_platino.wav y audio/mezcla_final.wav
  python trabajo/rewindlimbo2/musica_platino2.py analisis  -> sólo imprime tempo, tono y acordes de cada corte
"""
import glob
import json
import os
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy import signal

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, '..', '..'))
sys.path.insert(0, os.path.join(RAIZ, 'tools'))
import valrutas
import sonido  # noqa

SEP = os.path.join(AQUI, 'audio', 'sep', 'htdemucs', 'original')
SR = 22050                     # análisis
HOP = 256
FS_OUT = 44100
BANCO = 'BANK_BGM_FIELD'
# programas (GM): batería, bajo, cuerdas, arpa, flauta
P_BATERIA, P_BAJO, P_CUERDAS, P_ARPA, P_MELODIA = 1, 32, 48, 46, 73
KICK, CAJA, CHARLES, PLATO = 36, 38, 42, 49

# Cortes musicales (segundo inicial, final, tempo aproximado). Salen de segmentar.py + analizar_musica.py.
CORTES = [(3.1, 222.5, 123), (222.5, 291.9, 108), (291.9, 301.4, 120), (301.4, 363.4, 136), (364.8, 424.4, 108),
          (424.4, 446.9, 144), (453.0, 490.8, 89), (490.8, 567.9, 123), (567.9, 591.4, 118), (591.4, 615.1, 152)]

NOMBRES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']
KS_MAY = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
KS_MEN = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
ESC_MAY, ESC_MEN = [0, 2, 4, 5, 7, 9, 11], [0, 2, 3, 5, 7, 8, 10, 11]   # menor con la sensible


def leer(n, sr=SR):
    a, fs = sf.read(os.path.join(SEP, n + '.wav'), dtype='float32')
    a = a.mean(1)
    return a if sr == fs else librosa.resample(a, orig_sr=fs, target_sr=sr)


# ============================================================ análisis

def tonalidad(croma):
    c = croma.mean(1)
    mejor = max(((np.corrcoef(c, np.roll(K, k))[0, 1], k, m) for K, m in ((KS_MAY, 0), (KS_MEN, 1))
                 for k in range(12)))
    return mejor[1], mejor[2], mejor[0]          # tónica, menor?, confianza


def pulsos(env, t0, t1, bpm):
    """Pulsos del corte: el beat tracker con el tempo aproximado; si el tempo sale casi constante, una rejilla
    perfecta ajustada a ellos (más limpia)."""
    _, b = librosa.beat.beat_track(onset_envelope=env, sr=SR, hop_length=HOP, start_bpm=bpm, tightness=300,
                                   trim=False)
    tb = librosa.frames_to_time(b, sr=SR, hop_length=HOP)
    if len(tb) < 8:
        per = 60 / bpm
        return np.arange(0, t1 - t0, per)
    idx = np.arange(len(tb))
    per, fase = np.polyfit(idx, tb, 1)
    res = tb - (idx * per + fase)
    if np.abs(res).max() < 0.07:
        k0 = int(np.floor(fase / per))
        return np.arange(fase - k0 * per, t1 - t0, per)
    # rellena huecos y extiende hasta los extremos
    out = list(tb)
    while out[0] - per > 0:
        out.insert(0, out[0] - per)
    while out[-1] + per < t1 - t0:
        out.append(out[-1] + per)
    return np.array(out)


def plantillas():
    T, nombres = [], []
    for r in range(12):
        for tipo, iv in (('', (0, 4, 7)), ('m', (0, 3, 7))):
            v = np.zeros(12)
            v[[(r + i) % 12 for i in iv]] = 1
            v[r] += 0.5                                   # la fundamental pesa más
            T.append(v / np.linalg.norm(v))
            nombres.append((r, tipo))
    return np.array(T), nombres


def acordes(croma_b, croma_bajo, tonica, menor):
    """Un acorde por pulso con Viterbi (el acorde tiende a mantenerse). croma_*: (12, n_pulsos)."""
    T, nombres = plantillas()
    escala = set((tonica + i) % 12 for i in (ESC_MEN if menor else ESC_MAY))
    X = croma_b + 0.6 * croma_bajo
    X = X / (np.linalg.norm(X, axis=0, keepdims=True) + 1e-9)
    sim = T @ X                                           # (24, n)
    prior = np.array([0.06 if all((r + i) % 12 in escala for i in ((0, 3, 7) if t == 'm' else (0, 4, 7)))
                      else 0.0 for r, t in nombres])
    obs = sim + prior[:, None]
    n = obs.shape[1]
    quedarse = 0.12
    D = obs[:, 0].copy()
    atras = np.zeros((24, n), int)
    for j in range(1, n):
        cambio = D.max()
        mejor = D.argmax()
        sigo = D + quedarse
        atras[:, j] = np.where(sigo >= cambio, np.arange(24), mejor)
        D = np.maximum(sigo, cambio) + obs[:, j]
    camino = [int(D.argmax())]
    for j in range(n - 1, 0, -1):
        camino.append(atras[camino[-1], j])
    camino.reverse()
    return [nombres[k] for k in camino], sim.max(0)


def por_pulso(M, tiempos_m, rejilla):
    """Media de las columnas de M (features con tiempos tiempos_m) dentro de cada intervalo de la rejilla."""
    out = np.zeros((M.shape[0], len(rejilla) - 1))
    for i in range(len(rejilla) - 1):
        s = (tiempos_m >= rejilla[i]) & (tiempos_m < rejilla[i + 1])
        if s.any():
            out[:, i] = M[:, s].mean(1)
    return out


def analizar(datos, t0, t1, bpm):
    i0, i1 = int(t0 * SR), int(t1 * SR)
    mezcla = datos['drums'][i0:i1] + datos['bass'][i0:i1] + datos['other'][i0:i1]
    env = librosa.onset.onset_strength(y=mezcla, sr=SR, hop_length=HOP)
    tb = pulsos(env, t0, t1, bpm)
    per = float(np.median(np.diff(tb)))
    # semicorcheas
    semis = np.concatenate([np.linspace(tb[i], tb[i + 1], 5)[:-1] for i in range(len(tb) - 1)] + [[tb[-1]]])
    armonia = datos['other'][i0:i1] + datos['bass'][i0:i1]
    cr = librosa.feature.chroma_cqt(y=armonia, sr=SR, hop_length=HOP)
    crb = librosa.feature.chroma_cqt(y=datos['bass'][i0:i1], sr=SR, hop_length=HOP, fmin=librosa.note_to_hz('E1'),
                                     n_octaves=3)
    tm = librosa.frames_to_time(np.arange(cr.shape[1]), sr=SR, hop_length=HOP)
    tonica, menor, conf = tonalidad(cr)
    tmb = librosa.frames_to_time(np.arange(crb.shape[1]), sr=SR, hop_length=HOP)
    # compases: fase del primer tiempo = donde más pega el bombo/bajo
    bajos = librosa.onset.onset_strength(y=datos['drums'][i0:i1] + datos['bass'][i0:i1], sr=SR, hop_length=HOP,
                                         fmax=200)
    tb_f = np.clip(librosa.time_to_frames(tb, sr=SR, hop_length=HOP), 0, len(bajos) - 1)
    fase = int(np.argmax([bajos[tb_f[k::4]].mean() for k in range(4)]))
    # acordes por medio compás (sólo cambian en el 1.º o el 3.º pulso), luego repartidos a cada pulso
    medios = [0] + list(range(fase % 2, len(tb) - 1, 2))[1 if fase % 2 == 0 else 0:] + [len(tb) - 1]
    medios = sorted(set(medios))
    rej = tb[medios]
    cp, cpb = por_pulso(cr, tm, rej), por_pulso(crb, tmb, rej)
    acs_m, fuerza = acordes(cp, cpb, tonica, menor)
    acs = []
    for k in range(len(medios) - 1):
        acs += [acs_m[k]] * (medios[k + 1] - medios[k])
    acs += [acs[-1]] * (len(tb) - len(acs))
    # energía armónica por pulso (para saber dónde hay música de verdad)
    rms = librosa.feature.rms(y=armonia, hop_length=HOP)[0]
    rms_p = por_pulso(rms[None], librosa.frames_to_time(np.arange(len(rms)), sr=SR, hop_length=HOP), tb)[0]
    return dict(t0=t0, t1=t1, tb=tb, per=per, semis=semis, tonica=tonica, menor=menor, conf=conf,
                acordes=acs, fuerza=fuerza, rms=rms_p, fase=fase)


# ============================================================ batería

def bateria(datos, A):
    """Patrón de 16 semicorcheas (bombo, caja, charles) del corte y compases donde suena la batería."""
    t0, t1 = A['t0'], A['t1']
    d = datos['drums'][int(t0 * SR):int(t1 * SR)]
    S = np.abs(librosa.stft(d, n_fft=1024, hop_length=HOP))
    f = librosa.fft_frequencies(sr=SR, n_fft=1024)
    tm = librosa.frames_to_time(np.arange(S.shape[1]), sr=SR, hop_length=HOP)
    bandas = {KICK: (30, 140), CAJA: (900, 4000), CHARLES: (6000, 11000)}
    semis = A['semis']
    fuerza = {}
    for tecla, (a, b) in bandas.items():
        e = np.log1p(S[(f >= a) & (f < b)].sum(0))
        flujo = np.maximum(0, np.diff(e, prepend=e[0]))
        v = np.zeros(len(semis))
        for i, t in enumerate(semis):
            s = (tm >= t - 0.035) & (tm < t + 0.035)
            v[i] = flujo[s].max() if s.any() else 0
        fuerza[tecla] = v / (np.percentile(v, 95) + 1e-9)
    # semicorchea 0 = primer tiempo de compás
    inicio = A['fase'] * 4
    n_comp = (len(semis) - inicio) // 16
    patron = {}
    for tecla, v in fuerza.items():
        M = np.array([v[inicio + c * 16:inicio + c * 16 + 16] for c in range(n_comp)]) if n_comp else np.zeros((1, 16))
        patron[tecla] = np.median(M, axis=0)
    # compases con batería: energía de la pista de batería
    rms = librosa.feature.rms(y=d, hop_length=HOP)[0]
    nivel = 20 * np.log10(rms + 1e-6)
    activos = []
    for c in range(n_comp):
        a, b = semis[inicio + c * 16], semis[min(len(semis) - 1, inicio + c * 16 + 15)]
        s = (tm >= a) & (tm < b)
        activos.append(bool(s.any() and np.median(nivel[s]) > -42))
    return patron, activos, inicio


def notas_bateria(A, patron, activos, inicio):
    out = []
    semis = A['semis'] + A['t0']
    pk = patron[KICK]
    ps = patron[CAJA]
    ph = patron[CHARLES]
    # umbrales relativos: lo que de verdad se repite
    kick = [i for i in range(16) if pk[i] > max(0.35, 0.55 * pk.max())]
    caja = [i for i in range(16) if ps[i] > max(0.35, 0.55 * ps.max()) and i not in kick]
    hat = [i for i in range(16) if ph[i] > max(0.3, 0.5 * ph.max())]
    if not kick:
        kick = [0, 8]
    if not caja:
        caja = [4, 12]
    if len(hat) < 4:
        hat = [0, 2, 4, 6, 8, 10, 12, 14]
    previo = False
    for c, act in enumerate(activos):
        base = inicio + c * 16
        if not act:
            previo = False
            continue
        if not previo:
            out.append((semis[base], 0.4, PLATO, 90))
        for i in range(16):
            k = base + i
            if k >= len(semis):
                break
            t = semis[k]
            if i in kick:
                out.append((t, 0.15, KICK, 112 if i == 0 else 96))
            if i in caja:
                out.append((t, 0.15, CAJA, 100))
            if i in hat:
                out.append((t, 0.08, CHARLES, 70 if i % 4 else 84))
        previo = True
    return [(t, d, k, v, P_BATERIA, 64, 100) for t, d, k, v in out]


# ============================================================ armonía, bajo y melodía

def voz_acorde(r, tipo, previa):
    """Tres notas del acorde entre 52 y 71, lo más cerca posible de la voz anterior."""
    iv = (0, 3, 7) if tipo == 'm' else (0, 4, 7)
    pcs = [(r + i) % 12 for i in iv]
    cands = []
    for base in range(52, 64):
        if base % 12 not in pcs:
            continue
        v = sorted([base] + [base + ((p - base) % 12) for p in pcs if p != base % 12])
        if v[-1] <= 71:
            cands.append(v)
    if previa is None:
        return min(cands, key=lambda v: abs(v[1] - 62))
    return min(cands, key=lambda v: sum(abs(a - b) for a, b in zip(v, previa)))


def pitch_bajo(datos, A):
    """Nota del bajo original por frame (pyin) y fuerza de sus ataques."""
    y = datos['bass'][int(A['t0'] * SR):int(A['t1'] * SR)]
    f0, voz, prob = librosa.pyin(y, fmin=35, fmax=300, sr=SR, hop_length=HOP * 2, frame_length=4096)
    tm = librosa.frames_to_time(np.arange(len(f0)), sr=SR, hop_length=HOP * 2)
    midi = np.where(voz, librosa.hz_to_midi(np.nan_to_num(f0, nan=1.0)), np.nan)
    env = librosa.onset.onset_strength(y=y, sr=SR, hop_length=HOP)
    te = librosa.frames_to_time(np.arange(len(env)), sr=SR, hop_length=HOP)
    rms = librosa.feature.rms(y=y, hop_length=HOP)[0]
    return tm, midi, te, env / (np.percentile(env, 95) + 1e-9), 20 * np.log10(rms + 1e-6)


def notas_armonia(datos, A, melodia_bp):
    tb = A['tb']
    t0 = A['t0']
    acs = A['acordes']
    hay = np.array(A['rms']) > 10 ** (-45 / 20)            # pulsos con música
    tonal = A['conf'] > 0.55
    out = []
    # ---- cuerdas y arpa por tramos de acorde
    previa = None
    i = 0
    n = min(len(acs), len(hay))
    while i < n:
        j = i
        while j + 1 < n and acs[j + 1] == acs[i] and hay[j + 1] == hay[i]:
            j += 1
        if hay[i]:
            r, tipo = acs[i]
            v = voz_acorde(r, tipo, previa)
            previa = v
            a, b = t0 + tb[i], t0 + tb[min(j + 1, len(tb) - 1)]
            for p in v:
                out.append((a, max(0.2, b - a - 0.02), p, 58, P_CUERDAS, 64, 72))
            if A['conf'] < 0.45:                          # armonía dudosa: sólo el colchón de cuerdas
                i = j + 1
                continue
            # arpa: corcheas subiendo y bajando por el acorde, una octava arriba
            ciclo = [v[0] + 12, v[1] + 12, v[2] + 12, v[1] + 24, v[2] + 12, v[1] + 12]
            k = 0
            for q in range(i, j + 1):
                if q + 1 >= len(tb):
                    break
                for media in (0, 0.5):
                    t = t0 + tb[q] + media * (tb[q + 1] - tb[q])
                    out.append((t, (tb[q + 1] - tb[q]) * 0.45, ciclo[k % len(ciclo)], 52 if media else 62,
                                P_ARPA, 84, 70))
                    k += 1
        i = j + 1
    # ---- bajo
    tm, midi, te, env, nivel = pitch_bajo(datos, A)
    corcheas = np.concatenate([np.linspace(tb[q], tb[q + 1], 3)[:-1] for q in range(len(tb) - 1)])
    golpes = []
    for k, t in enumerate(corcheas):
        q = k // 2
        if q >= n or not hay[q]:
            continue
        s = (te >= t - 0.04) & (te < t + 0.04)
        fuerte = s.any() and env[s].max() > 0.45
        sn = (te >= t) & (te < t + 0.2)
        suena = sn.any() and np.median(nivel[sn]) > -45
        if (fuerte and suena) or (k % 4 == 0):            # siempre en el 1.º y 3.º pulso (en corcheas: 0, 2...)
            golpes.append((k, t))
    for g, (k, t) in enumerate(golpes):
        q = k // 2
        r, tipo = acs[q]
        pcs = [(r + i) % 12 for i in ((0, 3, 7) if tipo == 'm' else (0, 4, 7))]
        s = (tm >= t) & (tm < t + 0.18)
        m = np.nanmedian(midi[s]) if s.any() and np.isfinite(midi[s]).sum() >= 2 else np.nan
        p = int(round(m)) if np.isfinite(m) and int(round(m)) % 12 in pcs else r
        p = 28 + ((p - 28) % 12)                          # entre E1 y Eb2
        if p < 31:
            p += 12
        fin = golpes[g + 1][1] if g + 1 < len(golpes) else t + 2 * A['per']
        dur = min(fin - t, 2 * A['per']) * 0.9
        out.append((t0 + t, max(0.08, dur), p, 96 if k % 8 == 0 else 84, P_BAJO, 64, 112))
    # ---- melodía
    if tonal:
        out += melodia(A, melodia_bp)
    return out


def melodia(A, notas_bp):
    """Una sola voz, cuadrada a semicorcheas, sólo notas de la escala y del registro de melodía."""
    t0, t1 = A['t0'], A['t1']
    semis = A['semis'] + t0
    escala = set((A['tonica'] + i) % 12 for i in (ESC_MEN if A['menor'] else ESC_MAY))
    paso = A['per'] / 4
    rej = {}
    for a, b, p, v in notas_bp:
        if not (t0 <= a < t1) or p < 62 or p > 88 or v < 50 or p % 12 not in escala:
            continue
        i = int(np.argmin(np.abs(semis - a)))
        if abs(semis[i] - a) > paso * 0.45:
            continue
        largo = max(1, int(round((b - a) / paso)))
        if largo < 2 and v < 70:
            continue                                      # notas sueltísimas y flojas: fuera
        if i not in rej or p > rej[i][0]:                 # la voz de arriba
            rej[i] = (p, largo, v)
    idx = sorted(rej)
    out = []
    for n, i in enumerate(idx):
        p, largo, v = rej[i]
        sig = idx[n + 1] if n + 1 < len(idx) else i + largo
        largo = min(largo, sig - i, 8)
        if out and out[-1][2] == p and abs(out[-1][0] + out[-1][1] - semis[i]) < paso * 0.6:
            a0, d0, *_ = out[-1]
            out[-1] = (a0, semis[min(i + largo, len(semis) - 1)] - a0 - 0.01, p, out[-1][3], P_MELODIA, 44, 92)
            continue
        fin = semis[min(i + largo, len(semis) - 1)]
        out.append((semis[i], max(0.06, fin - semis[i] - 0.01), p, int(min(110, 60 + v * 0.4)), P_MELODIA, 44, 92))
    # quita notas aisladas (sin vecinas en un compás): suelen ser ruido
    limpias = []
    for k, nt in enumerate(out):
        vec = [o for o in out if o is not nt and abs(o[0] - nt[0]) < 4 * A['per']]
        if len(vec) >= 2:
            limpias.append(nt)
    return limpias


# ============================================================ volumen

def volumen(musica, original, fs):
    """Ganancia por corte (constante, igualada en RMS) con fundidos de 0,4 s y silencio donde no hay música."""
    g = np.zeros(len(musica), np.float32)
    rmsw = lambda x: np.sqrt((x ** 2).mean() + 1e-12)
    for t0, t1, _ in CORTES:
        a, b = int(t0 * fs), min(int(t1 * fs), len(musica))
        # nivel típico del original en el corte (ventanas de 2 s, mediana de las que tienen música)
        w = 2 * fs
        ro = [rmsw(original[i:i + w]) for i in range(a, b, w)]
        rn = [rmsw(musica[i:i + w].mean(1)) for i in range(a, b, w)]
        ro_v = [x for x in ro if x > 10 ** (-50 / 20)]
        if not ro_v:
            continue
        k = np.median(ro_v) / max(np.median([y for x, y in zip(ro, rn) if x > 10 ** (-50 / 20)]), 1e-5)
        k = min(k, 6.0)
        # sigue la forma de la original muy suavizada (ventanas de 4 s), limitada a ±6 dB
        env = np.array([np.clip(x / np.median(ro_v), 0.5, 2.0) if x > 10 ** (-52 / 20) else 0.0 for x in ro])
        env = np.convolve(env, np.ones(2) / 2, 'same')
        cen = a + w / 2 + np.arange(len(env)) * w
        forma = np.interp(np.arange(a, b), cen, env).astype(np.float32)
        f = int(0.4 * fs)
        rampa = np.ones(b - a, np.float32)
        rampa[:f] = np.linspace(0, 1, min(f, b - a))[:len(rampa[:f])]
        rampa[-f:] = np.minimum(rampa[-f:], np.linspace(1, 0, min(f, b - a))[-len(rampa[-f:]):])
        g[a:b] = np.maximum(g[a:b], k * forma * rampa)
    return g


def limitar(x, techo=0.9, fs=44100):
    """Limitador con anticipación: baja la ganancia 5 ms antes de cada pico y la recupera en 150 ms, sin distorsionar."""
    from scipy.ndimage import maximum_filter1d
    nivel = np.abs(x).max(1) if x.ndim == 2 else np.abs(x)
    g = np.minimum(1.0, techo / np.maximum(nivel, 1e-9))
    ataque = int(0.005 * fs)
    g = -maximum_filter1d(-g, 2 * ataque + 1)              # mínimo en una ventana alrededor de cada muestra
    a = np.exp(-1 / (0.15 * fs))
    g = signal.lfilter([1 - a], [1, -a], g - 1) + 1         # recuperación suave
    g = np.minimum(g, -maximum_filter1d(-g, 2 * ataque + 1))
    g = signal.lfilter([1 / ataque] * ataque, [1], g)[np.minimum(np.arange(len(g)) + ataque // 2, len(g) - 1)]
    g = np.minimum(g, techo / np.maximum(nivel, 1e-9))     # garantía final
    g = np.minimum(g, 1.0).astype(np.float32)
    return x * (g[:, None] if x.ndim == 2 else g)


# ============================================================ principal

def main():
    datos = {n: leer(n) for n in ('drums', 'bass', 'other')}
    bp = json.load(open(os.path.join(AQUI, 'audio', 'notas_other.json')))
    solo_analisis = len(sys.argv) > 1 and sys.argv[1] == 'analisis'
    notas = []
    for t0, t1, bpm in CORTES:
        A = analizar(datos, t0, t1, bpm)
        cambios = [(round(A['t0'] + A['tb'][i], 1), NOMBRES[r] + tp) for i, (r, tp) in enumerate(A['acordes'])
                   if i == 0 or A['acordes'][i - 1] != (r, tp)]
        print('%6.1f-%6.1f  %5.1f bpm  %s%s (%.2f)  compás en pulso %d  %d acordes: %s' % (
            t0, t1, 60 / A['per'], NOMBRES[A['tonica']], 'm' if A['menor'] else '', A['conf'], A['fase'],
            len(cambios), ' '.join('%s@%s' % (c, t) for t, c in cambios[:12])), flush=True)
        if solo_analisis:
            continue
        patron, activos, inicio = bateria(datos, A)
        notas += notas_bateria(A, patron, activos, inicio)
        notas += notas_armonia(datos, A, bp)
    if solo_analisis:
        return
    print(len(notas), 'notas', flush=True)
    voz, fs = sf.read(os.path.join(SEP, 'vocals.wav'), dtype='float32')
    son = sonido.Sonido(valrutas.rom())
    a = sonido.tocar_notas(son, BANCO, notas, len(voz) / fs + 1)
    a = signal.resample_poly(a, FS_OUT, sonido.FS, axis=0).astype(np.float32)[:len(voz)]
    if len(a) < len(voz):
        a = np.pad(a, ((0, len(voz) - len(a)), (0, 0)))
    original = sum(sf.read(os.path.join(SEP, n + '.wav'), dtype='float32')[0].mean(1) for n in ('drums', 'bass', 'other'))
    g = volumen(a, original, fs)
    a = limitar(a * g[:, None], 0.7, fs)
    sf.write(os.path.join(AQUI, 'audio', 'musica_platino.wav'), a, fs, subtype='FLOAT')
    mezcla = limitar(voz + a * 0.85, 0.95, fs)
    sf.write(os.path.join(AQUI, 'audio', 'mezcla_final.wav'), mezcla, fs, subtype='FLOAT')
    print('->', os.path.join(AQUI, 'audio', 'mezcla_final.wav'))


if __name__ == '__main__':
    main()
