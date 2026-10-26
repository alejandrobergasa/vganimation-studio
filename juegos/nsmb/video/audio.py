"""Mezcla de música y efectos (sintetizados desde sound_data.sdat) sincronizada con los eventos de la simulación."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'nsmb'))
import numpy as np
import sonido, rom
from rom import rutas

FS = sonido.FS
SFX = {'jump': 'SE_PLY_JUMP', 'coin': 'SE_OBJ_GET_COIN', 'stomp': 'SE_EMY_KURIBO_FUMU', 'flag': 'SE_SYS_GOAL_FLAG', 'bump': 'SE_PLY_HIT_BLOCK'}
CACHE = rutas.cache('nsmb')
_son = None


def son():
    global _son
    if _son is None: _son = sonido.Sonido(rom.find_rom())
    return _son


def _cached(key, fn):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, key + '.npy')
    if os.path.exists(p): return np.load(p)
    a = fn().astype(np.float32); np.save(p, a); return a


def bgm(name, seconds=None):
    return _cached('bgm_%s_%s' % (name, seconds), lambda: son().renderizar(name, seconds))


SFX_SECONDS = {'flag': 1.7, 'jump': 0.5, 'coin': 1.2, 'stomp': 0.4, 'bump': 0.5}
SFX_GAIN = {'jump': 3.0, 'coin': 5.0, 'stomp': 6.0, 'flag': 2.5, 'bump': 0.8}


def sfx(key):
    """Efecto ya recortado (algunos SE de la ROM son bucles que el juego corta por código) y con cola suavizada."""
    def render():
        a = son().efecto(SFX[key], SFX_SECONDS[key])
        env = np.abs(a).max(1); idx = np.nonzero(env > 1e-3)[0]
        a = a[:idx[-1] + 1] if len(idx) else a
        n = min(len(a), int(0.12 * FS)); a = a.copy(); a[-n:] *= np.linspace(1, 0, n)[:, None]
        return a
    return _cached('sfx2_' + key, render)


def put(mix, a, t, gain=1.0):
    i = int(t * FS)
    if i >= len(mix): return
    n = min(len(a), len(mix) - i)
    mix[i:i + n] += a[:n] * gain


def build(events, total, flag_t, clear_t):
    """events: [(segundos, nombre)]. flag_t: instante en que Mario agarra la bandera; clear_t: inicio de la fanfarria."""
    mix = np.zeros((int(total * FS) + FS, 2), np.float32)
    m = bgm('BGM_CHIJO', flag_t + 2); m = m / max(np.abs(m).max(), 1e-6) * 0.8
    m = m[:int((flag_t - 0.6) * FS)].copy()
    n = int(0.5 * FS); m[-n:] *= np.linspace(1, 0, n)[:, None]               # corte con fundido al agarrar la bandera
    fade_in = int(0.4 * FS); m[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    put(mix, m, 0.0)
    fan = bgm('BGM_COURSE_CLEAR'); put(mix, fan / max(np.abs(fan).max(), 1e-6) * 0.9, clear_t)
    for t, name in events:
        if name in SFX:
            put(mix, sfx(name), t, SFX_GAIN[name])
    peak = np.abs(mix).max()
    if peak > 0.92: mix *= 0.92 / peak
    return mix


def write_wav(path, mix):
    sonido.guardar_wav(path, mix)
