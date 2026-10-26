# Inazuma Eleven: recursos de la ROM

## Cobertura inicial

- La ROM YEES tiene 1846 entradas FAT; las entradas sin nombre incluyen overlays.
- `data_iz/` contiene PKB con índices PKH `PackNum 20080626`. Tipos 0: registros de 12 bytes (id, offset, longitud); tipos 2/3: bloques fijos.
- Los PAC contienen cantidad y pares offset/longitud absolutos. La extensión `.pac_` suele señalar LZ10.
- Los modelos Nitro BMD0 y BTX0 permiten exportar texturas con el lector existente de NSMB. Revisar las paletas elegidas antes de usar las imágenes.
- Pendiente: reconstruir sprites de cara/cuerpo, interpretar SPD/SPL/SPF, SADL, MODS y animaciones/modelos para vídeo.

## Uso

```powershell
python valedores.py extraer inazuma-eleven
python valedores.py extraer inazuma-eleven --rapido
```

Resultado: biblioteca/inazuma-eleven/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa queda a cargo del usuario; no está validado todavía el catálogo completo de esta ROM ni un vídeo de prueba.

## Referencias de formatos

- [Tinke: estructuras PAC y PKB/PKH](https://github.com/pleonex/tinke/blob/master/Plugins/INAZUMA11/INAZUMA11/Packs.cs)
