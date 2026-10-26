# Super Mario 64 DS: recursos de la ROM

## Cobertura inicial

- La ROM ASMP tiene 2175 entradas FAT; incluye 13 contenedores NARC y `data/sound_data.sdat`.
- Muchos BMD/BCA/BTP llevan el envoltorio ASCII LZ77 seguido de un flujo LZ10. Otros binarios de gráficos también usan LZ10 sin envoltorio.
- Los NARC se abren con ndspy y se conserva la procedencia y el nombre de cada miembro.
- Los BMD de SM64DS son un formato propio: no se pueden enviar al lector Nitro BMD0 de NSMB/MKDS sólo por su extensión.
- Pendiente: decodificar modelos BMD, animaciones BCA, texturas BTP, colisiones KCL, mapas, fuente y motor de vídeo.

## Uso

```powershell
python valedores.py extraer super-mario-64-ds
python valedores.py extraer super-mario-64-ds --rapido
```

Resultado: biblioteca/super-mario-64-ds/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa queda a cargo del usuario; no está validado todavía el catálogo completo de esta ROM ni un vídeo de prueba.
