"""Catálogo de tiles de suelo y objetos del mapa, construidos a partir de las texturas del juego.

Para añadir uno nuevo: busca la textura en sprites_extraidos/tilesets_mapa/ y añade una entrada.
- SUELOS: texturas que se repiten por todo el mapa según la posición del tile (pueden ser de 16x16,
  32x32, 64x64…). 'frames' = lista de PNG para animarlo; 'sobre' = se dibuja encima de otro suelo.
- OBJETOS: sprites colocados en el mapa y ordenados por profundidad (la Y de su base).
  'piezas' = lista de (png, recorte, desplazamiento) respecto al tile donde se coloca.
"""
from .recursos import imagen, recolorear_cian

T0 = 'tilesets_mapa/terreno/set_000/'
AN = 'tilesets_mapa/animados/'

SUELOS = {
    'cesped':       {'frames': [T0 + 'ngrass.png'], 'cian_a_verde': True},
    'cesped_claro': {'frames': [T0 + 'lgreen.png'], 'cian_a_verde': True},
    'baldosas':     {'frames': [T0 + 'flagstone.png']},
    'acera':        {'frames': [T0 + 'hodou.png'], 'recorte': (0, 0, 16, 32)},
    'arena':        {'frames': [T0 + 'nsand.png']},
    'tierra':       {'frames': [T0 + 'brown.png']},
    'agua':         {'frames': [AN + '01/sea_%d.png' % i for i in range(1, 9)], 'velocidad': 6},
    'flores_rojas': {'frames': [AN + '02/rhana_%d.png' % i for i in range(1, 5)], 'velocidad': 8, 'cian_a_verde': True},
    # flores con fondo transparente: se ponen encima del césped
    'flores_azules':   {'frames': [AN + '06/t3_fl_b_%d.png' % i for i in range(1, 5)], 'velocidad': 8, 'sobre': 'cesped'},
    'flores_moradas':  {'frames': [AN + '07/t3_fl_p_%d.png' % i for i in range(1, 5)], 'velocidad': 8, 'sobre': 'cesped'},
    'flores_rosas':    {'frames': [AN + '08/t3_fl_r_%d.png' % i for i in range(1, 5)], 'velocidad': 8, 'sobre': 'cesped'},
    'flores_amarillas': {'frames': [AN + '09/t3_fl_y_%d.png' % i for i in range(1, 5)], 'velocidad': 8, 'sobre': 'cesped'},
}

OBJETOS = {
    # árbol: copa oscura sobre tronco (ocupa 2x2 tiles, base en la fila inferior)
    'arbol': {'piezas': [(T0 + 'conttree_b.png', (0, 32, 32, 64), (0, -16)),
                         (T0 + 'conttree_b.png', (0, 0, 32, 32), (0, -40))],
              'solido': [(0, 0), (1, 0)]},
    'arbol_redondo': {'piezas': [(T0 + 'tree01.png', (32, 0, 64, 32), (0, -16)),
                                 (T0 + 'tree01.png', (32, 32, 64, 64), (0, -40))],
                      'solido': [(0, 0), (1, 0)]},
    'arbusto':  {'piezas': [(T0 + 'conttree_t.png', (0, 0, 32, 32), (-8, -16))], 'solido': [(0, 0)]},
    'arbusto_grande': {'piezas': [(T0 + 'conttree_t.png', (0, 32, 32, 64), (0, -16))], 'solido': [(0, 0), (1, 0)]},
    'valla':    {'piezas': [(T0 + 'imped.png', (0, 0, 16, 16), (0, -4))], 'solido': [(0, 0)]},
    'roca':     {'piezas': [(T0 + 'imped.png', (0, 32, 32, 64), (0, -16))], 'solido': [(0, 0), (1, 0)]},
    'piedra':   {'piezas': [(T0 + 'imped.png', (32, 48, 48, 64), (0, 0))], 'solido': [(0, 0)]},
    'maceta':   {'piezas': [(T0 + 'imped.png', (32, 32, 48, 48), (0, 0))], 'solido': [(0, 0)]},
}


_cache = {}


def frames_suelo(nombre):
    if nombre not in _cache:
        d = SUELOS[nombre]
        fr = []
        for f in d['frames']:
            im = imagen(f)
            if 'recorte' in d:
                im = im.crop(d['recorte'])
            if d.get('cian_a_verde'):
                im = recolorear_cian(im)
            fr.append(im)
        _cache[nombre] = fr
    return _cache[nombre]


def piezas_objeto(nombre):
    key = ('obj', nombre)
    if key not in _cache:
        _cache[key] = [(imagen(f).crop(rc), off) for f, rc, off in OBJETOS[nombre]['piezas']]
    return _cache[key]
