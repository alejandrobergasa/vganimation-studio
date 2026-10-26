"""Audio de Mario Kart DS: música y efectos sintetizados desde data/Sound/sound_data.sdat (sin nombres: se usan índices).

- Música: secuencia nº i  ->  bgm(i, segundos)
- Efectos: archivo SSAR s, secuencia k  ->  sfx_id(s, k, segundos)  (catálogo en assets_extraidos_mkds/audio/)
- `Mezcla` coloca clips en una línea de tiempo con ganancia, paneo y filtros sencillos."""
import os
import numpy as np

import sonido, mkrom
from . import CACHE

FS = sonido.FS
SDAT = 'data/Sound/sound_data.sdat'
_son = None
_DIR = os.path.join(CACHE, 'audio')
os.makedirs(_DIR, exist_ok=True)


def son():
    global _son
    if _son is None: _son = sonido.Sonido(mkrom.find_rom(), SDAT)
    return _son


def _cached(key, fn):
    p = os.path.join(_DIR, key + '.npy')
    if os.path.exists(p): return np.load(p)
    a = fn().astype(np.float32); np.save(p, a); return a


def bgm(i, segundos=None):
    """Música (secuencia i) renderizada; si el tema es un bucle infinito se corta en `segundos`."""
    def f():
        q = son().sdat.sequences[i][1]
        return sonido._Reproductor(son(), q, son().sdat.banks[q.bankID][1]).tocar(segundos)
    return _cached('bgm_%d_%s' % (i, segundos), f)


def sfx_id(ssar, k, segundos=None):
    """Efecto k del archivo de secuencias `ssar` (0..4)."""
    def f():
        ar = son().sdat.sequenceArchives[ssar][1]
        q = ar.sequences[k][1]
        class _S:
            eventsData = ar.eventsData
            bankID = q.bankID
            volume = q.volume
        return sonido._Reproductor(son(), _S, son().sdat.banks[q.bankID][1], q.firstEventOffset).tocar(segundos)
    return _cached('sfx_%d_%d_%s' % (ssar, k, segundos), f)


def recortar(a, umbral=1e-3, cola=0.08):
    """Quita el silencio final y suaviza la cola."""
    env = np.abs(a).max(1); idx = np.nonzero(env > umbral)[0]
    if len(idx): a = a[:idx[-1] + 1]
    n = min(len(a), int(cola * FS))
    a = a.copy(); a[-n:] *= np.linspace(1, 0, n)[:, None]
    return a


def normalizar(a, pico=0.9):
    m = np.abs(a).max()
    return a * (pico / m) if m > 1e-6 else a


def pitch(a, factor):
    """Cambio de tono por remuestreo (también cambia la duración)."""
    n = int(len(a) / factor)
    x = np.linspace(0, len(a) - 1, n)
    return np.stack([np.interp(x, np.arange(len(a)), a[:, c]) for c in range(2)], 1).astype(np.float32)


def fundido(a, entrada=0.0, salida=0.0):
    a = a.copy()
    if entrada > 0:
        n = min(len(a), int(entrada * FS)); a[:n] *= np.linspace(0, 1, n)[:, None]
    if salida > 0:
        n = min(len(a), int(salida * FS)); a[-n:] *= np.linspace(1, 0, n)[:, None]
    return a


class Mezcla:
    """Línea de tiempo estéreo. poner(clip, t, ganancia, pan) suma el clip en el segundo t."""
    def __init__(self, duracion):
        self.buf = np.zeros((int(duracion * FS) + FS, 2), np.float32)
        self.dur = duracion

    def poner(self, a, t, ganancia=1.0, pan=0.0):
        i = int(round(t * FS))
        if i >= len(self.buf) or i + len(a) <= 0: return
        a0 = max(0, -i); n = min(len(a) - a0, len(self.buf) - max(i, 0))
        g = np.array([ganancia * min(1, 1 - pan), ganancia * min(1, 1 + pan)], np.float32)
        self.buf[max(i, 0):max(i, 0) + n] += a[a0:a0 + n] * g

    def musica(self, a, t=0.0, ganancia=0.6, entrada=0.0, salida=0.0, hasta=None, curva=None):
        """curva(t_absoluto_array) -> multiplicador de ganancia (p. ej. subir el volumen en la salida)."""
        if hasta is not None: a = a[:int((hasta - t) * FS)]
        a = fundido(a, entrada, salida)
        if curva is not None:
            a = a * curva(t + np.arange(len(a)) / FS)[:, None].astype(np.float32)
        self.poner(a, t, ganancia)

    def sidechain(self, t0, t1, bajada=0.45, ataque=0.05, suelta=0.35, pista=None):
        """Baja la mezcla actual (música) entre t0 y t1; úsese antes de añadir los efectos."""
        env = np.ones(len(self.buf), np.float32)
        a, b = int(t0 * FS), int(t1 * FS)
        na, ns = int(ataque * FS), int(suelta * FS)
        env[max(0, a - na):a] = np.linspace(1, bajada, a - max(0, a - na))
        env[a:b] = bajada
        env[b:b + ns] = np.linspace(bajada, 1, len(env[b:b + ns]))
        self.buf *= env[:, None]

    def final(self, limite=0.93):
        x = self.buf[:int(self.dur * FS)].copy()
        x = np.tanh(x * 1.1) / np.tanh(1.1)          # limitador suave
        p = np.abs(x).max()
        if p > limite: x *= limite / p
        return x

    def guardar(self, ruta):
        sonido.guardar_wav(ruta, self.final())


def metricas(a):
    """(duración sin silencio final en s, pico, rms) de un clip."""
    env = np.abs(a).max(1); idx = np.nonzero(env > 1e-3)[0]
    dur = (idx[-1] + 1) / FS if len(idx) else 0.0
    return round(dur, 2), round(float(np.abs(a).max()), 3), round(float(np.sqrt((a ** 2).mean())), 4)


def _tarea_sfx(args):
    ssar, k, seg = args
    try:
        return args, metricas(sfx_id(ssar, k, seg))
    except Exception as e:
        return args, ('ERROR ' + repr(e)[:30], 0, 0)


def catalogar_sfx(seg=4, procesos=10, limite=6):
    """Renderiza todos los efectos en procesos aparte (algunas secuencias no terminan: se descartan por tiempo)."""
    import multiprocessing as mp
    trabajos = [(si, k, seg) for si, (_, ar) in enumerate(son().sdat.sequenceArchives) if ar is not None
                for k, (_, q) in enumerate(ar.sequences) if q is not None]
    res = {}
    pendientes = list(trabajos)
    while pendientes:
        pool = mp.get_context('spawn').Pool(procesos)
        try:
            lote = pendientes[:procesos * 4]
            asy = [(j, pool.apply_async(_tarea_sfx, (j,))) for j in lote]
            for j, r in asy:
                try:
                    res[j] = r.get(timeout=limite)[1]
                except mp.TimeoutError:
                    res[j] = ('TIMEOUT', 0, 0)
                    break
            pendientes = [j for j in pendientes if j not in res]
        finally:
            pool.terminate(); pool.join()
    return res
