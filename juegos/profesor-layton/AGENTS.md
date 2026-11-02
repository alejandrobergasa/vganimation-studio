# El profesor Layton y la villa misteriosa

Soporte actual: **extracción y motor de vídeo**, código A5FP. Escenas 2D con fondos, personajes ARC animados, fuente NFTR, música SDAT y audio SADL.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Usa la skill recursos-profesor-layton para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('profesor-layton').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas unitarias no necesitan ROM. Las pruebas de integración del motor usan la extracción local.
- El motor se importa desde rutas.motor_dir('profesor-layton'); usa la skill cinematica-profesor-layton y conocimiento/motor-video-nds.md.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
