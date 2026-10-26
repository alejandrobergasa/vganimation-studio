"""Modelos, texturas y animaciones de Mario Kart DS listos para renderizar (usa tools/nsmb/nitro3d.py)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'nsmb'))
sys.path.insert(0, HERE)
import nitro3d as N
import mkrom

# código de dos letras de cada piloto en los nombres de fichero
PILOTOS = {'mario': 'MR', 'luigi': 'LG', 'peach': 'PC', 'yoshi': 'YS', 'wario': 'WR', 'donkey': 'DK',
           'koopa': 'KP', 'daisy': 'DS', 'waluigi': 'WL', 'robo': 'RB', 'karon': 'KA', 'kinopio': 'KO'}

# los karts están repartidos entre varios .carc (Main, A, B y Menu)
ARC_KARTS = ('data/KartModelMain.carc', 'data/KartModelMainA.carc', 'data/KartModelMainB.carc', 'data/KartModelMenu.carc')

_CACHE = {}


def _memo(k, f):
    if k not in _CACHE: _CACHE[k] = f()
    return _CACHE[k]


def nitro(carc, ruta):
    return _memo((carc, ruta), lambda: N.Nitro(mkrom.narc(carc)[ruta]))


class Conjunto:
    """Un modelo con su banco de texturas y sus animaciones."""
    def __init__(self, modelo, texturas, anims=None, parches=None, nombre=''):
        self.nombre = nombre
        self.nitro = modelo
        self.model = modelo.models[0]
        self.texlook = N.TexLookup(texturas, modelo) if texturas is not None else N.TexLookup(modelo)
        self.anims = anims or {}
        self.patterns = parches or {}


def piloto(nombre):
    """Piloto sentado (P_xx) con animaciones drive / win / lose / spin."""
    c = PILOTOS[nombre]; base = 'character/%s/P_%s' % (nombre, c)
    arc = 'data/KartModelSub.carc'
    anims = {}
    for a in ('drive', 'win', 'lose', 'spin'):
        n = nitro(arc, '%s_%s.nsbca' % (base, a))
        for an in n.anims: anims[a] = an
    return Conjunto(nitro(arc, base + '.nsbmd'), nitro(arc, base + '.nsbtx'), anims, nombre=nombre)


def piloto_menu(nombre):
    """Piloto del menú (P_xx de KartModelMenu) con la animación de victoria."""
    c = PILOTOS[nombre]; base = 'character/%s/P_%s' % (nombre, c)
    arc = 'data/KartModelMenu.carc'
    n = nitro(arc, base + '.nsbca') if (base + '.nsbca') in mkrom.narc(arc) else None
    return Conjunto(nitro(arc, base + '.nsbmd'), nitro(arc, base + '.nsbtx'), nombre=nombre)


def kart(nombre, tipo='b'):
    """Kart del piloto: a/b/c = tres karts de la clase del piloto (el de Mario también tiene 'a')."""
    c = PILOTOS[nombre]; base = 'kart/%s/kart_%s_%s' % (nombre, c, tipo)
    arc = next((a for a in ARC_KARTS if base + '.nsbmd' in mkrom.narc(a)), None)
    if arc is None: raise KeyError(base + '.nsbmd')
    return Conjunto(nitro(arc, base + '.nsbmd'), nitro(arc, base + '.nsbtx'), nombre='kart_%s_%s' % (nombre, tipo))


def rueda(tam='M'):
    base = 'kart/tire/kart_tire_%s' % tam
    arc = 'data/KartModelMain.carc'
    return Conjunto(nitro(arc, base + '.nsbmd'), nitro(arc, base + '.nsbtx'), nombre='rueda_' + tam)


def objeto(ruta, carc='data/MainRace.carc', tex=None):
    n = nitro(carc, ruta)
    t = nitro(carc, tex) if tex else None
    return Conjunto(n, t, nombre=os.path.basename(ruta))


def circuitos():
    """Circuitos disponibles: nombre -> (carc de geometría, carc de texturas)."""
    out = {}
    for f in mkrom.listdir('data/Course/'):
        b = os.path.basename(f)
        if b.endswith('Tex.carc'): continue
        n = b[:-5]
        if n + 'Tex.carc' in {os.path.basename(x) for x in mkrom.listdir('data/Course/')}:
            out[n] = (f, f[:-5] + 'Tex.carc')
    return out


class Circuito:
    def __init__(self, nombre):
        geo, tex = circuitos()[nombre]
        self.nombre = nombre
        self.geo, self.tex = mkrom.narc(geo), mkrom.narc(tex)
        self.modelo = N.Nitro(self.geo['course_model.nsbmd'])
        # algunos circuitos llevan las texturas dentro del propio NSBMD
        self.texturas = N.Nitro(self.tex['course_model.nsbtx']) if 'course_model.nsbtx' in self.tex else None
        self.anim_tex = None
        self.cielo = None
        if 'course_model_V.nsbmd' in self.geo:
            self.cielo = N.Nitro(self.geo['course_model_V.nsbmd'])
            self.cielo_tex = N.Nitro(self.tex['course_model_V.nsbtx']) if 'course_model_V.nsbtx' in self.tex else None
        self.objetos = {os.path.basename(k)[:-6]: k for k in self.geo if k.startswith('MapObj/') and k.endswith('.nsbmd')}
        self.nkm = self.geo.get('course_map.nkm')
        self.kcl = self.geo.get('course_collision.kcl')

    def conjunto(self):
        return Conjunto(self.modelo, self.texturas, nombre=self.nombre)

    def conjunto_cielo(self):
        if self.cielo is None: return None
        return Conjunto(self.cielo, self.cielo_tex, nombre=self.nombre + '_cielo')

    def objeto(self, nombre):
        k = self.objetos[nombre]
        n = N.Nitro(self.geo[k])
        tex = [n]
        return Conjunto(n, None, nombre=nombre)
