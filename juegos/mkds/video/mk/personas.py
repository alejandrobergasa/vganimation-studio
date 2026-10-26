"""Personajes a medida sobre un piloto de la ROM: el modelo, la cabeza y las animaciones del piloto (drive / win / lose / spin) con la cara de una
foto como textura de la cara y el cuerpo recoloreado (pelo, camiseta, traje, corbata). Es lo que hace el ejemplo de Ábalos, generalizado.

- `cara_foto(foto, ojos, barbilla, centro)`: media cara de 128 px (centro de la cara en x = 0, como las caras del juego) alineada con los hitos
  de la foto: fila de los ojos, fila de la barbilla y columna del centro de la cara (los demás rasgos salen de proporciones medias).
- `cuerpo_piloto(base_main, ...)`: P_main de Mario recoloreado por regiones (gorra → pelo/calvo, pecho, mangas, torso, botones).
- `Personaje`: devuelve las `Instancia` del busto del piloto sentado o de pie con piernas de cajas que caminan (estilo `extra.Peaton`).
Ejes como el resto del motor: Y arriba, mira a +z con yaw = 0, +x es su izquierda."""
import math
import numpy as np
from PIL import Image
from scipy.ndimage import map_coordinates

import modelos as M
from . import escena as E, extra as X

# filas de la media cara del juego (0..32) y su posición relativa entre ojos (0) y barbilla (1) en la foto: medidas del ejemplo de Ábalos
_FILAS = np.array([0, 3, 11, 20, 26, 31.5, 32.0])
_REL = np.array([-0.30, -0.18, 0.0, 0.37, 0.58, 1.0, 1.05])
_ANCHO_REL = 0.72                       # medio ancho de la cara (hasta la oreja) en veces la distancia ojos-barbilla


def color_piel(foto, ojos, barbilla, centro, ancho=_ANCHO_REL):
    """Color medio de la mejilla (fuera de la sombra de la nariz) en RGB 0..1."""
    a = np.asarray(Image.open(foto).convert('RGB'), np.float32) / 255.0
    d = barbilla - ojos
    x, y = int(centro + 0.38 * ancho * d), int(ojos + 0.45 * d)
    r = max(2, int(0.06 * d))
    return a[max(0, y - r):y + r, max(0, x - r):x + r].reshape(-1, 3).mean(0)


def cara_foto(foto, ojos, barbilla, centro, tam=128, piel=None, ancho=_ANCHO_REL):
    """Media cara (derecha de la foto) con el centro en x = 0, ajustada a los hitos de la foto. RGBA uint8 (tam, tam)."""
    a = np.asarray(Image.open(foto).convert('RGB'), np.float32) / 255.0
    H, W = a.shape[:2]
    d = float(barbilla - ojos)
    ys = np.interp((np.arange(tam) + .5) / tam * 32, _FILAS, ojos + _REL * d)
    xs = centro + (np.arange(tam) + .5) / tam * (ancho * d)
    gy, gx = np.meshgrid(np.clip(ys, 0, H - 1), np.clip(xs, 0, W - 1), indexing='ij')
    out = np.stack([map_coordinates(a[..., c], [gy, gx], order=1, mode='nearest') for c in range(3)], -1)
    # un poco de contraste y saturación: las texturas del juego son planas y vivas
    lum = out @ np.array([.299, .587, .114], np.float32)
    out = lum[..., None] + (out - lum[..., None]) * 1.2
    out = np.clip((out - .5) * 1.12 + .5 + .02, 0, 1)
    p = color_piel(foto, ojos, barbilla, centro, ancho) if piel is None else np.asarray(piel)
    # el borde derecho de la textura da la vuelta a la nuca: se funde con la piel para no arrastrar el fondo de la foto
    u = np.clip(((np.arange(tam) + .5) / tam - 0.576 / ancho) / (0.10 / ancho), 0, 1)       # la oreja queda a ≈ 0,58 ojos-barbilla del centro
    w = (u * u * (3 - 2 * u))[None, :, None]
    out = out * (1 - w) + np.asarray(p, np.float32) * w
    rgba = (np.concatenate([out, np.ones(out.shape[:2] + (1,))], -1) * 255).astype(np.uint8)
    k = tam // 32
    rgba[int(28.6 * k):, int(28.2 * k):, :3] = (np.asarray(p) * 255).astype(np.uint8)      # la nariz del modelo usa la esquina inferior de la textura
    return rgba


def cuerpo_piloto(base, pelo, camisa, mangas, torso, botones, piel):
    """P_main (32x64) de Mario recoloreado por regiones: gorra → pelo (o piel si pelo es None: calvo), camisa (pecho), mangas, torso (mono),
    botones. Las manos (guantes) y el sombreado se conservan. Todos los colores RGB 0..1."""
    a = np.array(base, np.uint8).copy()
    f = a[..., :3].astype(np.float32)
    h, w = a.shape[:2]
    rojo = (f[..., 0] > 120) & (f[..., 1] < 110) & (f[..., 2] < 110)
    azul = (f[..., 2] > 110) & (f[..., 0] < 60)
    amar = (f[..., 0] > 180) & (f[..., 1] > 150) & (f[..., 2] < 140)
    yy, xx = np.mgrid[0:h, 0:w]
    gorra = (xx >= 16) & (xx < 48) & (yy >= 16)
    lum = f.mean(-1) / 255.0
    rng = np.random.default_rng(3)
    cabello = (np.asarray(piel if pelo is None else pelo, np.float32) * 255) * (0.94 + 0.12 * rng.random((h, w, 1)))
    flequillo = (xx < 17) & (yy < 9)
    out = f.copy()
    out[gorra] = cabello[gorra]
    out[flequillo] = cabello[flequillo]
    rojo = rojo & ~flequillo
    pecho = rojo & ~gorra & (xx < 16) & (yy >= 6)
    sombra = lambda m: (0.72 + 0.5 * lum[m])[:, None]
    out[pecho] = np.asarray(camisa, np.float32) * 255 * (0.82 + 0.18 * lum[pecho][:, None])
    resto = rojo & ~gorra & ~pecho
    out[resto] = np.asarray(mangas, np.float32) * 255 * (0.8 + 0.4 * lum[resto][:, None])
    out[azul] = np.asarray(torso, np.float32) * 255 * sombra(azul)
    out[amar] = np.asarray(botones, np.float32) * 255
    a[..., :3] = np.clip(out, 0, 255).astype(np.uint8)
    return a


class Personaje:
    """Piloto de la ROM como persona. `hitos` = (fila de los ojos, fila de la barbilla, columna del centro de la cara) en píxeles de la foto.
    `base` = piloto de la ROM cuya malla se usa (la textura sale siempre de Mario: mismo reparto de uv en todos); `pelo` None = calvo.
    Escala 5: el busto mide ≈ 4 u y con las piernas ≈ 6 u (un kart ≈ 6,7 u)."""
    def __init__(self, motor, nombre, foto, hitos, pelo, camisa, mangas, torso, botones, pantalon, zapato=(0.08, 0.08, 0.09),
                 base='mario', escala=5.0, largo=1.5, piel=None, ancho=_ANCHO_REL, brillo_calvo=1.18):
        self.nombre, self.escala, self.largo = nombre, escala, largo
        ojos, barbilla, centro = hitos
        self.piel = np.asarray(color_piel(foto, ojos, barbilla, centro, ancho) if piel is None else piel)
        mario = M.piloto('mario')
        main = cuerpo_piloto(mario.texlook.get('P_main', 'P_main_pl'), pelo, camisa, mangas, torso, botones,
                             np.clip(self.piel * brillo_calvo, 0, 1) if pelo is None else self.piel)
        cara = cara_foto(foto, ojos, barbilla, centro, piel=self.piel, ancho=ancho)
        self.p = X.Pasajero(motor, base, texturas={'P_face.1': cara, 'P_main': main}, nombre=nombre)
        self.pie = X.Peaton(motor, base, pantalon=pantalon, zapato=zapato, largo=largo, escala=escala, pasajero=self.p)
        self.textura_cara, self.textura_cuerpo = cara, main

    def sentado(self, pos, yaw=0.0, anim='drive', frame=14, escala_v=1.0, **kw):
        """Busto en `pos` (el origen del piloto es el asiento). Para ir en un kart: pos = kart + R @ (0, a·s, z·s) (ver `Kart.instancias`)."""
        R = E.rotacion(yaw)
        return [E.Instancia(self.p.malla(anim, frame), pos=pos, rot=R, escala=self.escala * escala_v, **kw)]

    def de_pie(self, pos, yaw=0.0, fase=None, amp=35.0, anim='drive', frame=14, bote=0.0, escala_v=1.0, **kw):
        """pos = suelo bajo los pies. fase = ángulo de paso en rad (None = quieto)."""
        return self.pie.instancias(pos, yaw, fase=0.0 if fase is None else fase, amp=0.0 if fase is None else amp, anim=anim, frame=frame,
                                   rebote=bote, escala_v=escala_v, **kw)
