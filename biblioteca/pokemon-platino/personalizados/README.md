# Sprites custom

Personajes propios con el estilo de Pokémon Platino. Para crear uno nuevo usa la skill
la skill `personaje-pokemon` (fotos en `entrada/<nombre>/`). Cada uno va en su carpeta:

- `mapa/frame_00..15.png`: 32x32, mismo orden que los del juego (0-3 arriba, 4-7 abajo, 8-11 izquierda,
  12-15 derecha; [quieto, paso, quieto, paso]). El motor de cinemáticas los encuentra por nombre:
  `esc.personaje('el_pana', tx, ty)`.
- `combate/frente.png` (80x80, el que ve el rival), `combate/espalda_0.png` y `espalda_1_lanzar.png`
  (80x80, el del jugador en combate; la 1 es la pose de lanzar la Poké Ball).
- `_vista.png`: resumen para enseñar (mapa x2 y combate x3). `_revision.png`: los 16 frames ampliados junto
  a su base, para revisar píxel a píxel. Los dos los regenera el script del personaje.
- `_bases/` (no es un personaje): hojas de candidatos y ampliaciones de `tools/custom/herramientas.py`.

## EL PANA
Generado con `python juegos/pokemon-platino/tools/custom/el_pana.py` (fotos de referencia en `entrada/el_pana/`). Pelo castaño
oscuro revuelto, gafas de pasta, barba y bigote, camiseta verde de manga larga y vaqueros oscuros.
Bases del juego retocadas: ayudante de laboratorio (mapa), Entrenador Guay (frente), Israel (espalda).

## SANTOS
Generado con `python juegos/pokemon-platino/tools/custom/santos.py` (fotos de referencia en `entrada/santos/`). Chico joven y
deportista: pelo castaño corto con la frente despejada, barba de pocos días y chándal azul marino con
cremallera y rayas blancas, zapatillas blancas.
Bases del juego retocadas: man1 (mapa, con la frente despejada a mano), entrenador guay 053 (frente: sin
flequillo; su mono pasa a chándal y los guantes a manos) e Israel (espalda, con el tupé recortado a una
cabeza redonda de pelo corto).

## Personajes de REWINDLIMBO2 (solo sprites del mapa)
- `el_maria`, `el_maria_sombrero`, `el_maria_sudadera` (`tools/custom/el_maria.py`): EL MARÍA sin sombrero (base
  man1) y con el sombrero beige de cinta violeta (base explorador 048), con camiseta negra o sudadera gris. Frames
  extra: 16 agachado, 17 sentado (de frente), 18 agachado de espaldas. `el_maria_sombrero` además: 19 con la pipa en
  la boca, 20 con el mapa abierto, 21 agachado con la pipa; `el_maria` (sin sombrero): 16 con el sombrero en las manos.
- `santos_camisa` (`tools/custom/santos_camisa.py`): SANTOS con camisa azul clarito y pantalón negro.
- `robot_valedores` (`tools/custom/robot_valedores.py`): robot con cuerpo de microondas (base 406), brazos con llave
  inglesa y ojos rojos. Frames 16-17: brazos arriba.
- `gorgibot`, `gorgibot_azul`, `gorgibot_rojo`, `gorgibot_amarillo` (`tools/custom/gorgibot.py`): la cabeza de Santos
  sobre un cuerpo de metal oscuro con una rueda; las variantes cambian el color de la cara.
- `chini`, `chini_chaqueta` (`tools/custom/chini.py`): chico de pelo castaño corto (base man5 066) con camiseta negra
  o con chaqueta roja sobre camiseta azul.

## Personajes de FORMIGAL (solo sprites del mapa)
`python juegos/pokemon-platino/tools/custom/formigal.py`: `formi_verde` (camiseta verde oliva, base 066), `formi_gris` (sudadera gris, base 008),
`formi_gafas` (gorro negro, gafas de sol, braga roja, plumas negro, base 147 sunglasses) y `formi_rojo`
(chaqueta roja con capucha gris, base 066).
