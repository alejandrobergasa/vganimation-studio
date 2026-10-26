# Mario Party DS: recursos de la ROM

## Cobertura inicial

- La ROM A8TP contiene 706 entradas FAT; la mayoría de los recursos con nombre están en `data/*.bin`.
- Los archivos BIN pueden ser flujos LZ10 completos o tablas de miembros. Las tablas contienen cantidad u32 y pares offset/longitud; el offset es relativo al byte 4.
- Los miembros pueden contener a su vez recursos comprimidos; se recorren hasta seis niveles.
- SDAT: se conservan secuencias, bancos, archivos de ondas y streams nativos. Los WAV son muestras de instrumentos; no canciones sintetizadas.
- Pendiente: interpretar los formatos propios de modelos, animación, tableros y minijuegos; no hay motor de vídeo.

## Uso

```powershell
python valedores.py extraer mario-party-ds
python valedores.py extraer mario-party-ds --rapido
```

Resultado: biblioteca/mario-party-ds/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa queda a cargo del usuario; no está validado todavía el catálogo completo de esta ROM ni un vídeo de prueba.

## Referencias de formatos

- [Mario Party DS Editor: sistema de archivos y compresión](https://github.com/aleokdev/mario-party-editor)
