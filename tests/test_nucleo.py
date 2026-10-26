"""Pruebas del núcleo y del servidor del estudio. Se ejecutan con `python -m pytest tests` (no necesitan ROMs ni agentes)."""
import json
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import urllib.error
import urllib.request

import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, REPO)                          # `estudio`
sys.path.insert(0, os.path.join(REPO, 'nucleo'))  # `valedores` (el paquete, no el valedores.py de la raíz)

from valedores import juegos, proyectos, rutas, skills  # noqa: E402


@pytest.fixture
def repo_temporal(monkeypatch):
    """Redirige proyectos, entrada y salida a una carpeta temporal (dentro del repo, ignorada) para no ensuciarlo."""
    os.makedirs(os.path.join(REPO, '.cache'), exist_ok=True)
    tmp_path = pathlib.Path(tempfile.mkdtemp(prefix='test-', dir=os.path.join(REPO, '.cache')))
    for nombre in ('PROYECTOS', 'ENTRADA', 'SALIDA'):
        d = tmp_path / nombre.lower()
        d.mkdir()
        monkeypatch.setattr(rutas, nombre, str(d))
    monkeypatch.delenv('VALEDORES_PROYECTO', raising=False)
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)


def test_manifiestos_validos():
    ids = rutas.juegos()
    assert {'animal-crossing', 'nsmb', 'mkds', 'pokemon-platino'} <= set(ids)
    for j in juegos.todos():
        assert j['rom']['codigos'], j['id']
        assert j['formatos'], j['id']
        for f in j['formatos']:
            assert f['skill'] in juegos.skills_del_juego(j['id']), '%s: falta la skill %s' % (j['id'], f['skill'])


def test_skills_sincronizadas():
    assert skills.fuentes()                                   # sin nombres repetidos (si no, SystemExit)
    assert skills.sincronizar(solo_comprobar=True), 'ejecuta: python valedores.py skills'


def test_slugify():
    assert proyectos.slugify('¡Tom Nook cobra la hipoteca!') == 'tom_nook_cobra_la_hipoteca'
    assert proyectos.slugify('???') == 'video'


def test_crear_proyecto_y_fases(repo_temporal):
    p = proyectos.crear('Mi vídeo', 'animal-crossing', brief='idea')
    assert p['slug'] == 'mi_video' and p['fase_actual'] == 'idea'
    assert proyectos.crear('Mi vídeo', 'animal-crossing')['slug'] == 'mi_video_2'
    proyectos.fase('mi_video', 'idea', 'validar')
    assert proyectos.leer('mi_video')['fases']['idea']['estado'] == 'validar'
    proyectos.fase('mi_video', 'idea', 'aprobada', archivos=['brief.md'])
    q = proyectos.leer('mi_video')
    assert q['fase_actual'] == 'guion' and q['fases']['idea']['archivos'] == ['brief.md']
    with pytest.raises(ValueError):
        proyectos.fase('mi_video', 'nada', 'validar')
    with pytest.raises(ValueError):
        proyectos.fase('mi_video', 'idea', 'raro')
    with pytest.raises(ValueError):
        proyectos.crear('x', 'no-existe')


def test_contexto_menciona_proyecto(repo_temporal):
    proyectos.crear('Contexto', 'mkds')
    c = proyectos.contexto('contexto')
    assert 'VALEDORES_PROYECTO=contexto' in c and 'cinematica-mkds' in c


def test_salida_y_trabajo_siguen_al_proyecto(repo_temporal, monkeypatch):
    monkeypatch.setenv('VALEDORES_PROYECTO', 'demo')
    assert rutas.salida('mkds').endswith(os.path.join('salida', 'demo'))
    assert rutas.trabajo('mkds').replace('\\', '/').endswith('demo/trabajo')


def test_traductores():
    from estudio.agentes import TraductorClaude, TraductorCodex
    t = TraductorClaude()
    ev = t({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'hola'},
                                                       {'type': 'tool_use', 'id': 'a', 'name': 'Bash', 'input': {'command': 'ls'}}]}})
    assert [e['t'] for e in ev] == ['asistente', 'herramienta']
    c = TraductorCodex()
    assert c({'type': 'thread.started', 'thread_id': 'T'}) == [] and c.sesion == 'T'
    ev = c({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'OK'}})
    assert ev and ev[0]['t'] == 'asistente'


# ---------------------------------------------------------------- servidor
@pytest.fixture
def servidor(repo_temporal):
    from estudio import servidor as S
    srv = S.Servidor(('127.0.0.1', 0), S.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield 'http://127.0.0.1:%d' % srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _pedir(url, metodo='GET', cuerpo=None, cab=None):
    r = urllib.request.Request(url, data=json.dumps(cuerpo).encode() if cuerpo is not None else None, method=metodo, headers=cab or {})
    try:
        with urllib.request.urlopen(r) as x:
            return x.status, x.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def test_servidor_seguridad(servidor):
    assert _pedir(servidor + '/')[0] == 200
    assert _pedir(servidor + '/api/estado', cab={'Host': 'evil.example'})[0] == 403
    assert _pedir(servidor + '/api/proyectos', 'POST', {})[0] == 403                    # sin X-Estudio
    assert _pedir(servidor + '/api/archivo?ruta=roms/x.nds')[0] == 403
    assert _pedir(servidor + '/api/archivo?ruta=../../../../Windows/win.ini')[0] == 403
    assert _pedir(servidor + '/vistas/mkds/..%2F..%2FAGENTS.md')[0] == 404


def test_servidor_proyecto(servidor):
    cab = {'X-Estudio': '1', 'Content-Type': 'application/json'}
    cod, cuerpo = _pedir(servidor + '/api/proyectos', 'POST', {'titulo': 'Uno', 'juego': 'nsmb', 'agente': 'claude'}, cab)
    assert cod == 201
    slug = json.loads(cuerpo)['slug']
    cod, cuerpo = _pedir(servidor + '/api/proyectos/' + slug)
    assert cod == 200 and len(json.loads(cuerpo)['fases']) == len(proyectos.FASES)
    cod, _ = _pedir(servidor + '/api/proyectos/' + slug + '/fase', 'POST', {'fase': 'idea', 'accion': 'aprobar'}, cab)
    assert cod == 200
    assert proyectos.leer(slug)['fases']['idea']['estado'] == 'aprobada'
    cod, _ = _pedir(servidor + '/api/entrada?nombre=..%2F..%2Fmal.txt&proyecto=' + slug, 'POST', None, {'X-Estudio': '1'})
    assert cod in (201, 400)
    assert not os.path.exists(os.path.join(rutas.ENTRADA, '..', 'mal.txt'))
