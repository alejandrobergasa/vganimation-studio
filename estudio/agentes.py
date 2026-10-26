"""Agentes de IA locales (Claude Code y Codex) detrás de una interfaz común.

Cada turno de chat lanza el CLI del agente en modo no interactivo, en la raíz del repo, con el proyecto activo
(`VALEDORES_PROYECTO`), y traduce su salida JSON a eventos sencillos para el estudio:

    {'t': 'delta', 'texto'}            trozo de texto que se está escribiendo (no se guarda)
    {'t': 'asistente', 'texto'}        mensaje completo del agente
    {'t': 'herramienta', 'id', 'nombre', 'resumen'}
    {'t': 'resultado', 'id', 'ok', 'resumen'}
    {'t': 'uso_vivo', 'entrada', 'salida', 'cache_leida', 'cache_escrita'}   consumo del turno hasta ahora (no se guarda)
    {'t': 'fin', 'coste', 'duracion', 'tokens', 'uso', 'modelo'}      `uso` = {entrada, salida, cache_leida, cache_escrita}
    {'t': 'error', 'texto'}
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid

try:
    import tomllib
except ImportError:  # Python < 3.11
    tomllib = None

FLAGS_OCULTAR = 0x08000000 if os.name == 'nt' else 0   # CREATE_NO_WINDOW

HERRAMIENTAS_CLAUDE = 'Bash,PowerShell,Read,Write,Edit,MultiEdit,Glob,Grep,NotebookEdit,WebFetch,WebSearch,TodoWrite,Skill,Agent,Task'

PERMISOS = {
    'normal': 'Normal: puede editar ficheros y ejecutar comandos dentro del repo.',
    'total': 'Total: sin ninguna restricción (úsalo solo si confías en la tarea).',
}


CAMPOS_USO = ('entrada', 'salida', 'cache_leida', 'cache_escrita')


def _uso_vacio():
    return dict.fromkeys(CAMPOS_USO, 0)


def _sumar(a, b):
    return {k: a[k] + b[k] for k in CAMPOS_USO}


def precios():
    """Precios en USD por millón de tokens definidos por el usuario en `valedores.toml` (`[precios."modelo"]`).
    Claude Code informa del coste real de cada turno; para otros agentes solo hay precio si se configura aquí."""
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'valedores.toml')
    if tomllib is None or not os.path.isfile(p):
        return {}
    try:
        with open(p, 'rb') as f:
            return tomllib.load(f).get('precios', {})
    except Exception:
        return {}


def coste_estimado(modelo, uso):
    """USD según los precios configurados, o None si no hay precio para ese modelo."""
    t = precios().get(modelo or '')
    if not t or not uso:
        return None
    try:
        return sum(uso[k] * float(t.get(k, 0)) for k in CAMPOS_USO) / 1e6
    except (TypeError, ValueError):
        return None


def _config_codex():
    p = os.path.join(os.path.expanduser('~'), '.codex', 'config.toml')
    if tomllib is None or not os.path.isfile(p):
        return {}
    try:
        with open(p, 'rb') as f:
            return tomllib.load(f)
    except Exception:
        return {}


def catalogo():
    """Agentes instalados y sus modelos/esfuerzos para el selector del estudio."""
    cx = _config_codex()
    modelo_codex = cx.get('model')
    return {
        'claude': {
            'nombre': 'Claude Code', 'disponible': bool(shutil.which('claude')),
            'modelos': [{'id': 'claude-fable-5-1', 'nombre': 'Fable 5.1'}, {'id': 'claude-opus-5-5', 'nombre': 'Opus 5.5'},
                        {'id': 'claude-sonnet-5-5', 'nombre': 'Sonnet 5.5'}, {'id': 'claude-haiku-5-5', 'nombre': 'Haiku 5.5'}],
            'modelo_defecto': 'claude-sonnet-5-5',
            'esfuerzos': ['low', 'medium', 'high', 'xhigh', 'max'], 'esfuerzo_defecto': 'high',
        },
        'codex': {
            'nombre': 'Codex', 'disponible': bool(shutil.which('codex')),
            'modelos': ([{'id': modelo_codex, 'nombre': '%s (tu configuración)' % modelo_codex}] if modelo_codex else []),
            'modelo_defecto': modelo_codex,
            'esfuerzos': ['low', 'medium', 'high', 'xhigh'], 'esfuerzo_defecto': cx.get('model_reasoning_effort', 'high'),
        },
    }


# ------------------------------------------------------------------ resúmenes de herramientas

def _recortar(s, n=220):
    s = (s or '').strip().replace('\r', '')
    return s if len(s) <= n else s[:n - 1] + '…'


def resumen_herramienta(nombre, entrada):
    if not isinstance(entrada, dict):
        return _recortar(str(entrada))
    for k in ('command', 'file_path', 'path', 'pattern', 'url', 'query', 'skill', 'description'):
        if entrada.get(k):
            v = str(entrada[k]).strip().splitlines()[0]
            return _recortar(v)
    return _recortar(json.dumps(entrada, ensure_ascii=False))


def _texto_resultado(c):
    if isinstance(c, list):
        c = ' '.join(b.get('text', '') for b in c if isinstance(b, dict))
    return _recortar(str(c), 400)


# ------------------------------------------------------------------ traductores de salida

class TraductorClaude:
    def __init__(self):
        self.vistos = set()
        self.sesion = None
        self.hubo_delta = False
        self.uso_hecho = _uso_vacio()     # mensajes (llamadas al modelo) ya terminados en este turno
        self.uso_msg = _uso_vacio()       # el que se está escribiendo ahora

    def __call__(self, ev):
        out = []
        t = ev.get('type')
        if t == 'system' and ev.get('subtype') == 'init':
            self.sesion = ev.get('session_id')
        elif t == 'stream_event':
            e = ev.get('event', {})
            if e.get('type') == 'content_block_delta' and e.get('delta', {}).get('type') == 'text_delta':
                self.hubo_delta = True
                out.append({'t': 'delta', 'texto': e['delta']['text']})
            elif e.get('type') in ('message_start', 'message_delta'):
                u = (e.get('message', {}).get('usage') if e['type'] == 'message_start' else e.get('usage')) or {}
                if e['type'] == 'message_start':
                    self.uso_hecho = _sumar(self.uso_hecho, self.uso_msg)
                self.uso_msg = {'entrada': u.get('input_tokens') or 0, 'salida': u.get('output_tokens') or 0,
                                'cache_leida': u.get('cache_read_input_tokens') or 0,
                                'cache_escrita': u.get('cache_creation_input_tokens') or 0}
                out.append(dict(_sumar(self.uso_hecho, self.uso_msg), t='uso_vivo'))
        elif t == 'assistant':
            msg = ev.get('message', {})
            for b in msg.get('content', []):
                if b.get('type') == 'text' and b.get('text', '').strip():
                    clave = ('texto', msg.get('id'), b['text'])
                    if clave not in self.vistos:
                        self.vistos.add(clave)
                        out.append({'t': 'asistente', 'texto': b['text']})
                elif b.get('type') == 'tool_use':
                    if b['id'] not in self.vistos:
                        self.vistos.add(b['id'])
                        out.append({'t': 'herramienta', 'id': b['id'], 'nombre': b['name'],
                                    'resumen': resumen_herramienta(b['name'], b.get('input'))})
        elif t == 'user':
            c = ev.get('message', {}).get('content')
            if isinstance(c, list):
                for b in c:
                    if isinstance(b, dict) and b.get('type') == 'tool_result':
                        out.append({'t': 'resultado', 'id': b.get('tool_use_id'), 'ok': not b.get('is_error'),
                                    'resumen': _texto_resultado(b.get('content'))})
        elif t == 'result':
            if ev.get('is_error'):
                out.append({'t': 'error', 'texto': _recortar(str(ev.get('result') or 'El agente terminó con error.'), 600)})
            u = ev.get('usage') or {}
            uso = {'entrada': u.get('input_tokens') or 0, 'salida': u.get('output_tokens') or 0,
                   'cache_leida': u.get('cache_read_input_tokens') or 0, 'cache_escrita': u.get('cache_creation_input_tokens') or 0}
            modelos = list((ev.get('modelUsage') or {}).keys())
            out.append({'t': 'fin', 'coste': ev.get('total_cost_usd'), 'duracion': (ev.get('duration_ms') or 0) / 1000,
                        'tokens': uso['entrada'] + uso['salida'], 'uso': uso, 'modelo': modelos[0] if modelos else None})
        return out


class TraductorCodex:
    def __init__(self):
        self.sesion = None

    def __call__(self, ev):
        out = []
        t = ev.get('type')
        if t == 'thread.started':
            self.sesion = ev.get('thread_id')
        elif t in ('item.started', 'item.completed'):
            it = ev.get('item', {})
            ty = it.get('type')
            if ty == 'agent_message' and t == 'item.completed' and it.get('text', '').strip():
                out.append({'t': 'asistente', 'texto': it['text']})
            elif ty == 'command_execution':
                if t == 'item.started':
                    out.append({'t': 'herramienta', 'id': it['id'], 'nombre': 'Comando', 'resumen': _recortar(_limpiar_cmd(it.get('command', '')))})
                else:
                    out.append({'t': 'resultado', 'id': it['id'], 'ok': it.get('exit_code') in (0, None),
                                'resumen': _recortar(it.get('aggregated_output', ''), 400) or 'código %s' % it.get('exit_code')})
            elif ty == 'file_change' and t == 'item.completed':
                cambios = ', '.join(os.path.basename(c.get('path', '')) for c in it.get('changes', []))
                out.append({'t': 'herramienta', 'id': it['id'], 'nombre': 'Editar', 'resumen': _recortar(cambios)})
            elif ty in ('mcp_tool_call', 'web_search') and t == 'item.started':
                out.append({'t': 'herramienta', 'id': it['id'], 'nombre': ty, 'resumen': _recortar(json.dumps(it, ensure_ascii=False), 160)})
            elif ty == 'error':
                out.append({'t': 'error', 'texto': _recortar(it.get('message', ''), 600)})
        elif t == 'turn.completed':
            u = ev.get('usage') or {}
            cacheado = u.get('cached_input_tokens') or 0          # en Codex `input_tokens` ya incluye lo cacheado
            uso = {'entrada': max(0, (u.get('input_tokens') or 0) - cacheado), 'salida': u.get('output_tokens') or 0,
                   'cache_leida': cacheado, 'cache_escrita': 0}
            out.append({'t': 'fin', 'coste': None, 'duracion': None, 'tokens': (u.get('input_tokens') or 0) + (u.get('output_tokens') or 0),
                        'uso': uso, 'modelo': None})
        elif t in ('turn.failed', 'error'):
            msg = ev.get('message') or (ev.get('error') or {}).get('message') or str(ev)
            out.append({'t': 'error', 'texto': _recortar(msg, 600)})
        return out


def _limpiar_cmd(c):
    """Quita el envoltorio `pwsh -Command '...'` que Codex añade en Windows."""
    for pref in ('-Command ',):
        if pref in c:
            c = c.split(pref, 1)[1].strip()
            break
    return c.strip('\'"')


# ------------------------------------------------------------------ lanzamiento

def construir(agente, texto, modelo, esfuerzo, permisos, sesion, sistema=None):
    """(argv, stdin, id_sesion_nuevo). `sesion` es el id guardado o None si es el primer turno con este agente."""
    if agente == 'claude':
        exe = shutil.which('claude')
        if not exe:
            raise RuntimeError('Claude Code no está instalado o no está en el PATH.')
        nuevo = sesion or str(uuid.uuid4())
        argv = [exe, '-p', '--output-format', 'stream-json', '--verbose', '--include-partial-messages']
        if modelo:
            argv += ['--model', modelo]
        if esfuerzo:
            argv += ['--effort', esfuerzo]
        if permisos == 'total':
            argv += ['--permission-mode', 'bypassPermissions']
        else:
            argv += ['--permission-mode', 'acceptEdits', '--allowedTools', HERRAMIENTAS_CLAUDE]
        argv += ['--resume', sesion] if sesion else ['--session-id', nuevo]
        if sistema:
            argv += ['--append-system-prompt', sistema]
        return argv, texto, nuevo
    if agente == 'codex':
        exe = shutil.which('codex')
        if not exe:
            raise RuntimeError('Codex no está instalado o no está en el PATH.')
        base = [exe, 'exec']
        if sesion:
            base += ['resume']
        base += ['--json', '--skip-git-repo-check']
        if modelo:
            base += ['-c', 'model="%s"' % modelo]
        if esfuerzo:
            base += ['-c', 'model_reasoning_effort="%s"' % esfuerzo]
        if permisos == 'total':
            base += ['--dangerously-bypass-approvals-and-sandbox']
        else:
            base += ['-c', 'sandbox_mode="workspace-write"']
        if sesion:
            base += [sesion, '-']
        else:
            base += ['-']
        if sistema and not sesion:
            texto = sistema + '\n\n---\n\n' + texto
        return base, texto, sesion
    raise ValueError('Agente desconocido: %s' % agente)


def matar(proc):
    """Termina el proceso del agente y todos sus hijos."""
    if proc is None or proc.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(proc.pid)], capture_output=True, creationflags=FLAGS_OCULTAR)
        else:
            proc.terminate()
    except Exception:
        pass


def ejecutar_turno(agente, texto, modelo, esfuerzo, permisos, sesion, cwd, env_extra, emitir, sistema=None, registrar_proc=None):
    """Ejecuta un turno y llama a `emitir(evento)` por cada evento traducido. Devuelve el id de sesión a recordar."""
    argv, stdin, id_nuevo = construir(agente, texto, modelo, esfuerzo, permisos, sesion, sistema)
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1', **env_extra)
    tr = TraductorClaude() if agente == 'claude' else TraductorCodex()
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            creationflags=FLAGS_OCULTAR)
    if registrar_proc:
        registrar_proc(proc)
    errores = []

    def _leer_err():
        for linea in proc.stderr:
            errores.append(linea.decode('utf-8', 'replace'))

    hilo = threading.Thread(target=_leer_err, daemon=True)
    hilo.start()
    try:
        proc.stdin.write(stdin.encode('utf-8'))
        proc.stdin.close()
    except OSError:
        pass
    huboerror = False
    for linea in proc.stdout:
        linea = linea.decode('utf-8', 'replace').strip()
        if not linea.startswith('{'):
            continue
        try:
            ev = json.loads(linea)
        except ValueError:
            continue
        for e in tr(ev):
            huboerror |= e['t'] == 'error'
            emitir(e)
    codigo = proc.wait()
    hilo.join(timeout=2)
    if codigo != 0 and not huboerror:
        cola = ''.join(errores).strip()[-600:]
        emitir({'t': 'error', 'texto': 'El agente terminó con código %s. %s' % (codigo, cola)})
    return tr.sesion or id_nuevo
