# «Mario: todo al rojo»

Revisión 3: vídeo vertical 1080×1920, 30 fps, 40 segundos, H.264/AAC.
El compositor trabaja a 216×384 y amplía x5 sin suavizar.
La primera versión queda conservada en `.cache/nsmb/casino/version_anterior.mp4`.

Regenerar desde la raíz:

```powershell
python -I juegos/nsmb/tools/extraer_casino.py
python -I juegos/nsmb/video/casino_3d.py --preview
python -I juegos/nsmb/video/make_video.py --casino
python valedores.py revisar hoja salida/nsmb/mario_casino_vertical.mp4 3 5
python valedores.py revisar frame salida/nsmb/mario_casino_vertical.mp4 22
python valedores.py revisar audio salida/nsmb/mario_casino_vertical.mp4
```

Salida: `salida/nsmb/mario_casino_vertical.mp4`.
También se guarda `salida/nsmb/mario_casino_vertical_v3.mp4` para distinguir esta revisión.
Se conserva `salida/nsmb/mario_casino_vertical_v2.mp4`.
Las otras cinemáticas se conservan y siguen usando sus opciones anteriores.

Los personajes, animaciones, casino, monedas, fuente y sonidos vienen de la ROM.
El casino se extrae de `ARCHIVE/casino.narc`; los Toads proceden de
`ARCHIVE/luigi_model_mg.narc/kino_d.nsbmd`, con `kino_wait` y `kino_walk`.
La ruleta roja y negra es una adaptación autorizada expresamente por el usuario:
geometría nueva con texturas de la ROM, 37 casillas y bola animada que termina en el 15 negro.
La ruleta se proyecta como un disco en el mismo espacio 3D que los personajes.
Peach usa un gesto de su animación original; la ROM no incluye una animación de crupier.

`casino_3d.py` fija posiciones y alturas mundiales: Mario 13 unidades, Luigi 13,5,
Peach 14, Bowser 19, Toads 8,6 y Koopas 10,5. Los cambios de plano mueven la cámara,
sin ampliar cada personaje por separado. Los modelos completos, sus cabezas y el
casino se dibujan juntos con perspectiva, recorte cercano y búfer de profundidad.
El suelo continúa la textura original con la misma transformación UV y la misma luz.
Las sombras de contacto y los gestos están anclados al suelo del escenario.
El rasterizador `casino_render3d.py` usa Numba para conservar los píxeles y las
texturas de la ROM sin introducir filtrado. Requiere numpy, Pillow, ndspy, Numba, SciPy y ffmpeg.

En la revisión 3 se respetan los parámetros nativos de cada material: repetición
en espejo en S/T, escala UV, caras posteriores, transparencia y paleta. Los ojos
de Mario y Luigi usan sus patrones NSBTP originales para parpadear.
`casino_motion.py` interpola el esqueleto a tiempos fraccionarios, mezcla las
rotaciones mediante cuaterniones y enlaza las acciones durante 160 ms.
Los clips de reacción, ataque y derrota se ejecutan una sola vez. Los ciclos
de locomoción y reposo cierran con una transición de cinco fotogramas DS.
Los agarres elevan al Toad desde el suelo sin saltar su posición y los giros
de Mario y los testigos son continuos.

Auditoría: `python -I juegos/nsmb/video/revisar_casino.py`. Comprueba 16 materiales,
24 clips, 58 transiciones, 12 cierres de bucle y genera vistas de los seis
personajes por delante, detrás y a ambos lados, además de secuencias de movimiento.
Los informes y las imágenes se guardan en `.cache/nsmb/casino_3d/pulido/`.

La música es una partitura nueva para cada escena, sintetizada con los instrumentos
SBNK y las muestras SWAR del banco `BANK_CHIJO_BGM` de la ROM. No requiere un SF2 externo.
Los diálogos se muestran en español con `font_a.NFTR`; el sonido es balbuceo de
videojuego a partir de las voces originales, sin doblaje de las frases completas.
Se conserva «LET IT RIDE!» tal como se pidió.

La pista adicional contiene 35 vocalizaciones sincronizadas (10,3 segundos de
clips, además del balbuceo de los diálogos): dudas de Luigi, esfuerzos de Mario,
risas de Bowser y reacciones de Peach. Para los clientes se reutilizan breves
granos vocales de la ROM con el tono adaptado; no hay doblaje externo.
Se recortan los silencios iniciales y baja la música durante las reacciones.
Pista e inventario: `.cache/nsmb/casino_3d/voces_personajes.wav` y `voces_personajes.json`.

La segunda petición del usuario añade sangre estilizada: explosiones rojas y gotas
tridimensionales con gravedad y colisión contra el suelo, mesas, máquinas y paredes.
Cada mancha permanece en el punto de impacto y participa en el mismo búfer de
profundidad. Los guantes de Mario se manchan y conservan ese color durante la lucha.
No se muestra anatomía explícita ni desmembramientos.

Procedencia base: `biblioteca/nsmb/extraidos/casino/procedencia.json`.
Posiciones, escalas y eventos de esta versión: `.cache/nsmb/casino_3d/escena.json`.
Partitura reproducible: `.cache/nsmb/casino_3d/partitura.json`.
Revisión visual: `.cache/nsmb/casino_3d/storyboard_visual.png` y `movimiento_ataques.png`.
La ROM se abre sólo para lectura.
