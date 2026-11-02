# El profesor Layton y la villa misteriosa: recursos de la ROM

## Cobertura inicial

- La cabecera A5FP contiene el título interno LAYTON1. Se han observado 4265 entradas FAT.
- ARC/ARJ/BGX pueden llevar un tipo u32 antes de la compresión BIOS: 1=RLE, 2=LZ10, 3=Huffman4, 4=Huffman8.
- El lector actual admite LZ10/LZ11 y RLE; Huffman se registra como compresión pendiente y se conserva el original.
- Los fondos bajo `data/bg/` contienen cantidad de colores u32, colores BGR555, cantidad de tiles u32, tiles 8x8 de 8 bpp, ancho y alto en tiles u16 y entradas de mapa u16. Se respetan flips X/Y.
- Las fuentes NFTR se exportan como atlas y mapa de códigos/ancho; el mapa conserva la codificación original de la fuente.
- Pendiente: ARJ de `data/ani/`, interpretación GDS, audio PCM y vídeo MODS. El motor ya interpreta clips ARC y audio SADL IMA/Procyon. ARC es una extensión contextual, no un contenedor NARC.

## Uso

```powershell
python valedores.py extraer profesor-layton
python valedores.py extraer profesor-layton --rapido
```

Resultado: biblioteca/profesor-layton/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa se ha ejecutado y el motor dispone de una prueba de integración en proyectos/prueba_motor_profesor_layton/.

## Referencias de formatos

- [Tinke: estructura de fondos](https://github.com/pleonex/tinke/blob/master/Plugins/LAYTON/LAYTON/Bg.cs)
- [LaytonEditor: envoltorios de compresión](https://github.com/C3RV1/LaytonEditor/blob/master/formats/compression/__init__.py)

## Motor de vídeo

Escenas 2D con fondos, personajes ARC animados, fuente NFTR, música SDAT y audio SADL.

Entrada: video/motor.py (Video, Recursos, Plano, Clip, Fuente, Superposicion, interpolar).
Implementación compartida en nucleo/valedores/video_nds.py, activos_video_nds.py, modelos_video_nds.py y sonido_video_nds.py.
Consulta conocimiento/motor-video-nds.md para la API, un ejemplo y las limitaciones de cada formato.
Prueba: python -I juegos/profesor-layton/video/demo.py [--formato vertical].
La geometría 3D HBDF/BMD se carga en pose de reposo; ANMF/BCA siguen pendientes. Esto no impide animar la cámara y las capas.

### Caras y texto (corregido)

- `Recursos.personaje_layton('layton','talk')` monta cuerpo + `_e_face` con la posición deducida por coincidencia de píxeles (`alinear_cara_layton`).
  No uses posiciones a ojo: con `(38,37)` la boca de Layton salía en la frente; la correcta es `(38,57)`. Si un personaje no encaja
  (error de la función), pasa `posicion=(x, y)` tras comprobarlo con un fotograma ampliado.
- Las NFTR de Layton (`fontevent`, `fontq`) mezclan glifos con avance == ancho de tinta (letras pegadas) y glifos con margen propio
  (`y`, `i`, `.`, `¿`), lo que daba un kerning irregular. `Recursos.fuente()` usa `espaciado=1`: cada glifo se coloca por su tinta con 1 px
  de hueco fijo y el espacio conserva su avance.
- `fontevent` (12 px) es la de diálogo; `font18` es la japonesa y se descarta por la prioridad del español.
