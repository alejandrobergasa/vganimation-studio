"""Cerrojo de fichero y comprobación de procesos, compartidos por quien toca `proyecto.json` o `tareas.json`.

El estudio, el agente principal y los agentes en paralelo escriben el mismo fichero de estado desde procesos distintos;
cada lectura-modificación-escritura se hace con el cerrojo para que ninguna actualización pise a otra.
"""
import contextlib
import os
import time


@contextlib.contextmanager
def bloqueo(ruta_cerrojo, espera=8.0, caduca=20.0):
    """Exclusión mutua entre procesos con un fichero creado en exclusiva. Un cerrojo más viejo que `caduca` s se da por abandonado."""
    os.makedirs(os.path.dirname(ruta_cerrojo), exist_ok=True)
    t0 = time.time()
    while True:
        try:
            os.close(os.open(ruta_cerrojo, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except (FileExistsError, PermissionError):      # en Windows, crear un fichero que otro acaba de borrar da PermissionError
            try:
                if time.time() - os.path.getmtime(ruta_cerrojo) > caduca:
                    os.remove(ruta_cerrojo)
                    continue
            except OSError:
                pass
            if time.time() - t0 > espera:
                raise TimeoutError('No se pudo obtener el cerrojo %s' % os.path.basename(ruta_cerrojo))
            time.sleep(0.03)
    try:
        yield
    finally:
        try:
            os.remove(ruta_cerrojo)
        except OSError:
            pass


def reemplazar(origen, destino, intentos=10):
    """os.replace con reintentos: en Windows falla si otro proceso tiene el destino abierto en ese instante."""
    for i in range(intentos):
        try:
            os.replace(origen, destino)
            return
        except PermissionError:
            if i == intentos - 1:
                raise
            time.sleep(0.05)


def vivo(pid):
    """¿Sigue existiendo el proceso? (`os.kill(pid, 0)` en Windows mataría al proceso, por eso se pregunta a la API.)"""
    if not pid:
        return False
    if os.name == 'nt':
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, int(pid))          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            codigo = ctypes.c_ulong()
            return bool(k.GetExitCodeProcess(h, ctypes.byref(codigo))) and codigo.value == 259   # STILL_ACTIVE
        finally:
            k.CloseHandle(h)
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
