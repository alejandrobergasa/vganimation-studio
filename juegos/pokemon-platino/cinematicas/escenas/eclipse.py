"""ECLIPSE. Versión Platino del vídeo «EL ECLIPSE» (meme de la escena del eclipse de Apocalypto, doblada).

Acto 1 (Ciudad Jubileo): un prisionero pintado de azul, tumbado en el altar. El «sacerdote» (se presenta como
Stephen Hawking) le va a clavar el cuchillo: «según mis cálculos habrá un eclipse solar». Hay eclipse, la
multitud entra en pánico, alguien dice que es un eclipse LUNAR y el sacerdote, ofendido: «no es un lunar, es
una peca».
Acto 2 (cuarto con PC): EL PANA busca «lunar» en el buscador y se queda alucinado.
Acto 3 (avenida): un corredor que parece Rubba pasa a toda velocidad; EL PANA para a todos: «este men no es
Rubba». Amplía la imagen: no tiene lunar. «Este es Marina». Suscríbete al canal.

Ejecutar desde cinematicas/:  python escenas/eclipse.py
"""
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..'))
sys.path.insert(0, AQUI)
from motor import Escena, MapaReal
from motor.recursos import RAIZ, SPR, CUSTOM, TRABAJO, SALIDA, CACHE, fuente, frames_personaje, imagen
import eclipse_gfx as g

# V2: la música es la del vídeo original tocada con el banco de Platino (trabajo/eclipse); la escena no pone
# música del juego y guarda en MARCAS el frame del anillo del eclipse (donde cambia a la canción 2).
V2 = os.environ.get('ECLIPSE_V2') == '1'
MARCAS = {}

calle = MapaReal('jubileo', hora=12)          # Ciudad Jubileo: avenida x 44-49, y 10-58
cuarto = MapaReal(land=313)                   # cuarto con PC


def musica(nombre, volumen=0.55):
    return esc.accion(lambda: None) if V2 else esc.musica(nombre, volumen)


def parar(frames=30):
    return esc.accion(lambda: None) if V2 else esc.parar_musica(frames)


def d(texto, espera=50):
    """Diálogo con comprobación de ancho (26 caracteres por línea)."""
    for l in texto.split('\n'):
        if len(l) > 26:
            print('LINEA LARGA (%d): %s' % (len(l), l))
    assert len(texto.split('\n')) <= 2, 'demasiadas líneas: ' + texto
    return esc.dialogo(texto, espera=espera)


# ---------------------------------------------------------------- reparto
esc = Escena(calle)
victima = esc.personaje('chini', 46, 11, mira='abajo', sombra=False)
sacerdote = esc.personaje('gingaboss', 46, 13, mira='arriba')
fila = [(44, 12, 'gingam'), (44, 14, 'gingaw'), (44, 16, 'gingam'),
        (48, 12, 'gingaw'), (48, 14, 'gingam'), (48, 16, 'gingaw')]
multitud = [esc.personaje(s, x, y, mira=('derecha' if x < 46 else 'izquierda')) for x, y, s in fila]
pana = esc.personaje('el_pana', 45, 20, mira='arriba')
pana.visible = False
chini2 = esc.personaje('chini_chaqueta', 47, 20, mira='arriba')
chini2.visible = False
rubba = esc.personaje('santos', 47, 58, mira='arriba')
rubba.visible = False
marina = esc.personaje('033', 46, 60, mira='arriba')
marina.visible = False
esc.camara_fija(46, 14)

tumbada = g.tumbado(frames_personaje('chini')[4])

# ---------------------------------------------------------------- ACTO 1: el sacrificio
esc.hacer(victima.posar(tumbada), victima.tenir((40, 90, 255), 0.55), sacerdote.llevar(g.cuchillo(), 11, 0))
esc.hacer(esc.fundido(entrada=True, frames=30), musica('SEQ_D_AGITO', 0.5))
esc.esperar(20)
esc.hacer(d('PRISIONERO: ¡AYUDA! ¡ME\nHAN SECUESTRADO!'))
esc.hacer(victima.temblar(frames=20, amplitud=1))
esc.esperar(10)
esc.hacer(d('GALAXIA: ¡PARECES UN\nPITUFO, XD!'))
esc.esperar(8)
esc.hacer(d('PRISIONERO: ¡POR FAVOR,\nNO ME CLAVES ESE CUCHILLO!'))
esc.esperar(14)
esc.hacer(sacerdote.mirar('arriba'), sacerdote.saltar(altura=3, frames=8), musica('SEQ_EYE_GINGA', 0.5))
esc.esperar(6)
esc.hacer(d('HAWKING: ME LLAMO STEPHEN\nHAWKING.'))
esc.hacer(d('HAWKING: Y TE HE\nSECUESTRADO, XD.'))
esc.esperar(10)
esc.hacer(sacerdote.llevar(g.cuchillo(), 11, -8))          # alza el cuchillo
esc.hacer(d('HAWKING: PREPÁRATE, VOY A\nCLAVARTE ESTE CUCHILLO.'))
esc.hacer(d('HAWKING: SEGÚN MIS\nCÁLCULOS...'))
esc.hacer(d('HAWKING: AHORA HABRÁ UN\nECLIPSE SOLAR, XD.'))
esc.esperar(14)

# el eclipse (plano de cielo, como en la película)
esc.hacer(parar(20))
esc.hacer(esc.mostrar('cielo', g.cielo_eclipse(0), frames=14))
esc.esperar(26)
esc.hacer(esc.cambiar_capa('cielo', g.cielo_eclipse(1)), esc.sonido('SEQ_SE_DP_KAIDAN2', 0.3))
esc.esperar(30)
esc.hacer(esc.cambiar_capa('cielo', g.cielo_eclipse(2)), esc.temblor_pantalla(frames=24, amplitud=2),
          esc.accion(lambda: MARCAS.__setitem__('anillo', esc.t)))
esc.esperar(46)
esc.hacer(esc.ocultar('cielo', frames=10), esc.tenir_pantalla((0, 0, 40), 0.55, frames=20))
esc.esperar(8)
esc.hacer(*[m.emocion('!', frames=30) for m in multitud], *[m.saltar(altura=5, frames=8) for m in multitud[::2]])
esc.hacer(sacerdote.saltar(altura=4, frames=8), musica('SEQ_BA_GINGA', 0.45))
esc.esperar(12)
esc.hacer(d('GALAXIA: ¡YA VALIMOS!\n¡NOS VAMOS A MORIR!'))
esc.hacer(*[m.temblar(frames=24, amplitud=1) for m in multitud])
esc.hacer(d('GALAXIA: ¡MIRAD LA LUNA!\n¡ESTÁ NARANJA!'))
esc.hacer(victima.saltar(altura=5, frames=8))
esc.hacer(d('PRISIONERO: ¡AYÚDAME!\n¡ESTA COSA SE HA PRENDIDO!'))
esc.esperar(10)
esc.hacer(multitud[1].mirar('derecha'), multitud[1].saltar(altura=3, frames=8))
esc.hacer(d('GALAXIA: ¡QUE ALGUIEN\nNOS AYUDE!'))
esc.hacer(d('GALAXIA: ESO NO ES UN\nECLIPSE SOLAR...'))
esc.esperar(14)
esc.hacer(parar(10))
esc.hacer(d('GALAXIA: ES UN ECLIPSE\nLUNAR.', espera=60))
esc.esperar(20)
esc.hacer(sacerdote.mirar('derecha'))
esc.esperar(6)
esc.hacer(sacerdote.mirar('abajo'), sacerdote.emocion('!', frames=24), sacerdote.saltar(altura=6, frames=8))
esc.hacer(musica('SEQ_EYE_GINGA', 0.5))
esc.esperar(8)
esc.hacer(d('HAWKING: ¡YA ME OFENDISTE!'))
esc.hacer(d('HAWKING: ¡NO ES UN LUNAR,\nES UNA PECA!', espera=70))
esc.esperar(14)
esc.hacer(esc.fundido(entrada=False, frames=24), parar(30))
esc.esperar(20)

# ---------------------------------------------------------------- ACTO 2: el buscador
esc.hacer(*[m.desaparecer() for m in multitud + [sacerdote, victima]], esc.tenir_pantalla(None, 0, frames=1))
esc.hacer(pana.teletransportar(8, 4), pana.mirar('arriba'), pana.aparecer(),
          chini2.teletransportar(6, 5), chini2.mirar('arriba'), chini2.aparecer(),
          esc.cambiar_mapa(cuarto, fija=(5, 4)))
esc.hacer(esc.fundido(entrada=True, frames=20), musica('SEQ_PC_01', 0.5))
esc.esperar(20)
esc.hacer(esc.sonido('SEQ_SE_DP_PC_ON', 0.6))
esc.esperar(20)
esc.hacer(esc.mostrar('google', g.google(), frames=14, efecto='subir'), esc.sonido('SEQ_SE_DP_PC_LOGIN', 0.5))
esc.esperar(60)
esc.hacer(esc.ocultar('google', frames=10, efecto='bajar'))
esc.hacer(pana.emocion('!', frames=30), pana.saltar(altura=5, frames=8),
          chini2.emocion('!', frames=30), chini2.saltar(altura=5, frames=8))
esc.esperar(6)
esc.hacer(d('EL PANA: ¡OH, DIOS MÍO!\n¡MIRA ESTO, MIRA ESTO!'))
esc.esperar(10)
esc.hacer(esc.fundido(entrada=False, frames=20), parar(25))
esc.esperar(16)

# ---------------------------------------------------------------- ACTO 3: ¿es Rubba?
esc.hacer(pana.teletransportar(44, 40), pana.mirar('derecha'), pana.aparecer(),
          chini2.teletransportar(44, 42), chini2.mirar('derecha'), chini2.aparecer(),
          rubba.teletransportar(48, 52), rubba.mirar('arriba'), rubba.aparecer(),
          esc.cambiar_mapa(calle, fija=(46, 41)))
esc.hacer(esc.fundido(entrada=True, frames=20), musica('SEQ_ROAD_A_D', 0.5))
esc.esperar(30)
esc.hacer(rubba.correr('arriba', 8), esc.sonido('SEQ_SE_DP_NIGERU', 0.5))
esc.hacer(chini2.emocion('!', frames=20), chini2.saltar(altura=4, frames=8))
esc.hacer(rubba.correr('arriba', 6), d('CHINI: ¡VENGA, RUBÉN!\n¡DALE FUERTE, SIGUE ASÍ!'))
esc.hacer(rubba.correr('arriba', 10))
esc.hacer(rubba.desaparecer())
esc.esperar(10)
esc.hacer(pana.mirar('abajo'), pana.emocion('!', frames=24), pana.saltar(altura=5, frames=8))
esc.esperar(8)
esc.hacer(pana.mirar(chini2), chini2.mirar(pana))
esc.hacer(d('EL PANA: ¡ESPERAD, AMIGOS\nDE YOUTUBE!'))
esc.hacer(d('EL PANA: ESTE MEN NO ES\nRUBBA.', espera=60))
esc.hacer(chini2.mirar('arriba'), chini2.saltar(altura=3, frames=8))
esc.hacer(d('CHINI: ¿NO ME CREES?\nPUES VAMOS A VERLO.'))
esc.esperar(6)
esc.hacer(d('EL PANA: VAMOS A AMPLIAR\nLA IMAGEN.'))
esc.hacer(esc.mostrar('zoom', g.inserto(g.zoom_cara(imagen(os.path.join(CUSTOM, 'santos',
                                                                   'combate', 'frente.png')), False),
                                        1, 'AMPLIANDO IMAGEN...', ancho=220), y=8, frames=14, efecto='zoom'),
          esc.sonido('SEQ_SE_DP_PC_ON', 0.5))
esc.esperar(70)
esc.hacer(d('EL PANA: ¡NO TIENE LUNAR!\nSIN LUNAR NO HAY RUBBA.', espera=55))
esc.hacer(d('EL PANA: ES HABITUAL\nCONFUNDIRLOS, SON IGUALES', espera=60))
esc.hacer(esc.ocultar('zoom', frames=10))
esc.esperar(10)

# Marina entra por abajo
esc.hacer(marina.teletransportar(46, 49), marina.aparecer())
esc.hacer(marina.andar('arriba', 6), pana.mirar('abajo'), chini2.mirar('abajo'))
esc.hacer(marina.mirar('izquierda'))
esc.esperar(8)
esc.hacer(d('EL PANA: ESTE ES MARINA.', espera=60))
esc.hacer(marina.saltar(altura=5, frames=8), marina.emocion('!', frames=24))
esc.esperar(14)
esc.hacer(pana.mirar('abajo'))
esc.hacer(d('EL PANA: ¡SUSCRÍBETE AL\nCANAL!', espera=70))
esc.hacer(musica('SEQ_FANFA1', 0.6))
esc.esperar(20)
esc.hacer(esc.mostrar('camiseta', g.camiseta(), frames=24, orden=2))
esc.esperar(90)
esc.hacer(esc.fundido(entrada=False, frames=24), parar(30))
esc.esperar(10)

if __name__ == '__main__':
    if V2:
        import json
        esc.renderizar(os.path.join(SALIDA, 'eclipse_v2_sinmusica'), gif=False)
        json.dump(dict(MARCAS, frames=esc.t), open(os.path.join(CACHE, 'eclipse_marcas.json'), 'w'))
        print('MARCAS', MARCAS)
    else:
        esc.renderizar(os.path.join(SALIDA, 'eclipse'))
