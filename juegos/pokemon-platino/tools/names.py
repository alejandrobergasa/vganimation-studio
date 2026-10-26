# Tablas de nombres auxiliares para la extracción.

# ---- pl_otherpoke: (nombre, vista, [(variante, indice_paleta)]) por cada gráfico (orden espalda, frente)
_FORMS = [  # (nombre_base, formas, paletas, orden_graficos)
    # paletas: 'shared' = un par normal/shiny para todas; 'pairs' = n,s por forma;
    #          'grouped' = todas las normales y luego todas las shiny; 'egg' = una por forma
    # orden_graficos: 'pairs' = espalda,frente por forma; 'bf' = todas las espaldas y luego los frentes
    ('386_deoxys', ['normal', 'ataque', 'defensa', 'velocidad'], 'shared', 'pairs'),
    ('201_unown', [chr(c) for c in range(ord('a'), ord('z') + 1)] + ['exclamacion', 'interrogacion'], 'shared', 'pairs'),
    ('351_castform', ['normal', 'sol', 'lluvia', 'nieve'], 'grouped', 'bf'),
    ('412_burmy', ['planta', 'arena', 'basura'], 'pairs', 'pairs'),
    ('413_wormadam', ['planta', 'arena', 'basura'], 'pairs', 'pairs'),
    ('422_shellos', ['oeste', 'este'], 'pairs', 'bf'),
    ('423_gastrodon', ['oeste', 'este'], 'pairs', 'bf'),
    ('421_cherrim', ['encapotado', 'soleado'], 'grouped', 'bf'),
    ('493_arceus', ['normal', 'lucha', 'volador', 'veneno', 'tierra', 'roca', 'bicho', 'fantasma', 'acero',
                    'misterio', 'fuego', 'agua', 'planta', 'electrico', 'psiquico', 'hielo', 'dragon', 'siniestro'], 'pairs', 'pairs'),
    ('000_huevo', ['normal', 'manaphy'], 'egg', 'front'),
    ('492_shaymin', ['tierra', 'cielo'], 'pairs', 'pairs'),
    ('479_rotom', ['normal', 'calor', 'lavado', 'frio', 'ventilador', 'corte'], 'pairs', 'pairs'),
    ('487_giratina', ['modificada', 'origen'], 'pairs', 'pairs'),
    ('extra', ['154_155'], 'pairs', 'pairs'),
]


def _build():
    out = {}
    g = 0
    p = 0
    for base, forms, pal_mode, layout in _FORMS:
        n = len(forms)
        for fi, form in enumerate(forms):
            if pal_mode == 'shared':
                pals = [('normal', p), ('shiny', p + 1)]
            elif pal_mode == 'pairs':
                pals = [('normal', p + fi * 2), ('shiny', p + fi * 2 + 1)]
            elif pal_mode == 'grouped':
                pals = [('normal', p + fi), ('shiny', p + n + fi)]
            else:
                pals = [('normal', p + fi)]
            name = '%s_%s' % (base, form)
            if layout == 'front':
                out[g + fi] = (name, 'frente', pals)
            elif layout == 'bf':
                out[g + fi] = (name, 'espalda', pals)
                out[g + n + fi] = (name, 'frente', pals)
            else:
                out[g + fi * 2] = (name, 'espalda', pals)
                out[g + fi * 2 + 1] = (name, 'frente', pals)
        g += n if layout == 'front' else 2 * n
        p += 2 if pal_mode == 'shared' else n if pal_mode == 'egg' else 2 * n
    # 156: sombras de combate (usa la última paleta)
    out[g] = ('sombras_combate', 'frente', [('normal', p - 2)])
    return out


OTHERPOKE = _build()

ICON_FORMS = (['000_huevo', '000_huevo_manaphy', '386_deoxys_ataque', '386_deoxys_defensa', '386_deoxys_velocidad']
              + ['201_unown_' + c for c in [chr(x) for x in range(ord('a'), ord('z') + 1)] + ['exclamacion', 'interrogacion']]
              + ['412_burmy_arena', '412_burmy_basura', '413_wormadam_arena', '413_wormadam_basura',
                 '422_shellos_este', '423_gastrodon_este', '487_giratina_origen', '492_shaymin_cielo',
                 '479_rotom_calor', '479_rotom_lavado', '479_rotom_frio', '479_rotom_ventilador', '479_rotom_corte'])
MMODEL_HINTS = {  # según pokemon_platinum_assets.md
    90: 'heroe_andar_correr', 91: 'heroina_andar_correr', 92: 'heroe_bici', 93: 'heroina_bici',
    155: 'heroe_sacar_pokeball', 156: 'heroina_sacar_pokeball', 157: 'heroe_regar', 158: 'heroina_regar',
    159: 'heroe_surf', 160: 'heroina_surf', 164: 'heroe_traje', 165: 'heroina_vestido',
    166: 'heroe_pescar', 167: 'heroina_pescar', 363: 'heroe_poketch', 364: 'heroina_poketch',
    365: 'heroe_guardar', 366: 'heroina_guardar', 367: 'heroe_centro_pokemon', 368: 'heroina_centro_pokemon',
    415: 'heroe_buscapelea', 416: 'heroina_buscapelea',
}
NARC_INFO = {}
