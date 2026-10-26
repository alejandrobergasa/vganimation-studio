# Storyboard — «Todo al rojo», revisión de puesta en escena

Vertical 9:16, 216×384 → 1080×1920, 30 fps, 40 segundos.
Todos los personajes, la mesa y los objetos se renderizan juntos en un espacio 3D,
con cámara compartida, escala métrica constante, sombras de contacto y búfer de profundidad.
Los cortes cambian la cámara; nunca el tamaño del modelo ni su posición en el casino.
Casino y modelos originales de la ROM. Ruleta nueva ya autorizada con texturas originales.
La revisión del usuario autoriza sangre estilizada: partículas rojas balísticas y manchas
persistentes sobre suelo, mobiliario y pared, sin anatomía explícita ni desmembramientos.
Fuente NFTR y música propia con muestras SBNK/SWAR del juego. ROM de sólo lectura.

| Tiempo | Acción | Sonido y diálogo |
|---|---|---|
| 0–2,5 | Entrada con travelling: Mario avanza decidido, Luigi lo sigue con dudas. Bowser y Peach permanecen en sus puestos. | Swing rápido, pasos. |
| 2,5–6 | Luigi se detiene y retrocede; mira a Mario y hacia la salida. | «Mario, me da miedo apostar. Vámonos.» |
| 6–9 | Mario se inclina y empuja una pila de monedas sobre el rojo; Luigi intenta frenarlo. | «¡Todas mis monedas al rojo!» y cascada de monedas. |
| 9–14 | Bowser se ríe, intercambia miradas con Mario y señala la mesa. | «Lo que a la rule le das, la rule te lo quita.» en dos páginas fluidas. |
| 14–15,7 | Mario exige seguir y golpea el borde de la mesa. | «LET IT RIDE!» |
| 15,7–17 | Peach lanza la bola con un gesto y sigue su trayectoria. | «¡No va más!» |
| 17–22 | Ruleta 3D con giro, bola, frenada y miradas; dos cortes breves y coherentes de cámara. | Redoble corto, clics de la bola y frenada. |
| 22–24,7 | Bola en 15 negro. Peach recoge las monedas; Mario muestra las manos vacías. | «Negro.» / «¡MIS MONEDAS!» Corte musical. |
| 24,7–31 | Mario se da la vuelta, persigue y agarra a tres Toads; impactos violentos, sangre roja que salpica y deja manchas en el casino. | Música de caos, golpes secos, gritos breves del juego. |
| 31–36 | Koopas entran por la salida, cortan la carrera de Mario, lo rodean y lo derrotan. Las manchas anteriores permanecen. | Marcha urgente, impactos y derrota. |
| 36–40 | Iris sobre Mario derrotado, remate corto de Luigi y GAME OVER. | «Te dije que nos fuéramos.» Cadencia final. |

Regenerar: python -I juegos/nsmb/video/make_video.py --casino
Salida: salida/nsmb/mario_casino_vertical.mp4

## Revisión 3 — texturas, continuidad y voces

Se conservan los 40 segundos y el montaje de la revisión 2.
Revisar todos los materiales de Mario, Luigi, Peach, Bowser, Toad y Koopa:
repetición en espejo, paletas, escalado UV, caras visibles y transparencia.
Comparar frente, perfiles y espalda de cada modelo y mirar secuencias alrededor
de cada cambio de pose. Las acciones de una sola ejecución no deben reiniciarse;
mezclar las poses y los giros durante las transiciones y elevar al Toad desde el suelo
sin saltos de posición. Añadir respiraciones, dudas, risas, esfuerzos, alarmas y
reacciones de los personajes mediante los clips originales de la ROM.
Exportar la revisión como salida/nsmb/mario_casino_vertical_v3.mp4 y conservar v2.
