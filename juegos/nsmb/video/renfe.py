"""Cinemática vertical satírica. Mario, fondos, fuente y sonido salen de la ROM.

Excepciones pedidas por el usuario: tren RENFE y retrato local oscarpuente.jfif.
Regenerar: python -I video/make_video.py --renfe
"""
from functools import lru_cache
from pathlib import Path
import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageOps

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'tools' / 'nsmb'))
import backgrounds
import chars
import engine
import text
import world
import renfe_audio
from rom import rutas

W, H, FPS, SCALE = 216, 384, 30, 5
TOTAL = renfe_audio.DURATION
CACHE = Path(rutas.cache('nsmb')) / 'renfe'
FINAL = Path(rutas.salida('nsmb')) / 'mario_renfe_vertical.mp4'
WHITE = (249, 250, 241)
INK = (20, 19, 41)
YELLOW = (255, 222, 84)
PURPLE = (116, 35, 104)


def clamp(x):
    return max(0, min(1, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


@lru_cache(maxsize=512)
def lettering(s, color=WHITE, scale=1):
    im = text.render(s, color=color, outline=INK)
    if scale != 1:
        im = im.resize((im.width * scale, im.height * scale), Image.Resampling.NEAREST)
    return im


def label(im, s, y, scale=1, color=WHITE, x=None):
    t = lettering(s, color, scale)
    if x is None:
        x = (W - t.width) // 2
    im.alpha_composite(t, (int(x), int(y)))


def panel(im, box, fill=(18, 18, 39, 245), border=(225, 224, 244), width=2):
    d = ImageDraw.Draw(im)
    d.rectangle(box, fill=fill, outline=border, width=width)


def caption(im, lines, y=307, color=WHITE):
    height = len(lines) * 19 + 12
    panel(im, (12, y, W - 13, y + height), border=(255, 219, 82))
    for i, line in enumerate(lines):
        label(im, line, y + 5 + i * 19, color=color)


@lru_cache(maxsize=16)
def dialogue_lines(s):
    """Fijar los saltos antes de escribir para que las palabras no salten de línea."""
    punchline = 'un glazing al perro'
    if s.endswith(punchline):
        return [s[:-len(punchline)].strip(), punchline]
    lines = ['']
    for word in s.split(' '):
        proposal = (lines[-1] + ' ' + word).strip()
        if lettering(proposal).width > 178:
            lines.append(word)
        else:
            lines[-1] = proposal
    return lines


class Film:
    def __init__(self):
        CACHE.mkdir(parents=True, exist_ok=True)
        self.actor = chars.mario()
        self.back = backgrounds.layer('back')
        self.front = backgrounds.layer('free', alpha2=.85)
        self.w = world.get()
        # Una banda real de suelo de 1-1; el resto del campo conserva las capas del juego.
        band = self.w.layer.crop((0, 480, 256, 496))
        # Elegir un tile opaco, evitando repetir los huecos reales del nivel 1-1.
        alpha = np.asarray(band)[..., 3]
        gx = max(range(0, 240, 16), key=lambda x: int(alpha[:, x:x + 16].sum()))
        self.ground = band.crop((gx, 0, gx + 16, 16))
        self.coin = self.w.coin_img
        # El logo aportado se compone a resolución lógica; el original no se modifica.
        source = np.asarray(Image.open(Path(rutas.personalizados('nsmb')) / 'renfelogo.png').convert('RGB'))
        ink = 255 - source[..., 1]
        logo = np.zeros((*ink.shape, 4), np.uint8)
        logo[..., :3] = (113, 0, 93)
        logo[..., 3] = np.where(ink > 25, ink, 0)
        logo = Image.fromarray(logo)
        self.logo = logo.crop(logo.getbbox())
        self.badge = self.logo.resize((56, 21), Image.Resampling.BOX)
        # Pocos niveles de transparencia conservan el borde de píxel del juego.
        badge = np.asarray(self.badge).copy()
        badge[..., 3] = (badge[..., 3] > 115).astype(np.uint8) * 255
        self.badge = Image.fromarray(badge)
        self.portrait = ImageOps.fit(Image.open(Path(rutas.personalizados('nsmb')) / 'oscarpuente.jfif').convert('RGB'),
                                     (52, 66), method=Image.Resampling.BOX).resize(
                                         (104, 132), Image.Resampling.NEAREST).convert('RGBA')
        # Precargar una vuelta de cada animación; después todos los fotogramas son reutilizables.
        self.sprites = {}
        for anim, frames in [('run', range(0, 60, 3)), ('wait', range(0, 160, 12)),
                             ('jump', [5]), ('jumped', [4]), ('dead', range(0, 40, 3)),
                             ('find_surprise', [5, 10, 15]), ('door_walk', [0, 6, 12])]:
            self.sprites[anim] = [self.actor.sprite(anim, i) for i in frames]
        self.train_closed = self.train(False)
        self.train_open = self.train(True)
        yy, xx = np.mgrid[0:H, 0:W]
        edge = ((xx - W / 2) / (W / 2)) ** 2 * .45 + ((yy - H / 2) / (H / 2)) ** 2 * .3
        vignette = np.zeros((H, W, 4), np.uint8)
        vignette[..., :3] = (8, 11, 29)
        vignette[..., 3] = np.clip((edge - .12) * 46, 0, 34).astype(np.uint8)
        self.vignette = Image.fromarray(vignette)
        print('Assets y animaciones preparados.', flush=True)

    def mario(self, im, x, feet, anim='wait', t=0, factor=2, front=False):
        frames = self.sprites[anim]
        pose, origin = frames[int(t * (20 if anim == 'run' else 10)) % len(frames)]
        if front:
            pose, origin = self.actor.sprite('wait', 0, yaw=0)
        pose = pose.resize((round(pose.width * factor), round(pose.height * factor)), Image.Resampling.NEAREST)
        im.alpha_composite(pose, (round(x - origin[0] * factor), round(feet - origin[1] * factor)))

    def landscape(self, offset, ground=270, rails=False):
        im = Image.new('RGBA', (W, H), (24, 144, 255, 255))
        # Nubes y colinas usan velocidades distintas para dar profundidad.
        im.alpha_composite(engine.tile_h(self.back, offset * .18, W), (0, ground - 512))
        im.alpha_composite(engine.tile_h(self.front, offset * .45, W), (0, ground - 512 + 8))
        d = ImageDraw.Draw(im)
        d.rectangle((0, ground + 9, W, H), fill=(26, 126, 42))
        # Textura de suelo extraída y repetida con vecino más cercano.
        im.alpha_composite(engine.tile_h(self.ground, offset, W), (0, ground))
        for y in range(ground + 30, H, 18):
            for x in range(-int(offset) % 32 - 32, W, 32):
                d.line((x, y, x + 4, y), fill=(48, 152, 52), width=2)
        if rails:
            d.rectangle((0, 268, W, 291), fill=(56, 54, 61))
            for x in range(-int(offset) % 18 - 18, W, 18):
                d.rectangle((x, 271, x + 5, 287), fill=(113, 77, 58))
            d.rectangle((0, 272, W, 274), fill=(202, 207, 215))
            d.rectangle((0, 284, W, 286), fill=(202, 207, 215))
        return im

    def train(self, opened):
        """Carrocería con volúmenes, cabina aerodinámica y bogies de doble eje."""
        im = Image.new('RGBA', (392, 132))
        d = ImageDraw.Draw(im)
        # Rodaje en varias capas: bastidor, suspensión, frenos y llantas.
        d.rectangle((12, 102, 354, 112), fill=(39, 39, 53))
        for bx in (24, 255):
            d.polygon([(bx, 110), (bx + 7, 103), (bx + 61, 103), (bx + 70, 111),
                       (bx + 63, 122), (bx + 8, 122)], fill=(61, 66, 80), outline=(19, 23, 37))
            d.rectangle((bx + 18, 111, bx + 52, 117), fill=(117, 124, 136))
            for wx in (bx + 5, bx + 48):
                d.ellipse((wx, 109, wx + 21, 130), fill=(20, 24, 38), outline=(153, 159, 173), width=2)
                d.ellipse((wx + 5, 114, wx + 16, 125), fill=(74, 82, 100), outline=(188, 195, 204))
                d.rectangle((wx + 9, 118, wx + 12, 121), fill=(212, 215, 218))
        shell = [(4, 25), (13, 17), (306, 17), (327, 23), (344, 38), (360, 64),
                 (382, 85), (390, 93), (386, 103), (13, 105), (3, 97)]
        d.polygon(shell, fill=(234, 237, 233), outline=(35, 36, 54), width=2)
        # Techo curvo y faldón inferior, sin degradados que borren la cuadrícula.
        d.polygon([(6, 27), (14, 19), (305, 19), (323, 25), (333, 34), (8, 34)], fill=(214, 221, 227))
        d.line([(13, 21), (306, 21), (320, 25)], fill=(255, 255, 246), width=3)
        d.rectangle((8, 35, 331, 37), fill=(255, 255, 247))
        d.polygon([(6, 91), (378, 91), (388, 95), (383, 102), (13, 102), (6, 96)], fill=(171, 182, 195))
        d.line((13, 100, 378, 100), fill=(110, 123, 141), width=2)
        d.polygon([(6, 79), (366, 79), (380, 88), (7, 88)], fill=(111, 0, 89))
        d.line((9, 77, 363, 77), fill=(187, 104, 163))
        d.line((9, 89, 380, 89), fill=(249, 247, 239))
        # Ventanillas oscuras con reflejos oblicuos y marcos empotrados.
        for x in (17, 57, 155, 198, 241, 283):
            d.rounded_rectangle((x, 37, x + 31, 57), radius=3, fill=(73, 85, 106), outline=(187, 195, 201))
            d.rectangle((x + 3, 40, x + 28, 54), fill=(24, 43, 64))
            d.polygon([(x + 4, 40), (x + 14, 40), (x + 8, 54), (x + 4, 54)], fill=(57, 94, 119))
            d.line((x + 4, 41, x + 26, 41), fill=(150, 206, 215))
        # Cristal envolvente de cabina, limpiaparabrisas, faros y acoplador.
        d.polygon([(321, 31), (334, 38), (356, 69), (325, 66)], fill=(23, 37, 56), outline=(115, 130, 148))
        d.polygon([(325, 34), (332, 39), (345, 57), (329, 52)], fill=(82, 135, 156))
        d.line((329, 62, 347, 62), fill=(171, 194, 207))
        d.line((337, 62, 345, 46), fill=(16, 23, 39))
        d.polygon([(367, 78), (374, 83), (380, 86), (368, 85)], fill=(255, 241, 171))
        d.rectangle((381, 95, 390, 98), fill=(57, 61, 77))
        d.line((348, 72, 362, 75), fill=(193, 203, 211))
        # Puerta corredera, peldaño, junta y marco.
        d.rectangle((99, 32, 140, 101), fill=(122, 132, 151), outline=(206, 214, 216))
        d.rectangle((102, 35, 137, 97), fill=(219, 224, 225), outline=(76, 89, 111))
        if opened:
            d.rectangle((105, 37, 134, 96), fill=(22, 25, 43))
            d.rectangle((106, 39, 109, 92), fill=(68, 52, 83))
            d.rectangle((103, 97, 138, 101), fill=(244, 210, 83))
            d.line((107, 100, 134, 100), fill=(255, 252, 207))
        else:
            d.line((119, 36, 119, 97), fill=(92, 106, 125))
            for x in (106, 123):
                d.rectangle((x, 42, x + 9, 62), fill=(34, 55, 76))
                d.line((x + 1, 43, x + 7, 43), fill=(123, 190, 204))
            d.rectangle((114, 69, 116, 74), fill=(113, 117, 129))
        # Paneles de servicio, rejillas y reflejos de la carrocería.
        for x in (16, 67, 213, 245):
            d.line((x, 65, x, 74), fill=(201, 208, 211))
            d.line((x, 74, x + 17, 74), fill=(211, 215, 214))
        for x in range(226, 251, 4):
            d.line((x, 94, x + 2, 94), fill=(78, 94, 113))
        d.rectangle((182, 106, 230, 116), fill=(67, 77, 93), outline=(133, 143, 158))
        d.line((13, 58, 93, 58), fill=(249, 250, 244))
        # Logo real aportado, sin sustituir su tipografía por la fuente del juego.
        im.alpha_composite(self.badge, (146, 56))
        d.rectangle((209, 13, 255, 17), fill=(113, 126, 143))
        d.line((213, 11, 244, 1, 265, 10, 237, 16, 213, 11), fill=(39, 48, 66), width=2)
        d.line((231, 0, 263, 0), fill=(97, 110, 129), width=2)
        for x in (38, 72, 279):
            d.rectangle((x, 14, x + 20, 17), fill=(157, 170, 183))
        return im

    def interior(self, t, dark=False, emergency=False, mario=True):
        offset = 630 + max(0, min(t, 15) - 9) * 104
        outside = self.landscape(offset, ground=267)
        im = Image.new('RGBA', (W, H), (183, 184, 196, 255))
        d = ImageDraw.Draw(im)
        # Techo con paneles y perspectiva; las luces pertenecen al vagón.
        d.rectangle((0, 0, W, 97), fill=(116, 122, 143))
        d.polygon([(0, 0), (216, 0), (186, 66), (30, 66)], fill=(174, 177, 186))
        d.line((30, 66, 186, 66), fill=(218, 216, 211), width=2)
        for x in (29, 186):
            d.line((x, 0, 63 if x < 100 else 152, 69), fill=(90, 98, 121), width=2)
        d.polygon([(45, 0), (51, 0), (76, 62), (72, 62)], fill=(255, 248, 218))
        d.polygon([(165, 0), (171, 0), (143, 62), (139, 62)], fill=(255, 248, 218))
        d.rectangle((0, 73, W, 95), fill=(87, 94, 115))
        d.line((0, 76, W, 76), fill=(213, 216, 214), width=2)
        for x in range(0, W, 16):
            d.line((x, 80, x + 9, 80), fill=(138, 150, 164))
        d.rectangle((0, 96, W, 111), fill=(227, 225, 219))
        d.rectangle((0, 226, W, 298), fill=(213, 211, 205))
        d.rectangle((0, 299, W, H), fill=(67, 60, 80))
        for x in [-38, 111]:
            d.rectangle((x, 118, x + 134, 218), fill=(68, 63, 78), outline=(236, 232, 220), width=3)
            crop = outside.crop((max(0, x + 5), 141, max(0, x + 5) + 125, 230))
            im.alpha_composite(crop, (x + 5, 124))
            d.rectangle((x + 5, 124, x + 129, 126), fill=(131, 203, 221))
            d.line((x + 64, 124, x + 64, 212), fill=(141, 146, 163), width=3)
        # Portaequipajes, luminarias, pasamanos y asientos reconocibles.
        d.rectangle((6, 102, 210, 105), fill=(74, 73, 93))
        for x in [13, 145]:
            d.rectangle((x, 109, x + 56, 113), fill=(255, 255, 233))
        for x in [-15, 137]:
            d.rounded_rectangle((x, 235, x + 68, 286), radius=4, fill=(85, 38, 111), outline=(39, 28, 65), width=3)
            d.rectangle((x + 7, 242, x + 59, 248), fill=(136, 77, 148))
            d.rectangle((x + 6, 284, x + 74, 295), fill=(119, 60, 138), outline=(36, 26, 59), width=2)
            d.rectangle((x + 13, 296, x + 19, 306), fill=(40, 39, 53))
            for yy in (253, 264, 275):
                d.line((x + 10, yy, x + 55, yy), fill=(97, 47, 123))
            d.rectangle((x + 4, 237, x + 63, 244), fill=(207, 205, 206))
            d.line((x + 9, 245, x + 58, 245), fill=(127, 83, 148))
        d.line((207, 112, 207, 291), fill=(93, 99, 115), width=3)
        for y in range(309, H, 19):
            d.line((0, y, W, y), fill=(82, 73, 96))
        if mario:
            if 15 <= t < 16.2:
                q = t - 15
                self.mario(im, 91 - 40 * ease(q), 297 - 40 * math.sin(clamp(q) * math.pi), 'jumped', t)
            elif t >= renfe_audio.DEATH_T:
                q = t - renfe_audio.DEATH_T
                self.mario(im, 79, 299 - 126 * q + 120 * q * q, 'dead', q)
            else:
                self.mario(im, 87, 298, 'wait' if t < 17 else 'find_surprise', t)
        if t < 15:
            # Bandas de sol que cruzan despacio el interior durante el viaje.
            sun = Image.new('RGBA', (W, H))
            sd = ImageDraw.Draw(sun)
            sx = int((t * 19) % 140) - 70
            for px in (sx, sx + 138):
                sd.polygon([(px, 218), (px + 33, 218), (px + 100, 379), (px + 43, 379)],
                           fill=(255, 225, 159, 21))
            im.alpha_composite(sun)
        if dark:
            a = np.asarray(im).copy()
            a[..., :3] = (a[..., :3].astype(np.float32) * .155).astype(np.uint8)
            im = Image.fromarray(a)
        if emergency:
            pulse = .5 + .5 * math.sin((t - 17) * math.pi * 2 / 1.2)
            yy, xx = np.mgrid[0:H, 0:W]
            reach = np.clip(1 - np.sqrt(((xx - 108) / 190) ** 2 + ((yy - 108) / 360) ** 2), 0, 1)
            glow = np.zeros((H, W, 4), np.uint8)
            glow[..., :3] = (209, 1, 22)
            glow[..., 3] = (reach * (22 + pulse * 73)).astype(np.uint8)
            im.alpha_composite(Image.fromarray(glow))
            d = ImageDraw.Draw(im)
            d.rectangle((92, 102, 123, 113), fill=(round(150 + 100 * pulse), 9, 26), outline=(255, 78, 72), width=2)
            d.line((100, 97, 96, 92), fill=(255, 80, 64), width=2)
            d.line((115, 97, 120, 91), fill=(255, 80, 64), width=2)
        return im

    def finish(self, im, t):
        """Pequeños movimientos de cámara y viñeta, respetando la cuadrícula lógica."""
        if t < 4.8:
            zoom = 1.035 + .045 * ease(t / 4.8)
            cx, cy = 105 + 2 * math.sin(t * 1.1), 204
        elif 6 <= t < 8.77:
            zoom = 1.02 + .03 * ease((t - 6) / 2.7)
            cx, cy = 107, 212
        elif 9.17 <= t < 12.5:
            zoom = 1.0 + .025 * ease((t - 9.17) / 3.3)
            cx, cy = 108, 206
        else:
            zoom, cx, cy = 1, W / 2, H / 2
        if zoom > 1:
            cw, ch = round(W / zoom), round(H / zoom)
            x = max(0, min(W - cw, round(cx - cw / 2)))
            y = max(0, min(H - ch, round(cy - ch / 2)))
            im = im.crop((x, y, x + cw, y + ch)).resize((W, H), Image.Resampling.NEAREST)
        if t < renfe_audio.GAMEOVER_T:
            im.alpha_composite(self.vignette)
        return im.convert('RGB')

    def header(self, im, mode, t):
        panel(im, (12, 22, W - 13, 44), fill=(22, 18, 39, 255), border=(132, 109, 158), width=1)
        label(im, mode, 24, color=YELLOW)
        # Indicador de avance de cuatro capítulos.
        d = ImageDraw.Draw(im)
        chapter = 0 if t < 9 else 1 if t < 17 else 2 if t < renfe_audio.DIALOGUE_END else 3
        for i in range(4):
            d.rectangle((81 + i * 14, 356, 90 + i * 14, 358), fill=YELLOW if i <= chapter else (95, 87, 113))

    def frame(self, t):
        if t < 4.8:
            im = self.landscape(t * 82, ground=306)
            q = clamp((t - 1.65) / .65)
            airborne = 1.65 <= t < 2.3
            feet = 306 - (62 * math.sin(q * math.pi) if airborne else 0)
            self.mario(im, 79, feet, 'jump' if airborne else 'run', t, factor=2.2)
            for i, at in enumerate([1.96, 3.2]):
                if t < at:
                    x = 79 + (at - t) * 82
                    y = 228 if i == 0 else 263
                    im.alpha_composite(self.coin.resize((22, 22), Image.Resampling.NEAREST), (round(x), y))
            # Vegetación de la ROM en primer término, con un tercer plano de profundidad.
            bush = self.front.crop((265, 435, 512, 512))
            im.alpha_composite(engine.tile_h(bush, t * 122, W), (0, 341))
            if not airborne:
                d = ImageDraw.Draw(im)
                for j in range(3):
                    phase = (t * 7 + j / 3) % 1
                    x = 65 - phase * 29
                    y = 305 - math.sin(phase * math.pi) * 6
                    d.rectangle((x, y, x + 2, y + 1), fill=(169, 192, 104))
        elif t < 9:
            im = self.landscape(395 + (t - 4.8) * 20, rails=True)
            opened = 6.3 <= t < 8.15
            d = ImageDraw.Draw(im)
            d.line((0, 128, W, 128), fill=(68, 81, 97))
            d.line((194, 128, 194, 274), fill=(106, 116, 130), width=3)
            d.line((163, 128, 194, 148), fill=(106, 116, 130), width=2)
            if t < 6:
                tx = round(225 - 237 * ease((t - 4.8) / .9))
                train = self.train_closed.resize((225, 76), Image.Resampling.NEAREST)
                im.alpha_composite(train, (tx, 197))
            else:
                im.alpha_composite(self.train_open if opened else self.train_closed, (-5, 145))
            d.rectangle((0, 277, W, 301), fill=(133, 135, 151))
            d.rectangle((0, 277, W, 281), fill=YELLOW)
            d.line((0, 300, W, 300), fill=(75, 83, 102), width=2)
            for x in range(0, W, 14):
                d.rectangle((x, 284, x + 5, 286), fill=(92, 89, 108))
            if t < 7.85:
                q = clamp((t - 6.65) / 1.2)
                x = 49 + 66 * ease((t - 5.7) / 2.15)
                feet = 277 - 33 * q - 33 * math.sin(q * math.pi)
                self.mario(im, x, feet, 'jump' if t >= 6.65 else 'run', t, factor=1.6)
        elif 12.5 <= t < 13.8:
            im = self.landscape(900 + t * 180, rails=True)
            # Plano general del tren entero dentro del encuadre vertical.
            small_train = self.train_closed.resize((225, 76), Image.Resampling.NEAREST)
            im.alpha_composite(small_train, (-12, 197 + int(math.sin(t * 13))))
            # Postes cercanos cruzan rápido; las colinas se desplazan más despacio.
            px = int(360 - (t - 12.5) * 330)
            ImageDraw.Draw(im).line((px, 40, px, 292), fill=(75, 85, 107), width=4)
            ImageDraw.Draw(im).line((0, 125, W, 125), fill=(70, 82, 101))
            for y, n in [(155, 28), (297, 38)]:
                ImageDraw.Draw(im).line((5, y, 5 + n, y), fill=(235, 248, 255), width=2)
        elif t < 20:
            im = self.interior(t, dark=t >= 16.55, emergency=t >= 17.1)
            if 15 <= t < 15.9:
                q = t - 15
                if q < .27:
                    # Plano del impacto: el morro se detiene contra un tope de vía.
                    im = self.landscape(1060, rails=True)
                    hit_train = self.train_closed.resize((225, 76), Image.Resampling.NEAREST)
                    im.alpha_composite(hit_train, (-38 + round(18 * ease(q / .09)), 197))
                    block = ImageDraw.Draw(im)
                    block.rectangle((191, 235, 207, 270), fill=(62, 53, 65), outline=WHITE, width=2)
                    for yy in range(239, 265, 8):
                        block.line((194, yy, 205, yy + 6), fill=YELLOW, width=3)
                dx = round(math.sin(q * 83) * 9 * (1 - q))
                dy = round(math.cos(q * 71) * 6 * (1 - q))
                moved = Image.new('RGBA', (W, H), INK)
                moved.alpha_composite(im, (dx, dy))
                im = moved
                for i in range(20):
                    a = i * 2.399
                    x = 108 + math.cos(a) * (20 + q * 150)
                    y = 180 + math.sin(a) * (20 + q * 130) + q * q * 75
                    ImageDraw.Draw(im).rectangle((x, y, x + 3, y + 3), fill=YELLOW if i % 2 else WHITE)
                if t < 15.067:
                    im.alpha_composite(Image.new('RGBA', (W, H), (255, 235, 180, 140)))
            if 16.2 <= t < 16.55:
                im = engine.fade(im, 0.2 if int(t * 18) % 2 else .85).convert('RGBA')
            if 16.55 <= t < 17.1:
                # Pausa real en negro antes de la emergencia.
                im = Image.new('RGBA', (W, H), (1, 1, 5))
        elif t < renfe_audio.DIALOGUE_END:
            im = self.interior(t, dark=True, emergency=True)
            # Resplandor de la pantalla: el comunicado ilumina el vagón en azul.
            yy, xx = np.mgrid[0:H, 0:W]
            reach = np.clip(1 - np.sqrt(((xx - 108) / 145) ** 2 + ((yy - 150) / 235) ** 2), 0, 1)
            spill = np.zeros((H, W, 4), np.uint8)
            spill[..., :3] = (73, 125, 174)
            spill[..., 3] = (reach * 34 * ease((t - 20) / .3)).astype(np.uint8)
            im.alpha_composite(Image.fromarray(spill))
            panel(im, (39, 70, 176, 234), fill=(21, 26, 46, 120), border=(52, 78, 102), width=1)
            panel(im, (42, 73, 173, 231), fill=(26, 21, 43), border=(181, 123, 194), width=3)
            # Reducción de la foto dentro del compositor a píxeles lógicos del juego.
            photo = self.portrait
            if t < 20.3:
                # Entrada por bandas horizontales.
                photo = photo.copy()
                ImageDraw.Draw(photo).rectangle((0, round(132 * ease((t - 20) / .3)), 104, 132), fill=(26, 21, 43))
            im.alpha_composite(photo, (56, 82))
            label(im, 'ÓSCAR PUENTE', 214, color=YELLOW)
            start, end, line = next((p for p in renfe_audio.PAGES if p[0] <= t < p[1]), renfe_audio.PAGES[0])
            count = max(0, int((t - start) * renfe_audio.TEXT_CPS))
            if 0 < count < len(line):
                # Tres barras de voz dentro del monitor, sin mensajes adicionales.
                md = ImageDraw.Draw(im)
                for j in range(3):
                    bar = 3 + (int(t * 22 + j * 3) % 8)
                    md.rectangle((47 + j * 3, 205 - bar, 48 + j * 3, 205), fill=(133, 213, 224))
            lines = dialogue_lines(line)
            panel(im, (12, 248, W - 13, 324), border=(245, 219, 111))
            for i, s in enumerate(lines):
                visible = s[:max(0, count)]
                if visible:
                    label(im, visible, 256 + i * 19, x=20)
                count -= len(s) + 1
            if t >= start + len(line) / renfe_audio.TEXT_CPS and int(t * 3) % 2:
                ImageDraw.Draw(im).polygon([(185, 310), (191, 310), (188, 314)], fill=YELLOW)
            # La luz de la transmisión afecta al entorno sin añadir rótulos.
            d = ImageDraw.Draw(im)
            d.line((46, 75, 64, 75), fill=(181, 198, 226))
            d.line((44, 77, 44, 91), fill=(181, 198, 226))
        elif t < renfe_audio.GAMEOVER_T:
            im = self.interior(t, dark=True, emergency=True)
            if t > renfe_audio.IRIS_T:
                q = ease((t - renfe_audio.IRIS_T) / .8)
                mask = Image.new('L', (W, H), 255)
                r = 330 * (1 - q)
                ImageDraw.Draw(mask).ellipse((79 - r, 270 - r, 79 + r, 270 + r), fill=0)
                im.paste((6, 5, 16), (0, 0, W, H), mask)
        else:
            im = Image.new('RGBA', (W, H), (12, 9, 25))
            d = ImageDraw.Draw(im)
            for y in range(0, H, 8):
                d.line((0, y, W, y), fill=(16, 13, 32))
            self.header(im, 'FIN DEL TRAYECTO', t)
            label(im, 'GAME', 117, 2, (255, 116, 103))
            label(im, 'OVER', 151, 2, (255, 116, 103))
            label(im, 'MARIO PERDIÓ EL TREN', 207)
            self.mario(im, 108, 280, 'dead', 1.2, factor=1.5)
            if t >= renfe_audio.GAMEOVER_T + 1.1:
                caption(im, ['CONTINUAR...'], y=306, color=YELLOW)
            label(im, 'Una aventura de ficción', 335, color=(172, 157, 188))
            if t > TOTAL - .5:
                im = engine.fade(im, (TOTAL - t) / .5).convert('RGBA')
        if 8.77 <= t < 9.17:
            # Barrido en dos tiempos que enlaza puerta e interior sin salto abrupto.
            q = (t - 8.77) / .4
            x = round((q * 2 - 1) * W)
            ImageDraw.Draw(im).rectangle((x, 0, x + W, H), fill=INK)
        return self.finish(im, t)


def preview():
    film = Film()
    times = [1, 5.8, 7.2, 10, 13, 15.15, 16.8, 18, 22.5, 28, 33, 38,
             renfe_audio.DIALOGUE_END - .1, renfe_audio.DEATH_T + .35,
             renfe_audio.GAMEOVER_T - .2, renfe_audio.GAMEOVER_T + 2]
    sheet = Image.new('RGB', (W * 4, (H + 24) * 4), (15, 12, 25))
    for i, t in enumerate(times):
        fr = film.frame(t)
        fr.save(CACHE / ('previo_%s.png' % t))
        x, y = i % 4 * W, i // 4 * (H + 24)
        sheet.paste(fr, (x, y))
        sheet.paste(lettering('%.2f s' % t).convert('RGB'), (x + 8, y + H + 2))
    sheet.save(CACHE / 'storyboard_visual.png')
    print(CACHE / 'storyboard_visual.png', flush=True)


def main():
    FINAL.parent.mkdir(parents=True, exist_ok=True)
    film = Film()
    silent = CACHE / 'imagen.mp4'
    # Se envía resolución lógica a ffmpeg; el escalado exacto x5 mantiene todos los píxeles.
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
           '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-vf', 'scale=1080:1920:flags=neighbor',
           '-an', '-c:v', 'libx264', '-preset', 'fast', '-crf', '17', '-pix_fmt', 'yuv420p', str(silent)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for i in range(round(TOTAL * FPS)):
            p.stdin.write(film.frame(i / FPS).tobytes())
            if i % 150 == 0:
                print('Imagen: %d / %s s' % (i // FPS, TOTAL), flush=True)
    finally:
        p.stdin.close()
        code = p.wait()
    if code:
        raise RuntimeError('ffmpeg no pudo completar la imagen')
    wav = renfe_audio.build()
    subprocess.check_call(['ffmpeg', '-y', '-loglevel', 'error', '-i', str(silent), '-i', str(wav),
                           '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                           '-af', 'loudnorm=I=-16:TP=-1.5:LRA=8', '-t', str(TOTAL),
                           '-movflags', '+faststart', str(FINAL)])
    print(FINAL, flush=True)


if __name__ == '__main__':
    preview() if '--preview' in sys.argv else main()
