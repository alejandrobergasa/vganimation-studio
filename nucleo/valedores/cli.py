"""Línea de órdenes de valedores-studio: `python valedores.py <orden>`."""
import argparse
import os
import subprocess
import sys

from . import doctor, extraer, juegos, proyectos, revisar, rutas, skills


def _utf8():
    for f in (sys.stdout, sys.stderr):
        try:
            f.reconfigure(encoding='utf-8')
        except Exception:
            pass


def cmd_estado(a):
    print('\nJuegos:')
    for m in juegos.todos():
        st = juegos.estado(m['id'])
        print('  %-16s %-28s ROM: %-9s assets: %s' % (m['id'], m['nombre'], 'sí' if st['rom'] else 'NO', juegos.ETIQUETAS[st['estado']]))
    ps = proyectos.listar()
    print('\nProyectos (%d):' % len(ps))
    for p in ps:
        print('  %-24s %-16s fase: %-10s (%s)' % (p['slug'], p['juego'], p['fase_actual'], p['fases'][p['fase_actual']]['estado']))
    print('\nEntrada: %d fichero(s) · Salida: %d proyecto(s) con vídeos' % (
        len(proyectos.entradas()), len([d for d in os.listdir(rutas.SALIDA) if os.path.isdir(os.path.join(rutas.SALIDA, d))]) if os.path.isdir(rutas.SALIDA) else 0))
    return 0


def cmd_roms(a):
    rs = rutas.roms_disponibles()
    if not rs:
        print('No hay ROMs en %s. Copia ahí tus .nds (se reconocen por su cabecera).' % rutas.ROMS)
        return 1
    por_codigo = {}
    for m in juegos.todos():
        for c in m['rom']['codigos']:
            por_codigo[c] = m['nombre']
    for p, c in rs.items():
        print('%-5s %-32s %s' % (c, por_codigo.get(c, '(sin soporte todavía)'), os.path.relpath(p, rutas.REPO)))
    return 0


def cmd_extraer(a):
    ids = a.juegos
    if a.todos:
        ids = rutas.juegos()
    elif a.pendientes:
        ids = [m['id'] for m in juegos.todos() if juegos.estado(m['id'])['estado'] in ('sin_extraer', 'desactualizado', 'parcial')]
        if not ids:
            print('Todo está al día.')
            return 0
    if not ids:
        if not sys.stdin.isatty():
            print('Indica juegos (p. ej. `extraer animal-crossing nsmb`), --todos o --pendientes.')
            return 2
        ids = extraer.preguntar()
        if not ids:
            return 0
    malos = 0
    for j in ids:
        if j not in rutas.juegos():
            print('Juego desconocido: %s (hay: %s)' % (j, ', '.join(rutas.juegos())))
            malos += 1
            continue
        print('\n=== %s ===' % juegos.cargar(j)['nombre'])
        try:
            if not extraer.ejecutar(j, rapido=a.rapido):
                malos += 1
        except FileNotFoundError as e:
            print('✗ %s' % e)
            malos += 1
    return 1 if malos else 0


def cmd_skills(a):
    ok = skills.sincronizar(solo_comprobar=a.check)
    if a.check:
        print('skills al día' if ok else 'hay skills desactualizadas: python valedores.py skills')
        return 0 if ok else 1
    return 0


def cmd_proyecto(a):
    if a.accion == 'nuevo':
        p = proyectos.crear(a.titulo, a.juego, a.formato, a.ritmo, a.agente, a.modelo, brief=a.brief or '')
        print('Proyecto creado: proyectos/%s/  (juego %s, formato %s)' % (p['slug'], p['juego'], p['formato']))
        return 0
    if a.accion == 'lista':
        for p in proyectos.listar():
            print('%-24s %-16s %-12s fase %s' % (p['slug'], p['juego'], p['formato'], p['fase_actual']))
        return 0
    if a.accion == 'ver':
        import json
        print(json.dumps(proyectos.leer(a.titulo), ensure_ascii=False, indent=2))
        return 0
    return 2


def cmd_fase(a):
    p = proyectos.fase(a.slug, a.fase, a.estado, a.archivo, a.nota)
    print('%s · %s → %s' % (a.slug, a.fase, a.estado))
    return 0


def cmd_ejecutar(a):
    if not proyectos.existe(a.slug):
        print('No existe el proyecto %s' % a.slug)
        return 2
    cmd = a.comando[1:] if a.comando and a.comando[0] == '--' else a.comando
    if not cmd:
        print('Falta el comando: valedores.py ejecutar <slug> -- python -I ...')
        return 2
    env = dict(os.environ, VALEDORES_PROYECTO=a.slug, PYTHONIOENCODING='utf-8')
    return subprocess.call(cmd, cwd=rutas.REPO, env=env)


def cmd_revisar(a):
    revisar.principal(a.args)
    return 0


def cmd_doctor(a):
    return doctor.principal()


def cmd_estudio(a):
    sys.path.insert(0, rutas.REPO)
    from estudio import servidor
    return servidor.principal(puerto=a.puerto, abrir=not a.no_abrir)


def principal(argv=None):
    _utf8()
    ap = argparse.ArgumentParser(prog='valedores.py', description='valedores-studio: vídeos a partir de assets de videojuegos.')
    sub = ap.add_subparsers(dest='orden', required=True)

    sub.add_parser('estado', help='resumen de juegos, proyectos y bandejas').set_defaults(f=cmd_estado)
    sub.add_parser('roms', help='ROMs encontradas en roms/ y a qué juego corresponden').set_defaults(f=cmd_roms)
    sub.add_parser('doctor', help='comprueba dependencias, agentes, ROMs y skills').set_defaults(f=cmd_doctor)

    e = sub.add_parser('extraer', help='extrae (o actualiza) los assets de las ROMs; sin argumentos pregunta cuáles')
    e.add_argument('juegos', nargs='*', help='ids de juego (ver `estado`)')
    e.add_argument('--todos', action='store_true')
    e.add_argument('--pendientes', action='store_true', help='solo los sin extraer o con extractor nuevo')
    e.add_argument('--rapido', action='store_true', help='muestras en vez de todo (si el juego lo admite)')
    e.set_defaults(f=cmd_extraer)

    s = sub.add_parser('skills', help='sincroniza las skills con .claude/ y .agents/')
    s.add_argument('--check', action='store_true', help='solo comprobar')
    s.set_defaults(f=cmd_skills)

    p = sub.add_parser('proyecto', help='crear/listar/ver proyectos de vídeo')
    p.add_argument('accion', choices=['nuevo', 'lista', 'ver'])
    p.add_argument('titulo', nargs='?', help='título del vídeo (o slug con `ver`)')
    p.add_argument('--juego', default=None)
    p.add_argument('--formato', default=None)
    p.add_argument('--ritmo', default='paso_a_paso', choices=list(proyectos.RITMOS))
    p.add_argument('--agente', default='claude', choices=['claude', 'codex'])
    p.add_argument('--modelo', default=None)
    p.add_argument('--brief', default=None)
    p.set_defaults(f=cmd_proyecto)

    f = sub.add_parser('fase', help='el agente marca el estado de una fase de un proyecto')
    f.add_argument('slug')
    f.add_argument('fase', choices=proyectos.IDS_FASE)
    f.add_argument('estado', choices=proyectos.ESTADOS)
    f.add_argument('--archivo', nargs='*', default=None, help='ficheros del proyecto que produce la fase')
    f.add_argument('--nota', default=None, help='resumen para el usuario')
    f.set_defaults(f=cmd_fase)

    x = sub.add_parser('ejecutar', help='ejecuta un comando con el proyecto activo (salida/ y trabajo/ del proyecto)')
    x.add_argument('slug')
    x.add_argument('comando', nargs=argparse.REMAINDER)
    x.set_defaults(f=cmd_ejecutar)

    r = sub.add_parser('revisar', help='info | hoja | frame | audio de un vídeo')
    r.add_argument('args', nargs=argparse.REMAINDER)
    r.set_defaults(f=cmd_revisar)

    g = sub.add_parser('estudio', help='abre la interfaz gráfica con el chat del agente')
    g.add_argument('--puerto', type=int, default=8765)
    g.add_argument('--no-abrir', action='store_true', help='no abrir el navegador')
    g.set_defaults(f=cmd_estudio)

    a = ap.parse_args(argv)
    if a.orden == 'proyecto' and a.accion == 'nuevo' and (not a.titulo or not a.juego):
        ap.error('proyecto nuevo "<título>" --juego <id>')
    try:
        return a.f(a)
    except (ValueError, FileNotFoundError, KeyError) as e:
        print('Error: %s' % e)
        return 1
