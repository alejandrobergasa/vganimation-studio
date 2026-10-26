"""EL_PANA_01. EL PANA se acerca a un niño pequeño en la calle y hablan.

  EL PANA: ILLO NO ESTARAS COMIENDO AZUCAR
  NIÑO: ESTOY METIENDOME PILA AZUCAR!!
  EL PANA: INACEPTABLE BRO
  NIÑO: PERO SI TU ESTAS AHI CON UN POPPER
  NIÑO: NUNCA HE VISTO A ALGUIEN POPAR TAN DURO
  EL PANA: ESTO ES DIFERENTE
  EL PANA: HAY ESTUDIOS

El niño se asusta y se va corriendo. Aparecen dos policías por detrás. El pana se asusta al verlos,
intenta escapar, pero le pillan.

  POLICIA 1: DE VERDAD CREIAS QUE PODIAS ESCAPAR CHAVAL
  EL PANA: NO ME RENTAREIS DE NUEVO

El policía 2 pega a el pana.

  POLICIA 2: TE VIENES DE VUELTA AL PROVINCIAL
  EL PANA: NUNCA!
  POLICIA 1: ANDANDO CHAVAL

Los policías se llevan al pana de escena. Hay un fundido a negro y luego vuelve la escena, el pana está
encerrado en el interior de una celda. Se ve unos segundos como el pana camina como león enjaulado por la
habitación y hay de nuevo un fundido a negro.

Ejecutar desde cinematicas/:  python escenas/el_pana_01.py
Planos:  python herramientas.py mapa jubileo   /   python herramientas.py mapa celda
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from motor import Escena, MapaReal
from motor.recursos import SALIDA

# ---------------------------------------------------------------- mapas reales del juego
calle = MapaReal('jubileo', hora=12)      # Ciudad Jubileo; avenida asfaltada del sureste (x 44-48)
celda = MapaReal('celda', hora=12)        # sala oscura con valla de postes en U (land_data 289)

# ---------------------------------------------------------------- reparto
esc = Escena(calle)
pana = esc.personaje('el_pana', 46, 53, mira='arriba')
nino = esc.personaje('babyboy1', 47, 45, mira='abajo')
poli1 = esc.personaje('policeman', 47, 54, mira='arriba')
poli2 = esc.personaje('policeman', 45, 54, mira='arriba')
esc.camara_fija(46, 45)

# ---------------------------------------------------------------- 1. EL PANA y el niño
esc.hacer(esc.fundido(entrada=True), pana.andar('arriba', 2), esc.musica('SEQ_CITY01_D'))   # tema de Jubileo
esc.hacer(pana.andar('arriba', 6))                       # sube por la avenida hasta el niño
esc.hacer(pana.mirar(nino))
esc.esperar(10)
esc.hacer(nino.mirar(pana))
esc.esperar(8)
esc.hacer(esc.dialogo('EL PANA: ILLO, ¿NO ESTARÁS\nCOMIENDO AZÚCAR?'))
esc.hacer(nino.saltar(altura=4, frames=8))
esc.hacer(esc.dialogo('NIÑO: ¡ESTOY METIÉNDOME\nPILA AZÚCAR!'))
esc.esperar(8)
esc.hacer(esc.dialogo('EL PANA: INACEPTABLE, BRO.'))
esc.esperar(8)
esc.hacer(esc.dialogo('NIÑO: PERO SI TÚ ESTÁS AHÍ\nCON UN POPPER.'))
esc.hacer(esc.dialogo('NIÑO: NUNCA HE VISTO A\nALGUIEN POPAR TAN DURO.'))
esc.esperar(10)
esc.hacer(esc.dialogo('EL PANA: ESTO ES DIFERENTE.'))
esc.esperar(6)
esc.hacer(esc.dialogo('EL PANA: HAY ESTUDIOS.'))
esc.esperar(10)

# ---------------------------------------------------------------- 2. el niño huye
esc.hacer(nino.emocion('!', frames=24), nino.saltar(altura=6, frames=8))
esc.esperar(4)
esc.hacer(nino.correr('arriba', 10), esc.sonido('SEQ_SE_DP_NIGERU'))   # sale por arriba de la pantalla
esc.hacer(nino.desaparecer())
esc.esperar(14)

# ---------------------------------------------------------------- 3. llegan los policías por detrás
esc.hacer(pana.mirar('arriba'))                          # se queda mirando por donde se fue el niño
esc.hacer(poli1.andar('arriba', 6), poli2.andar('arriba', 6))   # se colocan a la espalda de EL PANA
esc.esperar(10)
esc.hacer(pana.mirar('abajo'))
# como cuando te ve un entrenador: «!» y cambia la música (encuentro con el Equipo Galaxia)
esc.hacer(pana.emocion('!', frames=24), pana.saltar(altura=6, frames=8), esc.musica('SEQ_EYE_GINGA'))
esc.esperar(6)
# intenta escapar por la calle de la derecha, pero el policía 1 le adelanta y le corta el paso;
# el policía 2 le cierra por detrás (a la izquierda el tejado del edificio taparía la escena)
esc.hacer(pana.correr('derecha', 4), esc.sonido('SEQ_SE_DP_NIGERU'),
          poli1.ruta(('arriba', 2), ('derecha', 4), ('arriba', 1), modo='sprint'),
          poli2.ruta(('arriba', 2), ('derecha', 4), ('arriba', 1), modo='correr'))
esc.hacer(poli1.mirar('izquierda'), poli2.mirar('derecha'))
esc.hacer(pana.saltar(altura=4, frames=6))
esc.esperar(10)
esc.hacer(esc.dialogo('POLICÍA 1: ¿DE VERDAD CREÍAS\nQUE PODÍAS ESCAPAR, CHAVAL?'))
esc.esperar(6)
esc.hacer(esc.dialogo('EL PANA: ¡NO ME RENTARÉIS\nDE NUEVO!'))
esc.esperar(8)

# ---------------------------------------------------------------- 4. el policía 2 le pega
esc.hacer(poli2.golpear(pana))
esc.esperar(10)
esc.hacer(pana.mirar(poli2))
esc.esperar(6)
esc.hacer(esc.dialogo('POLICÍA 2: TE VIENES DE\nVUELTA AL PROVINCIAL.'))
esc.esperar(6)
esc.hacer(esc.dialogo('EL PANA: ¡NUNCA!'))
esc.esperar(8)
esc.hacer(pana.mirar(poli1))
esc.esperar(4)
esc.hacer(esc.dialogo('POLICÍA 1: ANDANDO, CHAVAL.'))
esc.esperar(8)
esc.hacer(poli2.mirar('izquierda'), poli1.mirar('izquierda'))
esc.esperar(6)

# ---------------------------------------------------------------- 5. se lo llevan
# en fila hacia la izquierda; desaparecen tras el edificio
esc.hacer(poli2.andar('izquierda', 11), pana.andar('izquierda', 11), poli1.andar('izquierda', 11))
esc.hacer(poli1.desaparecer(), poli2.desaparecer(), pana.desaparecer())   # ya tras el edificio
esc.hacer(esc.fundido(entrada=False, frames=20), esc.parar_musica(30))
esc.esperar(30)

# ---------------------------------------------------------------- 6. la celda
esc.hacer(pana.teletransportar(4, 13), pana.mirar('derecha'), pana.aparecer(), esc.cambiar_mapa(celda, fija=(7, 10)))
esc.hacer(esc.fundido(entrada=True, frames=20), esc.sonido('SEQ_SE_DP_KI_GASYAN'))   # la reja se cierra
esc.hacer(esc.musica('SEQ_D_AGITO'))                     # tema de la guarida Galaxia
esc.esperar(10)
# da vueltas como un león enjaulado
for _ in range(2):
    esc.hacer(pana.andar('derecha', 6))
    esc.esperar(4)
    esc.hacer(pana.andar('izquierda', 6))
    esc.esperar(4)
esc.hacer(pana.andar('derecha', 3))
esc.hacer(pana.mirar('abajo'))
esc.esperar(30)
esc.hacer(esc.fundido(entrada=False, frames=25), esc.parar_musica(35))
esc.esperar(10)

if __name__ == '__main__':
    salida = os.path.join(SALIDA, 'el_pana_01')
    esc.renderizar(salida)
