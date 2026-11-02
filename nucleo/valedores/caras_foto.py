"""Caras de foto sobre modelos 3D, con parpadeo y boca animados.

Las UV de la cabeza de un modelo DS suelen estar reflejadas (mitad izquierda = mitad derecha) y a muy
poca resolución, así que hornear la foto en su textura la vuelve simétrica y borrosa. Aquí la foto es una
calca propia: una segunda pasada sobre los mismos triángulos de la cabeza, con UV nuevas y su propio
alfa. La malla y sus animaciones se conservan; lo que queda fuera de la calca (orejas, nuca) usa la
textura nativa teñida con el tono de piel de la foto.
"""
from dataclasses import dataclass
import math

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

N_TARJETA = 256
# Rasgos en la tarjeta normalizada (fracciones del lado).
OJOS_Y, OJOS_D = 0.40, 0.30         # altura de los ojos y distancia entre ellos
BARBILLA_Y = 0.91


@dataclass
class Hitos:
    """Rasgos en píxeles de la foto. El agente puede leerlos de la imagen o usar `detectar_hitos`."""
    ojo_i: tuple        # ojo a la izquierda de la imagen
    ojo_d: tuple
    boca: tuple = None
    barbilla: tuple = None

    def __post_init__(self):
        ix, iy = self.ojo_i
        dx, dy = self.ojo_d
        d = math.hypot(dx - ix, dy - iy)
        if d <= 0 or dx <= ix:
            raise ValueError('ojo_i debe quedar a la izquierda de ojo_d en la imagen')
        cx, cy = (ix + dx) / 2, (iy + dy) / 2
        # Perpendicular hacia abajo de la línea de los ojos; proporciones medias de una cara.
        px, py = -(dy - iy) / d, (dx - ix) / d
        if self.boca is None:
            self.boca = (cx + px * d * 1.05, cy + py * d * 1.05)
        if self.barbilla is None:
            self.barbilla = (cx + px * d * 1.70, cy + py * d * 1.70)


def detectar_hitos(foto):
    """Localiza ojos con OpenCV (`pip install opencv-python-headless`). Falla si no ve una cara clara."""
    try:
        import cv2
    except ImportError as e:
        raise RuntimeError('Falta OpenCV para detectar la cara; instálalo o indica Hitos(...) a mano') from e
    im = np.asarray(_abrir(foto).convert('L'))
    caras = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(
        im, 1.08, 5, minSize=(max(24, im.shape[1] // 8),) * 2)
    if not len(caras):
        raise ValueError('No se ha detectado una cara frontal; indica Hitos(ojo_i, ojo_d, boca, barbilla) a mano')
    x, y, w, h = max(caras, key=lambda c: c[2] * c[3])
    zona = im[y:y + h * 6 // 10, x:x + w]
    ojos = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml').detectMultiScale(
        zona, 1.05, 4, minSize=(w // 10,) * 2, maxSize=(w // 3,) * 2)
    centros = sorted(((x + ex + ew / 2, y + ey + eh / 2) for ex, ey, ew, eh in ojos), key=lambda c: c[0])
    izquierda = [c for c in centros if c[0] < x + w * 0.5]
    derecha = [c for c in centros if c[0] >= x + w * 0.5]
    if izquierda and derecha:
        # Se queda con el candidato más alejado del centro de cada lado: evita falsos en la nariz.
        return Hitos(izquierda[0], derecha[-1])
    # Sin ojos fiables se usan las proporciones del recuadro de la cara.
    return Hitos((x + w * 0.31, y + h * 0.40), (x + w * 0.69, y + h * 0.40))


def _abrir(foto):
    return foto if isinstance(foto, Image.Image) else Image.open(foto)


def _elipse(N, cx, cy, rx, ry, suavidad):
    """Máscara 0..1 de una elipse con borde suave; coordenadas en fracciones del lado."""
    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    d = np.hypot((x - cx) / rx, (y - cy) / ry)
    return np.clip((1 - d) / suavidad, 0, 1)


class CaraFoto:
    """Tarjeta facial alineada y sus expresiones, en el espacio canónico de la cara.

    `hitos`: `Hitos` medidos a ojo, o None para detectarlos. `brillo` corrige fotos oscuras."""

    EXPRESIONES = ('neutra', 'parpadeo', 'boca1', 'boca2', 'boca3', 'ojos_abiertos', 'enfado', 'alegria')

    def __init__(self, foto, hitos=None, brillo=1.0, contraste=1.0, nombre='cara'):
        self.nombre = nombre
        foto = _abrir(foto).convert('RGB')
        self.hitos = hitos if hitos is not None else detectar_hitos(foto)
        self.tarjeta = self._alinear(foto)
        self.tarjeta = np.clip((self.tarjeta - 0.5) * contraste + 0.5, 0, 1) * brillo
        self.tarjeta = np.clip(self.tarjeta, 0, 1)
        self.piel = self._muestrear_piel()
        # Posición de la boca dentro de la tarjeta, según la foto.
        self.boca_y = self._boca_y
        self._memo = {}

    def _alinear(self, foto):
        """Lleva ojos y barbilla a su sitio canónico con una afinidad (corrige cabeza inclinada)."""
        h = self.hitos
        n = N_TARJETA
        ix, iy = h.ojo_i
        dx, dy = h.ojo_d
        cx, cy = (ix + dx) / 2, (iy + dy) / 2
        d = math.hypot(dx - ix, dy - iy)
        ux, uy = (dx - ix) / d, (dy - iy) / d
        vx, vy = -uy, ux
        # Longitud ojos-barbilla medida en la foto: fija la escala vertical.
        bx, by = h.barbilla
        alto = (bx - cx) * vx + (by - cy) * vy
        if alto <= 0:
            raise ValueError('La barbilla debe quedar por debajo de los ojos')
        self._boca_y = OJOS_Y + ((h.boca[0] - cx) * vx + (h.boca[1] - cy) * vy) / alto * (BARBILLA_Y - OJOS_Y)
        ex = d / (OJOS_D * n)                                  # píxeles de foto por píxel de tarjeta
        ey = alto / ((BARBILLA_Y - OJOS_Y) * n)
        gy, gx = np.mgrid[0:n, 0:n].astype(np.float32)
        gx = (gx + 0.5 - 0.5 * n) * ex
        gy = (gy + 0.5 - OJOS_Y * n) * ey
        sx, sy = cx + ux * gx + vx * gy, cy + uy * gx + vy * gy
        a = np.asarray(foto, np.float32) / 255.0
        return np.stack([map_coordinates(a[..., c], [sy, sx], order=1, mode='nearest') for c in range(3)], -1)

    def _muestrear_piel(self):
        n = N_TARJETA
        muestras = []
        for cx in (0.5 - OJOS_D * 0.62, 0.5 + OJOS_D * 0.62):
            cy = OJOS_Y + 0.14
            x0, x1, y0, y1 = int((cx - .035) * n), int((cx + .035) * n), int((cy - .03) * n), int((cy + .03) * n)
            muestras.append(self.tarjeta[y0:y1, x0:x1].reshape(-1, 3))
        return np.median(np.concatenate(muestras), 0)

    # --------------------------------------------------------------- expresiones

    def _parpadeo(self, im):
        n = N_TARJETA
        salida = im.copy()
        for cx in (0.5 - OJOS_D / 2, 0.5 + OJOS_D / 2):
            # El párpado toma el color de la piel justo encima del ojo.
            y0 = int((OJOS_Y - 0.075) * n)
            x0, x1 = int((cx - 0.04) * n), int((cx + 0.04) * n)
            parpado = np.median(im[y0:y0 + 6, x0:x1].reshape(-1, 3), 0)
            m = _elipse(n, cx, OJOS_Y, 0.078, 0.042, 0.45)[..., None]
            salida = salida * (1 - m) + parpado * m
            linea = _elipse(n, cx, OJOS_Y + 0.008, 0.062, 0.0085, 0.5)[..., None]
            salida = salida * (1 - linea * 0.82) + parpado * 0.28 * linea * 0.82
        return salida

    def _boca(self, im, apertura):
        """Abre la boca: baja la mandíbula deformando la foto y pinta el interior oscuro."""
        n = N_TARJETA
        by = self.boca_y
        gy, gx = np.mgrid[0:n, 0:n].astype(np.float32) / n
        # Solo se desplaza lo que está bajo la línea de la boca, y menos cuanto más lejos del centro.
        hueco = apertura * 0.052
        peso = np.clip((gy - by) / 0.02, 0, 1) * np.clip(1 - np.abs(gx - 0.5) / 0.31, 0, 1) ** 0.7
        desde = gy - hueco * peso
        salida = np.stack([map_coordinates(im[..., c], [desde * n - 0.5, gx * n - 0.5], order=1, mode='nearest')
                           for c in range(3)], -1)
        ry = 0.012 + hueco * 0.56
        rx = 0.065 + apertura * 0.008
        cy = by + hueco * 0.45
        interior = _elipse(n, 0.5, cy, rx, ry, 0.35)[..., None]
        fondo = np.array([0.20, 0.05, 0.06], np.float32)
        salida = salida * (1 - interior) + fondo * interior
        if apertura >= 0.6:
            dientes = _elipse(n, 0.5, cy - ry * 0.62, rx * 0.72, ry * 0.26, 0.5)[..., None] * interior
            salida = salida * (1 - dientes) + np.array([0.92, 0.90, 0.86], np.float32) * dientes
        return salida

    def _enfado(self, im):
        """Cejas bajadas y sombra en el ceño, deformando la foto."""
        n = N_TARJETA
        gy, gx = np.mgrid[0:n, 0:n].astype(np.float32) / n
        cerca = np.clip(1 - np.abs(gy - (OJOS_Y - 0.07)) / 0.06, 0, 1)
        baja = cerca * np.clip(1 - np.abs(gx - 0.5) / 0.24, 0, 1) * 0.028
        s = np.stack([map_coordinates(im[..., c], [(gy - baja) * n - 0.5, gx * n - 0.5], order=1, mode='nearest')
                      for c in range(3)], -1)
        ceno = _elipse(n, 0.5, OJOS_Y - 0.04, 0.05, 0.03, 0.8)[..., None] * 0.22
        return s * (1 - ceno)

    def _alegria(self, im):
        """Comisuras y mejillas hacia arriba."""
        n = N_TARJETA
        gy, gx = np.mgrid[0:n, 0:n].astype(np.float32) / n
        zona = np.clip(1 - np.abs(gy - self.boca_y) / 0.09, 0, 1)
        lados = np.clip(np.abs(gx - 0.5) / 0.14, 0, 1)
        sube = zona * lados * 0.022
        return np.stack([map_coordinates(im[..., c], [(gy + sube) * n - 0.5, gx * n - 0.5], order=1, mode='nearest')
                         for c in range(3)], -1)

    def _ojos_abiertos(self, im):
        """Sorpresa: estira la zona de los ojos."""
        n = N_TARJETA
        gy, gx = np.mgrid[0:n, 0:n].astype(np.float32) / n
        k = np.clip(1 - np.abs(gy - OJOS_Y) / 0.09, 0, 1) * (gy - OJOS_Y) * 0.32
        return np.stack([map_coordinates(im[..., c], [(gy - k) * n - 0.5, gx * n - 0.5], order=1, mode='nearest')
                         for c in range(3)], -1)

    def imagen(self, expresion='neutra'):
        """Tarjeta RGB 0..1 con la expresión aplicada. Se puede combinar con '+': 'enfado+boca2'."""
        if expresion in self._memo:
            return self._memo[expresion]
        im = self.tarjeta
        for parte in expresion.split('+'):
            if parte == 'neutra':
                continue
            if parte == 'parpadeo':
                im = self._parpadeo(im)
            elif parte.startswith('boca'):
                im = self._boca(im, {'boca1': 0.45, 'boca2': 0.75, 'boca3': 1.0}[parte])
            elif parte == 'enfado':
                im = self._enfado(im)
            elif parte == 'alegria':
                im = self._alegria(im)
            elif parte == 'ojos_abiertos':
                im = self._ojos_abiertos(im)
            else:
                raise ValueError('Expresión desconocida: ' + parte)
        self._memo[expresion] = im
        return im


class CalcaCara:
    """Capa facial de un actor: triángulos de la cabeza, UV a la tarjeta y expresión según el tiempo."""

    def __init__(self, cara, indices, uv, alfa, halo, recorte=4):
        self.cara, self.indices, self.uv, self.alfa, self.halo = cara, indices, uv, alfa, halo
        self.base = 'neutra'
        self.tramos_expresion = []        # (desde, hasta, expresión)
        self.tramos_habla = []            # (desde, hasta, semilla) o (desde, envolvente, fps)
        self.parpadeos = []
        self.parpadeo_auto = 3.1
        self._rgba = {}

    def expresion(self, nombre, desde=0.0, hasta=math.inf):
        """Mantiene una expresión ('enfado', 'alegria', 'ojos_abiertos') durante un tramo."""
        self.tramos_expresion.append((desde, hasta, nombre))
        return self

    def hablar(self, desde, hasta, semilla=7, silabas=6.5):
        """Boca animada mientras habla. Sin audio asociado, un ritmo silábico determinista."""
        self.tramos_habla.append(('ritmo', desde, hasta, semilla, silabas))
        return self

    def hablar_audio(self, muestras, frecuencia, desde=0.0, umbral=0.04):
        """Boca sincronizada con la envolvente de una voz, al ritmo real del audio."""
        m = np.asarray(muestras, np.float32)
        if m.ndim == 2:
            m = m.mean(1)
        ventana = max(1, int(frecuencia / 30))
        n = len(m) // ventana
        if n:
            env = np.sqrt((m[:n * ventana].reshape(n, ventana) ** 2).mean(1))
            env = env / max(float(env.max()), 1e-6)
            self.tramos_habla.append(('audio', desde, desde + n / 30, env, umbral))
        return self

    def _boca_en(self, t):
        for tramo in self.tramos_habla:
            if tramo[0] == 'ritmo':
                _, ini, fin, sem, sil = tramo
                if ini <= t < fin:
                    i = int((t - ini) * sil)
                    r = (i * 2654435761 + sem * 97) % 1000 / 1000
                    if (i % 4) == 3 and r < 0.35:
                        return None
                    fase = (t - ini) * sil - i
                    k = math.sin(math.pi * fase)
                    if k < 0.28:
                        return 'boca1' if r < 0.5 else None
                    return 'boca3' if r > 0.66 and k > 0.7 else 'boca2'
            else:
                _, ini, fin, env, umbral = tramo
                if ini <= t < fin:
                    v = float(env[int((t - ini) * 30)])
                    if v < umbral:
                        return None
                    return 'boca1' if v < 0.25 else ('boca2' if v < 0.6 else 'boca3')
        return None

    def _parpadea(self, t):
        if any(a <= t < a + 0.12 for a in self.parpadeos):
            return True
        if self.parpadeo_auto:
            per = self.parpadeo_auto
            # Intervalos irregulares, pero siempre los mismos para el mismo instante.
            i = int(t / per)
            r = ((i * 2654435761) % 997) / 997
            cae = i * per + (0.25 + r * 0.6) * per
            return cae <= t < cae + 0.11
        return False

    def nombre_expresion(self, t):
        partes = []
        for ini, fin, nombre in self.tramos_expresion:
            if ini <= t < fin:
                partes.append(nombre)
        if self._parpadea(t):
            partes.append('parpadeo')
        boca = self._boca_en(t)
        if boca:
            partes.append(boca)
        return '+'.join(partes) if partes else 'neutra'

    def textura(self, t):
        """(clave, RGBA, repetir_s, repetir_t, espejo_s, espejo_t, suave) para el banco de la escena."""
        nombre = self.nombre_expresion(t)
        if nombre not in self._rgba:
            rgb = self.cara.imagen(nombre)
            # Lo que sale de la cara se funde con la piel; así tapa bigotes y ojos nativos sin un borde duro.
            mezcla = rgb * self.halo[..., None] + self.cara.piel * (1 - self.halo[..., None])
            rgba = np.dstack([mezcla, self.alfa])
            self._rgba[nombre] = (np.clip(rgba, 0, 1) * 255).astype(np.uint8)
        return ((id(self), nombre), self._rgba[nombre], False, False, False, False, True)


def tenir_piel(textura, piel):
    """Lleva los téxeles de piel de una textura nativa al tono de la foto, conservando el sombreado."""
    t = np.asarray(textura, np.float32) / 255.0
    r, g, b = t[..., 0], t[..., 1], t[..., 2]
    es_piel = (g / np.maximum(r, 1e-3) < 0.85) & (r > g) & (g > b) & (b / np.maximum(r, 1e-3) > 0.48) & (b / np.maximum(r, 1e-3) < 0.86) & (r > 0.32)
    if not es_piel.any():
        return np.asarray(textura).copy()
    ref = float(np.percentile(r[es_piel], 75))
    k = np.clip(r / max(ref, 1e-3), 0.3, 1.15)[..., None]
    salida = t.copy()
    tenido = np.asarray(piel, np.float32) * k
    salida[..., :3] = np.where(es_piel[..., None], tenido, t[..., :3])
    return (np.clip(salida, 0, 1) * 255).astype(np.uint8)


def poner_cara(actor, cara, ajuste, gorra=True, pelo=None, hueso='face', aplanar=1.0):
    """Aplica una `CaraFoto` a un `Actor3D`. Devuelve la calca, con la que se animan boca y expresión.

    `ajuste` (de la cabeza en reposo, en unidades del modelo): `ojos` altura de los ojos, `barbilla`,
    `frente` hasta dónde llega la foto, `ancho` semiancho de la cara, `tope` zona que debe taparse.
    `gorra=False` redondea la parte alta de la cabeza y la pinta del color de `pelo` (o de piel si es calvo).
    `aplanar` (0..1) cambia el relieve nativo de la zona de la cara por una superficie lisa; 0 conserva la malla.
    """
    m = actor.modelo
    if hueso not in m.indice_objeto:
        raise ValueError('El modelo no tiene el objeto ' + hueso)
    base = actor.base
    i_obj = m.indice_objeto[hueso]
    en_cabeza = np.flatnonzero(base.obj == i_obj)
    if not len(en_cabeza):
        raise ValueError('La cabeza del modelo no tiene malla')
    ojos, barbilla, frente, ancho = ajuste['ojos'], ajuste['barbilla'], ajuste['frente'], ajuste['ancho']
    if not barbilla < ojos < frente or ancho <= 0:
        raise ValueError('Ajuste de cara incoherente: se espera barbilla < ojos < frente y ancho > 0')
    # El paquete se copia: la cabeza de este actor deja de compartir vértices con otros del mismo modelo.
    p = base.p.copy()
    n = base.n.copy()
    cab = p[en_cabeza]
    if aplanar:
        # El relieve nativo (nariz de Mario, barbilla de Wario) rompería una cara real: los vértices de la
        # zona de la cara pasan a una superficie lisa ajustada a la cabeza. Los bordes conservan la malla.
        xy = cab.reshape(-1, 3)
        yc, ry = (frente + barbilla) / 2, (frente - barbilla) * 0.62
        rx = ancho * ajuste.get('ancho_liso', 1.32)
        rho = np.hypot(xy[:, 0] / rx, (xy[:, 1] - yc) / ry)
        centro_z_cab = float(xy[:, 2].mean())
        zona = (rho < 1) & (xy[:, 2] > centro_z_cab)
        if zona.any():
            z_c = float(np.percentile(xy[zona, 2], ajuste.get('relieve', 55)))
            z_b = float(np.percentile(xy[zona, 2], 8))
            prof = max(z_c - z_b, 0.05)
            superficie = z_b + prof * np.sqrt(np.clip(1 - rho * rho, 0, 1))
            peso = np.clip((1 - rho) / 0.22, 0, 1) * zona * aplanar
            xy[:, 2] += (superficie - xy[:, 2]) * peso
            cab = xy.reshape(-1, 3, 3)
            p[en_cabeza] = cab
    if not gorra:
        _quitar_gorra(actor, p, n, en_cabeza, ajuste, cara, pelo)
        cab = p[en_cabeza]
    # La luz debe seguir a la superficie nueva, no al relieve antiguo (dibujaría la silueta del bigote).
    from .modelos_video_nds import _normales_suaves
    n[en_cabeza] = _normales_suaves(p[en_cabeza], base.obj[en_cabeza])
    base.p, base.n = p, n
    actor._memo = (None, None)
    actor._alto = None

    # Tono de la piel en las texturas nativas de la cabeza (orejas, nuca, cuello).
    mats = set(base.mat[en_cabeza].tolist())
    for i in mats:
        mat = m.materials[i]
        if mat.tex and mat.tex in m.texturas and 'eye' not in mat.tex.lower():
            m.texturas[mat.tex] = tenir_piel(m.texturas[mat.tex], cara.piel)

    _borrar_rasgos(m, base, p, en_cabeza, ajuste, cara.piel)

    # UV a la tarjeta: ojos y barbilla de la foto coinciden con los del modelo; el ancho, con la cabeza.
    centro_z = float(cab[..., 2].mean())
    delante = (cab[..., 2] > centro_z).any(1) & (cab[..., 2].mean(1) > centro_z - 0.25)
    sel = en_cabeza[delante]
    q = p[sel]
    esc_y = (BARBILLA_Y - OJOS_Y) / (ojos - barbilla)
    esc_x = (OJOS_D * 2.1 / 2) / ancho
    # Corrección cilíndrica suave: a los lados la foto no se estira tanto al girar.
    x = q[..., 0]
    u = 0.5 + np.arcsin(np.clip(x / (ancho * 1.8), -1, 1)) * (ancho * 1.8) * esc_x
    v = OJOS_Y - (q[..., 1] - ojos) * esc_y
    N = N_TARJETA
    uv = np.stack([u * N, v * N], -1).astype(np.float32)
    # Quita lo que cae entero fuera de la tarjeta.
    dentro = ((uv[..., 0] > 0).any(1) & (uv[..., 0] < N).any(1) & (uv[..., 1] > 0).any(1) & (uv[..., 1] < N).any(1))
    sel, uv = sel[dentro], uv[dentro]

    y, x = np.mgrid[0:N, 0:N].astype(np.float32) / N
    # Halo: dentro, foto; fuera, piel lisa. Alfa: toda la zona de la cara, cortada en la frente.
    halo = _elipse(N, 0.5, 0.53, 0.315 * ajuste.get('halo_x', 1.0), 0.42, 0.28)
    # La mandíbula se estrecha: el cuello y la ropa de la foto no deben asomar a los lados de la barbilla.
    mandibula = 0.315 * ajuste.get('halo_x', 1.0) * (1 - 0.42 * np.clip((y - OJOS_Y - 0.14) / 0.3, 0, 1))
    halo *= np.clip((mandibula - np.abs(x - 0.5)) / 0.05, 0, 1)
    # Lejos del centro solo cuenta lo que parece piel: fuera fondo, orejas, pelo o cuello quemado por el sol.
    neutra = cara.imagen('neutra')
    tono = neutra / np.maximum(neutra.sum(-1, keepdims=True), 1e-4)
    piel = np.asarray(cara.piel, np.float32)
    luz = neutra.mean(-1) / max(float(piel.mean()), 1e-4)
    parecido = np.clip(1.6 - np.linalg.norm(tono - piel / max(float(piel.sum()), 1e-4), axis=-1) / 0.05, 0, 1)
    parecido *= np.clip((luz - 0.45) / 0.15, 0, 1) * np.clip((1.45 - luz) / 0.15, 0, 1)
    halo = np.maximum(_elipse(N, 0.5, 0.5, 0.22, 0.3, 0.3), halo * gaussian_filter(parecido, 2.0))
    alfa = np.clip((ajuste.get('alfa_x', 1.3) - np.abs(u_a_modelo(x, ancho, esc_x))) / 0.12, 0, 1)
    tope_v = OJOS_Y - (frente - ojos) * esc_y
    alfa *= np.clip((y - tope_v) / 0.03, 0, 1)
    tope_inf = BARBILLA_Y + ajuste.get('bajo_barbilla', 0.05)
    alfa *= np.clip((tope_inf - y) / 0.025, 0, 1)
    borde = 2 / N
    alfa *= (x > borde) & (x < 1 - borde) & (y > borde) & (y < 1 - borde)
    calca = CalcaCara(cara, sel, uv, gaussian_filter(alfa, 1.0), gaussian_filter(halo, 2.0))
    actor.calcas.append(calca)
    return calca


def _borrar_rasgos(m, base, p, en_cabeza, ajuste, piel):
    """Pinta de piel los téxeles que usa la cara nativa (ojos, cejas, bigote): no deben asomar por el borde.

    Las UV reflejadas hacen que el mismo téxel sirva a los dos lados, así que se borra simétrico."""
    x_max, y1 = ajuste['ancho'] * ajuste.get('borrar_x', 1.15), ajuste['frente']
    color = (np.clip(np.asarray(piel, np.float32), 0, 1) * 255).astype(np.uint8)
    cab = p[en_cabeza]
    media_z = float(cab[..., 2].mean())
    cruza = cab[..., 1].max(1) >= y1
    for t in np.flatnonzero((np.abs(cab[..., 0]).max(1) < x_max) & (cab[..., 1].min(1) < y1)
                            & (cab[..., 2].mean(1) > media_z)):
        i = en_cabeza[t]
        mat = m.materials[base.mat[i]]
        if not mat.tex or mat.tex not in m.texturas:
            continue
        tex = m.texturas[mat.tex]
        if not tex.flags.writeable:
            tex = m.texturas[mat.tex] = tex.copy()
        h, w = tex.shape[:2]
        uv = base.uv[i]
        x0, y0t = np.floor(uv.min(0)).astype(int)
        x1, y1t = np.ceil(uv.max(0)).astype(int) + 1
        gy, gx = np.mgrid[y0t:y1t, x0:x1]
        a, b, c = uv
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-6:
            continue
        l0 = ((b[1] - c[1]) * (gx + .5 - c[0]) + (c[0] - b[0]) * (gy + .5 - c[1])) / den
        l1 = ((c[1] - a[1]) * (gx + .5 - c[0]) + (a[0] - c[0]) * (gy + .5 - c[1])) / den
        dentro = (l0 >= -0.05) & (l1 >= -0.05) & (1 - l0 - l1 >= -0.05)
        if not dentro.any():
            continue
        def plegar(v, n, rep, esp):
            if not rep:
                return np.clip(v, 0, n - 1)
            return np.where((v // n) % 2 == 1, n - 1 - v % n, v % n) if esp else v % n
        ux = plegar(gx[dentro], w, mat.rep_s, mat.flip_s)
        uy = plegar(gy[dentro], h, mat.rep_t, mat.flip_t)
        opaco = tex[uy, ux, 3] > 0
        if cruza[t] and 'eye' not in mat.tex.lower():
            # Comparte téxeles con la gorra: de estos solo se borra lo oscuro. El material de ojos se borra entero.
            opaco &= tex[uy, ux, :3].max(-1) < 90
        tex[uy[opaco], ux[opaco], :3] = color


def u_a_modelo(u, ancho, esc_x):
    """Distancia al centro de la cara, en semianchos, de una columna de la tarjeta."""
    return (u - 0.5) / esc_x / ancho


def _quitar_gorra(actor, p, n, en_cabeza, ajuste, cara, pelo):
    """Redondea la parte superior de la cabeza sobre un elipsoide y la pinta de pelo o piel."""
    m = actor.modelo
    base = actor.base
    frente = ajuste['frente']
    cab = p[en_cabeza]
    bajo = cab[cab[..., 1] < frente].reshape(-1, 3)
    if not len(bajo):
        return
    # La gorra no vale de referencia: el cráneo se calcula con la parte de la cara.
    cx, cz = 0.0, float(np.median(bajo[:, 2]))
    rx = max(float(np.abs(bajo[:, 0]).max()) * 0.92, ajuste['ancho'] * 1.1)
    rz = max(float((bajo[:, 2].max() - bajo[:, 2].min()) * 0.5), rx * 0.8)
    ry = (frente - ajuste['barbilla']) * ajuste.get('craneo', 0.78)
    c = np.array([cx, frente - ry * 0.12, cz], np.float32)
    r = np.array([rx, ry, rz], np.float32)
    v = cab.reshape(-1, 3)
    d = (v - c) / r
    largo = np.maximum(np.linalg.norm(d, axis=1), 1e-5)
    alto = v[:, 1] > frente - 0.02
    v[alto] = c + d[alto] / largo[alto, None] * r
    normal = (v - c) / (r * r)
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-5)
    p[en_cabeza] = v.reshape(-1, 3, 3)
    nc = n[en_cabeza].reshape(-1, 3)
    nc[alto] = normal[alto]
    n[en_cabeza] = nc.reshape(-1, 3, 3)
    # Material liso propio para esos triángulos: la textura lleva pintada la gorra.
    color = np.asarray(cara.piel if pelo is None else pelo, np.float32)
    if color.max() > 1:
        color = color / 255      # Se admite (r, g, b) en 0..255 o en 0..1.
    _repintar_gorra(m, base, en_cabeza[cab.reshape(-1, 3, 3)[..., 1].min(1) > frente], color)
    from types import SimpleNamespace
    nuevo = len(m.materials)
    m.materials.append(SimpleNamespace(name='__pelo', tex=None, pal=None, alpha=1, cull_front=False, cull_back=False,
                                       sx=1, sy=1, rep_s=False, rep_t=False, flip_s=False, flip_t=False,
                                       light_mask=5, diffuse=tuple(float(x) for x in color), diffuse_vtx=False))
    triangulos = alto.reshape(-1, 3).any(1)
    base.mat = base.mat.copy()
    base.mat[en_cabeza[triangulos]] = nuevo


def _repintar_gorra(m, base, gorra, color):
    """Cambia en la textura de la cabeza el color de la gorra: la visera baja de la frente y seguiría asomando."""
    for i_mat in set(base.mat[gorra].tolist()):
        mat = m.materials[i_mat]
        if not mat.tex or mat.tex not in m.texturas or 'eye' in mat.tex.lower():
            continue
        tex = m.texturas[mat.tex] = m.texturas[mat.tex].copy()
        h, w = tex.shape[:2]
        uv = base.uv[gorra[base.mat[gorra] == i_mat]].reshape(-1, 2)
        muestra = tex[np.clip(uv[:, 1].astype(int) % h, 0, h - 1), np.clip(uv[:, 0].astype(int) % w, 0, w - 1), :3].astype(np.float32)
        tono = lambda a: a / np.maximum(a.sum(-1, keepdims=True), 1)
        ref = np.median(tono(muestra), 0)
        rgb = tex[..., :3].astype(np.float32)
        igual = (np.linalg.norm(tono(rgb) - ref, axis=-1) < 0.09) & (rgb.max(-1) > 25)
        brillo = rgb[igual].max(-1, keepdims=True) / 255
        tex[igual, :3] = np.clip(color * 255 * (0.55 + 0.6 * brillo), 0, 255).astype(np.uint8)
