"""Textos de REWINDLIMBO2 sincronizados con las voces del vídeo original (segundos absolutos del vídeo).

Parte 1 (0:00-5:30): transcripción de Descript (buzon/analisis_parte_1/transcripcion_automatica.srt), con
los segmentos partidos unidos y quien habla. Parte 2 (5:30-10:18): buzon/analisis_parte_2/assets/dialogos.json
(Whisper alineado). Lo dudoso va con «…» (la fuente del juego no tiene corchetes ni paréntesis).
"""

# (inicio, fin, quien, texto). quien = None: monólogo de EL MARÍA (sin nombre delante).
PARTE1 = [
    (70.26, 71.78, None, 'Esto es una puta vergüenza.'),
    (72.40, 75.56, None, 'En Logroño, Wu-Tang ha vuelto a decorar la ciudad.'),
    (76.18, 78.18, None, 'Esto es una puta vergüenza en Logroño.'),
    (78.42, 83.04, None, 'Esta vez han pintado las traseras de un pabellón aquí, jodiendo toda la pared.'),
    (83.40, 86.74, None, 'Hostias, está decorando todo Logroño, me cago en la hostia.'),
    (87.10, 88.86, None, 'Joder, compartir, compartir.'),
    (88.92, 90.60, None, 'Esto es una puta vergüenza.'),
    (91.02, 91.82, None, 'Me cago en Dios.'),
    (92.40, 93.66, None, '¿Quién tiene la culpa de esto, eh?'),
    (93.96, 95.08, None, '¿Quién tiene la culpa de esto?'),
    (95.14, 96.50, None, 'Me cago en Dios.'),
    (96.98, 97.72, None, 'Ahí vamos, claro.'),
    (97.98, 99.30, None, 'Primo, estoy perdidísimo.'),
    (99.34, 101.38, None, 'A ver si aquí hay algún primo que sepa.'),
    (104.14, 105.02, None, '¿Hay alguien ahí?'),
    (105.02, 107.98, None, '¿Me pueden ayudar a encontrar el proyecto?'),
    (110.71, 113.35, None, 'Me cago en Dios, aquí no trabaja ni su puta madre.'),
    (113.99, 116.43, None, 'Si no está en coca, a la gente ya no le interesa.'),
    (117.55, 119.87, None, 'Esta búsqueda es demasiado dura para mí.'),
    (126.48, 129.24, None, 'En El planeta de los simios seguir el mapa era más fácil.'),
    (129.42, 131.20, None, '¿Qué cojones es esta puta mierda?'),
    (132.00, 136.10, None, 'Tanta hostia para nada más que un billete de veinte de Panini no vale la pena.'),
    (136.54, 139.26, None, 'Estoy hasta la polla, primo, que le follen al proyecto.'),
    (139.72, 146.50, None, 'Luego para que encima me esté dando el coñazo de que lo ha financiado, pues me cago '
                           'en mi putísima madre, ¿por qué esto?'),
    (146.50, 147.10, None, 'Espera.'),
    (147.24, 149.98, None, 'No, no puedo rendirme, ya sé qué hacer.'),
    (154.56, 156.74, None, 'Sí, estoy preparado para el reto.'),
    (157.88, 162.82, None, 'Por gusto no llevo semanas tomando litronas de cafeína para entrenarme para este '
                           'momento.'),
    (177.87, 179.49, None, 'Uno de estos hará la función.'),
    (211.59, 213.09, None, 'Lo tengo, tiene que ser aquí.'),
    (213.43, 215.19, None, 'Voy a rentarme este proyecto.'),
    (215.47, 220.27, None, 'Malditos valedores que no confiaron, pues mirad dónde estoy ahora, hijos de puta.'),
    (220.97, 226.71, None, 'Nunca subestimes la capacidad de un autónomo para sacarse las castañas del fuego '
                           'bajo presión.'),
    (227.27, 230.95, None, 'Esta se la dedico al hijoputa de Kill Joker y a su puto perro Batman.'),
    (231.25, 232.69, None, 'Han acabado con el clan.'),
    (233.25, 235.87, None, 'Pero gracias a esto voy a devolverlo a su prime.'),
    (237.67, 238.51, None, 'El proyecto.'),
    (239.89, 240.95, None, 'Al fin eres mío.'),
    (241.61, 243.49, 'VALEDORES', 'Por favor, no abras esa caja.'),
    (243.53, 246.07, 'EL MARÍA', 'Pero qué cojones, Valedores, eres tú.'),
    (246.33, 249.29, 'EL MARÍA', '¿Tú tienes idea de lo que me ha costado llegar hasta aquí?'),
    (249.49, 252.67, 'EL MARÍA', 'Llevo más tiempo con esto que con lo del gimnasio, hijo de puta.'),
    (252.73, 257.50, 'VALEDORES', 'No lo entiendes. El contenido de esa caja es demasiado peligroso. Mira cómo '
                                  'termina…'),
    (257.50, 258.23, 'EL MARÍA', 'Primo, cállate.'),
    (258.27, 261.23, 'EL MARÍA', 'Voy a hacer lo que quiera con esta caja, te parezca bien o no.'),
    (261.25, 262.89, 'VALEDORES', 'Deja la caja donde estaba.'),
    (262.93, 264.83, 'VALEDORES', 'Vas a matarnos a todos, María.'),
    (264.91, 267.25, 'EL MARÍA', 'Ya te maté una vez y puedo hacerlo de nuevo.'),
    (271.83, 272.63, 'VALEDORES', 'No, por favor.'),
    (273.15, 274.25, 'VALEDORES', 'Por favor, basta.'),
    (274.89, 276.13, 'VALEDORES', 'Déjame ir, por favor.'),
    (279.67, 281.07, 'EL MARÍA', 'A cascarla, Valedores.'),
    (285.03, 288.01, 'EL MARÍA', 'Bastante estropeado estabas ya de todos modos.'),
    (289.57, 292.61, 'VOZ', 'Esta canción se llama No voy al Baige.'),
    (294.55, 301.59, 'NARRADOR', 'Desde que el Rewind desapareció en la gala del año 2024, los valedores habían '
                                 'perdido la esperanza por completo.'),
    (302.17, 308.51, 'NARRADOR', 'Pero el María encontró algo: un Rewind que no era ni de un año ni de otro, '
                                 'un Rewind limbo.'),
    (315.19, 320.19, 'NARRADOR', 'Ha llovido mucho desde el último Rewind y las cosas por Logroño están muy '
                                 'diferentes.'),
    (320.77, 330.00, 'NARRADOR', 'Valedores muy casados, valedores con trabajo, … y mucho menos son factores '
                                 'que han terminado con los valores clásicos de los valedores.'),
]

NOMBRES = {'CHIQUITIN': 'CHIQUITÍN', 'MANDARIN': 'MANDARÍN', 'EL MARIA': 'EL MARÍA', 'CHINI / PANINI': 'CHINI',
           'TRABAJADOR': 'OBRERO'}

# Parte 2 tal cual sale de dialogos.json: (inicio, fin, quien, texto)
PARTE2_BRUTO = [
    (330.00, 333.10, 'NARRADOR', 'La segunda venida del María a la tierra prometida de Logroño'),
    (333.10, 337.32, 'NARRADOR', 'aseguraba que […] las cosas, pero lo cierto es que solo han empeorado.'),
    (338.00, 340.58, 'NARRADOR', 'Solo había algo que podía salvar a los valedores.'),
    (341.32, 345.34, 'NARRADOR', 'Chini, el hijo pródigo de los valedores, estaba a punto de volver a Logroño'),
    (345.34, 348.10, 'NARRADOR', 'durante un fin de semana […] de visita anual.'),
    (348.56, 352.76, 'NARRADOR', 'Y en el grupo se estaba cocinando una gala de valedores que lo cambiaría todo.'),
    (353.50, 357.34, 'NARRADOR', 'Lo que los valedores no sabían era que ese cambio iba a acabar con ellos.'),
    (365.82, 370.22, 'POPS', 'A ver, ¿cuándo y dónde vamos a hacer la gala de valedores este año?'),
    (370.26, 371.86, 'CHIQUITIN', 'Toca improvisar modo esquimal.'),
    (372.32, 374.02, 'VIVI', 'Modo esquimal activado, primo.'),
    (374.38, 376.32, 'VIVI', 'Esto es una rentada de manual.'),
    (376.80, 377.96, 'VIVI', '¿No te atreves o qué?'),
    (377.96, 378.78, 'POPS', 'De manual, bro.'),
    (379.30, 380.92, 'POPS', 'Na que se vienen hostias polares.'),
    (381.24, 381.98, 'MANDARIN', 'No sé, bro.'),
    (382.34, 384.16, 'MANDARIN', 'Parece que se vienen hostias nivel Frozen.'),
    (384.26, 387.02, 'EL MARIA', 'Primos, nos vamos a morir congelados en esa gala.'),
    (387.02, 391.28, 'EL MARIA', '[…] me apunto igual. Total, que sea lo que Dios quiera.'),
    (391.28, 393.92, 'CHINI', 'Vamo a poner fecha ya que esto no aguanta más.'),
    (394.48, 396.44, 'CHINI / PANINI', '20 de enero? Va peña.'),
    (396.44, 398.48, 'CHIQUITIN', '20 de enero suena bien, primo.'),
    (398.48, 400.40, 'PANINI', 'Vava 20 de enero entonces.'),
    (400.40, 402.12, 'VIVI', 'Uuuuuuuuuu papá. Y el Gorgi qué,'),
    (402.12, 406.12, 'VIVI', 'viene con tabla de surf polar o qué. Para cuando diga me renta'),
    (406.12, 407.84, 'VIVI', 'ya estamos congelados.'),
    (407.84, 410.10, 'VIVI', 'No te enfríes mucho primo que luego'),
    (410.10, 411.60, 'VIVI', 'ni los radares te pillan.'),
    (411.60, 414.40, 'FRANKY', 'Te llevo de pasajero en mi tabla polar.'),
    (414.40, 416.00, 'FRANKY', 'Eso sí, agárrate bien.'),
    (416.00, 421.24, 'VIVI', 'Agarrarme dice. Primo si me subo a esa tabla no llegamos ni al puerto.'),
    (422.52, 424.54, 'ORDENADOR', '¿Te has quedado sin tokens? Suscríbete.'),
    (424.88, 427.08, 'VOZ', '[Frase no inteligible]'),
    (427.08, 429.40, 'VOZ', 'La puta IA, primo, no me deja cocinar.'),
    (429.92, 432.36, 'VOZ', 'Bueno, a ver si […] Fortnite.'),
    (434.06, 437.08, 'VOZ', 'Otro día que te metes a los Pilares en lugar de currar el […].'),
    (437.28, 439.38, 'VOZ', 'Primo, mañana le meto duro a la obra.'),
    (439.46, 442.50, 'VOZ', 'Ese gimnasio parece que en lugar de avanzar retrocede.'),
    (442.96, 444.04, 'VOZ', 'Mañana todo empezará.'),
    (444.04, 446.00, 'VOZ', 'Todo empezará por fin.'),
    (467.30, 469.96, 'SANTOS', 'Muy bien, muy bien. Seguid currando.'),
    (469.96, 475.04, 'SANTOS', 'Dejad el gorila en la puerta, quiero que sea lo primero que vea la gente al entrar.'),
    (475.04, 477.30, 'TRABAJADOR', 'Señor […], ¿no cree que ya podamos tomar un descanso…?'),
    (477.30, 478.90, 'SANTOS', 'Seguid currando, he dicho.'),
    (478.90, 482.58, 'SANTOS', 'Estos primos apenas han currado y ya quieren descansar.'),
    (482.58, 486.20, 'SANTOS', 'Cómo se nota que no habéis hecho el curso de […].'),
    (486.66, 488.32, 'SANTOS', 'Siempre fuiste la cabra del trabajo.'),
    (491.54, 495.76, 'SANTOS', 'No me jodas, no. Recogedlo todo rápido, joder.'),
    (496.56, 498.88, 'INSPECTOR', '¿Dónde tienes los baños de minusválidos?'),
    (498.98, 501.44, 'SANTOS', '¡Qué sorpresa, […]! No le esperaba hoy.'),
    (501.48, 503.80, 'INSPECTOR', '¿Dónde tienes los baños de minusválidos?'),
    (503.84, 507.96, 'SANTOS', 'Todo está en orden con la licencia de obra y esas movidas, ya sabes, mira.'),
    (508.00, 510.30, 'INSPECTOR', '¿Dónde tienes los baños de minusválidos?'),
    (510.32, 511.76, 'SANTOS', 'Está bien, está bien, sígueme.'),
    (515.38, 520.16, 'INSPECTOR', 'El techo cumple con la normativa de ignifugado vigente. Muy bien, muy bien.'),
    (520.30, 522.26, 'SANTOS', '¿De verdad hacía falta quemar el techo?'),
    (522.26, 524.52, 'INSPECTOR', '¿Dónde tienes los baños de minusválidos?'),
    (524.76, 525.44, 'SANTOS', '[…] ya te llevo.'),
    (526.92, 529.32, 'SANTOS', 'Bueno, pues aquí están los…'),
    (532.68, 536.42, 'INSPECTOR', 'El tamaño de este baño […] cumple con la normativa vigente.'),
    (536.74, 538.72, 'SANTOS', 'Espera un momento, lo podemos arreglar.'),
    (538.84, 541.72, 'INSPECTOR', 'El maletín está en el sofá gorila de la entrada.'),
    (541.82, 542.34, 'SANTOS', 'Espera.'),
    (542.38, 543.48, 'SANTOS', 'Ya sabes qué hacer.'),
    (543.48, 545.92, 'SANTOS', 'Necesito que esta vez hagas la vista gorda.'),
    (546.06, 548.88, 'INSPECTOR', 'El maletín está en el sofá gorila de la entrada.'),
    (549.14, 552.76, 'SANTOS', '[…], sabes que lo estoy dando todo por abrir este gimnasio.'),
    (554.22, 555.80, 'INSPECTOR', '¿Qué es eso que está sonando?'),
    (555.90, 558.80, 'SANTOS', 'Te lo debes estar imaginando, yo no escucho nada.'),
    (558.98, 560.36, 'INSPECTOR', '¿Dónde los escondes, Santos?'),
    (560.46, 561.30, 'SANTOS', '¿Esconder el qué?'),
    (561.50, 562.10, 'INSPECTOR', '¿Bajo el suelo?'),
    (562.18, 563.46, 'SANTOS', 'No sé de qué me estás hablando.'),
    (563.46, 564.22, 'INSPECTOR', '¿Debajo del ring?'),
    (564.22, 566.66, 'SANTOS', '[…], de verdad, te lo prometo que no sé de lo…'),
    (566.66, 567.56, 'INSPECTOR', 'Ya os tengo.'),
    (568.72, 570.48, 'GRUPO', '[…], es de mis favoritas.'),
    (570.82, 572.44, 'GRUPO', 'Un corrido de putísima madre.'),
    (572.44, 573.72, 'GRUPO', '[…] corrido, sí.'),
    (573.78, 576.12, 'GRUPO', 'Mira qué abrigo me compré […]'),
    (576.50, 577.02, 'INSPECTOR', 'Disculpa.'),
    (577.44, 581.40, 'INSPECTOR', 'Pensé que tenías a un grupo de fontaneros mexicanos escondidos.'),
    (581.44, 583.74, 'SANTOS', '¿Cómo puedes pensar eso de mí, […]?'),
    (583.96, 584.48, 'INSPECTOR', 'Me marcho.'),
    (584.68, 587.60, 'INSPECTOR', 'El maletín está en el sofá gorila de la entrada.'),
    (589.38, 591.72, 'SANTOS', 'Ya pueden salir los mexicanos.'),
    (593.24, 595.06, 'SANTOS', 'Primos, casi se me lía que flipas,'),
    (595.24, 598.62, 'SANTOS', 'y encima ahora le tengo que soplar 2.000 pavos a […]'),
    (598.62, 601.42, 'SANTOS', 'para que no me denuncie por lo del baño de minusválidos.'),
    (601.42, 602.98, 'GRUPO', '[Frase parcialmente ininteligible]'),
    (603.02, 604.98, 'SANTOS', 'Valedores, necesito vuestra ayuda.'),
    (605.12, 606.74, 'GRUPO', 'No podemos ayudarte, Santos.'),
    (607.32, 610.06, 'SANTOS', '¿Cómo cojones vamos a conseguir dos mil pavos?'),
    (610.14, 612.80, 'GRUPO', 'No sé, primo, montad un side hustle (?) o algo.'),
    (613.58, 614.50, 'GRUPO', 'Un side hustle (?).'),
]

# Los mensajes del grupo (365-422 s) salen como chat en pantalla, no como ventana de diálogo.
CHAT = (365.0, 422.0)
TIPO_NARRADOR = 17     # marco de mensaje del narrador (distinto del de los personajes)


def _limpiar(t):
    for a, b in (('[Frase no inteligible]', '…'), ('[Frase parcialmente ininteligible]', '…'), ('[…]', '…'),
                 (' (?)', ''), ('(?)', '')):
        t = t.replace(a, b)
    return ' '.join(t.split())


def parte2():
    return [(a, b, NOMBRES.get(q, q), _limpiar(t)) for a, b, q, t in PARTE2_BRUTO]


def subtitulos(desde=0.0, hasta=1e9, nombres=True):
    """Lista para Escena.subtitulos(): (inicio, fin, texto[, tipo de ventana]) que empiezan entre 'desde' y
    'hasta'. Cada texto dura al menos 1,2 s (sin pisar al siguiente) para poder leerse."""
    todos = sorted(s for s in PARTE1 + parte2() if not CHAT[0] <= s[0] < CHAT[1])
    out = []
    for i, (a, b, q, t) in enumerate(todos):
        sig = todos[i + 1][0] if i + 1 < len(todos) else 1e9
        b = min(max(b, a + 1.2), max(b, sig - 0.05))
        if not desde <= a < hasta or not t.strip('… .'):
            continue                    # fuera del tramo, o una frase ininteligible (solo «…»)
        if q == 'NARRADOR':
            out.append((a, b, t, TIPO_NARRADOR))
        elif q and nombres:
            out.append((a, b, '%s: %s' % (q, t)))
        else:
            out.append((a, b, t))
    return out


def chat():
    """Mensajes del grupo: (instante, quien, texto)."""
    return [(a, q, t) for a, b, q, t in parte2() if CHAT[0] <= a < CHAT[1]]
