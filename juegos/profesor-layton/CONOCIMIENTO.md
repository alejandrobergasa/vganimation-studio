# El profesor Layton y la villa misteriosa: recursos de la ROM

## Cobertura inicial

- La cabecera A5FP contiene el título interno LAYTON1. Se han observado 4265 entradas FAT.
- ARC/ARJ/BGX pueden llevar un tipo u32 antes de la compresión BIOS: 1=RLE, 2=LZ10, 3=Huffman4, 4=Huffman8.
- El lector actual admite LZ10/LZ11 y RLE; Huffman se registra como compresión pendiente y se conserva el original.
- Los fondos bajo `data/bg/` contienen cantidad de colores u32, colores BGR555, cantidad de tiles u32, tiles 8x8 de 8 bpp, ancho y alto en tiles u16 y entradas de mapa u16. Se respetan flips X/Y.
- Las fuentes NFTR se exportan como atlas y mapa de códigos/ancho; el mapa conserva la codificación original de la fuente.
- Pendiente: sprites y clips ARC/ARJ de `data/ani/`, interpretación GDS, audio SADL/PCM y vídeo MODS. ARC es una extensión contextual, no un contenedor NARC.

## Uso

```powershell
python valedores.py extraer profesor-layton
python valedores.py extraer profesor-layton --rapido
```

Resultado: biblioteca/profesor-layton/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa queda a cargo del usuario; no está validado todavía el catálogo completo de esta ROM ni un vídeo de prueba.

## Referencias de formatos

- [Tinke: estructura de fondos](https://github.com/pleonex/tinke/blob/master/Plugins/LAYTON/LAYTON/Bg.cs)
- [LaytonEditor: envoltorios de compresión](https://github.com/C3RV1/LaytonEditor/blob/master/formats/compression/__init__.py)
