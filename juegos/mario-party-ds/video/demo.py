"""Prueba del motor con assets de la ROM del juego."""
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta / 'valedores.toml').is_file():
        sys.path.insert(0,str(carpeta/'nucleo'))
        break
from valedores.demo_video_nds import principal
if __name__ == '__main__':
    raise SystemExit(principal('mario-party-ds'))
