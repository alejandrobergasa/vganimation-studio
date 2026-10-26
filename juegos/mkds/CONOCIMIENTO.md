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
- `biblioteca/mkds/extraidos/audio/catalogo_audio.csv` (duración/pico/rms). Ids elegidos para cada cinemática: ver su storyboard.

## Motor de render (`video/mk/`)
- Rasterizador numba propio (perspectiva correcta, z-buffer, mipmaps trilineales, niebla, recorte near, repetición/espejo por material, culling por material), 2 pasadas: opacos/recortes y mezcla/aditivo (ordenados por z).
- Cielo: `course_model_V` como capa < 0 anclada a la cámara; el color de niebla sale de la franja de horizonte del propio cielo.
- Render paralelo con `multiprocessing` (spawn): cada proceso construye la escena; `cuadro(t)` debe ser puro.
- Partículas: trayectoria cerrada (p0 + v·a + ½·g·a², con arrastre opcional) para evaluar cualquier t.
- Fallos resueltos: tex 4D en numba (`tex[mi]`), vecinos de mip en niveles pequeños, ejes (+x = izquierda del kart), signo de `curv`, ruedas que giran con `rot_x(+giro)`.
- Pendiente / ideas: animaciones de textura de circuito (`course_model.nsbta`: agua, lava), `nsbtp` de objetos, objetos de circuito (OBJI → modelos de `MapObj`), colisión KCL, SPA (partículas del juego), escenas `Scene/*.carc` (podio, créditos).
