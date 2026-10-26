"""Pista de audio de una escena: música y efectos de sonido del juego (SSEQ del ROM).

Las secuencias se sintetizan con tools/sonido.py y se guardan en cinematicas/cache/audio/.
"""
import os
import sys

import numpy as np

from .recursos import RAIZ, JUEGO, rutas
from .recursos import CACHE as _CACHE

CACHE = os.path.join(_CACHE, 'audio')
_son = None


def _sonido():
    global _son
    if _son is None:
        sys.path.insert(0, os.path.join(RAIZ, 'tools'))
        import sonido
        _son = sonido.Sonido(rutas.rom(JUEGO))
    return _son


def fs():
    sys.path.insert(0, os.path.join(RAIZ, 'tools'))
    import sonido
    return sonido.FS


def secuencia(nombre, segundos=None):
    """Audio (n, 2) float32 de la secuencia, normalizado a pico 1. La música (con bucle) se renderiza
    hasta 'segundos' redondeado a 30 s; los efectos, enteros."""
    os.makedirs(CACHE, exist_ok=True)
    largo = None if segundos is None else int(np.ceil(segundos / 30) * 30)
    ruta = os.path.join(CACHE, '%s_%s.npy' % (nombre, largo or 'entero'))
    if not os.path.exists(ruta):
        a = _sonido().renderizar(nombre, largo)
        pico = float(np.abs(a).max()) or 1.0
        np.save(ruta, (a / pico).astype(np.float32))
    return np.load(ruta)


def mezclar(eventos, duracion, fps):
    """eventos: (frame, 'musica'|'sonido'|'fundido_musica', nombre, volumen o frames).
    Devuelve el audio estéreo de 'duracion' segundos."""
    f = fs()
    n = int(duracion * f) + 1
    out = np.zeros((n, 2), np.float32)
    eventos = sorted(eventos, key=lambda e: e[0])
    # música: cada tema suena desde su evento hasta el siguiente cambio de música
    musicas = [e for e in eventos if e[1] in ('musica', 'fundido_musica')]
    for k, (fr, tipo, nombre, v) in enumerate(musicas):
        if tipo != 'musica' or nombre is None:
            continue
        i0 = int(fr / fps * f)
        sig = next((m for m in musicas[k + 1:]), None)
        i1 = n if sig is None else int(sig[0] / fps * f)
        env = np.full(i1 - i0, v, np.float32)
        if sig is not None and sig[1] == 'fundido_musica':      # baja el volumen hasta 0
            lf = int(sig[3] / fps * f)
            i1 = min(n, i1 + lf)
            env = np.concatenate([env, v * np.linspace(1, 0, i1 - i0 - len(env), dtype=np.float32)])
        a = secuencia(nombre, (i1 - i0) / f)[:i1 - i0]
        out[i0:i0 + len(a)] += a * env[:len(a), None]
    for fr, tipo, nombre, v in eventos:
        if tipo != 'sonido':
            continue
        i0 = int(fr / fps * f)
        a = secuencia(nombre)[:n - i0]
        out[i0:i0 + len(a)] += a * v
    pico = float(np.abs(out).max())
    if pico > 0.98:
        out *= 0.98 / pico
    return out


def guardar_wav(ruta, audio):
    import wave
    with wave.open(ruta, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(fs())
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype('<i2').tobytes())
