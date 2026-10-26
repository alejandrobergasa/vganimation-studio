# Phoenix Wright: Ace Attorney – Trials and Tribulations: recursos de la ROM

## Cobertura inicial

- La ROM YG3Y contiene 15 archivos NitroFS. `data.bin` agrupa gráficos y otros recursos sin un índice global; no debe tratarse como un único flujo LZ aunque comience por 0x10.
- `mes_all.bin` contiene cantidad u32 y pares offset/longitud absolutos. Se separan sus scripts y se descomprimen cuando el flujo es compatible; siguen siendo scripts binarios, no transcripciones.
- `sound_data.sdat` contiene secuencias y bancos; se exportan formatos nativos y muestras WAV.
- Pendiente: mapa de offsets de data.bin para esta región YG3Y, gráficos/personajes/fuentes, codificación de diálogos, síntesis de música y motor de juicios.
- No aplicar mapas de offsets de las versiones inglesa o japonesa a esta ROM.

## Uso

```powershell
python valedores.py extraer phoenix-wright-3
python valedores.py extraer phoenix-wright-3 --rapido
```

Resultado: biblioteca/phoenix-wright-3/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa queda a cargo del usuario; no está validado todavía el catálogo completo de esta ROM ni un vídeo de prueba.

## Referencias de formatos

- [Phoenix Tools: separación de mes_all.bin](https://github.com/Missingmew/phoenixtools/blob/master/extract-mes_all-bin.c)
- [Phoenix Tools: mapas de data.bin específicos por región](https://github.com/Missingmew/phoenixtools)
