# Super Mario 64 DS: recursos de la ROM

## Cobertura inicial

- La ROM ASMP tiene 2175 entradas FAT; incluye 13 contenedores NARC y `data/sound_data.sdat`.
- Muchos BMD/BCA/BTP llevan el envoltorio ASCII LZ77 seguido de un flujo LZ10. Otros binarios de gráficos también usan LZ10 sin envoltorio.
- Los NARC se abren con ndspy y se conserva la procedencia y el nombre de cada miembro.
- Los BMD de SM64DS son un formato propio: no se pueden enviar al lector Nitro BMD0 de NSMB/MKDS sólo por su extensión.
- Pendiente: animaciones BCA, cambios de textura BTP, colisiones KCL, mapas y fuente. El motor ya lee modelos BMD en pose de reposo, con materiales y texturas.

## Uso

```powershell
python valedores.py extraer super-mario-64-ds
python valedores.py extraer super-mario-64-ds --rapido
```

Resultado: biblioteca/super-mario-64-ds/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa se ha ejecutado y el motor dispone de una prueba de integración en proyectos/prueba_motor_super_mario_64_ds/.

## Caras de foto sobre BMD

`video/personajes.py` proyecta una foto sobre la malla de la cabeza de `data/player/b_mario_all.bmd`:

- `atlas_cara(modelo, 'mat_bm_head', foto, hitos, pelo=...)` rasteriza la malla en su atlas UV y proyecta la foto desde
  delante; la piel de los laterales se tiñe al tono muestreado de la foto. Devuelve un atlas RGBA ×4.
- `cara(vista, foto, hitos, ...)` lo aplica con `VistaModelo.reemplazar_textura(..., escala=4)`, que multiplica la
  resolución del atlas y las UV del material. Oculta `mat_bm_eye` (parches de ojos/boca nativos) y, con `sin_gorra=True`,
  `mat_bm_head_c` (la gorra). El material de la cabeza es `mat_bm_head`, textura `t2_p2` (32×64 nativa).
- `hitos` = (fila de los ojos, fila de la barbilla, columna del centro) en píxeles de la foto. Con `pelo=None` la nuca
  y las orejas se pintan del color de piel (calvo); si se pasa una tupla RGB 0..1, se pintan de ese color.
- La textura solo cubre la cara delantera: los planos de tres cuartos muy cerrados muestran el borde del parche. Usar
  planos frontales o tres cuartos suaves.
- El modelo completo `b_mario_all.bmd` está en pose de reposo (sentado, brazos abiertos); no hay BCA aplicado. Para una
  pose de pie habría que montar `mario_model.bmd` + `mario_head_cap.bmd`/`mario_head_nocap.bmd`, que van por piezas.

## Motor de vídeo

Escenas con modelos 3D BMD, materiales y texturas nativos, cámara animada, capas y música SDAT.

Entrada: video/motor.py (Video, Recursos, Plano, Clip, Fuente, Superposicion, interpolar).
Implementación compartida en nucleo/valedores/video_nds.py, activos_video_nds.py, modelos_video_nds.py y sonido_video_nds.py.
Consulta conocimiento/motor-video-nds.md para la API, un ejemplo y las limitaciones de cada formato.
Prueba: python -I juegos/super-mario-64-ds/video/demo.py [--formato vertical].
La geometría 3D HBDF/BMD se carga en pose de reposo; ANMF/BCA siguen pendientes. Esto no impide animar la cámara y las capas.
