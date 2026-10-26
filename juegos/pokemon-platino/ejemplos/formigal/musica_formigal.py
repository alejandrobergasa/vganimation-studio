"""Música de FORMIGAL v2: la música del vídeo original (separada con demucs, sin las voces del doblaje) tocada
nota a nota con los instrumentos de Pokémon Platino. Reutiliza la tubería v3 de REWINDLIMBO2.

  python musica_formigal.py            -> audio/musica_platino.wav (solo música)
  python musica_formigal.py comparar   -> parecido (croma) con la música original
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'rewindlimbo2'))
import musica_platino2 as m2  # noqa

# canción 1 (partitura de la película, 0:00-1:40) y canción 2 (a partir de 1:40, con batería)
CORTES = [(0.0, 44.4, 129)]
SEP = os.path.join(AQUI, 'audio', 'sep', 'htdemucs', 'original')
m2.SEP, m2.CORTES = SEP, CORTES
import musica_platino3 as m3  # noqa
for m in (m2, m3):
    m.SEP, m.CORTES, m.AQUI = SEP, CORTES, AQUI

if __name__ == '__main__':
    m3.comparar() if len(sys.argv) > 1 and sys.argv[1] == 'comparar' else m3.main()
