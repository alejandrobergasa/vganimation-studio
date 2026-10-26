"""Transcribe las pistas de música separadas (demucs) a notas con basic-pitch (umbrales algo más bajos que
los de serie para no perder notas suaves bajo las voces). Guarda audio/notas_<pista>.json:
[[inicio_s, fin_s, nota_midi, velocidad 0-127], ...]"""
import json
import os
import sys

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

AQUI = os.path.dirname(os.path.abspath(__file__))
SEP = os.path.join(AQUI, 'audio', 'sep', 'htdemucs', 'original')

for pista, kw in (('bass', dict(onset_threshold=0.35, frame_threshold=0.25, minimum_frequency=30,
                                maximum_frequency=400)),
                  ('other', dict(onset_threshold=0.4, frame_threshold=0.25, minimum_frequency=70))):
    _, _, notas = predict(os.path.join(SEP, pista + '.wav'), ICASSP_2022_MODEL_PATH,
                          minimum_note_length=90, **kw)
    out = [[float(a), float(b), int(p), int(round(v * 127))] for a, b, p, v, *_ in notas]
    out.sort()
    json.dump(out, open(os.path.join(AQUI, 'audio', 'notas_%s.json' % pista), 'w'))
    print(pista, len(out), flush=True)
