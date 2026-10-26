"""Diagnóstico del entorno: dependencias, agentes de IA, ROMs, assets y skills."""
import importlib
import shutil
import subprocess
import sys

from . import juegos, rutas, skills

NUCLEO = [('numpy', 'numpy'), ('numba', 'numba'), ('PIL', 'pillow'), ('scipy', 'scipy'), ('ndspy', 'ndspy')]
OPCIONAL = [('soundfile', 'soundfile'), ('librosa', 'librosa'), ('faster_whisper', 'faster-whisper'),
            ('demucs', 'demucs')]


def _version(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        return (r.stdout or r.stderr).strip().splitlines()[0]
    except Exception:
        return None


def comprobar():
    """Lista de (nivel, texto): nivel 'ok', 'aviso' o 'error'."""
    res = []
    v = sys.version_info
    res.append(('ok' if v >= (3, 10) else 'error', 'Python %d.%d.%d' % v[:3] + ('' if v >= (3, 10) else ' (hace falta 3.10 o más)')))
    for mod, pip in NUCLEO:
        try:
            importlib.import_module(mod)
            res.append(('ok', 'módulo %s' % mod))
        except ImportError:
            res.append(('error', 'falta el módulo %s  →  pip install -r requirements.txt' % pip))
    for mod, pip in OPCIONAL:
        try:
            importlib.import_module(mod)
            res.append(('ok', 'módulo opcional %s' % mod))
        except ImportError:
            res.append(('aviso', 'opcional: %s (análisis de audio de referencia)  →  pip install -r requirements-opcional.txt' % pip))
    for exe in ('ffmpeg', 'ffprobe'):
        v = _version([exe, '-version']) if shutil.which(exe) else None
        res.append(('ok', v) if v else ('error', 'falta %s en el PATH' % exe))
    for exe, nombre in (('claude', 'Claude Code'), ('codex', 'Codex')):
        v = _version([exe, '--version']) if shutil.which(exe) else None
        res.append(('ok', '%s: %s' % (nombre, v)) if v else ('aviso', '%s no está instalado (el estudio solo podrá usar el otro agente)' % nombre))
    for m in juegos.todos():
        st = juegos.estado(m['id'])
        nivel = 'ok' if st['estado'] == 'al_dia' else 'aviso'
        res.append((nivel, '%s: ROM %s · assets %s' % (m['nombre'], 'localizada' if st['rom'] else 'NO encontrada en roms/', juegos.ETIQUETAS[st['estado']])))
    ok = skills.sincronizar(solo_comprobar=True, salida=lambda *_: None)
    res.append(('ok' if ok else 'aviso', 'skills sincronizadas' if ok else 'las skills de .claude/ y .agents/ no están al día  →  python valedores.py skills'))
    return res


def principal():
    marcas = {'ok': '✔', 'aviso': '!', 'error': '✘'}
    malo = False
    for nivel, texto in comprobar():
        print(' %s %s' % (marcas[nivel], texto))
        malo |= nivel == 'error'
    return 1 if malo else 0
