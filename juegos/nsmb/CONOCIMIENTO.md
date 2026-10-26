# CONOCIMIENTO — NSMB (ROM europea ESP, código A2DP)

> Notas vivas de lo descubierto. Código en `tools/nsmb/`. (Las demás cosas de `tools/` —`extract.py`, `ndsgfx.py` raíz, `sonido.py` raíz, `custom/`…— son de un proyecto previo de Pokémon Platino y NO se usan.)

## ROM
- Título `NEW MARIO`, código `A2DP` (P = Europa), idiomas EEN/EFR/EGE/EIT/ESP (ficheros `*_ESP`, `*.EUR.ESP`).
- 2314 ficheros NitroFS, 135 overlays ARM9 (BLZ: `ndspy.codeCompression.decompress`). ARM9 también BLZ.
- `tools/nsmb/rom.py`: `rom.get(nombre)` bytes crudos, `rom.getu(nombre)` descomprime LZ10/LZ11 si hace falta.
- Los nombres de fichero NO aparecen como texto en el código: se referencian por ID de fichero (no se encontró la tabla nivel→tileset).
  Decisión: asignar tileset por nivel a mano (1-1 = `I_M_nohara` + `I_S_nohara`).

## Gráficos 2D (sin cabeceras Nitro, `BG_*`)
- `BG_ncg/*_ncg.bin`: tiles LZ10, **8 bpp** (64 B/tile). `BG_ncl/*_ncl.bin`: paleta BGR555 de 512 colores (2 bloques de 256), sin cabecera.
  `BG_nsc/*_nsc.bin`: mapa 64x64 u16 (tile 10 bits, hflip b10, vflip b11, banco b12-15).
- Fondos de parallax: `back_<tema>` y `free_<tema>`. Los índices de tile de la pantalla llevan base (back 1-1: 576, free: 256) y el banco
  (b12-15) menos el mínimo selecciona el bloque de 256 colores (back: 10/11, free: 8/9). **Validado** con 1-1 (castillo de Peach, colinas).
- Tilesets de terreno: `BG_pnl/d_2d_PA_<n>.bin` = Map16, 8 bytes/entrada (4 u16 TL,TR,BL,BR, mismo formato que nsc).
  `BG_unt/<n>.bin` + `<n>_hd.bin` = definiciones de objeto (hd: u16 offset, u8 w, u8 h por objeto).
  Tile = 3 bytes (ctrl, num, th). ctrl bit0 = se repite en X, bit1 = en Y. `0xFE` fin de fila, `0xFF` fin de objeto, `>=0x80` pendiente (sin implementar).
- **Espacio de tiles común**: Jyotyu (192 tiles, 0-191) + stage `tikei_*` (448 tiles, 192-639) + tercero (640+).
- Map16 `th`: 0 = jyotyu (si su entrada está vacía, la del stage), 1-3 = bloque `(th-1)*256` del pnl del stage, 4-5 = bloque `th-4` del pnl del tercero.
- Paleta: color = `pal[(banco % 2)*256 + pixel]` con la paleta del fichero dueño del Map16 (Jyotyu/stage/tercero). Validado visualmente.
- Las tuberías NO son tiles: son polígonos 3D con textura `polygon_unit/I_dokan.nsbtx` (pendiente).
- Hay marcadores "✕" en tiles (editor); no se usan en niveles.

## Niveles
- `course/<A01_1>.bin` (A = mundo 1, 01 = nivel, _1 = área) con 14 bloques (cabecera 14x(offset,len) u32).
  Bloque 0: cabecera (u16 +4 = tiempo), bloque 5: entradas (20 B), bloque 6: sprites (12 B: tipo u16, x u16, y u16, 6 B datos, terminador), bloque 7: zonas.
- `course/<A01_1>_bgdat.bin`: objetos de tilemap, 10 B (tipo u16, x, y, w, h en tiles), terminado en 0xFFFF.
  tipo: bits 12-15 = ranura de tileset (0 jyotyu, 1 stage, 2 tercero), bits 0-11 = objeto.
- 1-1 mide ~267x33 tiles. **Render validado** (suelo, bloques, monedas, escalera final, bandera, castillo).

## Modelos 3D (NSBMD/BMD0, NSBCA/BCA0, NSBTP/BTP0) — `tools/nsmb/nitro3d.py`
- Formato según NitroSDK (referencia: código de apicula, descargado a `biblioteca/nsmb/extraidos/_tmp/apicula`, no se redistribuye).
- Contenedor: magic, 0xFEFF, tamaño, secciones MDL0/TEX0/JNT0/PAT0. Info block: `rom.info_block` (count, 8 B cabecera, count*4, u16 size de dato, datos, nombres de 16 B).
- Modelo: objetos (huesos, TRS con pivotes o matriz 3x3 s16 por columnas), materiales (dif/amb, polygon attr, textura/paleta emparejadas por `info_block` aparte),
  piezas (display lists de GPU) y **comandos de render** (0x03 load, 0x04 mat, 0x05 draw, 0x06/0x26/0x46/0x66 mul objeto + store/load, 0x09 skin, 0x0B/0x2B escala).
  Las piezas usan `MTX_RESTORE` (0x14) con la pila del modelo: hay que pasar la pila a `run_dl` (fallo ya resuelto: sin eso las piernas salían en la cabeza).
- Animación JNT0 'J\0AC': por objeto flags (bit0 no animado; T bits1-2/3-5, R bits 6-7/8, S 9-10/11-13), curvas u32/u16, rotaciones por índice a tablas pivot/basis.
- Texturas TEX0: se reutiliza `ndsgfx._decode_tex`; la paleta se elige por el nombre del material.
- Mario: `player/mario_model_LZ.bin` (cuerpo, 16 huesos; modelos `mario_model` y `small_model`), cabeza aparte (`mario_head_cap_LZ.bin`) anclada a la pila 15 (`face_1`).
  Animaciones: `pl_mario` (run/walk/wait), `pl2` (big_walk, jump_*...), `pl`, `plnovs`. Altura grande ≈ 18 unidades -> se escala a ~30 px.
  El modelo mira a +z; para vista lateral derecha, rotar +90º en Y.
## Fuentes y textos
- `font_a.NFTR` (447 glifos 11x15, 2 bpp, con ñ/acentos/¡¿) y `font_b.NFTR` (8 glifos) están en el ARM9, LZ10 con envoltorio `LZ77`. Se extraen buscando `LZ77\x10` y `ndspy.lz10.decompress`.
- También en el ARM9: 5 bloques `GSEM` (=MESG invertido) con los textos de cada idioma.
- Dígitos y "MARIO/LUIGI" estilizados de la HUD: `ARCHIVE/Dat_Init.narc` (sprites OBJ, requieren celdas).
## Audio — `tools/nsmb/sonido.py` (reutilizado y adaptado)
- `sound_data.sdat` en la raíz del NitroFS. Música `BGM_*` (secuencias), efectos `SE_*` dentro de SSAR (`Sonido.efecto(nombre)`).
- BGM_CHIJO = tema de superficie; BGM_CHIKA subterráneo; BGM_SHIRO castillo; BGM_MUTEKI invencible; BGM_COURSE_CLEAR/BGM_GOAL_FANFARE2 meta; BGM_SELECT mapa.

## Ampliaciones (vídeo y extractor)
### Casino vertical
- `ARCHIVE/casino.narc` contiene un único `casino/casino_back.nsbmd`, comprimido con envoltorio `LZ77` seguido de LZ10. Tiene suelo, pared estrellada, mesas, tragaperras, taburetes y lámparas.
- Texturas del casino: `floor`, `wall`, `table`, `slot`, `slot_side`, `slot_borad`, `stool`, `flower_pot`, `leaf`, `light`; paletas homónimas con sufijo `_pl`.
- Los Toads normales están en `ARCHIVE/luigi_model_mg.narc`: miembro 0 `kino_d.nsbmd`, 1 `kino_wait.nsbca`, 2 `kino_walk.nsbca`. `enemy/kinoji.nsbmd` es el personaje anciano, no el cliente normal.
- Peach: `p_carry` la muestra tumbada, transportada por otro personaje. Para mantenerla de pie se usa `p_bt_wait`; `p_kiss2` aporta un gesto de mano para la ruleta. `p_fall_loop` extiende los brazos pero parece flotar y no se usa.
- Bowser: modelo `enemy/koopa_new.nsbmd`; reposo `kp_wait`, risa visual `kp_roar`. Efecto `SE_EMY_KOOPA_LAUGH`.
- `tools/extraer_casino.py` extrae texturas y vistas. `video/casino.py`, `casino_assets.py` y `casino_audio.py` generan 59 s verticales; entrada `python -I juegos/nsmb/video/make_video.py --casino`.
- Revisión de integración: `video/casino_3d.py` + `casino_render3d.py`; 40 s. Proyección conjunta con perspectiva y profundidad, escalas constantes, suelo continuo con UV derivada del mayor triángulo nativo, sombras y sangre estilizada persistente autorizada por el usuario. La primera versión se guarda en `.cache/nsmb/casino/version_anterior.mp4`.
- Los polígonos grandes deben recortarse contra el plano cercano antes de proyectarlos: descartar un triángulo entero cuando un vértice queda detrás de la cámara genera huecos grandes en el suelo. `project_clip` resuelve ese caso.
- El suelo original es material sin iluminación y sus normales guardadas no corresponden a la superficie; en el render conjunto se fijan hacia +Y, igual que en la continuación del suelo.
- La risa de Bowser usa los fotogramas 30–69 de `kp_roar`; los primeros fotogramas lo muestran agachado con la boca cerrada.
- Música propia con SBNK/SWAR nativos, sin SF2 externo. La sangre es procedural y estilizada, sin detalle anatómico.
- Texturas del casino 3D: no basta con repetir los UV mediante módulo. Los modelos de Luigi, Peach, Bowser, Toad y Koopa y los ojos de Mario usan repetición en espejo (`flip_s`/`flip_t`). Se refleja el índice en los períodos impares, incluidos los UV negativos. Omitirlo produce manchas, caras rotas y caparazones rayados.
- `casino_render3d.py` conserva la escala UV, el culling de cada material, la transparencia y los cambios de textura NSBTP. Al activar el culling, la continuación del suelo debe tener los triángulos orientados hacia arriba, no sólo las normales.
- `casino_motion.py` evalúa clips con tiempo fraccionario y mezcla articulaciones mediante cuaterniones. Las reacciones no se repiten. Los bucles nativos no siempre tienen extremos iguales: se añade un tramo de cierre de cinco fotogramas DS; el salto medido queda por debajo de 0,00014 unidades mundiales.
- Auditoría reproducible: `python -I juegos/nsmb/video/revisar_casino.py`, salidas en `.cache/nsmb/casino_3d/pulido/`: 16 materiales, 24 clips, 58 transiciones y 12 costuras. Revisión 3: `salida/nsmb/mario_casino_vertical_v3.mp4`; se conserva v2.

### Niveles / tuberías / colisión
- Objeto de ranura 0 `0x66` = tubería verde (en la ROM son polígonos 3D). Se monta en 2D con las texturas 16x16 `I_do_lu/ru/ld/rd` de `polygon_unit/I_dokan.nsbtx`
  (fila superior = borde, resto = cuerpo), 2 tiles de ancho, `h` de alto (`level.pipe_image`). `0x35` es una enredadera decorativa: se omite en el vídeo.
- Las celdas `(num=0, th=0)` de una definición de objeto son vacías (sin esto aparecían fragmentos naranjas sueltos en los arbustos `0x103f`).
- Sprites del nivel (bloque 6 de `course/*.bin`): `tipo u16, x u16, y u16` en **tiles**, 12 B. `0x94` = Goomba, `0x95` = Koopa. El suelo está en la fila 30; `y=29` = de pie sobre él.
- Colisión: no se usa la tabla `BG_chk` (existe, 55 ficheros, sin descifrar). Se renderiza cada objeto sólido por separado y su canal alfa da la máscara de píxeles
  (sirve también para las pendientes). Lista de ids sólidos en `video/world.py`. Bloques y ladrillos golpean con la cabeza.
- La banda de suelo de 1-1 es fina (1 fila) con columnas de tierra colgando: es lo que dicen los datos; debajo se ve la capa `free`.
### Fondos
- Índices de tile de la pantalla = base fija por capa: `free` 256, `back` 576 (comparten VRAM, 320 tiles cada una). Bloque de paleta = `banco % 2`.
  Antes se usaba el mínimo de la pantalla como base y 8 de 60 fondos salían con ruido. Validado con la hoja `hojas_contactos/fondos.png`.
- El segundo bloque de paleta de `free_nohara_W1_1` (arbustos/colinas lejanas) se pinta semitransparente (0.7) en el vídeo: imita la mezcla alfa de la DS.
### Personajes
- `mario_model.nsbmd` contiene `mario_model` (grande) y `small_model` (otra escala: 0.6 para igualar). Poses: `wait`, `run`, `walk`, `jump`, `jumped`, `tree_pose` (agarrado al mástil), `goal_jump`.
- Goomba: `kuribo.nsbmd`, anim `walk`, aplastado = anim `damage` (frame 6). Koopa `nokonoko.nsbmd`. Bandera final: `enemy/obj_goal_flag.nsbmd` (la bandera negra de Bowser).
- 11 modelos pequeños (`I_killer_*`, `W_tobira*`, `firebar1`, `bombhei`, `jump_step`, `paipo`) no se leen: el contenedor termina unos bytes antes de lo que espera el lector. Sin resolver.
### Audio
- Los SE de `SSAR` pueden ser **bucles sin fin** que el juego corta por código (`SE_SYS_GOAL_FLAG` sonaba 30 s): se recortan por duración y se suaviza la cola (`video/audio.py`).
- `SE_OBJ_BLOCK_KICK` / `SE_PLY_KICK` salen en silencio (peak 0): se usa `SE_PLY_HIT_BLOCK` para el golpe en bloque.
- Verificado con espectrograma/forma de onda (`ffmpeg showspectrumpic/showwavespic`): sin recortes (pico −0,5 dB), la fanfarria y la música se mezclan sin solaparse.
### Texto
- `font_a` es de trazo de 1 px (valor 1 en un bitmap de 2 bpp). Se dibuja blanca con contorno oscuro de 1 px; los títulos se escalan x2 con vecino más cercano.
### Vídeo
- Mario es un autómata (`video/sim.py`, 60 Hz): corre a 1,5 px/tick, salta con `vy0=-6,8`, `g=0,35`; salta pozos/paredes por mirada adelante en la máscara y pisa goombas
  (salto a 60 px de distancia) o salta por encima de koopas (46 px). La simulación se valida sin `HIT`/`FALL` antes de renderizar (`make_video.plan`).
- Cámara horizontal sigue a Mario; la vertical sólo sube cuando Mario salta por encima de la ventana (escaleras finales).
- Parallax: `back` ×0,18, `free` ×0,45. Vídeo: 256x192 → ×3 vecino más cercano (768x576), 30 fps, H.264 yuv420p + AAC.
