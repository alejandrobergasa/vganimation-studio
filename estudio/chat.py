"""Conversación de un proyecto con su agente: historial en disco, difusión de eventos y turnos en segundo plano."""
import json
import os
import queue
import threading
import time

from valedores import proyectos, rutas
from . import agentes

ESTADO = os.path.join(rutas.REPO, '.estudio', 'chats')


class Chat:
    def __init__(self, slug):
        self.slug = slug
        self.dir = ESTADO
        os.makedirs(self.dir, exist_ok=True)
        self.f_log = os.path.join(self.dir, slug + '.jsonl')
        self.f_ses = os.path.join(self.dir, slug + '.sesion.json')
        self.lock = threading.Lock()
        self.eventos = []
        self.suscriptores = []
        self.proc = None
        self.ocupado = False
        self.parado = False
        self.sesiones = {}
        if os.path.isfile(self.f_log):
            with open(self.f_log, encoding='utf-8') as f:
                for linea in f:
                    try:
                        self.eventos.append(json.loads(linea))
                    except ValueError:
                        pass
        if os.path.isfile(self.f_ses):
            try:
                with open(self.f_ses, encoding='utf-8') as f:
                    self.sesiones = json.load(f)
            except ValueError:
                self.sesiones = {}

    # ---- eventos
    def emitir(self, ev, persistir=True):
        with self.lock:
            ev = dict(ev, ts=time.strftime('%H:%M:%S'))
            if persistir:
                ev['n'] = len(self.eventos)
                self.eventos.append(ev)
                with open(self.f_log, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(ev, ensure_ascii=False) + '\n')
            subs = list(self.suscriptores)
        for q in subs:
            q.put(ev)

    def suscribir(self):
        q = queue.Queue()
        with self.lock:
            self.suscriptores.append(q)
        return q

    def baja(self, q):
        with self.lock:
            if q in self.suscriptores:
                self.suscriptores.remove(q)

    def _guardar_sesiones(self):
        with open(self.f_ses, 'w', encoding='utf-8') as f:
            json.dump(self.sesiones, f)

    # ---- turnos
    def enviar(self, texto):
        """Lanza un turno. Devuelve False si el agente sigue ocupado."""
        with self.lock:
            if self.ocupado:
                return False
            self.ocupado = True
            self.parado = False
        self.emitir({'t': 'usuario', 'texto': texto})
        self.emitir({'t': 'estado', 'estado': 'trabajando'}, persistir=False)
        threading.Thread(target=self._turno, args=(texto,), daemon=True).start()
        return True

    def _turno(self, texto, reintento=False):
        try:
            p = proyectos.leer(self.slug)
            agente = p.get('agente', 'claude')
            sesion = self.sesiones.get(agente)
            sistema = proyectos.contexto(self.slug)
            hubo_error = []

            def emitir(e):
                if self.parado and e['t'] == 'error':
                    return
                if e['t'] == 'error':
                    hubo_error.append(e['texto'])
                self.emitir(e, persistir=e['t'] != 'delta')

            nueva = agentes.ejecutar_turno(
                agente, texto, p.get('modelo'), p.get('esfuerzo'), p.get('permisos', 'normal'), sesion, rutas.REPO,
                {'VALEDORES_PROYECTO': self.slug}, emitir, sistema=sistema,
                registrar_proc=lambda pr: setattr(self, 'proc', pr))
            if sesion and hubo_error and 'No conversation found' in ' '.join(hubo_error) and not reintento:
                self.sesiones.pop(agente, None)
                self._guardar_sesiones()
                return self._turno(texto, reintento=True)
            if nueva:
                self.sesiones[agente] = nueva
                self._guardar_sesiones()
        except Exception as e:  # noqa: BLE001  (se muestra en el chat)
            self.emitir({'t': 'error', 'texto': str(e)})
        finally:
            with self.lock:
                self.ocupado = False
                self.proc = None
            if self.parado:
                self.emitir({'t': 'sistema', 'texto': 'Agente detenido.'})
            self.emitir({'t': 'estado', 'estado': 'libre'}, persistir=False)
            self.emitir({'t': 'proyecto'}, persistir=False)

    def parar(self):
        self.parado = True
        agentes.matar(self.proc)


_CHATS = {}
_L = threading.Lock()


def obtener(slug):
    with _L:
        if slug not in _CHATS:
            _CHATS[slug] = Chat(slug)
        return _CHATS[slug]
