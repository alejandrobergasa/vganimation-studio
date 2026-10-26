"""Punto de entrada: `python valedores.py <orden>` (ver `python valedores.py --help`)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'nucleo'))

from valedores.cli import principal  # noqa: E402

if __name__ == '__main__':
    sys.exit(principal())
