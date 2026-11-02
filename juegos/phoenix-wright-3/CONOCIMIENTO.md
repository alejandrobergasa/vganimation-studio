# Phoenix Wright: Ace Attorney – Trials and Tribulations: recursos de la ROM

## Personajes personalizados desde fotos

Adapta por defecto la identidad a bustos y poses anime en el estilo y resolución de los gráficos DS de `data.bin`.
Usa las poses nativas como referencia visual. No pegues una cara fotográfica sobre un cuerpo procedural.
`Recursos().personaje_personalizado(nombre, pose)` carga un manifiesto y atlas revisado en el proyecto activo;
una sola pose no aporta por sí sola animación de boca, parpadeo o gesto. Genera las variantes que necesite el guion.
Procedimiento, formato y límites: `conocimiento/personajes-desde-fotos.md`.

`video/juicio.py` aporta `Busto` (pose hablante mientras se escribe y quieta al acabar), `impacto` (destello breve,
líneas de velocidad y sacudida amortiguada), `rotulo_impacto` (rótulo con entrada rápida) y `banda_sonora`
(programa de pistas SSEQ por escena con pausas y ducking alrededor de los golpes). Se exportan desde `motor.py`.
Las poses dibujadas adicionales se cargan con `animaciones.<pose>.imagen/rejilla` en el manifiesto, conservando
el retrato canónico aprobado. Los diálogos políticos y del juicio de bolas_phoenix son ficción de parodia.
`Video.renderizar(nombre,audio_redes=True)` aplica dos pasadas de loudnorm a −16 LUFS y techo −2 dBTP antes
de AAC, conservando el vídeo. Requiere verificar la sonoridad y el pico del archivo final tras codificar.

## Cobertura inicial

- La ROM YG3Y contiene 15 archivos NitroFS. `data.bin` agrupa gráficos y otros recursos sin un índice global; no debe tratarse como un único flujo LZ aunque comience por 0x10.
- `mes_all.bin` contiene cantidad u32 y pares offset/longitud absolutos. Se separan sus scripts y se descomprimen cuando el flujo es compatible; siguen siendo scripts binarios, no transcripciones.
- `sound_data.sdat` contiene secuencias y bancos; se exportan formatos nativos y muestras WAV.
- Pendiente: gráficos sin cabecera, lector NFTR/binario de la fuente (hay una reconstrucción en fuente_rom.py, ver más abajo) y codificación de diálogos, y reconstrucción completa de guiones. El motor ya localiza gráficos con cabecera en YG3Y y sintetiza música SDAT.
- No aplicar mapas de offsets de las versiones inglesa o japonesa a esta ROM.

## Uso

```powershell
python valedores.py extraer phoenix-wright-3
python valedores.py extraer phoenix-wright-3 --rapido
```

Resultado: biblioteca/phoenix-wright-3/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa se ha ejecutado y el motor dispone de una prueba de integración en proyectos/prueba_motor_phoenix_wright_3/.

## Referencias de formatos

- [Phoenix Tools: separación de mes_all.bin](https://github.com/Missingmew/phoenixtools/blob/master/extract-mes_all-bin.c)
- [Phoenix Tools: mapas de data.bin específicos por región](https://github.com/Missingmew/phoenixtools)

## Motor de vídeo

Escenas 2D con gráficos y poses de data.bin, capas, cámara animada y música SDAT.

Entrada: video/motor.py (Video, Recursos, Plano, Clip, Fuente, Superposicion, interpolar).
Implementación compartida en nucleo/valedores/video_nds.py, activos_video_nds.py, modelos_video_nds.py y sonido_video_nds.py.
Consulta conocimiento/motor-video-nds.md para la API, un ejemplo y las limitaciones de cada formato.
Prueba: python -I juegos/phoenix-wright-3/video/demo.py [--formato vertical].
La geometría 3D HBDF/BMD se carga en pose de reposo; ANMF/BCA siguen pendientes. Esto no impide animar la cámara y las capas.

## Fuente de texto (reconstruida de la ROM) y límites de texto

- La ROM YG3Y es **español/italiano** (`spanish/` e `italian/` en NitroFS). No trae NFTR ni un lector de la fuente de diálogo, pero los gráficos
  con cabecera de `data.bin` incluyen **208 descripciones del Expediente en español** (índices 1743–1950 de `Recursos.graficos_phoenix()`;
  las italianas son 1527–1742): tiras 256×64 en blanco, 3 líneas con paso de 14 px, línea base en la fila 11 de cada línea.
- `juegos/phoenix-wright-3/video/fuente_rom.py` (`FuenteRom(recursos).texto(...)`) segmenta esas tiras por columnas vacías, agrupa los glifos
  idénticos y los nombra con `glifos_fuente.json` (hash de la forma → carácter). Atlas en `extraidos/fuente_atlas.json` (se regenera).
  Cada glifo lleva su avance medido (casi siempre ancho + 2 px; `N`, `L`, `4`… difieren) y el espacio entre palabras mide 6 px extra.
  Verificado: 5 tiras reescritas con el atlas coinciden píxel a píxel. `"` son dos `´` seguidos (2.º con avance 4).
- Cobertura: a-z, A-Y (no `Z`), 0-9, `á é í ó ú ñ Á É ¿ ? ! ( ) : ; , . - / = $ ´ ★ °`. **No** hay `Í Ó Ú Ñ Z`, `€` ni `¡` (este se obtiene girando 180° el `!`).
- Límites medidos en las descripciones: máx. 31 caracteres y 224 px por línea, 3 líneas por ventana.
- Otros textos prerrenderizados en la ROM (nombres de pruebas 815–1314, menús 10–60) usan la fuente de nombres/menú, no se mezclan con este atlas.
- Sala del tribunal, juez, mazo y banners «Testimonio»/«Prueba presentada» **no** están entre los gráficos con cabecera (los fondos 412–486 son
  miniaturas de lugares de 128×128; las poses de Phoenix/Edgeworth 61–110 son bustos sueltos). Los dibujos procedurales
  de `proyectos/bolas_phoenix/arte*.py` fueron una solución del proyecto anterior, no una referencia de estilo ni un fallback
  autorizado por defecto. Localiza y decodifica el recurso, usa un escenario nativo compatible o explica el límite.
- `data.bin` empieza con ≈ 8 MB de bloques LZ10 seguidos (fondos 256×192 de 49664 B, teselas…) todavía sin mapa; ahí estarán sala y sprites.
