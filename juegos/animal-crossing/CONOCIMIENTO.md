# CONOCIMIENTO — Animal Crossing: Wild World (ROM europea)

Todo lo aprendido al extraer la ROM y construir el vídeo. Si algo falla, mira primero aquí.

## La ROM

- `Animal Crossing - Wild World.nds`, título `ANIMAL CROSS`, código **ADMP** = **Europa** (no EE. UU.). Los rótulos de tienda
  existen por idioma (`obj_ngSs` = español); los textos están en `script/{ENG,FRN,GER,ITA,SPN}`.
- NitroFS con ~16 976 ficheros. Se lee con `ndspy`. Muchos ficheros llevan envoltura **`LZ77`** + flujo LZ10 de la BIOS
  (`tools/ww/rom.py: unwrap`, `Rom.get()` lo hace solo; `Rom.raw()` devuelve los bytes sin tocar).
- Tipos por número: bmg 8955 (textos), nsbtx 3175, arc 2127 (NARC), nsbmd 771, nsbca 591, bch 398, nsbtp 391, bsc/bpl 358, bin 155,
  nsbva 42, sdat 1.

## Formatos 3D (`tools/ww/nitro3d.py`, `anim.py`)

- **NSBMD/BMD0 → MDL0**: nodos con T/R/S y rotación "pivote" (select/neg), bytecode SBC (llamadas a malla, pila de matrices,
  *skinning*), listas de comandos GX con vértices comprimidos. Las matrices de rotación vienen **transpuestas**: se aplica `.T` al leer.
- **TEX0** (NSBTX o dentro del NSBMD): 7 formatos (A3I5, 4/16/256 colores, comprimido 4×4, A5I3, directo). El color 0 es
  transparente en los formatos de paleta si el bit de la textura lo indica. **Comprimido 4×4**: bloques en `comp_data` + info en
  `comp_info`; necesita la paleta completa.
- **Paleta compartida `house_pl`**: los edificios no llevan paleta propia; está en `str/house_pl/house_pl_{s,w}.nsbtx`.
  Regla del render: usar la paleta del propio banco salvo si pesa < 64 B (marcador) y existe otra ≥ 1024 B.
- Fachadas de tienda: el `.arc` (`str/shop/a/K/`) no trae texturas; están en `str/shop/n/K/<mismo nombre>.nsbtx`.
  Casas de vecinos: `str/npcHsTex/<A..>/house_<letra><n><s|w>.nsbtx`.
- **NARC** (`.arc`): el modelo está en `a/bmd/bmd0` dentro del arc (`ww.assets.narc_files`).
- **NSBCA**: JNT0/JAC0 con curvas constantes o con muestras; en la rotación hay que decodificar "basis" con
  `sx(x & 0x1FFF, 13)/4096` (el fallo de signo daba animaciones destrozadas). Animaciones a 30 fotogramas/s.
- **Vecinos**: `npc/model/<especie>/<n>.nsbmd` + `.nsbtx`. Clips `wait1`, `walk1`, `talk1` (solo la boca; se superpone
  a `wait1` con `pose_layered`), `mr_*` para emociones. Los ojos son texturas `e.0..e.7` de un banco externo (parpadeo = cambiar textura).
- **Jugador**: `PBody` (cuerpo), `PHead/<n>` (peinado), `PFcTx` (cara), `cloth/` (camisetas), `PPal` (paletas de pelo).
- **Orientación**: el frente de los modelos mira a **+Z**; la cámara está en +Z. Un `yaw` de `atan2(dx, dz)` orienta hacia (dx, dz).

## Rasterizador propio (`tools/ww/raster.py`)

- Vecino más cercano, sin antialiasing, perspectiva correcta, recorte por el plano cercano. Para que el suelo no desaparezca
  cuando hay vértices detrás de la cámara se **subdivide en celdas de 4 unidades**.
- Culling (atributo de polígono, bits 6-7): `1`= solo cara trasera, `2` = solo frontal, `3` = ambas. En `Canvas.draw`:
  `cull 1` descarta área > 0, `cull 2` descarta área < 0; la tabla es `{1: 2, 2: 1, 3: 0}`.

## 2D

- **Fuentes** (`font/fontA_{attr,img}.bin`): glifos 16×16 de 1 bpp, orden Windows-1252, anchos proporcionales en `attr` (u16 código, u16 ancho).
- **Nube de diálogo**: mapa `a_mes/a_mes0a_bg_nsc.bin` (32×32 celdas) con tiles `a_mes_bg_ncg.bin` (4 bpp) y paleta `a_mes_bg_ncl.bin`.
  Las celdas 17-152 son donde el juego escribe texto: se rellenan con el tile blanco 288 y se ensancha repitiendo la columna 16.
- NCG/NCL/NSC aquí son `.bin` crudos sin cabecera. Los `.bch/.bpl/.bsc` del menú (Jupiter) **no están decodificados**.

## Audio (`tools/ww/synth.py`)

- `sound_dataEUR.sdat` con 342 secuencias SSEQ **sin nombre** (ndspy no las nombra). Por rangos de índice:
  22-45 = 24 temas ambientales (*asumido: uno por hora, en orden*), 99-171 = efectos, 176-246 = K.K. Slider.
- Sintetizador propio: SSEQ (comandos de pista, bucles, llamadas, variables), SBNK (instrumentos y regiones),
  SWAR/SWAV (PCM8/16 y ADPCM IMA), envolvente ADSR de la DS y LFO. No es exacto al hardware pero reconocible.
- **Voces**: el juego no tiene voz grabada; "habla" reproduciendo sílabas de los archivos de ondas 10-19, con tono variable.
  18 → Nook (tono ×0,78) y 19 → un vecino (×1,35) en el vídeo; la asignación por personaje es aproximada.

## Fallos que ya se resolvieron

| Síntoma | Causa | Arreglo |
|---|---|---|
| apicula no compila | rustc 1.70 viejo | parsers propios |
| Modelos de espaldas, texto espejado, tienda hueca | culling invertido | tabla `{1:2, 2:1, 3:0}` |
| Animaciones con basura | rotaciones "basis" de 13 bits sin signo | `sx(x & 0x1FFF, 13)` |
| Casas blancas | paleta `house_pl` ausente / fachadas en otro banco | paleta compartida + rutas `shop/n`, `npcHsTex` |
| Colores de textura comprimida erróneos | se leía la paleta parcial | paleta completa + bloques `comp_data` |
| Suelo desaparece | vértices tras la cámara | subdividir en celdas de 4 |
| Camiseta negra | paleta del banco equivocado | preferir banco propio |
| Brazo de Nook estirado al hablar | `talk1` mueve todo el esqueleto | superponer solo nodos con muestras (`pose_layered`) |
| `KeyError 'mr_niko2'` | clip inexistente | el emote mantiene el último fotograma |
| Parches con `\0` no aplicaban | escapes en `heredoc` | usar Edit y verificar con grep |

## Vídeo (`video/`)

- Se renderiza a 640×360 y se amplía ×2 (vecino más cercano) a 1280×720, 30 fps. Cada fotograma es **función pura de t**,
  así que se paraleliza con `multiprocessing` (60 s en ~2 min). Pipe `rawvideo` → `ffmpeg` (H.264 yuv420p, CRF 17) + AAC.
- Audio: música SSEQ + sílabas de voz sincronizadas con el texto tecleado (22 caracteres/s), normalizado a pico 0,89.

## Limitaciones y cosas abiertas

- Orden horario de los 24 temas y mapeo exacto voz↔personaje **sin confirmar** (no hay nombres en el SDAT).
- Gráficos de menú `.bch/.bpl/.bsc` sin decodificar; animaciones no exportadas a fichero (solo se usan en el motor).
- `tools/` contiene restos de otro proyecto (Pokémon Platino: `extract.py`, `ndsgfx.py`, `nsbmd.py`, `sonido.py`, `msg.py`,
  `names.py`, `mapa3d*.py`, `custom/`). **No se usan** aquí; el código de Wild World vive en `tools/ww/`.
- El guion del vídeo de prueba estaba sin rellenar en el encargo; se eligió «Tom Nook explica este repo a un vecino» (petición posterior).

## Vídeo vertical y música propia (`video/gasto.py`, `video/reggaeton.py`)

- `VIDEO_VERTICAL=1` (antes de importar `motor`) da 360×640 ×3 = 1080×1920. En vertical el FOV de 34° recorta los lados: con dos
  personajes a ±1,25 hace falta cámara a ≥ 15 unidades; para dejar sitio a un cuadro arriba se apunta la cámara por encima de ellos.
- `synth.tocar_notas(son, banco, notas)` toca notas sueltas con un banco del SDAT (`AudioBank.notes`). Banco 12: p0 bombo, p1 caja,
  p2 hi-hat, p6 bajo, p3 punteo, p13 campanilla (suena una octava arriba). Tecla 36 = Do2 (65 Hz) afinada.
- Datos de gasto: IGAE publica COFOG en `igae.pap.hacienda.gob.es` (PDF «Funcional 2019-2023»); extraer con PyMuPDF por posición de palabras.
- Legibilidad en móvil: `Font.draw(..., scale=2, bold=True)` amplía los glifos (vecino más cercano); `make_bubble(rom, 13, extra_rows=5)`
  alarga la nube estirando su fila más ancha (laterales rectos). Texto de diálogo ×2 con ≤ 3 líneas (~18 caracteres por línea).
- Fallo corregido en `blit(tint=...)`: las máscaras de texto son negras y `tint` las multiplicaba, así que todo el texto salía negro;
  ahora `tint` es el color plano.

## Textos, pesca y personaje custom (`video/pesca.py`)

- **Ficheros `LZ77` de tipo 0xF7** (8 950 ficheros: `script/*`, textos BMG): `'LZ77'`, `0xF7` + tamaño u24, una tabla de u16 (uno por bloque de 4096 B) y
  después bloques LZ10 independientes (cada uno con su cabecera `10 + tamaño`). `Rom.get()` ya los descomprime (`rom.py: lz10_trozos`).
- **BMG** (`MESGbmg1`): secciones INF1 (n entradas, offsets u32) y DAT1 (cadenas cp1252 terminadas en 0, `0x1A` = código de control).
  Textos de peces: `script/SPN/string/obj_etc_fish.bmg` (ficha) y `script/SPN/message/obj/etc/getfish_.bmg` (frase al pescar); índice 26 = salmón, 27 = salmón rey.
- **Peces**: `fish/NN/fishXX.nsbmd` (+`.nsbca`); el modelo `fishXX` coincide con el id del texto. Eje largo = Y (cabeza +Y), cara plana hacia +Z.
  `fish/03/fish_shadow` = sombra plana para verlos bajo el agua.
- **Caña**: `PItm/Mdl0/15.nsbmd` (`pole0`; la dorada es la 3). Se acopla a la mano con `model.node_world[14]` (`Rhand`) tras `model.pose(pose)`
  (`nitro3d.py` guarda las matrices de nodo en `node_world`); la punta está en (0,0,3.06) del modelo. Clips de pesca (compatibles con los vecinos):
  `pol_wait1` (caña recogida atrás), `pol_swing1` (lanzar, 34 f; el último fotograma es la pose de espera), `pol_wait_nibble1`, `pol_hit1`, `pol_get1`,
  `comp_fish1/2` (presentar el pez; `comp_fish2` lo sostiene en `Lhand`, nodo 11).
- **Agua**: textura `grd_riv.0` con paleta `grd_riv_pl` (cáusticas translúcidas) sobre un plano azul; se desplazan con `t`. La paleta de cada textura de `grd_set0a`
  tiene su propio nombre (`grd_sea_pl`, `grd_was_pl`…): con `grd_pl` salen colores falsos.
- **Personaje custom `lincelucas`**: ver `biblioteca/animal-crossing/personalizados/lincelucas/README.md`. Recolorear texturas se hace con un banco falso (`BancoLince`) antepuesto a `asset.banks`.
- Los `python -I` ignoran `PYTHONIOENCODING`: usar `sys.stdout.reconfigure(encoding='utf-8')` para imprimir tildes en Windows.
- **SFX**: las secuencias 99-171 del SDAT renderizan como pulsos sueltos (no son efectos aislables a ciegas). `video/sfx.py` los construye con el banco 12
  (caja = ruido de banda ancha, campanilla, bombo…) + `scipy.signal` (barridos paso banda) + glissandos por remuestreo. Sin poder escuchar, se validan por
  espectrograma, duración y pico.
- **Efectos de vídeo** (`pesca.py`): cada fotograma es función pura de `t`, así que las transiciones son superposiciones sobre el plano que toque en `t`
  (el corte real ocurre en el centro de la transición); temblor = desplazamiento con bordes replicados; rebote = ease-out-back.

## Cabeza personalizada y Capitán (`video/pedro_parodia.py`)

- **Capitán** es `npc_sp/model/wip.nsbmd` con `wip_tex.nsbtx`. `upa` es el ajolote Dr. Sito, no Capitán.
- `PBody/boy.nsbmd` tiene el mismo esqueleto de 20 nodos que los vecinos y admite `ft_sitdown_wait1`; no contiene cabeza. La pose de sentado tiene los pies aproximadamente en Y=0,96: para sentarlo sobre un suelo Y=-0,18, trasladar el cuerpo a Y=-1,14.
- `PHead/0/0.nsbmd` se acopla con `world @ body.model.node_world[15]`; el eje X local del peinado se transforma en vertical. Bancos `PPal/0/0.nsbtx` y `PFcTx/0/0.nsbtx`. Sirve para la nuca vista desde atrás.
- `motor.draw_textured_quad` permite un decal RGBA con perspectiva y profundidad; esquinas en orden abajo izquierda, abajo derecha, arriba derecha, arriba izquierda. La cara externa de esta parodia es una excepción pedida explícitamente en el encargo, guardada en `biblioteca/animal-crossing/personalizados/pedro/`; no establece una excepción general a los assets ROM.

### Foto sobre vecino y transiciones v2

- `video/personajes/pedro.py`: cbr01 (`npc/model/24/29`) es un osezno de cabeza redonda. La foto se muestrea a 64×64 y se proyecta sobre e/m y los triángulos frontales superiores de b0. Las UV se calculan en pose neutra y siguen la misma topología al animar; `motor.draw_surface_texture` desplaza 0,008 según la normal para evitar z-fighting. Conserva el volumen de la cabeza original.
- `motor.screen_transition(img,t,cuts)` recibe los cortes por argumento: barras, zoom con flash, iris, barrido y fundido a color. La v2 deja 0,26 s entre corte y diálogo y exige 0,9 s de lectura tras completar el texto.
- Las carpetas `cloth` agrupan 16 prendas: cloth065 está en `cloth/4/`. La hoja de texturas no está necesariamente en orden numérico (buscar por nombre antes de asumir que corresponde a un índice de la hoja).

- `pedro_parodia_v3.py` separa transiciones principales de microtransiciones: estas últimas se componen sobre el escenario antes de pintar la nube, de modo que el texto no salta con la cámara. Las ventanas de reacción son renderizados del vecino en un `Canvas` pequeño, preparados en `init`; no son assets externos. El diálogo comienza a los 0,51 s. `motor.chromatic_shift` replica bordes al separar canales para evitar bandas negras.

### Cruce caminando y llanto tumbado (`pedro_parodia_v4.py`)

- `faint_A1` y `faint_B1` terminan boca abajo; para mantener visible la foto durante el llanto se usa `mr_naku1` seguido de `mr_naku2`, con un giro global gradual de 90° alrededor de Z. Ajustar la altura con el mínimo Y de los vértices ya rotados deja el personaje apoyado en el suelo mientras tiembla, sin integrar estado entre fotogramas.
- El caminante wip usa `walk1` y `pose_layered(walk1, ..., talk1, ...)` para caminar y cantar a la vez. La trayectoria debe empezar y terminar fuera del encuadre antes de añadir/quitar el actor. Los pasos se espaciaron a la mitad del periodo del clip, y el panorama de audio sigue X(t).
- Para una órbita que revele la cara, la cámara recorre ángulos de pi a 0 alrededor del personaje tumbado, con centro bajo y radio decreciente; al terminar mira su frente +Z. Las lágrimas se anclan al nodo head, no a coordenadas fijas de pantalla.
