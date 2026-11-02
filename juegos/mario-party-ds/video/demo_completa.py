"""Prueba de todo el motor: tablero real, cara de foto, animaciones nativas, cámara, interfaz y sonido.

    python valedores.py ejecutar prueba_motor_mario_party_ds -- \\
        python -I juegos/mario-party-ds/video/demo_completa.py --foto a.jpg --foto2 b.jpg

Sin fotos usa las caras nativas. `--fotogramas` solo escribe unos cuantos PNG de control en trabajo/.
"""
import argparse
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from motor import (Camara, CaraFoto, Escena3D, Particulas, Pista, Recursos, Video, efectos, interfaz, personajes, rutas)


def construir(foto=None, foto2=None, formato='horizontal'):
    rec = Recursos()
    video = Video(formato=formato, fps=30)
    W, H = video.tamano
    res = (W // 2, H // 2)
    fuente = rec.fuente_juego()
    cara1 = CaraFoto(foto, nombre='uno') if foto else None
    cara2 = CaraFoto(foto2, nombre='dos') if foto2 else None

    # --- Escena: dos personajes en el jardín real del juego ---------------------------------------
    esc = Escena3D(tamano=res, fondo=(120, 170, 225), ambiente=0.78)
    tablero = rec.escenario('jardin', y=-2, z=-40, escala=0.55)
    esc.actor(tablero)
    a = esc.actor(rec.personaje('mario', cara=cara1, x=Pista([(0, -60), (4, -13)], curva='recta'), giro=math.pi / 2))
    b = esc.actor(rec.personaje('luigi', cara=cara2, x=13, giro=-math.pi / 2))
    a.linea, b.linea = [], []
    a.anim('correr', 0).anim('quieto', 4).anim('saludar', 4.6, bucle=False).anim('quieto', 6.1)
    b.anim('quieto', 0).anim('saltar_alegre', 4.2, bucle=False).anim('quieto', 5.2).anim('dudar', 9.2).anim('celebrar', 12)
    a.anim('dudar', 12.1).anim('caer_de_cabeza', 15.2, bucle=False, velocidad=2)
    a.mirar(b, desde=6.2, hasta=12)
    b.mirar(a, desde=0.4, hasta=9)

    # Boca y expresión.
    for actor, tramos, expr in ((a, [(6.3, 8.6)], ('enfado', 8.9, 12)), (b, [(9.2, 11.8)], ('alegria', 12, 20))):
        if actor.cara:
            for ini, fin in tramos:
                actor.cara.hablar(ini, fin)
            actor.cara.expresion(expr[0], expr[1], expr[2])

    # --- Cámara: general, seguimiento, conjunto, primeros planos, órbita, temblor ------------------
    c = esc.camara = Camara((0, 60, 150), (0, 8, 0), 44)
    c.clave(0, (0, 60, 150), (0, 8, 0), 44)
    c.clave(2.2, (-30, 28, 85), a.centro, 36)                                   # acercamiento (dolly) al que corre
    c.dos_personajes(a, b, 4.0, altura=0.12, margen=1.2)                        # conjunto, también en vertical
    c.encuadre('primer_plano', a, 6.2, angulo=-0.45, corte=True)                # habla el primero
    c.encuadre('primer_plano', b, 8.8, angulo=0.45, corte=True)                 # contraplano
    c.dos_personajes(a, b, 12.0, corte=True, altura=0.15, margen=1.4)           # conjunto
    c.orbita(a, 34, 16, 0.3, 2.4, 12.6, 2.6)                                    # órbita alrededor del actor
    c.corte(15.2, (10, 2.5, 34), a.centro, 44)                                  # contrapicado a ras de suelo
    c.temblor(15.6, 0.6, 0.9)

    # --- Partículas con texturas de la ROM ---------------------------------------------------------
    esc.emitir(Particulas(rec.textura_efecto('star01_PLT256'), lambda t: b.hueso('spin', 12.0), desde=12.05, cantidad=28,
                          velocidad=24, gravedad=-20, tamano=0.9, vida=1.2, semilla=4))
    esc.emitir(Particulas(rec.textura_efecto('kemuri01_A5I3'), lambda t: a.posicion(15.6), desde=15.55, cantidad=18,
                          velocidad=12, gravedad=3, tamano=2.2, tamano_final=7, vida=0.8, alfa=0.8, semilla=9, arriba=0.3))

    # --- Montaje: dos planos con transición en estrella, cartel, diálogos, marcador ----------------
    final = 17.0
    principal = video.plano_escena(12.0, esc)
    segundo = video.plano_escena(final - 12.0, esc, inicio=12.0, transicion=('estrella', 0.7))
    escala_ui = 3 if W >= 1000 else 2
    margen = 40

    # Título y turno.
    principal.sprite(interfaz.Cartel(fuente, '¡TURNO DE MARIO!', escala=6, duracion=2.2), x=W / 2, y=H * 0.2, ancla=(.5, .5), pantalla=True, desde=0.3)

    # Marcador con iconos nativos: las monedas suben al saludar.
    moneda = rec.icono('moneda', escala=2)
    estrella = rec.icono('estrella', escala=2)
    for plano in (principal, segundo):
        plano.sprite(interfaz.Contador(fuente, 1, icono=estrella, escala=escala_ui + 1, ceros=1), x=margen, y=margen, ancla=(0, 0), pantalla=True)
        plano.sprite(interfaz.Contador(fuente, (lambda t: 20 + int(max(0, min(1.5, t - 4.6)) * 20)) if plano is principal else 50,
                                       icono=moneda, escala=escala_ui + 1),
                     x=margen, y=margen + 54, ancla=(0, 0), pantalla=True)

    # Diálogos con su tecleo.
    tecla = rec.efecto('SE_SYS_001')
    retrato1 = personajes.retrato(cara1, 72) if cara1 else None
    retrato2 = personajes.retrato(cara2, 72) if cara2 else None
    d1 = interfaz.Dialogo(fuente, '¡Eh! ¿Quién ha movido mis monedas del tablero?', tamano=(min(W - 80, 1000), 150), nombre='UNO', retrato=retrato1, duracion=2.5)
    d2 = interfaz.Dialogo(fuente, 'Yo no he sido... ¡palabra de Luigi!', tamano=(min(W - 80, 1000), 150), nombre='DOS', fondo_nombre=(40, 150, 60), retrato=retrato2, duracion=2.9)
    principal.sprite(d1, x=W / 2, y=H - 30, ancla=(.5, 1), pantalla=True, desde=6.2)
    principal.sprite(d2, x=W / 2, y=H - 30, ancla=(.5, 1), pantalla=True, desde=9.0)
    d1.sonar_letras(video, tecla, desde=6.2, volumen=0.35, cada=3)
    d2.sonar_letras(video, tecla, desde=9.0, volumen=0.35, cada=3)
    segundo.sprite(interfaz.Cartel(fuente, '¡MINIJUEGO!', escala=7, color=(255, 255, 255), sombra=(40, 70, 200), duracion=2.2), x=W / 2, y=H * 0.2, ancla=(.5, .5), pantalla=True, desde=0.2)

    # Barra de tiempo y efectos de imagen.
    segundo.sprite(interfaz.Barra((400, 27), Pista([(0, 1), (5, 0)], curva='recta'), escala=3), x=W - margen, y=margen, ancla=(1, 0), pantalla=True)
    principal.efecto(efectos.vineta(0.35))
    principal.efecto(efectos.destello(4.6, 0.2, fuerza=0.5))
    segundo.efecto(efectos.franjas_cine(0.09, desde=0.7, hasta=2.9))
    segundo.efecto(efectos.lineas_velocidad(3.6, 0.45))
    segundo.efecto(efectos.fundido(4.2, 0.8))

    # --- Sonido: música nativa, voces y efectos ------------------------------------------------------
    musica, fs = rec.musica('MU101', final)
    video.audio(musica, fs, volumen=0.55)
    video.sonido(rec.efecto(rec.voces('mario')[0]), desde=4.6)
    video.sonido(rec.efecto(rec.voces('luigi')[0]), desde=4.25, pan=0.4)
    video.sonido(rec.efecto('SE_SYS_005'), desde=4.6, volumen=0.8)
    video.sonido(rec.efecto('SE_SYS_010'), desde=12.05, volumen=0.7)
    video.sonido(rec.efecto('SE_MGP_004'), desde=15.6)
    return video


def principal():
    ap = argparse.ArgumentParser()
    ap.add_argument('--foto')
    ap.add_argument('--foto2')
    ap.add_argument('--formato', choices=('horizontal', 'vertical'), default='horizontal')
    ap.add_argument('--fotogramas', action='store_true')
    args = ap.parse_args()
    video = construir(args.foto, args.foto2, args.formato)
    if args.fotogramas:
        destino = Path(rutas.trabajo('mario-party-ds'))
        for t in (1.0, 3.0, 5.0, 7.0, 9.8, 11.75, 12.4, 13.5, 15.0, 15.9, 16.7):
            video.frame(t).save(destino / ('demo_%05.2f.png' % t))
        print(destino)
        return
    print(video.renderizar('demo_completa_%s.mp4' % args.formato))


if __name__ == '__main__':
    principal()
