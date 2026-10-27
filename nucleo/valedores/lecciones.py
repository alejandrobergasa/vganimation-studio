"""Lecciones aprendidas de las correcciones del usuario.

Cada vez que el usuario corrige algo, el agente destila una regla («haz X, no Y») y la registra aquí. Las reglas se guardan por juego
(`juegos/<id>/lecciones.json`) o comunes (`conocimiento/lecciones.json`) y se pintan en un `lecciones.md` corto que el agente lee al empezar.
Si una regla se repite se cuenta (`veces`); las que el usuario aprueba se promueven al `CONOCIMIENTO.md` del juego (o a
`conocimiento/reglas-de-produccion.md`) y dejan de ocupar sitio en la lista activa. El texto activo está acotado para no encarecer cada sesión.
"""
import difflib
import json
import os
import re
import time

from . import bloqueo, rutas

COMUN = 'comun'
MAX_ACTIVAS = 25            # por encima, el agente debe pedir que se consoliden (promover o descartar)
SECCION = '## Reglas de producción (aprendidas de las correcciones)'


def _dir(juego):
    return os.path.join(rutas.REPO, 'conocimiento') if juego == COMUN else rutas.juego_dir(juego)


def _json(juego):
    return os.path.join(_dir(juego), 'lecciones.json')


def _md(juego):
    return os.path.join(_dir(juego), 'lecciones.md')


def _normal(t):
    return re.sub(r'[^\w\s]', ' ', t.lower()).split()


def parecidas(a, b):
    na, nb = _normal(a), _normal(b)
    if not na or not nb:
        return False
    comunes = len(set(na) & set(nb))
    jaccard = comunes / len(set(na) | set(nb))
    return jaccard >= 0.6 or difflib.SequenceMatcher(None, ' '.join(na), ' '.join(nb)).ratio() >= 0.8


def leer(juego):
    try:
        with open(_json(juego), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {'siguiente': 1, 'lecciones': []}


def _guardar(juego, datos):
    os.makedirs(_dir(juego), exist_ok=True)
    tmp = _json(juego) + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    bloqueo.reemplazar(tmp, _json(juego))
    _pintar(juego, datos)


def activas(juego):
    ls = [l for l in leer(juego)['lecciones'] if l['estado'] == 'activa']
    return sorted(ls, key=lambda l: (-l['veces'], -l['ultima']))


def _pintar(juego, datos):
    act = sorted([l for l in datos['lecciones'] if l['estado'] == 'activa'], key=lambda l: (-l['veces'], -l['ultima']))
    if not act:
        if os.path.isfile(_md(juego)):
            os.remove(_md(juego))
        return
    lineas = ['# Lecciones de las correcciones (%s)' % ('comunes' if juego == COMUN else juego), '',
              'Reglas que el usuario ha tenido que corregir antes. Aplícalas desde el principio; no las repitas.', '']
    for l in act:
        lineas.append('- %s%s' % (l['regla'], ' (×%d)' % l['veces'] if l['veces'] > 1 else ''))
    with open(_md(juego), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lineas) + '\n')


def registrar(juego, regla, causa=None, slug=None, cambio=None):
    """Añade una regla o, si ya existe una parecida, cuenta una repetición más. Devuelve (lección, es_nueva, activas)."""
    regla = ' '.join((regla or '').split())
    if len(regla) < 12:
        raise ValueError('La regla es demasiado corta: una frase imperativa («haz X; no hagas Y»).')
    if len(regla) > 300:
        raise ValueError('La regla es demasiado larga (máx. 300 caracteres): una sola idea por lección.')
    os.makedirs(_dir(juego), exist_ok=True)
    with bloqueo.bloqueo(os.path.join(_dir(juego), '.lecciones.lock'), 10, 30):
        datos = leer(juego)
        origen = '%s#%s' % (slug, cambio) if slug and cambio else slug
        for l in datos['lecciones']:
            if l['estado'] != 'descartada' and parecidas(l['regla'], regla):
                if origen and origen in l['origenes']:
                    return l, False, len([x for x in datos['lecciones'] if x['estado'] == 'activa'])
                l['veces'] += 1
                l['ultima'] = int(time.time())
                if origen:
                    l['origenes'].append(origen)
                if causa and not l.get('causa'):
                    l['causa'] = causa
                if l['estado'] == 'promovida':
                    l['estado'] = 'activa'             # volvió a fallar aunque estaba en el conocimiento: que vuelva a verse
                    l['reabierta'] = l.get('reabierta', 0) + 1
                nuevo = False
                lec = l
                break
        else:
            lec = {'id': datos['siguiente'], 'regla': regla, 'causa': causa, 'veces': 1, 'origenes': [origen] if origen else [],
                   'estado': 'activa', 'creada': int(time.time()), 'ultima': int(time.time())}
            datos['siguiente'] += 1
            datos['lecciones'].append(lec)
            nuevo = True
        _guardar(juego, datos)
        return lec, nuevo, len([x for x in datos['lecciones'] if x['estado'] == 'activa'])


def _cambiar(juego, id_, estado):
    with bloqueo.bloqueo(os.path.join(_dir(juego), '.lecciones.lock'), 10, 30):
        datos = leer(juego)
        lec = next((l for l in datos['lecciones'] if l['id'] == id_), None)
        if not lec:
            raise ValueError('No existe la lección %s de %s' % (id_, juego))
        lec['estado'] = estado
        _guardar(juego, datos)
        return lec


def descartar(juego, id_):
    return _cambiar(juego, id_, 'descartada')


def promover(juego, id_):
    """Pasa la regla al conocimiento permanente (CONOCIMIENTO.md del juego, o reglas-de-produccion.md si es común)."""
    destino = os.path.join(rutas.REPO, 'conocimiento', 'reglas-de-produccion.md') if juego == COMUN else os.path.join(rutas.juego_dir(juego), 'CONOCIMIENTO.md')
    lec = _cambiar(juego, id_, 'promovida')
    texto = ''
    if os.path.isfile(destino):
        with open(destino, encoding='utf-8') as f:
            texto = f.read()
    elif juego == COMUN:
        texto = '# Reglas de producción comunes\n\nAprendidas de las correcciones del usuario en varios juegos; se leen con `crear-video`.\n'
    linea = '- %s\n' % lec['regla']
    if SECCION in texto:
        antes, despues = texto.split(SECCION, 1)
        resto = despues.lstrip('\n')
        m = re.search(r'^## ', resto, re.M)
        cuerpo, cola = (resto[:m.start()], resto[m.start():]) if m else (resto, '')
        texto = antes + SECCION + '\n\n' + cuerpo.rstrip('\n') + '\n' + linea + ('\n' + cola if cola else '')
    else:
        texto = texto.rstrip('\n') + '\n\n' + SECCION + '\n\n' + linea
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(texto)
    return lec
