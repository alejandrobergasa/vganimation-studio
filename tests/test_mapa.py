"""Pruebas del mapa del vídeo: elementos, cambios, tiempos estimados, consumo de tokens, carriles en paralelo y cola de mensajes."""
import json
import os
import sys
import threading
import time

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, 'nucleo'))

from valedores import proyectos, rutas, tareas  # noqa: E402
from test_nucleo import _pedir, repo_temporal, servidor  # noqa: E402,F401


def test_modificaciones_concurrentes_no_se_pisan(repo_temporal):
    proyectos.crear('Carrera', 'nsmb')
    fases = ['idea', 'guion', 'musica', 'storyboard']

    def marcar(f):
        for i in range(8):
            proyectos.fase('carrera', f, 'validar', nota='%s %d' % (f, i))
            proyectos.elemento('carrera', 'e_' + f, tipo='otro', fase_id=f, nota='n%d' % i)
    hilos = [threading.Thread(target=marcar, args=(f,)) for f in fases]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    p = proyectos.leer('carrera')
    assert all(p['fases'][f]['estado'] == 'validar' and p['fases'][f]['nota'].endswith(' 7') for f in fases)
    assert set(p['elementos']) == {'e_' + f for f in fases}


def test_fase_apunta_inicio_y_duracion(repo_temporal):
    proyectos.crear('Tiempos', 'nsmb')
    proyectos.fase('tiempos', 'guion', 'en_curso', eta=90)
    f = proyectos.leer('tiempos')['fases']['guion']
    assert f['eta'] == 90 and f['inicio'] and 'duraciones' not in f
    p = proyectos.leer('tiempos')
    p['fases']['guion']['inicio'] -= 30
    proyectos.guardar('tiempos', p)
    proyectos.fase('tiempos', 'guion', 'validar')
    f = proyectos.leer('tiempos')['fases']['guion']
    assert 'inicio' not in f and 'eta' not in f and 29 <= f['duraciones'][0] <= 32


def test_elementos(repo_temporal):
    proyectos.crear('Mapa', 'mkds')
    e = proyectos.elemento('mapa', 'mario', tipo='personaje', nombre='Mario', fase_id='escenas', estado='en_curso', progreso=40, depende=['guion'])
    assert e['nombre'] == 'Mario' and e['estado'] == 'en_curso' and e['progreso'] == 40 and e['inicio']
    proyectos.elemento('mapa', 'mario', archivos=['a.png', 'a.png'], estado='validar')
    e = proyectos.leer('mapa')['elementos']['mario']
    assert e['archivos'] == ['a.png'] and e['estado'] == 'validar' and 'inicio' not in e and e['nombre'] == 'Mario'
    assert proyectos.elemento('mapa', 'raro', tipo='inventado', fase_id='guion')['tipo'] == 'otro'
    with pytest.raises(ValueError):
        proyectos.elemento('mapa', 'sin_fase')
    with pytest.raises(ValueError):
        proyectos.elemento('mapa', 'x y')
    # al aprobar la fase, sus elementos en «validar» se aprueban
    proyectos.fase('mapa', 'escenas', 'aprobada')
    assert proyectos.leer('mapa')['elementos']['mario']['estado'] == 'aprobada'
    proyectos.elemento('mapa', 'mario', borrar=True)
    assert 'mario' not in proyectos.leer('mapa')['elementos']


def test_cambio_sobre_una_fase_anterior_marca_lo_que_depende(repo_temporal):
    proyectos.crear('Cambios', 'nsmb')
    for f in ('idea', 'guion', 'musica', 'storyboard', 'escenas'):
        proyectos.fase('cambios', f, 'aprobada')
    proyectos.fase('cambios', 'render', 'validar')
    proyectos.elemento('cambios', 'tema', tipo='musica', fase_id='musica', estado='aprobada')
    assert proyectos.posteriores('musica') == ['escenas', 'render', 'revision']
    assert proyectos.posteriores('guion') == ['musica', 'storyboard', 'escenas', 'render', 'revision']
    c = proyectos.pedir_cambio('cambios', 'La música, más lenta', [{'tipo': 'elemento', 'id': 'tema'}], ['escenas', 'render', 'revision'])
    p = proyectos.leer('cambios')
    assert c['id'] == 1 and c['estado'] == 'pendiente'
    assert [f for f in proyectos.IDS_FASE if p['fases'][f]['estado'] == 'cambios'] == ['musica', 'escenas', 'render']
    assert p['fases']['revision']['estado'] == 'pendiente'          # sin trabajo hecho: no se toca
    assert p['fases']['storyboard']['estado'] == 'aprobada'         # no depende de la música
    assert p['elementos']['tema']['estado'] == 'cambios' and p['fase_actual'] == 'musica'
    assert 'Cambio #1' in p['fases']['render']['nota']
    proyectos.cambio_estado('cambios', 1, 'hecho')
    assert proyectos.leer('cambios')['cambios'][0]['estado'] == 'hecho'
    assert proyectos.pedir_cambio('cambios', 'Otra cosa', [])['id'] == 2
    with pytest.raises(ValueError):
        proyectos.pedir_cambio('cambios', '  ', [])
    with pytest.raises(ValueError):
        proyectos.cambio_estado('cambios', 9, 'hecho')


def test_paralelo(repo_temporal):
    proyectos.crear('Paralelo', 'nsmb')
    p = proyectos.leer('paralelo')
    assert proyectos.puede_paralelo(p, 'musica')[0] is False
    proyectos.fase('paralelo', 'idea', 'aprobada')
    proyectos.fase('paralelo', 'guion', 'aprobada')
    p = proyectos.leer('paralelo')
    assert proyectos.puede_paralelo(p, 'musica')[0] and proyectos.puede_paralelo(p, 'storyboard')[0]
    assert not proyectos.puede_paralelo(p, 'escenas')[0] and not proyectos.puede_paralelo(p, 'guion')[0]
    assert 'EN PARALELO' in proyectos.contexto('paralelo', 'musica').upper()


def test_tareas_estiman_con_el_historial(repo_temporal):
    proyectos.crear('Render', 'nsmb')
    assert tareas.clave_de(['python', '-I', 'D:/x/proyectos/render/video.py', '--rapido']) == 'python -I video.py --rapido'
    assert tareas.etiqueta_de(['python', '-I', 'video.py']) == 'Ejecutando video.py'
    t = tareas.iniciar('render', 'Render', 'python -I video.py')
    act = tareas.activas('render')
    assert [x['id'] for x in act] == [t] and act[0]['eta'] is None
    tareas.terminar('render', t, True)
    assert tareas.activas('render') == []
    d = tareas._leer('render')
    d['historial']['python -I video.py'] = [100, 120, 140]
    tareas._modificar('render', lambda x: x.update(historial=d['historial']))
    assert tareas.estimar(d['historial'], 'python -I video.py') == 120
    assert tareas.estimar(d['historial'], 'python -I video.py --otro') == 120      # mismo script, otros argumentos
    t2 = tareas.iniciar('render', 'Render', 'python -I video.py', eta=300)
    assert tareas.activas('render')[0]['eta'] == 300
    tareas.terminar('render', t2, False)                                          # un fallo no ensucia el historial
    assert tareas._leer('render')['historial']['python -I video.py'] == [100, 120, 140]


def test_tareas_de_procesos_muertos_se_descartan(repo_temporal):
    proyectos.crear('Huerfana', 'nsmb')
    t = tareas.iniciar('huerfana', 'Algo', 'x', pid=2 ** 22 + 12345)
    assert tareas.activas('huerfana') == []
    tareas.terminar('huerfana', t)


def test_cli_ejecutar_registra_la_tarea(repo_temporal):
    from valedores import cli
    proyectos.crear('Cli', 'nsmb')
    codigo = cli.principal(['ejecutar', 'cli', '--eta', '5', '--', sys.executable, '-c', 'print(1)'])
    assert codigo == 0
    assert any(len(v) == 1 for v in tareas._leer('cli')['historial'].values())
    assert cli.principal(['elemento', 'cli', 'voz_1', '--tipo', 'voz', '--fase', 'guion', '--nombre', 'Voz del portero']) == 0
    assert proyectos.leer('cli')['elementos']['voz_1']['nombre'] == 'Voz del portero'


# ---------------------------------------------------------------- consumo de tokens
def test_traductor_claude_cuenta_tokens():
    from estudio.agentes import TraductorClaude
    t = TraductorClaude()
    inicio = {'type': 'stream_event', 'event': {'type': 'message_start', 'message': {'usage': {
        'input_tokens': 2, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 50, 'output_tokens': 1}}}}
    fin_msg = {'type': 'stream_event', 'event': {'type': 'message_delta', 'usage': {
        'input_tokens': 2, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 50, 'output_tokens': 30}}}
    vivo = t(inicio)[0]
    assert vivo['t'] == 'uso_vivo' and vivo['entrada'] == 2 and vivo['cache_leida'] == 50
    assert t(fin_msg)[0]['salida'] == 30
    seg = t(inicio)[0]                      # segunda llamada al modelo del mismo turno: se suma a la primera
    assert seg['entrada'] == 4 and seg['salida'] == 31 and seg['cache_escrita'] == 200
    r = t({'type': 'result', 'total_cost_usd': 0.5, 'duration_ms': 4000, 'modelUsage': {'claude-sonnet-5-5': {}},
           'usage': {'input_tokens': 4, 'output_tokens': 60, 'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 200}})[0]
    assert r['uso'] == {'entrada': 4, 'salida': 60, 'cache_leida': 100, 'cache_escrita': 200}
    assert r['coste'] == 0.5 and r['modelo'] == 'claude-sonnet-5-5'


def test_traductor_codex_separa_la_cache():
    from estudio.agentes import TraductorCodex
    r = TraductorCodex()({'type': 'turn.completed', 'usage': {'input_tokens': 1000, 'cached_input_tokens': 800, 'output_tokens': 70}})[0]
    assert r['uso'] == {'entrada': 200, 'salida': 70, 'cache_leida': 800, 'cache_escrita': 0} and r['coste'] is None


def test_coste_estimado_con_precios_del_usuario(monkeypatch):
    from estudio import agentes
    monkeypatch.setattr(agentes, 'precios', lambda: {'m': {'entrada': 2, 'salida': 10, 'cache_leida': 0.5}})
    uso = {'entrada': 1_000_000, 'salida': 100_000, 'cache_leida': 2_000_000, 'cache_escrita': 0}
    assert agentes.coste_estimado('m', uso) == pytest.approx(2 + 1 + 1)
    assert agentes.coste_estimado('otro', uso) is None


def test_resumen_de_uso_por_fase(repo_temporal, monkeypatch):
    from estudio import chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear('Gasto', 'nsmb')
    uso = {'entrada': 100, 'salida': 50, 'cache_leida': 1000, 'cache_escrita': 10}
    c = chat.obtener('gasto')
    c.emitir({'t': 'fin', 'coste': 0.10, 'coste_acum': 0.10, 'uso': uso, 'reparto': {'guion': 1.0}})
    c.emitir({'t': 'fin', 'coste': 0.20, 'coste_acum': 0.30, 'uso': uso, 'reparto': {'guion': 0.5, 'musica': 0.5}})
    c.emitir({'t': 'fin', 'coste': None, 'uso': uso, 'reparto': {'musica': 1.0}})
    c.emitir({'t': 'fin', 'coste': 0.01, 'tokens': 77})                      # historial antiguo sin desglose
    r = chat.resumen_uso('gasto')
    assert r['total']['entrada'] == 300 and r['total']['salida'] == 150 and r['total']['turnos'] == 4
    assert r['total']['coste'] == pytest.approx(0.31) and r['total']['coste_completo'] is False and r['total']['sin_desglose'] == 77
    assert r['por_fase']['guion']['entrada'] == 150 and r['por_fase']['guion']['coste'] == pytest.approx(0.20)
    assert r['por_fase']['musica']['coste'] == pytest.approx(0.10)
    chat._CHATS.clear()


def test_mensajes_en_cola_si_el_agente_esta_ocupado(repo_temporal, monkeypatch):
    from estudio import chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear('Cola', 'nsmb')
    c = chat.obtener('cola')
    lanzados = []
    monkeypatch.setattr(c, '_turno', lambda texto, reintento=False: lanzados.append(texto))
    c.ocupado = True
    assert c.enviar('segundo', None, 'instr') == 'cola' and c.textos_en_cola() == ['segundo']
    c.ocupado = False
    assert c.enviar('primero') == 'iniciado'
    time.sleep(0.1)
    assert lanzados == ['primero']
    chat._CHATS.clear()


# ---------------------------------------------------------------- servidor
def servidor_dir(monkeypatch):
    d = os.path.join(rutas.PROYECTOS, '..', 'chats')
    os.makedirs(d, exist_ok=True)
    return os.path.abspath(d)


def test_servidor_carriles_y_cambios(servidor, monkeypatch):
    from estudio import chat
    monkeypatch.setattr(chat, 'ESTADO', str(servidor_dir(monkeypatch)))
    chat._CHATS.clear()
    monkeypatch.setattr(chat.Chat, 'enviar', lambda self, texto, adjuntos=None, instrucciones=None: self.__dict__.setdefault('_vistos', []).append((texto, instrucciones)) or 'iniciado')
    cab = {'X-Estudio': '1', 'Content-Type': 'application/json'}
    _, cuerpo = _pedir(servidor + '/api/proyectos', 'POST', {'titulo': 'Par', 'juego': 'nsmb', 'agente': 'claude'}, cab)
    slug = json.loads(cuerpo)['slug']
    cod, cuerpo = _pedir(servidor + '/api/proyectos/%s/chat' % slug, 'POST', {'carril': 'musica'}, cab)
    assert cod == 400 and 'guion' in json.loads(cuerpo)['error']
    cod, _ = _pedir(servidor + '/api/proyectos/%s/chat' % slug, 'POST', {'carril': 'inventado', 'texto': 'x'}, cab)
    assert cod == 400
    proyectos.fase(slug, 'idea', 'aprobada')
    proyectos.fase(slug, 'guion', 'aprobada')
    cod, cuerpo = _pedir(servidor + '/api/proyectos/%s/chat' % slug, 'POST', {'carril': 'musica'}, cab)
    assert cod == 202
    assert 'música' in chat.obtener(slug, 'musica')._vistos[0][0].lower() or 'musica' in chat.obtener(slug, 'musica')._vistos[0][0]
    # un cambio sobre el guion (ya aprobado) afecta a lo posterior
    cod, cuerpo = _pedir(servidor + '/api/proyectos/%s/cambio' % slug, 'POST',
                         {'texto': 'Más corto', 'objetivos': [{'tipo': 'fase', 'id': 'guion'}], 'afectadas': ['musica', 'storyboard']}, cab)
    assert cod == 201 and json.loads(cuerpo)['fases_marcadas'] == ['guion']
    texto, instr = chat.obtener(slug)._vistos[-1]
    assert texto.startswith('✎ Cambio #1') and 'cambio %s 1 en_curso' % slug in instr
    cod, cuerpo = _pedir(servidor + '/api/proyectos/' + slug)
    v = json.loads(cuerpo)
    assert v['cambios'][0]['texto'] == 'Más corto' and v['paralelo']['musica']['puede'] is False   # el guion volvió a «cambios»
    assert {'total', 'por_fase'} <= set(v['uso']) and [c['id'] for c in v['carriles']] == ['principal', 'musica']
    cod, _ = _pedir(servidor + '/api/proyectos/%s/cambio/1' % slug, 'PATCH', {'estado': 'descartado'}, cab)
    assert cod == 200 and proyectos.leer(slug)['cambios'][0]['estado'] == 'descartado'
    cod, _ = _pedir(servidor + '/api/proyectos/%s/cambio' % slug, 'POST', {'texto': ''}, cab)
    assert cod == 400


# ---------------------------------------------------------------- ahorro de tokens (sesiones)
def test_traductor_claude_informa_del_contexto():
    from estudio.agentes import TraductorClaude
    t = TraductorClaude()
    t({'type': 'stream_event', 'event': {'type': 'message_start', 'message': {'usage': {
        'input_tokens': 3, 'cache_creation_input_tokens': 1000, 'cache_read_input_tokens': 29000, 'output_tokens': 1}}}})
    r = t({'type': 'result', 'total_cost_usd': 0.1, 'usage': {'input_tokens': 3, 'output_tokens': 5}})[0]
    assert r['contexto'] == 30003


def test_resumen_de_estado_y_contexto_estatico(repo_temporal):
    p = proyectos.crear('Resumen', 'nsmb')
    with open(os.path.join(rutas.proyecto_dir('resumen'), 'brief.md'), 'w', encoding='utf-8') as f:
        f.write('# Brief\n\nMario cruza la pantalla y se cae.\n')
    proyectos.fase('resumen', 'guion', 'validar', nota='Guion de 20 s', archivos=['guion.md'])
    proyectos.pedir_cambio('resumen', 'Más corto', [], [])
    r = proyectos.resumen_estado('resumen')
    assert 'Mario cruza la pantalla' in r and 'Guion de 20 s' in r and 'guion.md' in r and 'Más corto' in r
    assert r.count('\n') > 5 and '\\n' not in r
    # el texto de sistema no cambia con el estado del proyecto: si cambiara, la caché del prompt se perdería en cada mensaje
    a = proyectos.contexto('resumen', 'musica')
    proyectos.fase('resumen', 'storyboard', 'en_curso')
    assert proyectos.contexto('resumen', 'musica') == a


def test_politica_de_rotacion_de_sesion(repo_temporal, monkeypatch):
    from estudio import chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    p = proyectos.crear('Rota', 'nsmb')
    c = chat.obtener('rota')
    assert c._politica_sesion(p, 'claude', 'idea') == (None, None)                     # sin sesión no hay nada que renovar
    c.sesiones = {'claude': 'S1', '_meta': {'claude': {'fase': 'idea', 'ctx': 35_000, 'base': 29_000}}}
    assert c._politica_sesion(p, 'claude', 'guion') == ('S1', None)                    # cambio de fase, pero casi sin contexto extra
    c.sesiones['_meta']['claude']['ctx'] = 70_000
    assert c._politica_sesion(p, 'claude', 'idea') == ('S1', None)                     # misma fase: se sigue
    assert c._politica_sesion(p, 'claude', 'guion')[0] is None                         # otra fase y 41 k de más: sesión nueva
    assert c._politica_sesion(dict(p, optimizar=False), 'claude', 'guion') == ('S1', None)
    c.sesiones['_meta']['claude']['ctx'] = 160_000
    assert c._politica_sesion(p, 'claude', 'idea')[0] is None                          # demasiado grande aunque no cambie la fase
    c.sesiones['_meta']['claude']['ctx'] = 30_000
    c.renovar = True
    assert c._politica_sesion(p, 'claude', 'idea') == (None, 'a petición tuya')
    chat._CHATS.clear()


def test_turno_abre_sesion_nueva_con_resumen(repo_temporal, monkeypatch):
    from estudio import agentes, chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear('Giro', 'nsmb')
    c = chat.obtener('giro')
    visto = []

    def falso(agente, texto, modelo, esfuerzo, permisos, sesion, cwd, entorno, emitir, sistema=None, registrar_proc=None):
        visto.append((texto, sesion))
        emitir({'t': 'fin', 'uso': {'entrada': 1, 'salida': 1, 'cache_leida': 0, 'cache_escrita': 0}, 'contexto': 20_000 + 40_000 * len(visto), 'coste': 0.0})
        return 'S%d' % len(visto)
    monkeypatch.setattr(agentes, 'ejecutar_turno', falso)

    def turno(texto):
        c.ocupado = True
        c._turno(texto)
    turno('hola')
    assert visto[0] == ('hola', None)                                                  # primera vez: sin resumen
    turno('sigue')
    assert visto[1] == ('sigue', 'S1')                                                 # misma fase: se reanuda
    proyectos.fase('giro', 'idea', 'aprobada')
    proyectos.modificar('giro', lambda p: p.update(fase_actual='guion'))
    turno('ahora el guion')
    assert visto[2][1] is None and visto[2][0].endswith('ahora el guion') and 'Estado actual del proyecto' in visto[2][0]
    assert any(e.get('t') == 'sistema' and 'Sesión nueva' in e['texto'] for e in c.eventos)
    assert c.meta('claude')['base'] == 140_000 and c.sesiones['claude'] == 'S3'
    c.renovar_sesion()                                                                  # a petición del usuario, con el agente libre
    assert 'claude' not in c.sesiones and c.contexto_actual() == 0
    chat._CHATS.clear()


# ---------------------------------------------------------------- lecciones de las correcciones
@pytest.fixture
def juegos_temporales(repo_temporal, monkeypatch):
    """`juegos/` y `conocimiento/` de mentira (con el manifiesto real de NSMB) para no escribir lecciones en el repo de verdad."""
    import shutil
    raiz = repo_temporal / 'repo'
    (raiz / 'juegos' / 'nsmb').mkdir(parents=True)
    shutil.copy(os.path.join(rutas.JUEGOS, 'nsmb', 'juego.json'), raiz / 'juegos' / 'nsmb' / 'juego.json')
    (raiz / 'juegos' / 'nsmb' / 'CONOCIMIENTO.md').write_text('# NSMB\n\n## Otra cosa\n\ntexto\n', encoding='utf-8')
    monkeypatch.setattr(rutas, 'JUEGOS', str(raiz / 'juegos'))
    monkeypatch.setattr(rutas, 'REPO', str(raiz))
    return raiz


def test_lecciones_se_cuentan_y_se_promueven(juegos_temporales):
    from valedores import lecciones
    proyectos.crear('Lec', 'nsmb')
    l, nueva, _ = lecciones.registrar('nsmb', 'Pon los textos a la derecha del retrato; no los centres', 'tapaban la cara', 'lec', 1)
    assert nueva and l['veces'] == 1
    l2, nueva, _ = lecciones.registrar('nsmb', 'Pon los textos a la derecha del retrato, no los centres.', None, 'lec', 1)
    assert not nueva and l2['veces'] == 1                                   # misma corrección: no se cuenta dos veces
    l3, nueva, _ = lecciones.registrar('nsmb', 'pon los textos a la derecha del retrato; no los centres', None, 'otro', 2)
    assert not nueva and l3['id'] == l['id'] and l3['veces'] == 2           # otro vídeo con la misma corrección: sube el contador
    lecciones.registrar('nsmb', 'Normaliza el audio a -16 LUFS antes de mezclar la música', None, 'lec', 2)
    md = open(os.path.join(rutas.juego_dir('nsmb'), 'lecciones.md'), encoding='utf-8').read()
    assert md.index('retrato') < md.index('LUFS') and '(×2)' in md          # las más repetidas, primero
    with pytest.raises(ValueError):
        lecciones.registrar('nsmb', 'corta')
    lecciones.promover('nsmb', l['id'])
    conocimiento = open(os.path.join(rutas.juego_dir('nsmb'), 'CONOCIMIENTO.md'), encoding='utf-8').read()
    assert lecciones.SECCION in conocimiento and 'a la derecha del retrato' in conocimiento
    assert [x['id'] for x in lecciones.activas('nsmb')] != [l['id']] and 'retrato' not in open(os.path.join(rutas.juego_dir('nsmb'), 'lecciones.md'), encoding='utf-8').read()
    lecciones.registrar('nsmb', 'Pon los textos a la derecha del retrato; no los centres', None, 'tercero', 3)      # vuelve a fallar: se reabre
    assert l['id'] in [x['id'] for x in lecciones.activas('nsmb')]
    assert conocimiento.count('a la derecha del retrato') == 1


def test_madurez_y_cli_leccion(juegos_temporales, capsys):
    from valedores import cli, madurez
    proyectos.crear('Real', 'nsmb')
    assert cli.principal(['leccion', 'real', 'Mantén el texto dentro de la zona segura del vídeo vertical', '--comun']) == 0
    assert 'nueva' in capsys.readouterr().out
    m = {x['juego']: x for x in madurez.todos()}['nsmb']
    assert m['videos_reales'] == 1 and m['nivel'] in ('baja', 'media', 'alta')
    assert cli.principal(['lecciones']) == 0 and 'zona segura' in capsys.readouterr().out


def test_servidor_lecciones(servidor, juegos_temporales):
    from valedores import lecciones
    cab = {'X-Estudio': '1', 'Content-Type': 'application/json'}
    lecciones.registrar('nsmb', 'Deja un segundo de silencio al final de la música del vídeo', 'cortaba seco', 'x', 1)
    cod, cuerpo = _pedir(servidor + '/api/lecciones?juego=nsmb')
    ls = json.loads(cuerpo)
    assert cod == 200 and len(ls) == 1 and ls[0]['ambito'] == 'nsmb'
    assert _pedir(servidor + '/api/lecciones/nsmb/%d/promover' % ls[0]['id'], 'POST', None, {})[0] == 403           # sin X-Estudio
    assert _pedir(servidor + '/api/lecciones/nsmb/%d/promover' % ls[0]['id'], 'POST', {}, cab)[0] == 200
    assert json.loads(_pedir(servidor + '/api/lecciones?juego=nsmb')[1]) == []
    assert _pedir(servidor + '/api/lecciones/inventado/1/promover', 'POST', {}, cab)[0] == 404


# ---------------------------------------------------------------- coste por turno (Claude da el acumulado de la sesión)
def _chat_falso(monkeypatch, repo_temporal, nombre, turnos):
    """Chat cuyo agente devuelve, por turno, (coste acumulado, uso, contexto) como lo haría Claude Code con --resume."""
    from estudio import agentes, chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear(nombre, 'nsmb')
    c = chat.obtener(nombre)
    cola = list(turnos)

    def falso(agente, texto, modelo, esfuerzo, permisos, sesion, cwd, entorno, emitir, sistema=None, registrar_proc=None):
        acum, uso, ctx = cola.pop(0)
        emitir({'t': 'fin', 'coste': acum, 'uso': uso, 'contexto': ctx, 'modelo': 'claude-sonnet-5-5'})
        return 'S1'
    monkeypatch.setattr(agentes, 'ejecutar_turno', falso)
    return c


def test_coste_de_claude_es_la_diferencia_con_el_turno_anterior(repo_temporal, monkeypatch):
    from estudio import chat
    u = {'entrada': 1, 'salida': 10, 'cache_leida': 100, 'cache_escrita': 10}
    c = _chat_falso(monkeypatch, repo_temporal, 'acum', [(1.0, u, 20_000), (1.5, u, 20_000), (4.0, u, 20_000)])
    for t in ('uno', 'dos', 'tres'):
        c.ocupado = True
        c._turno(t)
    costes = [e['coste'] for e in c.eventos if e['t'] == 'fin']
    assert costes == pytest.approx([1.0, 0.5, 2.5])                       # no 1,0 + 1,5 + 4,0
    assert chat.resumen_uso('acum')['total']['coste'] == pytest.approx(4.0)
    chat._CHATS.clear()


def test_resumen_de_uso_corrige_el_historial_acumulado(repo_temporal, monkeypatch):
    from estudio import chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear('Viejo', 'nsmb')
    c = chat.obtener('viejo')
    for acum in (0.27, 0.39, 0.81, 7.07):                                  # así quedó guardado antes: el acumulado de la sesión en cada turno
        c.emitir({'t': 'fin', 'coste': acum, 'tokens': 1000})
    assert chat.resumen_uso('viejo')['total']['coste'] == pytest.approx(7.07)
    chat._CHATS.clear()


def test_consumo_del_turno_en_curso_y_del_interrumpido(repo_temporal, monkeypatch):
    from estudio import agentes, chat
    monkeypatch.setattr(chat, 'ESTADO', str(repo_temporal / 'chats'))
    chat._CHATS.clear()
    proyectos.crear('Curso', 'nsmb')
    proyectos.modificar('curso', lambda p: p.update(modelo='claude-sonnet-5-5'))
    c = chat.obtener('curso')

    def agente_que_se_cae(agente, texto, modelo, esfuerzo, permisos, sesion, cwd, entorno, emitir, sistema=None, registrar_proc=None):
        emitir({'t': 'uso_vivo', 'entrada': 10, 'salida': 1_000_000, 'cache_leida': 0, 'cache_escrita': 0})
        r = chat.resumen_uso('curso')                                       # a mitad del turno ya cuenta
        assert r['en_curso']['salida'] == 1_000_000 and r['en_curso']['coste'] == pytest.approx(10.0, abs=0.01) and r['en_curso']['carriles'] == ['principal']
        raise RuntimeError('se cayó')                                       # sin `result`
    monkeypatch.setattr(agentes, 'ejecutar_turno', agente_que_se_cae)
    c.ocupado = True
    c._turno('hola')
    fin = [e for e in c.eventos if e['t'] == 'fin']
    assert len(fin) == 1 and fin[0]['interrumpido'] and fin[0]['coste'] == pytest.approx(10.0, abs=0.01)
    r = chat.resumen_uso('curso')
    assert r['total']['salida'] == 1_000_000 and r['total']['coste'] == pytest.approx(10.0, abs=0.01) and r['en_curso']['carriles'] == []
    chat._CHATS.clear()


def test_precio_de_sonnet_coincide_con_el_que_informa_claude():
    from estudio import agentes
    uso = {'entrada': 136, 'salida': 101087, 'cache_leida': 10018195, 'cache_escrita': 214364}      # turno real de bolas_inazuma
    assert agentes.coste_estimado('claude-sonnet-5-5', uso) == pytest.approx(2.8704175, abs=1e-6)
