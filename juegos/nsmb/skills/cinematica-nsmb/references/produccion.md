# Producción, diálogo y audio

Leer las secciones pertinentes al montaje actual. Los valores siguientes son
ejemplos que funcionaron en el vídeo vertical, no parámetros obligatorios.
Las rutas de código son relativas a `juegos/nsmb/`.

## Encuadre vertical y píxel

- El compositor original es 256×192; cambiar sólo el tamaño de salida lo deforma.
  El montaje vertical usa 216×384 lógicos y escalado entero ×5 a 1080×1920, a 30 fps.
  Componer en ese encuadre desde el principio y exportar con vecino más cercano.
- Enviar resolución lógica por `stdin` a ffmpeg y escalar con
  `scale=1080:1920:flags=neighbor` evita transferir cada fotograma ya ampliado desde Python.
  H.264 con `yuv420p`, AAC y `+faststart` están implementados en `video/renfe.py`.
- Un vídeo vertical necesita planos generales para reconocer el objeto y cercanos
  para la acción; comprobar que el morro, la puerta y el logo no queden siempre fuera.
  Eliminar rótulos puede exigir recomponer el plano para no dejar espacios sin propósito.
- `engine.tile_h()` sirve para capas de parallax. Añadir primer término y pequeñas
  aproximaciones de cámara cuando aporten profundidad; evitar vibración continua o
  transiciones que tapen la acción y el diálogo.
- Al repetir suelo recortado del nivel real, revisar su alfa: puede contener pozos.
  Para una escena nueva de campo continuo, seleccionar un tile opaco; no rellenar
  los huecos del nivel real si se está reproduciendo ese nivel.
- La iluminación puede contar el cambio de escena sin un mensaje: sol móvil en
  el viaje, apagón, rojo localizado de alarma y luz fría de una pantalla.
  Mantener visibles las siluetas importantes; un vagón oscuro no debe ocultar toda la acción.
- Precargar/cachar ciclos de sprites y texto evita renderizar modelos 3D en cada frame.

## Imágenes y logos autorizados

- Localizar y abrir el archivo antes de integrarlo. El montaje actual recibe
  `oscarpuente.jfif` y `renfelogo.png`; no son assets extraídos de la ROM.
  Viven en `biblioteca/nsmb/personalizados/`, no en `extraidos/`, que es regenerable.
- Adaptar la resolución dentro del compositor conservando el original. Ejemplo de
  retrato: reducir a 52×66 y mostrar a 104×132 con vecino más cercano, antes del ×5 final.
  Es una elección estética, no la resolución obligatoria de todos los retratos.
- Para un logo real usar su imagen y proporción, no reescribir su nombre con NFTR.
  En el logo morado sobre blanco se recortó el margen y se creó alfa antes de reducir.
  Esa máscara depende del fondo y color originales: no aplicarla ciegamente a otro logo.
- Verificar las letras a tamaño lógico y en el MP4 ampliado: al reducir demasiado
  desaparecen trazos; el fondo blanco puede producir un rectángulo o halos.
  Un logo pequeño en el plano general puede necesitar un plano cercano legible.
- Un archivo aportado no demuestra una atribución concreta. Registrar la procedencia
  conocida y no arrastrar el crédito de otra imagen que sólo se buscó antes.

## Cronología y frases completas

En `video/renfe_audio.py` están `PAGES`, `TEXT_CPS`, `DIALOGUE_END`, `DEATH_T`,
`IRIS_T`, `GAMEOVER_T` y `DURATION`; el compositor importa esas constantes.
Usar esa relación al modificar esta escena en lugar de duplicar segundos a mano.

- Cada página contiene una unidad legible. Si el usuario pide conservar una frase
  completa, no separarla entre páginas aunque quepa por partes.
- Medir con la fuente real (`text.size()` o `lettering().width`), no por número
  fijo de caracteres. `dialogue_lines()` calcula el layout completo; después se
  revelan caracteres sobre esas líneas fijas. Así las palabras no cambian de línea al escribir.
- En el ejemplo caben 178 píxeles por línea en el panel. Verificar también altura,
  contornos y acentos. El remate protegido «un glazing al perro» ocupa una línea
  dentro de una página que contiene toda su frase; no trasladar ese texto a otro guion.
- Con escritura progresiva, comprobar el tiempo **después** de completarse el texto:
  `espera = fin_pagina - inicio_pagina - len(frase) / TEXT_CPS`.
  20 caracteres/s y pausas completas de 2,5–4,2 s funcionaron aquí; ajustar a la frase.
- Alargar el diálogo desplaza también el cierre y la derrota. Reservar margen para
  la última sílaba y su cola, y revisar un fotograma justo antes de cerrar.
- Para duraciones como 49,5 s, usar `round(DURATION * FPS)` fotogramas y una mezcla
  de `round(DURATION * FS)` muestras. No suponer que la duración es entera.

## Música nueva con instrumentos del juego

No hace falta descargar un SF2 para componer con este proyecto. La ROM aporta
SBNK/SWAR/SWAV y `tools/nsmb/sonido.py` ya los sintetiza.
Cambiar o recortar una BGM no equivale a componer música original.

```python
# Con tools/nsmb en sys.path, como hacen los scripts del repo.
import rom, sonido
son = sonido.Sonido(rom.find_rom())
# inicio_s, duración_s, tecla MIDI, velocidad, programa, panorama, volumen
notas = [(0.0, 0.18, 72, 100, 13, 64, 105)]
pcm = sonido.tocar_notas(son, 'BANK_CHIJO_BGM', notas, segundos=1.0)
```

- Los programas válidos dependen del banco; inspeccionar sus instrumentos y probar
  unas notas antes de componer todo. Un número vacío puede producir silencio.
- El patrón de `renfe_audio.score()` cambia motivo, armonía, tempo e instrumentación
  por escena; adaptar la composición al guion. Distinguir música instrumental,
  efectos y balbuceo, según lo que haya pedido el usuario.
- Guardar las notas y programas (`partitura.json` en el ejemplo) y los WAV de las
  piezas facilita revisar y rehacer la mezcla sin perder la composición.
- `sonido.FS` es 32768 Hz. Respetar el rate al leer efectos y remuestrear al exportar;
  no reinterpretar sus muestras como 44,1/48 kHz.

## Efectos, diálogo y mezcla

- Reutilizar `biblioteca/nsmb/extraidos/audio/efectos/*.wav` cuando ya están extraídos.
  Algunos SE son bucles que corta el juego: recortar su duración y suavizar la cola.
  `SE_OBJ_BLOCK_KICK` y `SE_PLY_KICK` resultaron mudos; usar un efecto comprobado.
- El primer diálogo usaba el mismo cursor repetido; para balbuceo de videojuego
  funcionan mejor fragmentos vocales cortos con pausas, variación de tono y acento.
  Es un efecto estilizado, no una voz hablada ni una imitación de la persona del retrato.
- `dialogue()` usa zonas sonoras de `SE_VOC_OPDM_UN_01`, `SE_VOC_OPDM_UN_02` y
  `SE_VOC_LU_HOH`: granos de unos 79 ms, sin offset DC, con rampas y filtrado suave.
  Evitar seleccionar el silencio de entrada o cortar un grano sin envolvente.
- Situar cada sílaba en el mismo reloj que revela las letras. Una cadencia fija de
  pitidos en cada espacio suele sonar mecánica. Escuchar el efecto si es posible.
- Bajar música y alarma durante las frases con rampas suaves; `speech_envelope()`
  aplica esa atenuación compartida. Una reverberación corta puede integrar la transmisión
  sin enturbiar las palabras. Conservar el impacto del choque y la pausa del apagón.
- Dejar margen al mezclar. Como punto de partida para redes puede usarse
  `loudnorm=I=-16:TP=-1.5:LRA=8`, midiendo después el AAC final: sus picos pueden cambiar.
  No afirmar que se alcanzó un objetivo sólo por haber escrito ese filtro.
- Espectrograma y onda sirven para detectar cortes, saturación y silencios; no prueban
  por sí solos que una melodía o un balbuceo suenen bien. No describir una escucha no realizada.

## Cierre de una revisión

Usar `python valedores.py revisar` (skill `revisar-video`) con la ruta explícita del MP4 final. La hoja mantiene la
proporción; extraer además planos completos de texto y de cualquier asset nuevo.
Comprobar que las pruebas corresponden a la última versión y no a imágenes previas.
Documentar duración, resultado real del audio y cómo regenerar; conservar la entrega
anterior y dar un enlace inequívoco a la nueva. No es necesario volver a renderizar
un vídeo cuando sólo se modifican instrucciones o documentación.
