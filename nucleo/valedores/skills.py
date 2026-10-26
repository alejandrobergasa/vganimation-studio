"""Sincroniza las skills con las carpetas que leen los agentes.

Fuente única, editable:
    skills/<nombre>/SKILL.md                 skills transversales
    juegos/<juego>/skills/<nombre>/SKILL.md  skills de cada juego
Copias generadas (no editar):
    .claude/skills/<nombre>/   Claude Code
    .agents/skills/<nombre>/   Codex
"""
import filecmp
import os
import shutil

from . import rutas

DESTINOS = ('.claude/skills', '.agents/skills')


def fuentes():
    """{nombre: carpeta} de todas las skills fuente. Los nombres no se pueden repetir."""
    res = {}
    cands = []
    base = os.path.join(rutas.REPO, 'skills')
    if os.path.isdir(base):
        cands += [os.path.join(base, n) for n in sorted(os.listdir(base))]
    for j in rutas.juegos():
        b = os.path.join(rutas.juego_dir(j), 'skills')
        if os.path.isdir(b):
            cands += [os.path.join(b, n) for n in sorted(os.listdir(b))]
    for d in cands:
        if not os.path.isfile(os.path.join(d, 'SKILL.md')):
            continue
        n = os.path.basename(d)
        if n in res:
            raise SystemExit('Skill duplicada «%s»: %s y %s' % (n, res[n], d))
        res[n] = d
    return res


def _iguales(a, b):
    if not os.path.isdir(b):
        return False
    cmp = filecmp.dircmp(a, b, ignore=['__pycache__'])
    if cmp.left_only or cmp.right_only or cmp.diff_files or cmp.funny_files:
        return False
    return all(_iguales(os.path.join(a, d), os.path.join(b, d)) for d in cmp.common_dirs)


def sincronizar(solo_comprobar=False, salida=print):
    """Copia las skills a los destinos. Con `solo_comprobar` solo informa; devuelve True si todo está al día."""
    src = fuentes()
    ok = True
    for dest in DESTINOS:
        raiz = os.path.join(rutas.REPO, dest)
        existentes = set(os.listdir(raiz)) if os.path.isdir(raiz) else set()
        for n, d in src.items():
            t = os.path.join(raiz, n)
            if _iguales(d, t):
                continue
            ok = False
            if solo_comprobar:
                salida('desactualizada: %s/%s' % (dest, n))
            else:
                if os.path.isdir(t):
                    shutil.rmtree(t)
                shutil.copytree(d, t, ignore=shutil.ignore_patterns('__pycache__'))
                salida('copiada: %s/%s' % (dest, n))
        for n in sorted(existentes - set(src)):
            ok = False
            if solo_comprobar:
                salida('sobra: %s/%s' % (dest, n))
            else:
                shutil.rmtree(os.path.join(raiz, n))
                salida('borrada (ya no existe la fuente): %s/%s' % (dest, n))
    return ok
