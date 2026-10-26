# Storyboard — pesca del salmón (vertical 1080×1920, ≈ 59 s, sin título)

**Idea**: un vecino normal (gato `npc/model/16/17`; el lince `lincelucas` queda guardado pero ya no se usa en este vídeo) pesca un salmón en el río y explica sus datos con
muchas palabrotas y chistes verdes sobre el tamaño. Formato móvil: render base 360×640 ×3, 30 fps (`VIDEO_VERTICAL=1`). Fuente `font/fontA`, nube `a_mes`.
**Aviso**: lenguaje malsonante y doble sentido a propósito (petición expresa); nada explícito.

**Datos y fuentes**
- Animal Crossing: Wild World (ROM ADMP, textos SPN `script/SPN/string/obj_etc_fish.bmg`): salmón = id 26 → «Tamaño: 90 cm · Hábitat: ríos y estuarios ·
  Mes: septiembre · famosos por remontar los ríos para desovar · su carne es rosa, pero es un pescado blanco»; salmón rey = id 27 → 160 cm, «el mayor de
  los salmones y es muy caro». Los modelos `fish26` (salmón) y `fish_shadow` salen de `fish/01` y `fish/03`.
- 1-4 años en el mar y regreso al río natal: FishBase (*Salmo salar*) / DFO Canadá («After 1-4 years at sea it migrates back to its natal river»).
- Olfato: FishBase («acute sense of smell … imprints a sequence of odours»).
- Saltos de más de 3 m: Scottish Wildlife Trust («leap vertical obstacles over 3 metres tall»).
- No verificado y por tanto **no usado**: porcentaje de supervivencia tras el desove, que no coma al remontar.

**Música**: `video/musica_pesca.py`, pasacalles en Do mayor a 116 bpm con el banco 12 del SDAT (bombo p0, caja p1, hi-hat p2, bajo p6, punteo p3, campanilla p13).
Voz: sílabas SDAT onda 19 (×1,15). «Ding» al revelar cada dato.

| Escena | Tiempo | Plano | Contenido |
|---|---|---|---|
| Apertura | 0–0,5 s | primer plano | Sin título: iris que se abre y primera frase |
| Pesca | 0,5–14 s | primer plano / general | Se queja, lanza la caña (`pol_swing1`), pican (`pol_wait_nibble1`), se engancha (`pol_hit1`), sombra del salmón bajo el agua |
| Captura | 14–17 s | plano del río | El salmón salta (arco 1,4 s) a la mano (`pol_get1` → `comp_fish2`) |
| Datos | 17–47 s | cuadro de datos arriba + lince abajo | 7 tarjetas: 90 cm · 160 cm rey · 1-4 años · olfato · +3 m · septiembre · carne rosa; chistes en primer plano |
| Resumen | ≈ 52 s | cuadro | Lista con los 7 datos + fuentes |
| Cierre | ≈ 56–62 s | general | Sombra gigante del salmón rey cruzando el río; fundido |

**Efectos visuales**: transiciones en cada corte (barras diagonales, zoom con flash, iris, barrido con estela, en ese orden), rótulos de cómic con rebote
(¡ZAS! ¡PICA! ¡ENGANCHADO! ¡SALMÓN! ¡EL REY!), bocadillos con «!» y palabrotas tachadas sobre la cabeza, temblor de cámara, golpes de zoom, líneas de velocidad,
rayos giratorios, confeti, estela de la caña, ondas y destellos en el agua, cifras que suben contando, tarjetas con rebote y viñeta.
**Efectos de sonido** (`video/sfx.py`, hechos con muestras del banco 12 del SDAT + filtrado propio): barridos de transición, chapoteos, plop, tics del flotador,
carrete, alerta, golpe, trino de tensión, fanfarria, ding por dato, «ba-dum» tras los chistes del tamaño, pitido de censura y «dun dun» del salmón rey.
Los 73 SFX de las secuencias 99-171 del SDAT se descartaron: suenan como pulsos sueltos sin pinta de efectos y no se pueden escuchar aquí.
