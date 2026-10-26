# CONOCIMIENTO — Mario Kart DS (ROM europea, código AMCP)

Código: `tools/mkds/` (ROM, modelos, NKM), `video/mk/` (motor). Reutiliza `tools/nsmb/nitro3d.py` (NSBMD/NSBCA/NSBTP/NSBTX) y `sonido.py`.

## ROM
- 610 ficheros; todo en `data/`. Los `.carc` son NARC comprimidos con LZ10 (`mkrom.narc(ruta)` → `{ruta interna: bytes}`).
- `mkrom.find_rom()` busca `Mario Kart DS*.nds`; `tools/nsmb/rom.py` prefiere `New Super Mario*.nds` (ya hay dos ROMs en la raíz).
- Pilotos: `KartModelSub.carc` `character/<piloto>/P_XX.nsbmd|nsbtx` + `P_XX_drive|win|lose|spin.nsbca` (12 pilotos: mario luigi peach yoshi wario donkey koopa daisy waluigi robo karon kinopio).
  `drive` = 29 fotogramas de volante (0 izquierda, 14 recto, 28 derecha); `spin` 28 (brazos al girar), `win` 100, `lose` 119.
- Karts: `kart/<piloto>/kart_XX_a|b|c` repartidos en `KartModelMain/MainA/MainB/Menu.carc` (`modelos.ARC_KARTS`); la clase `a` sólo existe en Mario. El cuerpo lleva las ruedas incrustadas (material `kart_tire`).
- Circuitos: `Course/<n>.carc` (+ `<n>Tex.carc`): `course_model.nsbmd`, `course_model_V.nsbmd` (cielo), `course_collision.kcl`, `course_map.nkm`, `MapObj/*`.
  Si falta `course_model.nsbtx` las texturas están en el propio NSBMD. 59 circuitos (incluye `Award`, `StaffRoll`, pruebas y misiones).
- Objetos de carrera: `MainRace.carc` (`Item/it_*` conchas, plátano, bomba, seta, estrella…, `effect/bombcore`, `MapObj/obj_shadow`, `box`, `question`).

## Modelos (diferencias respecto a NSMB)
- Sin problemas con el parser: pilotos, karts y circuitos se leen y texturizan igual. Texturas pequeñas (8..256); se usan mipmaps propios en `raster.py`.
- Vértices con colores horneados (circuitos, `luz_mask = 0`); pilotos/karts usan normales. El fondo negro con teselas azules tras la grada de Circuito Mario es la textura real (no un fallo).
- Escala: el kart (≈1,3 u) se dibuja ×5 respecto al circuito (calzada ≈ 16 u). `kartoffsetdata.bin` (224 B/kart, tabla de ruedas y asiento del menú) NO coincide con las ruedas incrustadas: se agrupan los triángulos `kart_tire` por lado y eje.

## NKM (mapa de circuito) — `tools/mkds/nkm.py`
- Cabecera `NKMD`, tamaño 0x4C, 17 secciones (OBJI PATH POIT STAG KTPS KTPJ KTP2 KTPC KTPM CPOI CPAT IPOI IPAT EPOI EPAT AREA CAME), offsets relativos al final de la cabecera.
- Tamaños de entrada: EPOI 0x18, CPOI 0x24, KTPS 0x1C, CAME 0x4C, OBJI 0x3C. Posiciones fx32 (/4096).
- **Las coordenadas del NKM están a 16:1 respecto al modelo** (validado: altura de EPOI = suelo del modelo, error < 0,004).
- EPOI = línea de carrera de los rivales (60 puntos en Circuito Mario): se suaviza con Catmull-Rom y se ajusta al suelo (`circuito.Suelo`, rejilla de triángulos con normal hacia arriba).
- Los circuitos de misión no tienen EPOI.

## Audio
- `data/Sound/sound_data.sdat`: **sin símbolos** (sin nombres). 76 secuencias de música, 5 SSAR de efectos (596+346+182+24+8). `Sonido(rom, sdat='data/Sound/sound_data.sdat')`.
- Ajustes hechos en `sonido.py` para MKDS: límite de 32 canales (la DS tiene 16; sin él algunas secuencias de efectos se desbocan y tardan minutos) y guardia contra bucles sin espera.
- Música propia: `mk/musica.py` (`Partitura` + programas del banco 50: 5 bajo, 3 acordes, 13 melodía, 14 pad, 15 metales, 4 campanilla; kit 127). Ejemplo: `proyectos/bolas_negras/musica_bn.py`. Notas con `dur` < intervalo entre notas dejan huecos de silencio total: solapa pad y bajo.
- `biblioteca/mkds/extraidos/audio/catalogo_audio.csv` (duración/pico/rms). Ids elegidos para cada cinemática: ver su storyboard.

## Motor de render (`video/mk/`)
- Rasterizador numba propio (perspectiva correcta, z-buffer, mipmaps trilineales, niebla, recorte near, repetición/espejo por material, culling por material), 2 pasadas: opacos/recortes y mezcla/aditivo (ordenados por z).
- Cielo: `course_model_V` como capa < 0 anclada a la cámara; el color de niebla sale de la franja de horizonte del propio cielo.
- Render paralelo con `multiprocessing` (spawn): cada proceso construye la escena; `cuadro(t)` debe ser puro.
- Partículas: trayectoria cerrada (p0 + v·a + ½·g·a², con arrastre opcional) para evaluar cualquier t.
- Fallos resueltos: tex 4D en numba (`tex[mi]`), vecinos de mip en niveles pequeños, ejes (+x = izquierda del kart), signo de `curv`, ruedas que giran con `rot_x(+giro)`.
- Pendiente / ideas: animaciones de textura de circuito (`course_model.nsbta`: agua, lava), `nsbtp` de objetos, objetos de circuito (OBJI → modelos de `MapObj`), colisión KCL, SPA (partículas del juego), escenas `Scene/*.carc` (podio, créditos).

## Personajes con foto sobre pilotos de la ROM (`mk/personas.py`) y escenarios a medida
- `Personaje(motor, nombre, foto, hitos, pelo, camisa, mangas, torso, botones, pantalon, ancho=..., escala=5)`: el **piloto de la ROM** (Mario) con la foto como
  `P_face.1` y `P_main` recoloreado (gorra → pelo o piel si `pelo=None`, camisa, mangas, torso, botones) y las animaciones del juego (`drive/win/lose/spin`).
  `hitos` = (fila de los ojos, fila de la barbilla, columna del centro de la cara) en píxeles de la foto; el resto de rasgos sale de proporciones medias medidas
  en el ejemplo de Ábalos. `.sentado(pos, yaw, anim, frame)` para ir en un kart (pos = kart + R @ (0, a·s, z·s): el origen del piloto es el asiento) y
  `.de_pie(pos, yaw, fase, anim, frame)` con piernas de cajas que caminan (`extra.Peaton`). Escala 5: busto ≈ 4 u, de pie ≈ 6 u.
- Trucos de la textura: el borde derecho de la cara da la vuelta a la nuca, por eso se funde con la piel (si no sale el fondo de la foto); la nariz del modelo
  usa la esquina inferior derecha de la textura (color de piel); `ancho` es el medio ancho de la cara en veces ojos-barbilla: 0,72 por defecto; **más ancho = cara menos estirada** (Alega y Vivi, de cara estrecha, quedan bien con 0,86; con 0,66 salen anchas y no se reconocen), y el fundido hacia la piel se desplaza con él; el calvo se aclara
  (`brillo_calvo`). Con el piloto de Luigi la malla da artefactos: se usa la de Mario para todos.
- Encuadre: la cara de un piloto sentado está ≈ 3,6 u sobre el suelo del kart; de pie ≈ 6,1 u locales (Q = 0,72). Apuntar la cámara a la frente (5,4 u) enseña solo la gorra.
  En un vestíbulo estrecho, la persona que cobra tapa al cliente: se aparta de eje en cada plano (cortes).
- Los materiales `m.solido(...)` **no tienen culling**: se ven por las dos caras. Un cuerpo de edificio cerrado tapa una puerta aunque haya otro objeto detrás,
  y desde dentro de una caja se ve el interior; para huecos (puertas) montar el edificio con varias cajas y forrar el vestíbulo.
- Vídeo «BOLAS NEGRAS»: en `mario_course` el único sitio llano, despejado y sin vallas junto a la calzada es el **lado izquierdo de la recta de s ≈ 75–150**
  (tras la meta); la recta de meta tiene vallas y farolas a 12–20 u de la calzada, y `ridge_course` va por un acantilado.
  El escenario propio se define en un sistema local (`Sitio`) respecto a `Pista.muestra(s, lateral)` con una escala `Q` para encajar con los karts.
- En vertical el ancho visible es 0,5625 × el alto: para encuadrar dos karts de 6 u hace falta una cámara a ≈ 20 u con FOV 56.
