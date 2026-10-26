"""Partitura original y efectos de la cinemática, con los bancos de NSMB."""
import json
from pathlib import Path
import re
import sys
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools' / 'nsmb'))
import sonido
import rom
from rom import rutas

FS = sonido.FS
PAGES = [(20.4, 24.5, 'chavales RENFE va de puta madre'),
         (24.5, 30.5, 'espero estéis disfrutando del viajecito a Madrid.'),
         (30.5, 35.5, 'Se está quedando Madrid de puta madre.'),
         (35.5, 41.5, 'me voy a tuitear un glazing al perro')]
TEXT_CPS = 20
DIALOGUE_END = PAGES[-1][1]
DEATH_T = DIALOGUE_END + .65
IRIS_T = DIALOGUE_END + 2.2
GAMEOVER_T = DIALOGUE_END + 3
DURATION = GAMEOVER_T + 5
CACHE = Path(rutas.cache('nsmb')) / 'renfe'


def normal(a, peak):
    return a * (peak / max(float(np.abs(a).max()), 1e-6))


def put(mix, a, t, gain=1.0):
    i = round(t * FS)
    n = min(len(a), len(mix) - i)
    if n > 0:
        mix[i:i + n] += a[:n] * gain


def fade(a, seconds=0.08):
    a = a.copy()
    n = min(len(a) // 2, round(seconds * FS))
    if n:
        a[:n] *= np.linspace(0, 1, n)[:, None]
        a[-n:] *= np.linspace(1, 0, n)[:, None]
    return a


def effect(name, duration, level=0.3):
    """Reutiliza los WAV extraídos; recorta los efectos que el juego detiene por código."""
    with wave.open(str(Path(rutas.extraidos('nsmb')) / 'audio' / 'efectos' / (name + '.wav'))) as w:
        rate, channels = w.getframerate(), w.getnchannels()
        a = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32)
    a = a.reshape(-1, channels)
    if channels == 1:
        a = np.repeat(a, 2, axis=1)
    if rate != FS:
        x = np.arange(round(len(a) * FS / rate)) * rate / FS
        a = np.stack([np.interp(x, np.arange(len(a)), a[:, c]) for c in range(2)], axis=1)
    a = a[:round(duration * FS)]
    return fade(normal(a, level), min(0.025, duration / 5))


def score(kind, duration):
    """Notas propias, sin reutilizar melodías BGM; t, duración, MIDI, vel, prog, pan, vol."""
    notes = []

    def note(t, d, key, prog=13, vel=98, pan=64, vol=105):
        if t < duration - 0.03:
            notes.append((float(t), min(float(d), duration - t), key, vel, prog, pan, vol))

    if kind in ('campo', 'viaje', 'comunicado'):
        bpm = {'campo': 150, 'viaje': 120, 'comunicado': 112}[kind]
        beat = 60 / bpm
        # Cuatro acordes, un motivo de carrera y dos variaciones de escena.
        roots = [48, 53, 57, 55]
        lead = {'campo': [72, 76, 79, 76, 81, 79, 74, 76, 77, 81, 79, 76, 74, 71, 74, 79],
                'viaje': [67, 72, 76, 79, 76, 72, 74, 71, 69, 72, 77, 81, 79, 76, 74, 72],
                'comunicado': [79, 79, 76, 0, 77, 74, 71, 0, 76, 72, 67, 0, 69, 71, 72, 0]}[kind]
        for step in range(int(duration / (beat / 2)) + 1):
            t = step * beat / 2
            root = roots[(step // 8) % 4]
            key = lead[step % len(lead)]
            if key:
                note(t, beat * (0.32 if kind == 'comunicado' else 0.42), key,
                     prog=18 if kind == 'comunicado' else 13, vel=104, pan=60)
            if step % 2 == 0:
                note(t, beat * 0.55, root if step % 4 == 0 else root + 7,
                     prog=11, vel=108, pan=64, vol=105)
            if step % 4 == 2:
                for chord in (root + 12, root + 16, root + 19):
                    note(t, beat * 0.3, chord, prog=14, vel=72, pan=45, vol=80)
            note(t, 0.065, 42 if step % 2 else 36, prog=125, vel=75 if step % 2 else 94,
                 pan=75, vol=84)
        if kind == 'campo':
            for t, key in [(7.3, 76), (7.55, 79), (7.8, 84)]:
                note(t, .18, key, prog=17, vel=100)
    elif kind == 'alarma':
        for i in range(int(duration / .6667) + 1):
            t = i * .6667
            for key in (48, 55, 60, 63):
                note(t, .14, key, prog=15, vel=76, pan=40, vol=88)
            note(t + .333, .13, 67 if i % 2 else 66, prog=17, vel=63, pan=90, vol=72)
    elif kind == 'derrota':
        for t, key, d in [(0, 72, .15), (.2, 67, .15), (.4, 63, .18), (.65, 60, .35),
                          (1.1, 59, .2), (1.4, 55, .5), (2.2, 48, 1.0)]:
            note(t, d, key, prog=18, vel=112)
        for key in (48, 51, 55):
            note(2.2, 1.0, key, prog=14, vel=68, vol=82)
    return notes


def dialogue():
    """Balbuceo por sílabas con granos vocales de la ROM; no es una voz imitada."""
    out = np.zeros((round(DURATION * FS), 2), np.float32)
    sources = []
    for name in ('SE_VOC_OPDM_UN_01', 'SE_VOC_OPDM_UN_02', 'SE_VOC_LU_HOH'):
        a = effect(name, .38, 1.0)
        # Seleccionar una zona sonora, evitando el silencio previo del efecto.
        mono = a.mean(axis=1)
        energy = np.convolve(mono * mono, np.ones(360) / 360, mode='same')
        center = int(np.argmax(energy))
        start = max(0, center - round(.027 * FS))
        grain = a[start:start + round(.079 * FS)].copy()
        grain -= grain.mean(axis=0, keepdims=True)
        sources.append(grain)
    for page, (start, end, line) in enumerate(PAGES):
        syllables = list(re.finditer(r'[aeiouáéíóúü]+', line, re.IGNORECASE))
        for j, syllable in enumerate(syllables):
            index = syllable.start()
            at = start + (index + 1) / TEXT_CPS
            vowel = syllable.group()[0].lower()
            semitone = {'a': -3, 'e': 0, 'i': 2, 'o': -4, 'u': -2}.get(vowel, -1)
            semitone += [-1, 1, 0, 2, -2][j % 5]
            # Caída suave al terminar cada página y acentos de palabra.
            semitone -= 2 if j == len(syllables) - 1 else 0
            grain = sources[(j + page) % len(sources)]
            ratio = 2 ** (semitone / 12)
            pos = np.arange(max(1, round(len(grain) / ratio))) * ratio
            a = np.stack([np.interp(pos, np.arange(len(grain)), grain[:, c]) for c in range(2)], axis=1)
            # Un pequeño filtrado quita dureza a los fragmentos y la envolvente evita clics.
            a = np.stack([np.convolve(a[:, c], np.ones(5) / 5, mode='same') for c in range(2)], axis=1)
            accented = index < 10 or line[max(0, index - 1):index] == ' '
            a = fade(normal(a, .235 if accented else .18), .012)
            a[:, page % 2] *= .92
            put(out, a, at)
            put(out, a, at + .052, .12)
            put(out, a, at + .105, .045)
        # Cambios de página discretos, sin el pitido de cursor repetido por letra.
        if page:
            put(out, effect('SE_SYS_WINDOW_OPEN', .09, .055), start - .035)
    return out


def speech_envelope():
    """Bajada suave de música y alarma mientras se escribe cada frase."""
    env = np.ones(round(DURATION * FS), np.float32)
    for start, end, line in PAGES:
        a, b = round((start - .06) * FS), round((start + len(line) / TEXT_CPS + .24) * FS)
        n = round(.08 * FS)
        env[a:a + n] = np.linspace(1, .48, n)
        env[a + n:b] = .48
        env[b:b + n] = np.linspace(.48, 1, n)
    return env


def build():
    CACHE.mkdir(parents=True, exist_ok=True)
    son = sonido.Sonido(rom.find_rom())
    mix = np.zeros((round(DURATION * FS), 2), np.float32)
    duck = speech_envelope()
    manifest = []
    for kind, start, end, level in [('campo', 0, 8.95, .29), ('viaje', 9, 15, .28),
                                     ('alarma', 17.1, 20.1, .16),
                                     ('comunicado', 20.1, DIALOGUE_END, .20),
                                     ('derrota', GAMEOVER_T, DURATION - .5, .33)]:
        print('Música original:', kind, flush=True)
        notes = score(kind, end - start)
        a = sonido.tocar_notas(son, 'BANK_CHIJO_BGM', notes, end - start)
        a = fade(normal(a, level), .09)
        if kind == 'comunicado':
            base = round(start * FS)
            a *= duck[base:base + len(a), None]
        sonido.guardar_wav(str(CACHE / ('musica_' + kind + '.wav')), a)
        put(mix, a, start)
        manifest.append({'escena': kind, 'inicio': start, 'fin': end,
                         'banco': 'BANK_CHIJO_BGM', 'notas': notes})

    cues = [(0, 'SE_SYS_COURSE_IN', .5, .25),
            (1.65, 'SE_PLY_JUMP', .5, .35),
            (1.96, 'SE_OBJ_GET_COIN', .6, .32),
            (3.2, 'SE_OBJ_GET_COIN', .6, .32),
            (4.8, 'SE_SYS_WIPE_1', .45, .22),
            (6.3, 'SE_OBJ_DOOR_OPEN', .55, .30),
            (6.65, 'SE_PLY_JUMP', .5, .34),
            (8.15, 'SE_OBJ_DOOR_CLOSE', .55, .32),
            (8.75, 'SE_SYS_WIPE_2', .25, .25),
            (12.5, 'SE_SYS_WIPE_2', .22, .14),
            (15.0, 'SE_OBJ_BIG_ROCK_CRASH', .68, .75),
            (15.04, 'SE_OBJ_BLOCK_BREAK', .5, .53),
            (15.4, 'SE_OBJ_TEKKYU_CRASH', .45, .32),
            (16.2, 'SE_SYS_SLEEP_IN', .35, .16),
            (17.1, 'SE_SYS_WARNING', .3, .38),
            (20.0, 'SE_SYS_WINDOW_OPEN', .3, .26),
            (DIALOGUE_END, 'SE_SYS_WINDOW_CLOSE', .3, .32),
            (DEATH_T, 'SE_PLY_DOWN', .5, .42),
            (GAMEOVER_T - .3, 'SE_SYS_WIPE_1', .4, .26),
            (GAMEOVER_T, 'SE_SYS_ONE_DOWN', .7, .32),
            (GAMEOVER_T + 3.1, 'SE_SYS_CURSOR', .13, .17)]
    for t in np.arange(.28, 4.8, .24):
        if not 1.65 < t < 2.3:
            cues.append((float(t), 'SE_PLY_FOOTNOTE', .09, .055))
    for t in np.arange(9.2, 15, .32):
        cues.append((float(t), 'SE_PLY_WALK_METAL', .10, .085))
    for t in np.arange(17.75, 20, 1.2):
        cues.append((float(t), 'SE_SYS_WARNING', .25, .22))
    loaded = {}
    for t, name, dur, level in cues:
        key = (name, dur, level)
        if key not in loaded:
            loaded[key] = effect(name, dur, level)
        put(mix, loaded[key], t)

    # Sirena propia de dos notas con muestras del banco; se atenúa bajo el diálogo.
    siren = []
    for t in np.arange(17.1, DIALOGUE_END, 1.2):
        gain = 91 if t < 20 else 65
        siren.extend([(float(t), .32, 81, gain, 17, 76, 96),
                      (float(t + .36), .32, 74, gain, 17, 50, 96)])
    a = sonido.tocar_notas(son, 'BANK_CHIJO_BGM', siren, DURATION)
    n = min(len(a), len(duck))
    a = normal(a[:n], .13)
    a *= duck[:n, None]
    put(mix, a, 0)
    speech = dialogue()
    sonido.guardar_wav(str(CACHE / 'dialogo_oscar.wav'), speech)
    put(mix, speech, 0)
    # Caída tonal de frenado, también con un instrumento de la ROM.
    notes = [(15 + i * .045, .07, 88 - i * 2, 90, 17, 64, 105) for i in range(20)]
    put(mix, normal(sonido.tocar_notas(son, 0, notes, 16.2), .22), 0)
    peak = float(np.abs(mix).max())
    if peak > .78:
        mix *= .78 / peak
    mix = fade(mix, .04)
    assert np.isfinite(mix).all() and np.abs(mix).max() < .99
    sonido.guardar_wav(str(CACHE / 'mezcla.wav'), mix)
    (CACHE / 'partitura.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
    print('Mezcla: pico %.2f dBFS' % (20 * np.log10(max(np.abs(mix).max(), 1e-8))), flush=True)
    return CACHE / 'mezcla.wav'


if __name__ == '__main__':
    build()
