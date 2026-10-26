# Revisión de vídeos

El procedimiento y las órdenes están en la skill `revisar-video` (`python valedores.py revisar info|hoja|frame|audio`). Aquí, los
errores de revisión que ya han ocurrido:

- **Dar por bueno lo que no se ha abierto.** Generar `hoja.png` no es revisarla: hay que leerla como imagen, y además mirar a tamaño
  real los fotogramas con texto, rótulos y cada tipo de gráfico (en miniatura no se ve si un texto de ×1 es legible en un móvil).
- **Revisar la versión anterior.** Las carpetas de revisión se sobrescriben: comprueba que las imágenes son del último render.
- **Texto cortado.** Verifica la frase completa *antes* del cambio de página y con la fuente real; mide con la fuente del juego, no por número de caracteres.
- **Audio “medido, no oído”.** Un espectrograma sin cortes no garantiza que suene bien. Di claramente qué se ha podido escuchar y qué no.
- **Duraciones no enteras.** Usa `round(DURATION * FPS)` fotogramas y `round(DURATION * FS)` muestras; no asumas segundos enteros.
- **Pico de audio tras AAC.** Mídelo en el MP4 final, no en el WAV intermedio.
- **Huecos negros / texturas sin asignar / caras de modelos al revés.** Suelen aparecer solo en ciertos ángulos o planos: mira un fotograma de cada plano.
- **Imágenes del usuario.** Antes de decir que falta una, búscala por su nombre real en `entrada/` y ábrela; un error de lectura previo no prueba que no exista.
- **Decodificar entero.** `ffmpeg -v error -i video.mp4 -f null -` debe terminar sin mensajes.

Entrega: ruta del MP4, duración, qué se comprobó, qué no, y el comando para regenerarlo.
