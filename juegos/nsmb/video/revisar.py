"""Herramientas de revisión del vídeo (iguales para cualquier agente): hoja de fotogramas, fotograma suelto, audio.

  python video/revisar.py hoja  [video.mp4] [segundos_entre_fotogramas=3] [columnas=5]   -> <trabajo>/revision/hoja.png
  python video/revisar.py frame [video.mp4] <segundo>                                    -> <trabajo>/revision/frame_<s>.png (tamaño completo)
  python video/revisar.py audio [video.mp4]                                              -> <trabajo>/revision/audio.png (espectrograma + onda) y niveles
Después hay que MIRAR la imagen generada (herramienta de lectura de imágenes del agente).
"""
import sys, os, subprocess, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools', 'nsmb'))
from rom import rutas
OUT = os.path.join(rutas.trabajo('nsmb'), 'revision')
DEFECTO = os.path.join(rutas.salida('nsmb'), 'nsmb_paseo_mundo_1-1.mp4')


def ff(*a):
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', *a])


def main(argv):
    os.makedirs(OUT, exist_ok=True)
    if not argv: raise SystemExit(__doc__)
    cmd, rest = argv[0], argv[1:]
    vid = rest.pop(0) if rest and rest[0].lower().endswith(('.mp4', '.gif', '.mkv')) else DEFECTO
    if cmd == 'hoja':
        paso = float(rest[0]) if rest else 3.0; cols = int(rest[1]) if len(rest) > 1 else 5
        dur = float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', vid]))
        filas = max(1, math.ceil(dur / paso / cols))
        p = os.path.join(OUT, 'hoja.png')
        # Mantener la proporción también en las cinemáticas verticales.
        ff('-i', vid, '-vf', 'fps=1/%s,scale=216:384:force_original_aspect_ratio=decrease,pad=216:384:(ow-iw)/2:(oh-ih)/2,tile=%dx%d' % (paso, cols, filas), '-frames:v', '1', p)
    elif cmd == 'frame':
        s = rest[0]; p = os.path.join(OUT, 'frame_%s.png' % s)
        ff('-ss', s, '-i', vid, '-frames:v', '1', p)
    elif cmd == 'audio':
        p = os.path.join(OUT, 'audio.png')
        ff('-i', vid, '-filter_complex', '[0:a]showspectrumpic=s=1200x300:legend=0[s];[0:a]showwavespic=s=1200x150[w];[s][w]vstack', '-frames:v', '1', p)
        r = subprocess.run(['ffmpeg', '-hide_banner', '-i', vid, '-af', 'volumedetect', '-vn', '-f', 'null', '-'], capture_output=True, text=True).stderr
        print('\n'.join(l.split('] ')[-1] for l in r.splitlines() if 'mean_volume' in l or 'max_volume' in l))
    else:
        raise SystemExit(__doc__)
    print(p)


if __name__ == '__main__':
    main(sys.argv[1:])
