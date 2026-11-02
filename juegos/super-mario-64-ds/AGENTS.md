# Super Mario 64 DS

Soporte actual: **extracción y motor de vídeo**, código ASMP. Escenas con modelos 3D BMD, materiales y texturas nativos, cámara animada, capas y música SDAT.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Usa la skill recursos-super-mario-64-ds para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('super-mario-64-ds').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas unitarias no necesitan ROM. Las pruebas de integración del motor usan la extracción local.
- El motor se importa desde rutas.motor_dir('super-mario-64-ds'); usa la skill cinematica-super-mario-64-ds y conocimiento/motor-video-nds.md.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
