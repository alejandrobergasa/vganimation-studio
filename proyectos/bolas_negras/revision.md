# Revisión — BOLAS NEGRAS

Vídeo revisado: `salida/bolas_negras/bolas_negras.mp4` (render final tras la corrección de la escena 9).

## Comprobado (con herramientas, no a oído)
- **Archivo**: 1080×1920, 30 fps, 36,0 s, H.264 `yuv420p` + AAC estéreo (32 kHz), 39,5 MB. Se decodifica entero sin errores (`ffmpeg -f null`).
- **Audio medido**: pico −0,7 dB, media −18,2 dB, sin silencios largos; en el espectrograma se distinguen las secciones de la música, las voces
  (marcas verticales cortas en cada diálogo) y el golpe final a 32,5 s.
- **Hoja de contactos** (1 fotograma cada 2 s) y fotogramas a tamaño real en 1,0 · 9,0 · 14,6 · 17,5 · 20,0 · 22,8 · 26,0: título completo,
  caras reconocibles, texto con la fuente del juego dentro de la zona segura, escenas en el orden del storyboard, QUEBUSCA a pantalla completa
  desde 34,0 s.
- **Texto** (ortografía y tildes): «¡QUÉ GANAS TENGO DE VER LA BOLA NEGRA!», «¡Y YO! LLEVO UNA SEMANA ESPERANDO.», «DICEN QUE ES SÚPER NEGRA.»,
  «¡CUANTO MÁS NEGRA, MEJOR!», «BUENAS. LA ENTRADA SON 10 EUROS.», «¡TOMA, CON GUSTO!», «¡Y LOS MÍOS!», «PASEN, PASEN.», «ESTO ES UNA LOCURA.»,
  «NO PUEDE SER QUE DOS HOMBRES CRECIDOS PAGUEN POR VER BOLAS NEGRAS.», «¿QUÉ BUSCAN?». Coinciden con el guion aprobado.

## Corregido durante el render y la revisión
- Caras de Alega y Vivi estiradas → más ancho de foto (`ancho` 0,86) y fundido lateral hacia la piel.
- Escena 9 (22–24 s): Pedro se salía por el borde derecho al apartarse → se aparta menos (x 3,3) y la cámara encuadra el conjunto.

## No se pudo comprobar / límites
- **No he visto el vídeo en movimiento ni he oído el audio**: solo fotogramas fijos y medidas. Sincronía de voces y efectos con el
  rótulo, equilibrio música/voces y gusto de la mezcla quedan para tu escucha.
- Durante el giro de Santos (≈ 25,8–26,3 s) su cara se ve de perfil y la textura frontal se parte un instante.
- A ≈ 22,8 s Alega, al entrar, tapa en parte a Pedro durante unas décimas.
- Primeros planos de Alega y Vivi (6,5, 9,0, 20,0 y 21,5 s): la boca sigue algo ancha por la propia cabeza del piloto del juego.
