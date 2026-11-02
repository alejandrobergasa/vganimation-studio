# Phoenix Wright: Ace Attorney – Trials and Tribulations

Soporte actual: **extracción y motor de vídeo**, código YG3Y. Escenas 2D con gráficos y poses de data.bin, capas, cámara animada y música SDAT.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Las fotos de personas se convierten en bustos y poses anime del estilo DS del juego por defecto.
  Sigue `conocimiento/personajes-desde-fotos.md`; carga derivados con `Recursos().personaje_personalizado()`.
- Usa la skill recursos-phoenix-wright-3 para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('phoenix-wright-3').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas unitarias no necesitan ROM. Las pruebas de integración del motor usan la extracción local.
- El motor se importa desde rutas.motor_dir('phoenix-wright-3'); usa la skill cinematica-phoenix-wright-3 y conocimiento/motor-video-nds.md.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
