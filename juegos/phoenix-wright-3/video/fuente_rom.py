"""Fuente de texto de Phoenix Wright 3 reconstruida con los píxeles de la propia ROM.

La ROM no trae la fuente de diálogo en un formato legible (no hay NFTR), pero sí las descripciones del
Expediente ya dibujadas con ella: tiras 256x64 en blanco, 3 líneas con paso de 14 px y línea base en la fila 11.
Se segmentan los glifos por columnas vacías, se agrupan los idénticos y se nombran con `glifos_fuente.json`
(hash de la forma -> carácter; ese fichero no contiene píxeles). El atlas resultante se guarda en la
carpeta de extraídos y se regenera solo. Cada glifo lleva su avance medido en la ROM (casi siempre ancho + 2 px).
`¡` no aparece en la ROM: se obtiene girando 180° el `!` de la propia fuente.
"""
import hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image

TIRAS = range(1743, 1951)        # descripciones en español (índices de Recursos.graficos_phoenix)
BASE, PASO, ENTRE = 11, 14, 2
AQUI = Path(__file__).resolve().parent


def _segmentos(columnas):
    xs = np.where(columnas)[0]
    if not len(xs):
        return []
    segs, s, p = [], xs[0], xs[0]
    for x in xs[1:]:
        if x - p > 1:
            segs.append((s, p)); s = x
        p = x
    segs.append((s, p))
    return segs


def construir_atlas(recursos):
    """{carácter: {top, filas, avance}} + '_espacio' (px extra de un espacio entre palabras)."""
    etiquetas = json.loads((AQUI / 'glifos_fuente.json').read_text(encoding='utf-8'))
    graficos = recursos.graficos_phoenix()
    atlas, lineas = {}, []
    for i in TIRAS:
        im = np.array(graficos[i][1])
        if im.shape[:2] != (64, 256):
            continue
        A = im[..., 3] > 0
        for k in range(4):
            sub = A[PASO * k + 1:PASO * k + 15]
            linea = []
            for a, b in _segmentos(sub.any(0)):
                bm = sub[:, a:b + 1]
                filas = np.where(bm.any(1))[0]
                t = bm[filas[0]:filas[-1] + 1]
                h = hashlib.sha1(repr((t.shape, np.packbits(t).tobytes())).encode()).hexdigest()[:12]
                c = etiquetas[h]['c'] if h in etiquetas else None
                if c and c not in atlas:
                    atlas[c] = {'top': etiquetas[h]['top'], 'filas': [''.join('#' if x else '.' for x in f) for f in t]}
                linea.append((c, int(a), int(b)))
            lineas.append(linea)
    # avance de cada glifo = distancia entre inicios de glifos consecutivos de la misma palabra
    medidas = {}
    for linea in lineas:
        for (c, a, b), (c2, a2, b2) in zip(linea, linea[1:]):
            if c and a2 - b - 1 <= 3:
                medidas.setdefault(c, []).append(a2 - a)
    for c, g in atlas.items():
        v = medidas.get(c)
        g['avance'] = max(set(v), key=v.count) if v else len(g['filas'][0]) + ENTRE
    espacios = []
    for linea in lineas:
        for (c, a, b), (c2, a2, b2) in zip(linea, linea[1:]):
            if c and a2 - b - 1 > 3:
                espacios.append(a2 - a - atlas[c]['avance'])
    atlas['_espacio'] = max(set(espacios), key=espacios.count)
    return atlas


class FuenteRom:
    """Mismo uso que Fuente.texto de los motores: devuelve una imagen RGBA con el texto."""
    def __init__(self, recursos, cache=None):
        from valedores import rutas
        cache = Path(cache or rutas.extraidos('phoenix-wright-3')) / 'fuente_atlas.json'
        if cache.is_file():
            atlas = json.loads(cache.read_text(encoding='utf-8'))
        else:
            atlas = construir_atlas(recursos)
            cache.write_text(json.dumps(atlas, ensure_ascii=False), encoding='utf-8')
        self.espacio = atlas.pop('_espacio')
        self.glifos = {}
        for c, g in atlas.items():
            m = np.array([[x == '#' for x in f] for f in g['filas']])
            self.glifos[c] = (m, g['top'], g['avance'])
        if '!' in self.glifos:
            m, top, av = self.glifos['!']
            # ¡ ocupa las mismas filas que ¿ (desciende bajo la línea base)
            self.glifos['¡'] = (m[::-1, ::-1], self.glifos['¿'][1] if '¿' in self.glifos else top, av)
        for c in ("'", '’'):
            self.glifos[c] = self.glifos['´']

    def tiene(self, c):
        return c == ' ' or c in self.glifos

    def _fila(self, linea):
        piezas, x, ultimo = [], 0, 0
        for c in linea.replace('…', '...').replace('“', '"').replace('”', '"'):
            if c == ' ':
                x += self.espacio
                continue
            if c == '"':       # dos comillas ´ seguidas: la 2.ª con avance 4 (medido en la ROM)
                m, top, _ = self.glifos['´']
                piezas += [(m, top, x), (m, top, x + 3)]
                x += 7
                ultimo = x - 4 + m.shape[1]
                continue
            if c not in self.glifos or self.glifos[c] is None:
                raise ValueError('La fuente del juego no contiene el carácter %r' % c)
            m, top, avance = self.glifos[c]
            piezas.append((m, top, x))
            x += avance
            ultimo = x - avance + m.shape[1]
        return piezas, ultimo

    def ancho(self, texto):
        return max(self._fila(l)[1] for l in texto.split('\n'))

    def texto(self, texto, escala=1, color='white', ancho=None, interlineado=PASO):
        from PIL import ImageColor
        rgb = ImageColor.getrgb(color)[:3] if isinstance(color, str) else tuple(color)[:3]
        lineas = texto.split('\n')
        filas = [self._fila(l) for l in lineas]
        W = max(1, max(w for _, w in filas))
        if ancho is not None and W * escala > ancho:
            raise ValueError('El texto excede el ancho; divide la frase en líneas')
        H = interlineado * (len(lineas) - 1) + 16
        salida = np.zeros((H, W, 4), np.uint8)
        for n, (piezas, _) in enumerate(filas):
            for m, top, x in piezas:
                y = n * interlineado + BASE + top
                sub = salida[y:y + m.shape[0], x:x + m.shape[1]]
                sub[m] = (*rgb, 255)
        im = Image.fromarray(salida, 'RGBA')
        return im.resize((max(1, round(W * escala)), max(1, round(H * escala))), Image.Resampling.NEAREST)
