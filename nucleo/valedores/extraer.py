"""Extracción de assets de las ROMs a `biblioteca/<juego>/extraidos/`.

Cada juego declara en su `juego.json` los comandos del extractor. Aquí se localizan las ROMs,
se ejecutan (siempre con la última versión del código) y se deja un sello con la huella del
extractor, para saber después si los assets están al día o hay que regenerarlos.
"""
import os
import subprocess
import sys

from . import juegos, rutas


def comandos(juego, rapido=False):
    """Lista de argv (sin el intérprete) del extractor del juego, con {rom} y {extraidos} resueltos."""
    m = juegos.cargar(juego)
    ex = m['extractor']
    cmds = ex.get('comandos') or [ex['comando']]
    rom = rutas.rom(juego)
    out = rutas.extraidos(juego)
    res = []
    for c in cmds:
        a = [x.replace('{rom}', rom).replace('{extraidos}', out) for x in c]
        if rapido and ex.get('rapido'):
            a += ex['rapido']
        res.append(a)
    return res


def ejecutar(juego, rapido=False, extra=None, salida=print):
    """Extrae los assets del juego. `salida(linea)` recibe el progreso. Devuelve True si todo fue bien."""
    m = juegos.cargar(juego)
    rom = rutas.rom(juego)          # FileNotFoundError con instrucciones si falta
    if rapido and not m['extractor'].get('rapido'):
        salida('(«%s» no tiene modo rápido: se extrae todo)' % m['nombre'])
        rapido = False
    os.makedirs(rutas.extraidos(juego), exist_ok=True)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    env.pop('VALEDORES_PROYECTO', None)
    for argv in comandos(juego, rapido):
        if extra:
            argv = argv + list(extra)
        salida('$ python -I ' + ' '.join(argv))
        p = subprocess.Popen([sys.executable, '-I'] + argv, cwd=m['dir'], env=env, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for linea in p.stdout:
            salida(linea.rstrip('\n'))
        if p.wait() != 0:
            salida('✗ El extractor terminó con error (código %d).' % p.returncode)
            return False
    juegos.escribir_sello(juego, rom, rapido)
    salida('✓ %s: assets en %s' % (m['nombre'], os.path.relpath(rutas.extraidos(juego), rutas.REPO)))
    return True


def preguntar(entrada=input, salida=print):
    """Muestra los juegos con su estado y pregunta cuáles extraer. Devuelve la lista de ids elegidos."""
    todos = juegos.todos()
    salida('\nJuegos disponibles:\n')
    for i, m in enumerate(todos, 1):
        st = juegos.estado(m['id'])
        rom = '✔ ROM' if st['rom'] else '✘ sin ROM'
        extra = ''
        if st['sello']:
            extra = ' · extraído el ' + st['sello']['fecha'][:10]
        salida(' %d) %-30s %-9s assets: %s%s' % (i, m['nombre'], rom, juegos.ETIQUETAS[st['estado']], extra))
    salida('\nElige qué extraer: números separados por comas, «todos», «pendientes» (sin extraer o desactualizados)')
    r = entrada('o Enter para salir > ').strip().lower()
    if not r:
        return []
    if r in ('todos', 't'):
        return [m['id'] for m in todos]
    if r in ('pendientes', 'p'):
        return [m['id'] for m in todos if juegos.estado(m['id'])['estado'] in ('sin_extraer', 'desactualizado', 'parcial')]
    ids = []
    for tok in r.replace(' ', ',').split(','):
        if tok.isdigit() and 1 <= int(tok) <= len(todos):
            ids.append(todos[int(tok) - 1]['id'])
        elif tok:
            salida('No entiendo «%s»; lo salto.' % tok)
    return ids
