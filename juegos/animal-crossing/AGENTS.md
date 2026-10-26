# Animal Crossing: Wild World (ROM europea, ADMP)

Solo se usan assets extraídos de la ROM (más lo que el usuario aporte en `entrada/`, anotado en el brief). No modificar la ROM.
Texto del vídeo en español con la fuente del juego (`font/fontA`). Formatos y fallos resueltos: `CONOCIMIENTO.md`.
Flujo de trabajo general: skill `crear-video`; aquí solo lo específico de este juego.

## Estructura (`juegos/animal-crossing/`)
- `tools/ww/`: lector de ROM y de formatos Nitro, rasterizador y sintetizador de audio (propios).
- `tools/extraer.py`: extractor → `biblioteca/animal-crossing/extraidos/` (regenerable, no editar a mano).
- `video/`: motor (`motor.py`, `escena.py`, `audio.py`) y guiones de referencia (`prueba.py`, `gasto.py` vertical con datos,
  `pesca.py` con efectos y transiciones, `pedro_parodia_v*.py`, `reggaeton.py`/`musica_pesca.py` música, `sfx.py`), con sus `storyboard_*.md`.
  `video/personajes/`: personajes propios recoloreados (`lincelucas.py`, `pedro.py`).
- Assets propios del usuario: `biblioteca/animal-crossing/personalizados/`.
- Los scripts de vídeo nuevos van en `proyectos/<slug>/video.py` (cabecera estándar de `crear-video`), no aquí.

## Comandos
- Extraer: `python valedores.py extraer animal-crossing` (o `python -I juegos/animal-crossing/tools/extraer.py [--rapido] [--fase 2d texturas modelos audio]`).
- Ejemplo de vídeo: `python -I juegos/animal-crossing/video/prueba.py [--solo-frames 2,8,20]` → `salida/animal-crossing/prueba_nook.mp4`;
  fotogramas de revisión en `.cache/animal-crossing/trabajo/frames/`.

## Reglas
- Revisar con los propios ojos (hojas de contactos / fotogramas) antes de dar nada por bueno.
- Cada fotograma es función pura de `t`; no meter estado global en el render.
- Frente de los modelos = +Z; cámara en +Z. No cambiar el culling sin mirar `CONOCIMIENTO.md`.
- Ejecutar Python con `-I`.
- Skills: `cinematica-animal-crossing` (horizontal) y `cinematica-animal-crossing-movil` (vertical para redes).
