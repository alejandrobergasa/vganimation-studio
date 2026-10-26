# New Super Mario Bros. (DS) — ROM europea española, A2DP

Todo lo que sale en el vídeo viene de la ROM (más lo que el usuario aporte en `entrada/`, anotado en el brief). La ROM no se modifica nunca.
Notas técnicas y fallos resueltos: `CONOCIMIENTO.md`. Flujo de trabajo general: skill `crear-video`.

## Estructura (`juegos/nsmb/`)
- `tools/nsmb/`: librería propia (rom, raw2d, level, backgrounds, nitro3d, chars, nftr, sonido). `tools/extraer_todo.py` y
  `tools/extraer_casino.py`: extractores → `biblioteca/nsmb/extraidos/` (regenerable). Mario Kart DS reutiliza esta librería (`juegos/mkds/`).
- `video/`: motor del vídeo: `world.py` (nivel 1-1, colisión), `sim.py` (Mario autómata), `engine.py` (compositor 256x192),
  `text.py` (fuente del juego), `audio.py`, `make_video.py`; montajes de referencia `renfe*.py` y `casino*.py` (ver `RENFE.md`, `CASINO.md`).
- Fotos y logos del usuario: `biblioteca/nsmb/personalizados/`. Caché de audio renderizado: `.cache/nsmb/`.

## Comandos
- Extraer: `python valedores.py extraer nsmb` (≈5 min con audio; a mano: `python -I juegos/nsmb/tools/extraer_todo.py [--sin-audio] [--solo modelos,fondos,...]`).
- Paseo 1-1: `python -I juegos/nsmb/video/make_video.py` → `salida/nsmb/nsmb_paseo_mundo_1-1.mp4`. Montajes: `--renfe`, `--casino`.
- Revisión: `python valedores.py revisar hoja|frame|audio|info <video>` y mirar la imagen.

## Reglas
- Texto en español con `font_a.NFTR` (`video/text.py`). Nada se da por bueno sin verlo: hoja de fotogramas y mirarla.
- Ejecutar siempre con `python -I`; los scripts añaden sus rutas. Comentarios y mensajes en español; estilo del código existente.
- Los vídeos nuevos van en `proyectos/<slug>/video.py`. Skills: `cinematica-nsmb`, `recursos-nsmb`.
