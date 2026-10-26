"""eleccionesdont: vídeo educativo sobre la ley D'Hondt de las elecciones generales españolas.

Un profesor explica en la plaza de Pueblo Aromaflor, con ayuda de pizarras (escenas/dhondt_gfx.py), a dos
alumnos: cómo se reparten los 350 escaños, el método paso a paso con una provincia de ejemplo (partidos
inventados), por qué se eligió, ventajas, desventajas y paradojas. La música (reggaetón con el banco de
Platino) se genera aparte con trabajo/dhondt/musica_reggaeton.py y se mezcla con trabajo/dhondt/montaje.py.

Ejecutar desde cinematicas/:  python escenas/eleccionesdont.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from motor_v2 import Escena, MapaReal
from motor.recursos import SALIDA
from motor.escena import envolver
import dhondt_gfx as g

mapa = MapaReal('aromaflor', hora=12)
esc = Escena(mapa)
profe = esc.personaje('doctor', 17, 48, mira='abajo')
lucas = esc.personaje('heroe_andar_correr', 14, 51, mira='arriba')
maya = esc.personaje('pl_girl01c', 20, 51, mira='arriba')
esc.camara_fija(17, 48)

NOMBRES = {'P': 'PROFE', 'L': 'LUCAS', 'M': 'MAYA'}


def habla(quien, texto, espera=58):
    """Una intervención (puede ocupar varias ventanas de 2 líneas)."""
    lineas = envolver('%s: %s' % (NOMBRES[quien], texto))
    esc.hacer(esc.dialogo('\n'.join(lineas), espera=espera, velocidad=1.6))


def pizarra(img, entrada=True):
    esc.hacer(esc.mostrar('p', img, 0, 0, frames=10, efecto='subir', orden=5))


def cambia(img):
    esc.hacer(esc.cambiar_capa('p', img))


def quita():
    esc.hacer(esc.ocultar('p', frames=10, efecto='bajar'))


def ding(nombre='SEQ_SE_DP_PINPON', v=0.6):
    esc.hacer(esc.sonido(nombre, v))


# ================================================================ entrada
esc.hacer(esc.fundido(entrada=True, frames=24), lucas.andar('arriba', 3), maya.andar('arriba', 3))
esc.hacer(lucas.andar('derecha', 1), maya.andar('izquierda', 1))
esc.hacer(lucas.mirar('derecha'), maya.mirar('izquierda'))
esc.esperar(10)
habla('L', '¡Profe! Mañana hay examen y no entiendo la ley d\'Hondt.')
esc.hacer(profe.mirar('izquierda'))
esc.esperar(6)
habla('P', 'Tranquilo, es solo una división con una tabla. Te lo cuento con partidos inventados, para no meternos en política.')
esc.hacer(profe.mirar('abajo'))
pizarra(g.p_titulo())
ding('SEQ_SE_DP_KIRAKIRA', 0.5)
habla('P', 'La ley d\'Hondt reparte los escaños del Congreso de los Diputados en las elecciones generales.')

# ================================================================ el reparto territorial
cambia(g.p_congreso(0))
habla('P', 'El Congreso tiene 350 diputados.')
habla('M', '¿Y cómo se reparten entre las provincias?')
cambia(g.p_congreso(1))
habla('P', 'España tiene 52 circunscripciones: las 50 provincias, Ceuta y Melilla. Cada provincia recibe 2 diputados fijos, y Ceuta y Melilla uno cada una. Son 102 en total.')
habla('P', 'Los otros 248 se reparten según la población. Por eso Madrid tiene 37 diputados, y Soria, solo 2.')
cambia(g.p_listas())
habla('L', '¿Y votamos a personas?')
habla('P', 'No. Votas una lista cerrada y bloqueada: el orden de los candidatos lo decide el partido. Los escaños se asignan por listas, y es ahí donde entra d\'Hondt.')

# ================================================================ el método
cambia(g.p_votos())
habla('P', 'Ejemplo: una provincia de 7 escaños, con 860 mil votos. Fuego, 340 mil; Agua, 280 mil; Planta, 160 mil; Rayo, 60 mil y Hada, 20 mil.')
cambia(g.p_votos(True))
ding('SEQ_SE_DP_DECIDE', 0.5)
habla('P', 'Primero, la barrera: una lista necesita el 3 por ciento de los votos válidos de la provincia. Aquí son 25.800 votos.')
habla('P', 'Hada solo tiene 20 mil. Se queda fuera del reparto.')
quita()
esc.hacer(maya.emocion('!', frames=26), maya.saltar(altura=6, frames=8))
esc.esperar(10)
habla('M', '¡Pobre Hada! Sus votos no valen nada.')
esc.hacer(profe.mirar('derecha'))
esc.esperar(6)
habla('P', 'De momento, no. Más tarde volveremos a eso.')
esc.hacer(profe.mirar('abajo'))
pizarra(g.p_tabla(0))
habla('P', 'Paso uno: divide los votos de cada partido entre 1, entre 2, entre 3, entre 4... en una tabla.')
habla('P', 'Paso dos: ordena todos esos cocientes de mayor a menor. Paso tres: los 7 cocientes más altos se llevan un escaño cada uno.')
habla('P', 'Vamos a verlo.', espera=30)
frases = ['Primero: 340, de Fuego.', 'Segundo: 280, de Agua.', 'Tercero: 170, otra vez de Fuego.',
          'Cuarto: 160, de Planta.', 'Quinto: 140, de Agua.', 'Sexto: 113, de Fuego.',
          'Séptimo: 93, de Agua. ¡Ya están los 7 escaños!']
for n, frase in enumerate(frases, 1):
    cambia(g.p_tabla(n))
    ding('SEQ_SE_DP_PINPON', 0.55)
    habla('P', frase, espera=34)
cambia(g.p_resultado())
ding('SEQ_SE_DP_KIRAKIRA', 0.5)
habla('P', 'Resultado: Fuego 3, Agua 3, Planta 1 y Rayo 0.')
habla('M', 'Rayo sacó un 7 por ciento de los votos y se quedó sin escaño.')
habla('P', 'Exacto. Los cocientes de los partidos grandes bajan despacio, y se llevan los primeros puestos.')
cambia(g.p_comparar())
habla('P', 'Con otros métodos, como restos mayores o Sainte-Laguë, Rayo habría conseguido 1 escaño y Agua se quedaría con 2.')
habla('P', 'Mismos votos, otro reparto. D\'Hondt favorece a los más votados.')

# ================================================================ por qué
cambia(g.p_historia(1))
habla('L', '¿Y por qué se usa justo este?')
habla('P', 'El jurista belga Victor d\'Hondt publicó la fórmula en 1878.')
cambia(g.p_historia(2))
habla('P', 'En España llegó con la Transición: las primeras elecciones libres fueron en 1977.')
cambia(g.p_historia(3))
habla('P', 'La Constitución de 1978 pide un reparto proporcional y fija la provincia como circunscripción.')
cambia(g.p_historia(4))
habla('P', 'Y la ley electoral de 1985 fijó el Congreso en 350 diputados.')
cambia(g.p_objetivos())
habla('P', 'Se buscaba estabilidad, para evitar parlamentos con cientos de partidos pequeños.')
habla('P', 'También que cada provincia, hasta la más pequeña, tuviera voz. Y una fórmula sencilla que todos pudieran comprobar.')

# ================================================================ ventajas y desventajas
cambia(g.p_ventajas())
habla('P', 'Sus ventajas: es simple y transparente, y se calcula con una tabla.')
habla('P', 'Da mayorías más claras y gobiernos más estables. Y cada provincia, grande o pequeña, tiene sus diputados.')
cambia(g.p_desventajas())
habla('P', 'Sus desventajas: premia a los grandes y castiga a los pequeños.')
habla('P', 'Además, no todos los votos valen lo mismo: depende de la provincia. Y con listas cerradas no eliges a la persona.')

# ================================================================ datos reales y paradojas
cambia(g.p_votos_escano())
habla('P', 'Datos reales de noviembre de 2019: un escaño del PP costó unos 56 mil votos. Uno de Ciudadanos, unos 165 mil.')
quita()
esc.hacer(lucas.emocion('!', frames=26), lucas.saltar(altura=6, frames=8))
esc.esperar(10)
habla('L', '¡Casi el triple de votos por escaño!')
esc.esperar(6)
pizarra(g.p_provincias())
habla('P', 'Y tu voto pesa según dónde vivas. En Soria hay un diputado por cada 44 mil habitantes, más o menos; en Madrid, por cada 180 mil.')
cambia(g.p_umbral())
habla('P', 'La barrera del 3 por ciento apenas importa en las provincias grandes. En las pequeñas, el listón real es muchísimo más alto.')
habla('P', 'Con 2 escaños, hace falta casi un tercio de los votos. Por eso existe el voto útil: muchos votan al grande por miedo a perder su voto.')
cambia(g.p_disperso())
habla('P', 'Una paradoja: en 2008, IU sacó unos 963 mil votos y consiguió 2 escaños. El PNV, 306 mil votos, y 6 escaños.')
habla('P', 'Los votos concentrados en pocas provincias rinden mucho más que los repartidos por toda España.')
cambia(g.p_alabama(2))
habla('P', 'Otra paradoja es la de Alabama, y d\'Hondt se libra de ella. Con restos mayores y 11 escaños, Planta tiene 3.')
habla('P', 'Si subimos a 12 escaños, ¡Planta pierde uno! Con d\'Hondt, añadir escaños nunca quita ninguno.')
cambia(g.p_coalicion(1))
habla('P', 'Y una rareza más: con d\'Hondt, unirse sale a cuenta. Separados, Fuego y Agua suman 2 escaños.')
cambia(g.p_coalicion(2))
ding('SEQ_SE_DP_KIRAKIRA', 0.5)
habla('P', 'Juntos, en una sola lista, suman 3. Y el escaño de más lo pierde Planta.')

# ================================================================ cierre
cambia(g.p_resumen())
habla('P', 'En resumen: d\'Hondt es sencillo y da estabilidad, pero premia a los grandes y castiga el voto disperso.')
habla('P', 'Ningún sistema es neutro: cada uno reparte el poder de una forma distinta.')
quita()
esc.hacer(lucas.emocion('!', frames=26), lucas.saltar(altura=6, frames=8))
esc.esperar(10)
habla('L', '¡Ahora sí lo he entendido! Dividir y elegir los mayores.')
esc.hacer(maya.saltar(altura=6, frames=8))
habla('M', '¡Y yo voy a repasar la tabla en casa!')
pizarra(g.p_final())
habla('P', 'Haced la tabla con los votos de vuestra provincia. Y recordad: ¡informarse es votar mejor!')
quita()
esc.esperar(14)
esc.hacer(esc.fundido(entrada=False, frames=36))
esc.esperar(30)

if __name__ == '__main__':
    salida = os.path.join(SALIDA, 'eleccionesdont')
    esc.exportar(salida, cada=60)
