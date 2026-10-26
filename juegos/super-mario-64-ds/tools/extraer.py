"""Extrae los recursos base de Super Mario 64 DS; la ROM se abre sólo para lectura."""
from pathlib import Path
import sys


def _nucleo():
    for carpeta in Path(__file__).resolve().parents:
        if (carpeta / 'valedores.toml').is_file():
            return str(carpeta / 'nucleo')
    raise RuntimeError('No se encuentra valedores.toml')


sys.path.insert(0, _nucleo())
from valedores.recursos_nds import principal  # noqa: E402


if __name__ == '__main__':
    raise SystemExit(principal('super-mario-64-ds'))
