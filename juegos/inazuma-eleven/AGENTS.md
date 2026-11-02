# Inazuma Eleven

Soporte actual: **extracción y motor de vídeo**, código YEES. Escenas 2D con mapas y retratos PAC, capas animadas, fuente NFTR y voz SADL de la ROM.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Los personajes del escenario son los sprites RPG pequeños de `spr/char`: usa `Recursos().personaje()`.
  Una foto se adapta a ese sprite por defecto; consulta `conocimiento/personajes-desde-fotos.md`.
- Usa el escenario real con `Recursos().escenario()` y `Video.plano_rpg()`: cámara y actores comparten píxeles
  lógicos y una única ampliación. `*_mn` es minimapa. Orienta con `Recorrido`/`ActorDireccional` y exige ocho vistas.
- Usa la skill recursos-inazuma-eleven para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('inazuma-eleven').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas unitarias no necesitan ROM. Las pruebas de integración del motor usan la extracción local.
- El motor se importa desde rutas.motor_dir('inazuma-eleven'); usa la skill cinematica-inazuma-eleven y conocimiento/motor-video-nds.md.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
