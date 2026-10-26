# Mario Party DS

Soporte actual: **extracción base de recursos**, código A8TP. No hay motor de cinemáticas.

- Lee CONOCIMIENTO.md y el índice conocimiento/README.md antes de trabajar.
- Usa la skill recursos-mario-party-ds para extraer o inspeccionar recursos.
- La ROM nunca se modifica. Los resultados van a rutas.extraidos('mario-party-ds').
- tools/extraer.py delega en nucleo/valedores/recursos_nds.py y nitro.py; los lectores gráficos/audio compartidos están en juegos/nsmb/tools/nsmb/.
- Ejecuta los scripts de juego con python -I; usa valedores.rutas para localizar datos.
- Las pruebas no necesitan la ROM. La extracción completa la ejecuta el usuario cuando lo indique.
- Un archivo original extraído no equivale a un recurso decodificado. Consulta los avisos, errores y formatos pendientes antes de prometer una escena.
- No inventes capturas para vistas/ ni registres formatos de vídeo sin un motor probado.
