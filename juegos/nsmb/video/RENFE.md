# Mario coge el RENFE

Vídeo revisado: `mario_renfe_vertical_v3.mp4` (también `mario_renfe_vertical.mp4`).
Duración 49,5 segundos, 1080×1920 (9:16), 30 fps, H.264 y audio AAC estéreo a 48 kHz.
Aproximadamente 17 MB.
Se conservan las entregas anteriores en `mario_renfe_vertical_v1.mp4` y `mario_renfe_vertical_v2.mp4`.

Mario corre por el campo, sube al tren, viaja, sufre un choque de videojuego,
queda a oscuras con una alarma roja, recibe el comunicado y termina en GAME OVER.
La fotografía aportada aparece pixelada y la frase solicitada se muestra completa
en cuatro páginas de diálogo. Sólo permanecen su nombre, sus frases y los textos del final.
Se añaden «espero estéis disfrutando del viajecito a Madrid.» y
«Se está quedando Madrid de puta madre.». El remate completo
«me voy a tuitear un glazing al perro» ocupa una única página y permanece
escrito entero durante 4,2 segundos. «un glazing al perro» comparte una sola línea.
Su diálogo tiene balbuceo de videojuego hecho con granos vocales de la ROM,
acentos y variaciones de tono por sílaba, pausas y una reverberación corta.
No hay voz hablada inteligible ni imitación de su voz. La música y la alarma bajan
mientras se escribe cada frase. La mención de ficción queda en la pantalla final.

El tren tiene carrocería sombreada, cristales con reflejos, cabina con limpiaparabrisas,
faros, bogies de doble eje, suspensión, puertas y detalles de servicio.
Se usan un plano general y un plano cercano para el embarque.
El campo añade vegetación en primer término y polvo al correr; la cámara se acerca
suavemente. El vagón tiene techo detallado, asientos tapizados y bandas de sol móviles.
La alarma ilumina de rojo el interior y la transmisión aporta una luz fría localizada.

## Recursos

- Mario: modelos y animaciones de la ROM, mediante `tools/nsmb/chars.py`.
- Campo: fondos `back_nohara_W1_1` y `free_nohara_W1_1`, suelo y monedas de 1-1.
- Textos: `font_a.NFTR`, dibujada con `video/text.py`.
- Cinco piezas instrumentales originales: campo, viaje, alarma, comunicado y derrota.
  Secuencias nuevas sintetizadas con `BANK_CHIJO_BGM`, extraído de `sound_data.sdat`.
  Se conservan las notas y programas en `.cache/nsmb/renfe/partitura.json` y los WAV de cada pieza.
- Efectos originales de la ROM: pasos, salto, moneda, puertas, barridos, impactos,
  advertencia, ventanas, texto y muerte. Sirena y frenado secuenciados con el banco del juego.
- Tren, interior y tope de vía: pixel art del compositor, excepción
  solicitada para esta historia. Es una representación estilizada, no un modelo ferroviario exacto.
- Logo real: `renfelogo.png`, aportado por el usuario. Se elimina el blanco dentro
  del compositor y se reduce a 56×21 píxeles lógicos, conservando la forma de sus letras.
  El archivo original permanece intacto.
- Retrato: `oscarpuente.jfif`, aportado por el usuario. Se conserva el original;
  el compositor lo reduce a 52×66 y lo muestra con vecino más cercano.
  No se ha verificado su procedencia ni se atribuye a la imagen de Moncloa buscada antes.

La ROM no se ha escrito ni modificado.

## Regenerar

Desde la raíz del proyecto, con Python, Pillow, numpy, ndspy y ffmpeg disponibles:

```powershell
python -I juegos/nsmb/video/make_video.py --renfe
```

Storyboard: `video/storyboard.md`. Escenas: `video/renfe.py`.
Partitura y mezcla: `video/renfe_audio.py`.
El render anterior de Mundo 1-1 sigue disponible mediante el comando sin `--renfe`.

## Revisión realizada

Se han visto la hoja de fotogramas del MP4 revisado, planos completos
del embarque, choque, retrato y GAME OVER, y el espectrograma con la onda.
Se ha comprobado la retirada de cabeceras, comentarios, contadores y onomatopeyas.
Se verificaron los 1485 fotogramas, la duración de 49,5 segundos y la decodificación
completa de vídeo y audio sin errores. Pico de muestras: −1,5 dBFS;
pico real medido: −1,45 dBTP; sonoridad integrada medida: −17,52 LUFS.
Sin recorte a 0 dB ni mesetas de saturación. El apagón y las pausas finales son deliberados.

Material de revisión de esta entrega: `.cache/nsmb/renfe/revision_v3/`.

```powershell
python valedores.py revisar hoja salida/nsmb/mario_renfe_vertical.mp4 2 5
python valedores.py revisar frame salida/nsmb/mario_renfe_vertical.mp4 30
python valedores.py revisar audio salida/nsmb/mario_renfe_vertical.mp4
```
