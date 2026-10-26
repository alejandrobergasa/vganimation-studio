# Lo aprendido montando escenas con Pokémon Platino

Notas técnicas para no redescubrirlas. El uso del motor está en `cinematicas/README.md`; aquí va el porqué.

## Escenarios: usar los mapas 3D reales, no tiles 2D
- En Platino el mundo no es una rejilla de tiles 2D. Cada trozo de 32x32 tiles (512x512 px) es un modelo 3D
  (NSBMD dentro de `fielddata/land_data/land_data.narc`) con sus texturas: pinos hechos de capas
  (`conttree_t` / `conttree_b`), taludes y orillas del agua, vallas, hierba alta, etc.
- Montar esas texturas a mano en 2D **no funciona** (el usuario lo rechazó: «los árboles no encajan y el
  agua no tiene borde»). El catálogo 2D (`motor/catalogo.py`, clase `Mapa`) queda solo como recurso antiguo.
- `tools/mapa3d.py` (clase `Mundo`) + `tools/nsbmd.py` (parser MDL0 + rasterizador) renderizan el terreno y
  los edificios con la luz del juego. `cinematicas/motor/mapa_real.py` (`MapaReal`) lo usa como fondo y
  guarda el resultado en `.cache/pokemon-platino/` (borra esa carpeta si cambias el renderizador).

## Formatos (ROM ES de Platino)
- **land_data**: cabecera de 4 u32 = tamaños de permisos (0x800), edificios, NSBMD y BDHC. Datos desde el
  byte 16, en ese orden.
  - Permisos: 32x32 u16. El byte bajo es el comportamiento (hierba, puerta 0x69/0x6E/0x6F, agua...) y
    `0x8000` = no se puede pisar.
  - Edificios: entradas de 48 bytes: u32 modelo (`fielddata/build_model/build_model.narc`), posición fx32
    x, y, z (centrada en el trozo, ±256), rotación ×3 (se ignora, en los pueblos probados era 0),
    escala ×3 y 8 de relleno.
- **Matriz del mapa**: `fielddata/mapmatrix/map_matrix.narc` fichero 0 = Sinnoh, 30x30, ids de land_data
  (0xFFFF = vacío). Para ver la rejilla de ids, imprime `Mundo(rom).matrix` (ver `mapa3d.py`).
  Zonas comprobadas a ojo: Aromaflor (19,5) 2x1, Hojaverde (26,3) 2x1, Ruta 204 sur (21,5) 2x1,
  Ciudad Jubileo (23,4) 2x2 (avenidas asfaltadas; la x=46 está libre de y 30 a 63).
- **Interiores**: no están en la matriz 0. `map_matrix.narc` tiene 289 matrices (1 = `single`, el resto
  `m_<sala>_`: `m_h01_` casas, `m_pc` Centros, `m_ajito` guarida Galaxia, `m_dun` cuevas...) y casi todos
  los interiores son un solo land_data (ids ~180-335). `Mundo.usar_land(id)` los renderiza. Algunos
  dejan muebles sueltos fuera de la sala. Salen más oscuros que en el juego (la luz es la de exterior).
  Hoja de candidatos: renderizar varios ids y montarlos en una rejilla. El 289 (sala azul oscuro con
  valla de postes en U) sirve de celda (`INTERIORES['celda']`).
  Para identificar una zona nueva, renderízala en pequeño y mírala; luego añádela a `ZONAS`.
- **Texturas**: van en `area_map_tex/map_tex_set.narc` (terreno) y `areabm_texset.narc` (edificios). Se elige
  el set con más nombres en común con los materiales. Paletas: por material del modelo.
- **Luz**: `data/arealight.narc` fichero 0 es texto. Cada bloque empieza por la hora en unidades de 2 s
  (21600 = mediodía), 4 luces y luego difusa/ambiente/especular/emisión. Los materiales de mapa solo usan la luz 0.
- **Fallo ya corregido**: el alfa de las texturas A3I5/A5I3 desbordaba `uint8` en numpy y el agua y algunos
  edificios (el arco de Aromaflor) salían casi invisibles. Si algo sale translúcido, mira primero el decodificador.
- El agua de lagos y estanques es una textura translúcida (`lake`, `seaside3`) sobre un fondo (`puddle_b`).
  Es estática en el render; en el juego se anima. Las flores tampoco se animan todavía.

## Sonido (`tools/sonido.py`)
- `data/sound/sound_data.sdat` tiene los nombres (`SEQ_*`, 829 secuencias con datos); `pl_sound_data.sdat`
  casi no tiene símbolos. No hay SSAR ni STRM: los efectos también son SSEQ sueltos.
- ndspy parsea SDAT, SBNK y SWAR, pero no reproduce nada; el intérprete de bytes SSEQ y el sintetizador son
  propios. Fórmulas del driver: paso de 5,2095 ms (64·2728/33513982 s), tempo acumulado de 240 en 240,
  envolvente en 1/1280 dB desde -92544 (Cnv_Attack/Cnv_Fall/Cnv_Sust), volumen total en décimas de dB
  sumando envolvente + velocidad + volumen de pista + expresión + volumen global + volumen del SSEQ.
  Tono en 1/64 de semitono respecto a la nota raíz; frecuencia de la muestra = 16756991 / time.
- ADPCM: IMA con cabecera de 4 bytes (muestra inicial s16, índice), nibble bajo primero. El inicio de bucle
  en muestras es (loopOffset·4 − 4)·2.
- El 0xC7 es «mono» (la pista espera a que acabe cada nota) y por defecto está activo.
- Comprobado con espectrogramas (notas armónicas limpias y con ritmo, ondas periódicas), **no a oído**.
  Si el usuario nota algo raro (tono, tempo, instrumentos), revisa primero volúmenes y vibrato.
- Al editar ficheros con acentos desde un heredoc de bash, usa `python -X utf8 -`; las barras invertidas
  del heredoc llegan a medias, así que constrúyelas con `chr(92)` o usa la herramienta Edit.

## Proyección y coordenadas
- Vista oblicua ortográfica: `x_pantalla = x`, `y_pantalla = z - y*K`. Uso **K = 1.0**, el que más se
  parece al juego (las pruebas A/B/C con K = 1 / 0.75 / 0.5 están en `salida/pokemon-platino/pruebas/`). Falta
  que el usuario lo confirme.
- El suelo de los pueblos está a y ≈ 80 (no 0). Por eso la imagen se renderiza desde y = -128 (`Y0` en `mapa3d.py`).
- Tile de personaje = 16x16 px de mundo. Los pies quedan en `z = ty*16 + 16` y se dibujan subidos `altura*K`.
  La altura por tile es la superficie casi horizontal más baja que lo cubre (así no cuentan las copas).
- **Oclusión**: un píxel del mapa tapa a un personaje si su z de mundo > z de los pies. Con un billboard
  vertical y K = 1 esto equivale exactamente a comparar la profundidad. Consecuencia: al pasar bajo el arco
  de Aromaflor o justo detrás del tejado de un edificio, el personaje desaparece un momento (en el juego
  pasa algo parecido).
- La burbuja «!» se dibuja aparte, encima de todo.
- **Ojo con los tejados altos**: en Jubileo, los edificios de la fila de abajo tapan casi por completo a
  quien esté en las 3-4 filas de calle de encima (x 37-41, y 43-46). Antes de colocar un diálogo junto a
  un edificio, mide la oclusión: fracción de `zbuf > z_pies` dentro de la caja del sprite. Sirve también
  a propósito: hacer que alguien «salga» andando por detrás de un edificio (ocúltalo luego con
  `desaparecer()`, porque la sombra asoma por el borde del tejado).
- Para conversaciones, ponlos **lado a lado** (izquierda/derecha): en columna, el de abajo habla de
  espaldas y los sprites se pisan.

## Personajes
- Mapa: 32x32. Frames 0-3 arriba, 4-7 abajo, 8-11 izquierda, 12-15 derecha [quieto, paso, quieto, paso].
  Los protagonistas tienen además 16-31 para correr.
- Policía: `032_policeman` (16 frames). No hay otro sprite de policía; para dos, se repite.
- Efectos útiles: `efectos_ataques/33` (destello rojo de impacto, 3 celdas que crecen; la 3.ª es enorme),
  `efectos_ataques/11` (símbolo de enfado). Las de `efectos_ataques/03` son manos señalando, no puños.
- Combate: los frontales de entrenador son 80x80 (el PNG estático es de 160x80 y la mitad derecha suele estar
  vacía). Los de espalda tienen 2 poses de 80x80 (la 2.ª es la de lanzar, desplazada +74, +3 en Israel).

## Personajes custom (`biblioteca/pokemon-platino/personalizados/`)
- Técnica que funciona: partir de un sprite del juego parecido y recolorear **por zonas** (cabeza / torso /
  piernas), porque la misma paleta se reutiliza en pelo, ropa y botas. Después se pintan a mano los rasgos
  (gafas, barba) con coordenadas fijas. Ejemplo completo en `tools/custom/el_pana.py`.
- Para buscar una base, saca hojas con todos los sprites mirando abajo y amplía los candidatos con rejilla:
  `tools/custom/herramientas.py` (`bases`, `ampliar`, `paleta`). Flujo completo en la skill `/personaje`;
  utilidades comunes en `tools/custom/comun.py`.
- Prima la **silueta** (pelo, gorra, complexión) al elegir base: recolorear es fácil y redibujar la silueta
  no. Las 16 direcciones, de la misma base.
- Las paletas del juego tienen 15 colores + transparente. EL PANA llega a ~21 por frame (barba y recoloreos)
  y el usuario lo aprobó, así que es una guía, no una regla.
- Casi todos los sprites del mapa llevan el pelo en casco tapando la frente. `080_middleman2` la trae
  despejada, pero el usuario lo vio «viejo y gordo» con ojos raros: para un chico joven es mejor partir de
  `008_man1` (joven, delgado, ojos normales) y despejarle la frente a mano relativa a la fila de los ojos
  (`_frente` en `tools/custom/santos.py`). En combate, para acortar el pelo de Israel
  (la única espalda de chico sin gorra) se recorta con una elipse y se redibuja el contorno: ver
  `_pelo_corto` en `tools/custom/santos.py`. El contorno se calcula sobre una copia del alfa; si se mira
  el propio píxel ya ennegrecido, todo el pelo acaba negro.
- Aseprite (MCP `pixel-plugin`) estaba configurado pero no conectó; todo se hizo con PIL y numpy.

## Flujo que ha funcionado con el usuario
- Antes de rehacer algo grande, generar **imágenes estáticas de prueba** etiquetadas y dejar que el usuario
  elija (él mismo lo propuso). Se guardan en `salida/pokemon-platino/pruebas/`.
- Revisar siempre las hojas de contacto y los frames ampliados antes de entregar.

## Vídeos largos sincronizados con un audio (REWINDLIMBO2, 10:18)
- **Audio**: `demucs` (htdemucs) separa voces / batería / bajo / resto; `basic-pitch` transcribe bajo y resto a notas
  (`trabajo/rewindlimbo2/transcribir.py`). En Windows hay que lanzarlo con `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` o
  revienta al imprimir emojis (cp1252) sin escribir el MIDI. `tools/sonido.py:tocar_notas()` toca esas notas con
  los instrumentos de un banco del juego (BANK_BGM_FIELD 1001: programa 1 batería GM, 32 bajo, 2 pulsado,
  48 sostenido; FS = 32768 Hz).
- **No toques nota a nota lo que transcribe basic-pitch** (v1, `musica_platino.py`). Suena trabado: las notas
  salen troceadas, cogen ruido y efectos del original, la batería detectada por ataques no va a tempo y una
  ganancia por ventanas de 0,5 s bombea. Lo que funciona es **re-arreglar** (`musica_platino2.py`). Por cada
  corte de la canción: rejilla de pulsos (beat_track, o constante si encaja), tonalidad (Krumhansl), acordes por
  medio compás (Viterbi sobre tríadas con cromagrama), un patrón de batería de 16 semicorcheas sacado del stem
  y repetido, bajo en corcheas con la nota del pyin si es del acorde, colchón de cuerdas y arpa en corcheas.
  La melodía sólo se pone si la tonalidad es clara (conf > 0,55). Ganancia constante por corte, igualada en RMS
  a la original.
- **Pero re-arreglar (v2) hace que la canción deje de reconocerse**: el usuario la oyó peor. La buena es la v3
  (`musica_platino3.py`, usada en el vídeo v4), que toca las notas reales de la canción, limpias: ajustadas a la
  semicorchea, sin armónicos falsos, con los trozos de la misma nota unidos y en legato. La melodía (la voz más
  aguda, monofónica) va con el programa 2, el acompañamiento con hasta 4 voces (4/48) y el bajo monofónico con
  el 33. La batería es la del original golpe a golpe, pero en la rejilla. El volumen es constante por corte.
  `python musica_platino3.py comparar` mide el parecido de croma con la original: v1 0,88, v2 0,73, v3 0,83.
  No bajes de ~0,8.
- BANK_BGM_FIELD usa números de programa tipo GM: 1 batería (36 bombo, 38 caja, 42/46 charles, 49 plato),
  2 lead, 4/5 pianos eléctricos, 11 vibráfono, 12 marimba, 24/26 guitarras, 32-34 y 39 bajos, 40 violín,
  45 pizzicato, 46 arpa, 48 cuerdas, 56 trompeta, 57 trombón, 60 trompa, 65 saxo, 68 oboe, 71 clarinete,
  73 flauta, 74 flauta dulce, 78 silbato.
- Las muestras sin bucle cortadas en seco chasqueaban: `_sintetizar` les aplica una rampa de 64 muestras.
- **Efectos en bucle**: `audio.secuencia()` normaliza cada efecto a pico 1, así que a volumen 0,3 ya suenan más
  fuerte que la música. Además W053 (fuego) dura 3,9 s y W025 1,2 s: dispararlos cada 1-1,5 s los solapa y
  queda un ruido continuo. Espácialos más que su duración y déjalos en 0,12-0,2. Nada de `tanh` en el montaje
  (distorsiona); usa `limitar()` de `musica_platino2.py`, un limitador con anticipación.
- **Tramos**: una `Escena(mapa, t0=...)` por plano o escenario de ~15-90 s, `esc.hasta(seg)` para cada golpe y
  `subtitulos()` con los tiempos del SRT. Render a ~6x tiempo real. Montaje: concatenar sólo el vídeo y rehacer el
  audio entero (mezcla + cada `_sfx.wav` en su segundo): si se concatenan los AAC de cada tramo quedan huecos.
- Las frases que el SRT marca como ininteligibles (sólo «…») no se muestran (`textos.subtitulos`).
- **Zona 26,4 (2x2)**: Pueblo Arena + ruta 202. Hierba alta x 10-20, y 10-19; playa x 46-57, y 26-46; casita del
  tejado azul x 38-41, y 16-22 (puerta desde (39,23)). La fila 16 de x 19-37 es un bordillo: se baja saltando en
  x 23 con `mover(0, 32, 16, arco=10)`, no andando (da `AVISO`).
- **Ciudad Canal (22,1, 2x1)**: el agua del canal (x 12-17) sale como pisable en los permisos; no andes por ella.
  Calles libres x 0-3, x 10-11 (y 28-40), x 19 (y 25-40) y x 20-29.
- **Interiores útiles**: 313 cuarto con PC (sala 10x9; el PC en (7-9,3), delante (7,4)); 254 almacén gris con
  cajas (sirve de gimnasio en obras); 237 sala con escaleras mecánicas; 210 sala pequeña de suelo gris; 280 cuarto
  pequeño marrón. En salas de menos de 12 tiles de alto la cámara las centra y el diálogo tapa las 2-3 filas de
  abajo: pon la acción en las filas de arriba.
- `efectos_mapa/113/gym07sandbag.png` es sólo una textura roja plana, no un saco: dibújalo. `efectos_ataques/32`
  tiene una sola celda (la Z); las bolas de fuego son `efectos_ataques/33`. Notas musicales: `efectos_ataques/29`.
- Marcos de mensaje: el tipo 5 trae píxeles magenta (transparencia mal resuelta); para burbujas verdes usa el 9.
  En los tipos 1 y 9 el texto empieza en x = 17 y hay que dejar ~22 px a la derecha.
- La fuente del juego no tiene `[ ] ( ) ; « » " € % / & +`; sí `… ¿ ¡` y tildes.
- `esc.esperar(n)` ya añade su paso: no va dentro de `esc.hacer(...)` (da «'Escena' object is not an iterator»).
- Bash en Windows: los heredocs con comillas o barras invertidas se rompen; para ficheros con apóstrofes usa
  la herramienta Write o un script de parcheo en un fichero.
- **Gráficos propios (v3 del tramo 1)**: cuando un plano necesita objetos que el juego no tiene (coche, manos, pipa,
  mechero), se dibujan en código con `escenas/rewindlimbo2/dibujo.py`. `Lienzo.forma()` rellena una máscara con una
  rampa de 3-4 tonos (luz arriba a la izquierda) y contorno oscuro de 1 px, que es lo que hace que encajen con el
  juego. Los primeros planos van a 1x dentro de `inserto(img, 1)` y se animan cambiando la imagen de la capa cada
  frame con `esc.durante()` (`plano()` en `t1_preparativos.py`, con caché por argumentos). Vista previa:
  `python escenas/rewindlimbo2/graficos_v3.py`.
- Las manos: un puño (dorso redondeado + 4 falanges apiladas + pulgar encima) se lee bien a 1x; dedos extendidos
  en horizontal parecen un gesto de «paz». Para la llama que se mete en la cazoleta, dóblala hacia la boca de la
  pipa; doblada en horizontal parece un lanzallamas. Para humo de pipa en el mapa, el humo del juego (058) a 16x16.
- Un objeto del mapa (`esc.objeto`) es un Personaje: `posar(img)` cambia su imagen (la puerta del coche) y
  `temblar()` lo sacude (motor arrancando, portazo). Las acciones de `esc.hacer` no corren al escribir el guion:
  `esc.ahora` dentro de los argumentos vale el t0, así que usa segundos fijos.


## ECLIPSE (adaptación del vídeo «EL ECLIPSE», `cinematicas/escenas/eclipse.py`)
- Audio del vídeo transcrito con `faster-whisper` (modelo medium, `pip install faster-whisper`; el small se inventa
  frases). Los memes doblados salen con ruido: mira también los fotogramas (`ffmpeg -vf fps=1/3,tile`).
- Gráficos propios en `escenas/eclipse_gfx.py`: cielo de eclipse, sprite tumbado sobre losa (`tumbado`, un frame
  girado 90° y pasado a `posar`), buscador, camiseta «I ♥ EL LUNAR». Para el primer plano de una cara, recorta la
  cabeza del sprite de combate y escálala x4 (entero, sin suavizar).
- Jubileo: la avenida x 44-49, y 10-58 aguanta una multitud en fila (x 44 y 48, y 12-16). Con `camara_sigue` a un
  personaje que corre, los espectadores quedan fuera de plano: mejor `camara_fija` y que el corredor cruce.
- Los `personaje.visible = ...` fuera de `esc.hacer` se ejecutan al escribir el guion (el personaje salía desde el
  principio): usa siempre `aparecer()`/`desaparecer()` dentro de `hacer`.
- **ECLIPSE v2 (música del vídeo original en soundfont de Platino)**: `trabajo/eclipse/` reutiliza la tubería v3 de
  REWINDLIMBO2 (`musica_eclipse.py` parchea SEP/CORTES de `musica_platino2/3`; demucs + `transcribir.py`). El
  original tiene dos canciones: partitura ambiental de película 0:00-1:40 (muy baja, -39 dB; sube con bajo de 1:20
  a 1:40) y, desde 1:40, una canción con batería a ~144 bpm. Croma 0,74 / 0,69 / 0,84. La escena corre con
  `ECLIPSE_V2=1 python escenas/eclipse.py` (sin música del juego, guarda el frame del anillo en
  `.cache/pokemon-platino/eclipse_marcas.json`) y `python juegos/pokemon-platino/ejemplos/eclipse/montaje.py` coloca la canción 1 + subida antes del anillo y la
  canción 2 desde el anillo, y la mezcla con los efectos. Salida: `salida/pokemon-platino/eclipse_v2.mp4` (sin GIF: no lleva audio).

## BROMAS PARA EL PANA (`escenas/bromas_pana.py`, 57 s)
- Aromaflor (hora 17): plaza libre x 13-21, y 46-51; la fila y=49 de x 23-25 está bloqueada (edificio azul): Santos entra por y=51.
- Solo existe la burbuja «!»; para un «?» se usa `llevar(texto_img('?', k=2), dx=6, dy=-22)`.
- La fuente no tiene paréntesis: no escribir «(...)» en diálogos. Tarta dibujada con `Lienzo` en `bromas_pana.tarta()`.

## FORMIGAL (`escenas/formigal.py`, 64 s)
- Une dos vídeos de móvil: casa (interior 313 con nevera y mesa dibujadas con `Lienzo`) y fiesta nocturna en la
  avenida de Jubileo (x 44-49, y 10-17) con la multitud de `skierm`/`skierw`. Cambio de mapa con `cambiar_mapa` tras
  un fundido, ocultando antes los objetos y personajes de la casa con `desaparecer()`.
- `fiestaformigal.MP4` lleva rotación en los metadatos: para ver los fotogramas, `ffmpeg -noautorotate`.
- Whisper large-v3 con `initial_prompt` con las palabras dudosas (nuggets, birra) acierta más que medium.

## EXPLICACIÓN 1 (`escenas/explicacion1.py`, 57 s)
- Interior 313 con ALEGA y EL MARÍA, planos detalle con `panel()` (ventana + título x2 + dibujo de ≤184x54 px: la
  ventana tapa ~16 px por cada lado). Alega usa de momento el sprite de `el_pana` (no existe uno propio).
- Música: `trabajo/explicacion1/musica.py` (dembow 90 bpm, Am F C G, banco BANK_BGM_FIELD). Se pasa como `audio_base`
  a `esc.exportar`. Para clavar el baile al compás: imprime `esc.t` con `esc.hacer(esc.accion(...))` (sin `hacer` no
  se ejecuta) y recorta/retrasa el wav (desfase negativo = empieza a mitad de compás). 1 beat = 20 frames a 90 bpm.
- Sin GIF en `exportar`: se saca del MP4 con ffmpeg (paletagen).

## ELECCIONESDONT (`escenas/eleccionesdont.py`, 4:37, vídeo educativo sobre la ley D'Hondt)
- Formato «pizarra»: paneles de 256x140 dibujados con la fuente del juego en `escenas/dhondt_gfx.py`, mostrados con
  `esc.mostrar(..., efecto='subir')` / `cambiar_capa` / `ocultar(efecto='bajar')`. Tapan casi toda la pantalla, así que
  los personajes solo se ven al ocultarla (reacciones). Vista previa de todos: `python escenas/dhondt_gfx.py`.
- La fuente no tiene `% / + = < > ’`, pero sí `' ÷ ×`. Escribe «POR CIENTO» y «Y» en vez de «+».
- Evita empates de cocientes en los ejemplos de D'Hondt (el desempate cambia el reparto); se buscaron cifras sin empate.
- Música: `trabajo/dhondt/musica_reggaeton.py` (dembow 94 bpm, La menor, banco BANK_BGM_FIELD: bombo 36, caja 38, charles 42/46,
  bajo 33, piano eléctrico 4, marimba 12, flauta 73, cuerdas 48, arpa 46). `montaje.py` la mezcla con los efectos
  (render de la escena -> duración -> música a medida -> ffmpeg amix). Comprobada con espectro y volumen, no a oído.


## Motor v2 (`cinematicas/motor_v2/`, skill `/cinematica_v2`)
- **Sombra**: `efectos_mapa/017/kage.png` (16x16, filas 4-12) asoma 3 filas por debajo del tile. `MapaReal.tapar()` repinta
  los píxeles del mapa con z > z de los pies, y el suelo justo debajo de los pies cumple eso, así que borraba esas
  filas y dejaba la última suelta (glitch visible a zoom). v2: la sombra tiene su propio `tapar` con tolerancia
  `TOL_SOMBRA = 6` y el `tapar` del sprite acaba en los pies.
- **Animación del terreno**: el juego cambia texturas por nombre. Los materiales del mapa traen `t3_fl_b.1`, `lakep.1`...
  y `data/fldtanime.narc` guarda `X.1..X.n` (BTX0 con sus paletas `X.k_pl`); `data/fld_anime<N>.bin` da nombre de
  fichero y (fotograma, ticks) por paso: casi todo 9 ticks. `tools/mapa3d_v2.py` (`MundoAnim.render_estado`) sustituye
  el material y rasteriza (1,4 s por estado). Flores de Aromaflor (4 estados) y espuma de lagos (`lakep`, 4) animan;
  la superficie del agua de lago es estática también en el juego. Pendiente: lámparas de Jubileo (`c1_lamp01`, sin
  sufijo `.1`), el mar (`sea`, 8 estados, ninguna zona con costa en ZONAS) y las flores `rhana` (16 ticks).
- Paso asumido: 9 frames de escena a 30 fps por fotograma de animación (no comprobado contra el juego real).
