# Mario Kart DS — ROM europea, AMCP

Todo lo que sale en pantalla y en el audio viene de la ROM (más lo que el usuario aporte en `entrada/`, anotado en el brief);
los efectos (partículas, bloom, líneas de velocidad…) son código propio. La ROM no se modifica nunca.
Notas técnicas y fallos resueltos: `CONOCIMIENTO.md`. Flujo de trabajo general: skill `crear-video`.

## Estructura (`juegos/mkds/`)
- `tools/mkds/`: acceso a la ROM y a los `.carc` (`mkrom.py`), `modelos.py`, `nkm.py`. `tools/extraer_mkds.py`: hojas y catálogos →
  `biblioteca/mkds/extraidos/`. Los modelos NO se copian: se leen de la ROM bajo demanda.
- Depende de `juegos/nsmb/tools/nsmb/` (nitro3d, nftr, sonido): es la misma librería Nitro; `video/mk/__init__.py` la añade al path.
- `video/mk/`: motor 3D vertical (escena, raster numba, kart, circuito, carrera, fx, post, cámaras, texto, audio, director).
  `video/mk_demo.py`: cinemática de ejemplo; `video/mk_abalos*.py`: ejemplo con personaje de textura propia (foto en `biblioteca/mkds/personalizados/`).
- Los vídeos nuevos van en `proyectos/<slug>/video.py`.

## Comandos
- Extraer hojas y catálogos: `python valedores.py extraer mkds` (a mano: `python -I juegos/mkds/tools/extraer_mkds.py [--solo ...]`).
- Demo: `python -I juegos/mkds/video/mk_demo.py [--rapido --hoja 16 | --frame 12.5]` → `salida/mkds/mk_demo_carrera.mp4`.

## Reglas
- Texto en español con la fuente del juego (`mk/texto.py`). Nada se da por bueno sin verlo (`--hoja`, `--frame`, `valedores.py revisar`).
- Ejecutar con `python -I`. Skills: `cinematica-mkds`, `recursos-mkds`.
