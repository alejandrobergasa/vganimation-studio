# Storyboard — «Mario coge el RENFE»

Formato vertical 9:16, 216×384 píxeles lógicos → 1080×1920, 30 fps, 49,5 s.
Parodia ficticia. Diálogo escrito con balbuceo de videojuego; música instrumental original.
La petición autoriza las excepciones a los assets de la ROM: tren RENFE dibujado
en pixel art, logo real `renfelogo.png` y fotografía de Óscar Puente aportada por el usuario.
La ROM permanece en sólo lectura. Mario, paisaje, fuente e instrumentos proceden del juego.
Acabado revisado: Mario más cerca, tres planos de parallax en el campo,
polvo al correr, acercamientos de cámara suaves, catenaria y postes en el exterior,
interior con techo detallado, asientos tapizados y rayos de sol en movimiento.
El apagón conserva el ambiente oscuro con una iluminación roja localizada;
la transmisión aporta luz fría al vagón y un pequeño indicador de voz sin texto.

| Tiempo | Acción y transición | Música y efectos |
|---|---|---|
| 0–5 s | Mario corre por el campo y recoge monedas. Parallax y seguimiento, sin títulos ni mensajes. | Composición alegre en do mayor, 150 BPM; pasos, monedas, salto. |
| 5–9 s | Tren redibujado con carrocería sombreada, bogies, cabina y logo real reducido a píxeles. Mario salta al andén y entra. Barrido al interior, sin rótulos. | Variación de llegada; apertura/cierre, aviso de salida. |
| 9–15 s | Mario viaja en el vagón. Campo por las ventanas. Corte al exterior del tren en marcha. | Tema original de viaje, 120 BPM; traqueteo. |
| 15–17 s | Choque de videojuego: sacudida, partículas y frenazo. El tren se detiene y se apaga la luz. | Golpe, bloques rotos y caída tonal. Música cortada; pausa. |
| 17–20 s | Vagón oscuro y alarma roja pulsante, sin mensajes. | Ostinato tenso en do menor, 90 BPM; alarma de dos notas con instrumentos del juego. |
| 20–24,5 s | Retrato pixelado y nombre de Óscar Puente. «chavales RENFE va de puta madre». | Balbuceo de videojuego con granos vocales de la ROM, tono y acentos por sílaba; música y alarma bajan mientras aparece el texto. No imita su voz. |
| 24,5–30,5 s | Página completa: «espero estéis disfrutando del viajecito a Madrid.» | Sílabas sincronizadas y pausa suficiente para leer. |
| 30,5–35,5 s | Página completa: «Se está quedando Madrid de puta madre.» | Continúan música y balbuceo sincronizado. |
| 35,5–41,5 s | Una única página para «me voy a tuitear un glazing al perro». La frase permanece completa en pantalla más de cuatro segundos, sin cambios de página intermedios. | Balbuceo hasta terminar «perro» y cola completa antes de cerrar la transmisión. |
| 41,5–44,5 s | Desaparece el retrato. Mario salta en pose de derrota y cae. Cierre de iris. | Desaparición y muerte; descenso instrumental original. |
| 44,5–49,5 s | «GAME OVER», «MARIO PERDIÓ EL TREN», «CONTINUAR...». | Cadencia original de derrota y sonido de menú. |

Retrato: archivo `oscarpuente.jfif` aportado por el usuario. Se conserva sin modificar.
Logo: `renfelogo.png`, aportado por el usuario; se conserva sin modificar y se adapta dentro del compositor.
Revisión solicitada: se retiran todos los textos ajenos al diálogo y al final, incluidos cabeceras, subtítulos, contadores, onomatopeyas y pie de ficción.
Su procedencia no se ha verificado; no se atribuye a la fotografía de Moncloa buscada previamente.
Regeneración: `python -I juegos/nsmb/video/make_video.py --renfe`.
