"""REWINDLIMBO2 · tramo 10 (7:27-8:11). La obra del gimnasio.

Original: sacos de boxeo; dos obreros con casco trabajan (escaleras, sierra, sacando bíceps) y meten un sofá con
forma de gorila (7:27-7:45). Santos, con camisa y brazos cruzados, les mete prisa: «Dejad el gorila en la
puerta», un obrero pide descanso y él les grita (7:45-8:06). Cuadro enmarcado: «Siempre fuiste la cabra del
trabajo» (8:06-8:11).

Versión Platino: un almacén gris con cajas (interior land 254) como gimnasio a medio montar. Sacos de boxeo del
gimnasio de Rocavelo, obreros del juego, el sofá gorila es un Slaking tumbado y el cuadro, el Duque del juego.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comun import efecto, escalar, exportar, inserto, polvo, textos  # noqa
from motor import Escena, MapaReal
from motor.recursos import imagen

T0, T1 = 447.0, 491.0
mapa = MapaReal(land=254, hora=12)
esc = Escena(mapa, t0=T0)
esc.subtitulos(textos.subtitulos(T0, T1))


def saco():
    """Saco de boxeo colgado (14x30): cadena gris y cuerpo de cuero rojo oscuro con brillo."""
    a = Image.new('RGBA', (14, 30))
    d = ImageDraw.Draw(a)
    d.line((7, 0, 7, 6), fill=(150, 150, 160, 255))
    d.rounded_rectangle((1, 6, 12, 29), 4, fill=(150, 40, 40, 255), outline=(40, 16, 16, 255))
    d.line((4, 9, 4, 26), fill=(200, 80, 72, 255))
    d.rectangle((2, 12, 11, 14), fill=(40, 40, 48, 255))
    return a


sacos = [esc.objeto(saco(), x, y) for x, y in ((10, 3), (12, 3), (2, 6))]
GORILA = imagen('pokemon/frente/normal/289_slaking.png').crop((0, 0, 80, 80))
GORILA = GORILA.crop(GORILA.getbbox())
GORILA = GORILA.resize((GORILA.width * 3 // 4, GORILA.height * 3 // 4), Image.NEAREST)
sofa = esc.objeto(GORILA, 6, 12, visible=False)
obrero1 = esc.personaje('workman', 8, 3, mira='izquierda')
obrero2 = esc.personaje('workman', 4, 8, mira='abajo')
santos = esc.personaje('santos_camisa', 12, 8, mira='abajo')
santos.visible = False
esc.camara_fija(8, 7)
esc.negro = 1.0                                       # sigue el negro del tramo anterior
ENFADO = efecto(11)[0]


def enfado(p, frames=24):
    def acc():
        for f in range(frames):
            esc.efectos.append((ENFADO, p.x + 18, p.y - 22 - p.elevacion - (2 if f % 8 < 4 else 0)))
            p.empuje = ((1 if f % 2 else -1) if f < 12 else 0, 0)
            yield
        p.empuje = (0, 0)
    return acc()


def currar(p, frames, cada=14):
    """Martillazos: un golpecito con ruido cada poco y algo de polvo."""
    def acc():
        for f in range(frames):
            g = f % cada
            p.empuje = (0, -1 if g < 3 else 0)
            if g == 0 and (f // cada) % 2 == 0:              # un martillazo sí y otro no
                esc.audio.append((esc.t, 'sonido', 'SEQ_SE_DP_KON', 0.12))
            if g < 6:
                esc.efectos.append((polvo()[g // 3].resize((10, 10)), p.x + 10, p.y + 6))
            yield
        p.empuje = (0, 0)
    return acc()


def cuadro():
    """El cuadro: el Duque del juego en un marco dorado."""
    d = imagen('entrenadores/frente/estatico/034_duque.png').crop((0, 0, 80, 80))
    lienzo = Image.new('RGBA', (80, 80), (232, 196, 120, 255))
    lienzo.alpha_composite(d)
    m = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
    dr = ImageDraw.Draw(m)
    dr.rectangle((0, 0, 95, 95), fill=(176, 120, 32, 255), outline=(72, 44, 16, 255))
    dr.rectangle((3, 3, 92, 92), outline=(248, 216, 96, 255))
    dr.rectangle((6, 6, 89, 89), fill=(96, 60, 20, 255))
    m.alpha_composite(lienzo, (8, 8))
    return inserto(m, 1)


# ---------------------------------------------------------------- 7:27 los sacos y los obreros
esc.hacer(esc.hasta(449.6))
esc.hacer(esc.fundido(entrada=True, frames=12), esc.en_paralelo(currar(obrero1, int(11 * 30))))
for t in (450.4, 451.6):
    esc.hacer(esc.hasta(t))
    esc.hacer(sacos[0].temblar(10, 2), esc.sonido('SEQ_SE_DP_KOUKA_L', 0.4))
esc.hacer(esc.hasta(453.0))
esc.hacer(obrero2.ruta(('arriba', 1), ('izquierda', 1)))                         # -> (3,7), junto al saco
esc.hacer(obrero2.mirar('izquierda'), esc.en_paralelo(currar(obrero2, int(5 * 30), 10)))
esc.hacer(esc.hasta(459.0))
esc.hacer(obrero2.mirar('abajo'), obrero2.saltar(6, 8), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.3))   # saca bíceps
esc.hacer(obrero2.saltar(6, 8))

# ---------------------------------------------------------------- 7:41 entra el sofá gorila
esc.hacer(esc.hasta(460.8))
esc.hacer(obrero1.andar('abajo', 5), obrero2.ruta(('derecha', 1), ('abajo', 1)))   # -> (8,8) y (4,8)
esc.hacer(obrero1.mirar('abajo'), obrero2.mirar('abajo'), sofa.aparecer())
esc.hacer(sofa.mover(0, -32, 50, animar=False), obrero1.temblar(50, 1), obrero2.temblar(50, 1),
          esc.sonido('SEQ_SE_DP_DANSA', 0.4))                                     # lo empujan hasta la puerta
esc.hacer(obrero1.mirar('arriba'), obrero2.mirar('arriba'))
esc.hacer(esc.hasta(464.8))

# ---------------------------------------------------------------- 7:45 Santos mete prisa
esc.hacer(santos.desvanecer(True, 12), esc.sonido('SEQ_SE_DP_DOOR_OPEN', 0.4))
esc.hacer(esc.hasta(467.3))
esc.hacer(santos.mirar('izquierda'))
esc.hacer(esc.hasta(469.9))
esc.hacer(santos.mirar('abajo'))                                                 # señala la puerta
esc.hacer(esc.hasta(472.4))
esc.hacer(obrero1.mirar('derecha'), obrero2.mirar('arriba'), esc.en_paralelo(currar(obrero1, 70)))
esc.hacer(esc.hasta(475.0))
esc.hacer(obrero2.mirar('arriba'))                                               # «¿un descanso…?»
esc.hacer(santos.mirar('izquierda'))
esc.hacer(esc.hasta(477.3))
esc.hacer(enfado(santos, 30), santos.saltar(4, 8))
esc.hacer(obrero2.mirar('abajo'), esc.en_paralelo(currar(obrero2, int(8 * 30), 12), currar(obrero1, int(8 * 30))))
esc.hacer(esc.hasta(478.9))
esc.hacer(santos.mirar('abajo'))
esc.hacer(esc.hasta(482.6))
esc.hacer(enfado(santos, 30))
esc.hacer(esc.hasta(486.5))

# ---------------------------------------------------------------- 8:06 el cuadro
esc.hacer(esc.mostrar('cuadro', cuadro(), y=12, efecto='zoom', frames=10), esc.sonido('SEQ_SE_DP_KIRAKIRA', 0.4))
esc.hacer(esc.hasta(490.3))
esc.hacer(esc.ocultar('cuadro', 8))
esc.hacer(esc.hasta(T1))

if __name__ == '__main__':
    exportar(esc, 't10_obra', T0, T1, desde=float(sys.argv[1]) if len(sys.argv) > 1 else None)
