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
    c.emitir({'t': 'fin', 'coste': 0.10, 'uso': uso, 'reparto': {'guion': 1.0}})
    c.emitir({'t': 'fin', 'coste': 0.20, 'uso': uso, 'reparto': {'guion': 0.5, 'musica': 0.5}})
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
