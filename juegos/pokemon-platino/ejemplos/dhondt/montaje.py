"""Mezcla la instrumental de reggaetón con el vídeo de eleccionesdont (efectos del juego + música)."""
import os
import sys as _sys
_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))
import valrutas  # noqa: E402
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
SAL = valrutas.SALIDA
video = os.path.join(SAL, 'eleccionesdont.mp4')
sfx = os.path.join(SAL, 'eleccionesdont_sfx.wav')
musica = os.path.join(AQUI, 'reggaeton.wav')
final = os.path.join(SAL, 'eleccionesdont_final.mp4')

dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0',
                                     video]).decode().strip())
subprocess.run([sys.executable, os.path.join(AQUI, 'musica_reggaeton.py'), '%.1f' % dur, musica], check=True)
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', video, '-i', musica, '-i', sfx, '-filter_complex',
                '[1:a]volume=0.55[m];[2:a]volume=0.9[s];[m][s]amix=inputs=2:normalize=0,alimiter=limit=0.95[a]',
                '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', '%.2f' % dur, final],
               check=True)
print('->', final)
