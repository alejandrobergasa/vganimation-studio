"""REWINDLIMBO2 · tramo 1 (0:00-1:10). Preparativos (v3).

Original: dentro del coche arranca y prepara la pipa (0:00-0:14); sale, se pone el sombrero y cierra la puerta
(0:14-0:24); llena, enciende y fuma la pipa (0:24-0:40); fuma y consulta el mapa dibujado a mano (0:40-0:59);
cruza la calzada y llega al cartel del parque (0:59-1:10).

Versión Platino (v3): Pueblo Arena (zona 26,4) con un coche plateado propio aparcado en la calle, cuya puerta se
abre y se cierra. Las manipulaciones se cuentan con primeros planos animados en ventanas del juego, dibujados en
pixel art propio (graficos_v3.py): la llave en el contacto, cargar la pipa dentro del coche, encenderla con el
mechero junto al coche y desplegar el mapa. EL MARÍA tiene poses nuevas: sombrero en las manos, pipa en la boca,
agachado encendiéndola y con el mapa abierto.

Ejecutar desde cinematicas/:  python escenas/rewindlimbo2/t1_preparativos.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import cartel_pintado, exportar, humo, inserto, textos  # noqa
from graficos_v3 import coche, contacto, plano_mapa, plano_pipa  # noqa
from PIL import Image

from motor import Escena, MapaReal

T0, T1 = 0.0, 70.0
mapa = MapaReal(fila=26, col=4, filas=2, cols=2, hora=12)
esc = Escena(mapa, t0=T0)
COCHE, COCHE_ABIERTO = coche(), coche(True)
auto = esc.objeto(COCHE, 44, 13)
maria = esc.personaje('el_maria', 44, 14, mira='abajo')
maria.visible = False                                            # empieza dentro del coche
letrero = esc.objeto(cartel_pintado(), 25, 10)
esc.camara_fija(44, 11)
esc.subtitulos(textos.subtitulos(T0, T1))
VX, VY = 34, 6                                                   # esquina de las ventanas de primer plano
PIPA_BOCA = (11, 22)                                             # cazoleta en los frames 19/21, en px del sprite


# ---------------------------------------------------------------- utilidades de los primeros planos

def ventana(img):
    return inserto(img, 1)


def plano(nombre, frames, dibujo):
    """Anima una ventana ya mostrada: dibujo(f) da la imagen del frame f (0..frames-1). Cachea por argumentos."""
    cache = {}

    def paso(f):
        clave = dibujo(f)
        if clave not in cache:
            fn, args = clave[0], clave[1:]
            cache[clave] = ventana(fn(*args))
        if nombre in esc.capas:
            esc.capas[nombre][0] = cache[clave]
    return esc.durante(frames, paso)


def cargar(fondo, frames, relleno0=0):
    """Pellizcos de tabaco: la mano baja, aprieta y sube; cada dos el tabaco sube de nivel."""
    def dib(f):
        ciclo, g = divmod(f, 26)
        alto = (14, 10, 6, 3, 0, 0, 0, 0, 2, 6, 10, 14, 16)[min(12, g // 2)]
        relleno = min(2, relleno0 + (ciclo + (g >= 12)) // 2)
        return (plano_pipa, fondo, relleno, 'pinza', alto)
    return dib


def encender(fondo, frames, relleno=2):
    """Mechero: chispa, llama que tiembla y que se mete en la cazoleta en cada calada; brasa y humo."""
    def dib(f):
        if f < 6:
            return (plano_pipa, fondo, relleno, 'mechero', 0, None, 0.0, 0, None)
        calada = (f - 6) % 30
        tirar = 0.0 if calada < 8 else min(1.0, (calada - 8) / 6) if calada < 22 else max(0.0, 1 - (calada - 22) / 4)
        tirar = round(tirar * 4) / 4
        brasa = min(2, (f - 6) // 30 + (calada > 14))
        hum = (calada - 14) if calada >= 14 else None
        return (plano_pipa, fondo, relleno, 'mechero', 0, (f // 3) % 3, tirar, brasa, hum)
    return dib


HUMO_PIPA = [im.resize((16, 16), Image.NEAREST) for im in humo()]     # el humo del juego, a escala de pipa


def fumada(t):
    """Una bocanada pequeña saliendo de la cazoleta de la pipa (frames 19/21) en el segundo t."""
    def gen():
        yield from esc.hasta(t)
        for f in range(24):
            img = HUMO_PIPA[min(3, f // 6)]
            esc.efectos.append((img, maria.x + PIPA_BOCA[0] - 24, maria.y + PIPA_BOCA[1] - 26 - f // 2 - maria.elevacion))
            yield
    return gen()


def fumar(desde, hasta, cada=2.4):
    acc = []
    t = desde
    while t < hasta:
        acc.append(fumada(t))
        t += cada
    return acc


# ---------------------------------------------------------------- 0:00 dentro del coche: el contacto
esc.hacer(esc.fundido(entrada=True, frames=30))
esc.hacer(esc.mostrar('plano', ventana(contacto(0.0)), x=VX, y=VY, efecto='zoom', frames=8))
esc.hacer(plano('plano', 30, lambda f: (contacto, min(1.0, round(f / 24 * 8) / 8), 0.0, False, 0)))   # entra la mano
esc.hacer(esc.hasta(2.6))
esc.hacer(plano('plano', 6, lambda f: (contacto, 1.0, (f + 1) / 6, False, 0)), esc.sonido('SEQ_SE_DP_KASYA', 0.5))
esc.hacer(plano('plano', 36, lambda f: (contacto, 1.0, 1.0, True, (1 if f % 4 < 2 else 0) if f < 24 else 0)),
          auto.temblar(24, 1), esc.sonido('SEQ_SE_DP_KOUKA_L', 0.25))                         # arranca el motor
esc.hacer(esc.hasta(4.6))
esc.hacer(esc.ocultar('plano', 6))

# ---------------------------------------------------------------- 0:05 carga la pipa y la enciende en el asiento
esc.hacer(esc.hasta(5.2))
esc.hacer(esc.mostrar('plano', ventana(plano_pipa('coche', 0)), x=VX, y=VY, efecto='zoom', frames=8))
esc.hacer(plano('plano', int(2.6 * 30), cargar('coche', 78)))
esc.hacer(plano('plano', 12, lambda f: (plano_pipa, 'coche', 2)))
esc.hacer(esc.hasta(9.6))
esc.hacer(plano('plano', int(2.9 * 30), encender('coche', 87)), esc.sonido('SEQ_SE_DP_KASYA', 0.4))
esc.hacer(plano('plano', 10, lambda f: (plano_pipa, 'coche', 2, None, 0, None, 0.0, 1, 12 + f)))
esc.hacer(esc.hasta(13.0))
esc.hacer(esc.ocultar('plano', 8))

# ---------------------------------------------------------------- 0:14 sale, se pone el sombrero y cierra
esc.hacer(esc.hasta(14.0))
esc.hacer(auto.posar(COCHE_ABIERTO), esc.sonido('SEQ_SE_DP_DOOR_OPEN', 0.5))
esc.hacer(maria.desvanecer(True, 8))
esc.hacer(esc.hasta(16.0))
esc.hacer(maria.posar(16))                                                     # el sombrero en las manos
esc.hacer(esc.hasta(19.3))
esc.hacer(maria.posar(None), maria.cambiar_sprite('el_maria_sombrero'), maria.saltar(4, 8),
          esc.animacion(HUMO_PIPA, maria.x + 16, maria.y - 14, 16, cada=4), esc.sonido('SEQ_SE_DP_BOX01', 0.4))
esc.hacer(esc.hasta(20.6))
esc.hacer(maria.mirar('arriba'))
esc.hacer(esc.hasta(22.4))
esc.hacer(auto.posar(COCHE), auto.temblar(6, 1), esc.sonido('SEQ_SE_DP_DOOR_CLOSE', 0.6))   # portazo
esc.hacer(esc.hasta(23.6))
esc.hacer(maria.mirar('abajo'))

# ---------------------------------------------------------------- 0:24 llena la pipa junto al coche
esc.hacer(esc.hasta(24.6))
esc.hacer(maria.posar(19))
esc.hacer(esc.mostrar('plano', ventana(plano_pipa('calle', 0)), x=VX, y=VY, efecto='zoom', frames=8))
esc.hacer(plano('plano', int(5.0 * 30), cargar('calle', 150)))
esc.hacer(esc.hasta(30.2))
esc.hacer(esc.ocultar('plano', 6))

# ---------------------------------------------------------------- 0:32 agachado, la enciende con el mechero
esc.hacer(esc.hasta(31.6))
esc.hacer(maria.posar(21))
esc.hacer(esc.hasta(32.5))
esc.hacer(esc.mostrar('plano', ventana(plano_pipa('calle', 2, 'mechero')), x=VX, y=VY, efecto='zoom', frames=6),
          esc.sonido('SEQ_SE_DP_KASYA', 0.4))
esc.hacer(plano('plano', int(3.0 * 30), encender('calle', 90)))
esc.hacer(esc.ocultar('plano', 6), esc.en_paralelo(fumada(35.8)))
esc.hacer(esc.hasta(36.0))
esc.hacer(maria.posar(19), maria.saltar(3, 6), esc.en_paralelo(*fumar(36.8, 59.0)))   # se levanta fumando

# ---------------------------------------------------------------- 0:40 despliega el mapa
esc.hacer(esc.hasta(42.0))
esc.hacer(maria.posar(20), esc.sonido('SEQ_SE_DP_KAMI', 0.5),
          esc.mostrar('plano', ventana(plano_mapa(0)), x=VX - 8, y=VY, efecto='subir', frames=10))
esc.hacer(plano('plano', 18, lambda f: (plano_mapa, 0 if f < 6 else 1 if f < 12 else 2)))
esc.hacer(esc.hasta(50.0))
esc.hacer(esc.ocultar('plano', 10, 'bajar'), maria.posar(19))
esc.hacer(esc.hasta(55.0))
esc.hacer(maria.posar(20), esc.sonido('SEQ_SE_DP_KAMI', 0.5),
          esc.mostrar('plano', ventana(plano_mapa(2)), x=VX - 8, y=VY, efecto='subir', frames=10))
esc.hacer(esc.hasta(58.6))
esc.hacer(esc.ocultar('plano', 10, 'bajar'), maria.posar(19))

# ---------------------------------------------------------------- 0:59 cruza hacia el parque
esc.hacer(esc.hasta(59.5))
esc.hacer(maria.posar(None), esc.accion(lambda: esc.camara_sigue(maria)),
          maria.ruta(('izquierda', 3), ('arriba', 2), ('izquierda', 16)))            # (44,14) -> (25,12)
esc.hacer(maria.mirar('arriba'))
esc.hacer(esc.hasta(68.2))
esc.hacer(maria.emocion('!', 30), maria.saltar(5, 8))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't1_preparativos', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
