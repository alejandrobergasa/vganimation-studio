# Mario Party DS

Soporte actual: **extracción y motor de vídeo**, código A8TP. Escenas 3D con tableros y personajes HBDF, animaciones nativas ANMF, caras de foto sobre el modelo, interfaz 2D, música, voces y efectos SDAT.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Usa la skill recursos-mario-party-ds para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('mario-party-ds').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas unitarias no necesitan ROM. Las pruebas de integración del motor usan la extracción local.
- El motor se importa desde rutas.motor_dir('mario-party-ds'); usa la skill cinematica-mario-party-ds y conocimiento/motor-video-nds.md.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
