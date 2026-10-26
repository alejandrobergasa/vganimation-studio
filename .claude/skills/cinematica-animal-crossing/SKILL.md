---
name: cinematica-animal-crossing
description: Crea un vídeo horizontal (1280x720) de Animal Crossing Wild World con el motor de juegos/animal-crossing/video usando solo assets de la ROM. Úsala cuando el usuario pida un vídeo, escena, corto o animación de Animal Crossing en horizontal; para móvil/redes usa cinematica-animal-crossing-movil. Se usa dentro del flujo de crear-video.
---

# Cinemática de Animal Crossing: Wild World (horizontal)

Se usa dentro del flujo por fases de `crear-video` (idea → guion → música → storyboard → previsualización → render →
revisión). Esta skill solo aporta lo específico de este motor.
Argumento: la idea del vídeo (tema, duración, personajes). Si falta algo, elige un valor razonable, anótalo y sigue; no preguntes salvo bloqueo real.

## Reglas (de `juegos/animal-crossing/AGENTS.md`)
- Solo assets de la ROM (modelos, texturas, fuente `font/fontA`, música/voces del SDAT) y lo que el usuario aporte en
  `entrada/` (excepción anotada en el brief). No modificar la ROM. Texto en español con la fuente del juego. ROM europea (ADMP).
- Si falta un asset, dilo y propón la alternativa más cercana.
- No entregues nada que no hayas visto: abre los PNG de revisión con la herramienta de lectura de imágenes.

## Procedimiento
1. **Assets**: `python valedores.py estado`; si no están, `python valedores.py extraer animal-crossing`. Personajes y objetos:
   hojas en `biblioteca/animal-crossing/extraidos/_hojas/` y rutas en su `README.md`.
2. **Storyboard**: `proyectos/<slug>/storyboard.md` (tabla escena / tiempo / contenido / assets), como `juegos/animal-crossing/video/storyboard_prueba.md`.
3. **Script**: copia `juegos/animal-crossing/video/prueba.py` a `proyectos/<slug>/video.py`, cambia la cabecera por la estándar de
   `crear-video` (`JUEGO = 'animal-crossing'`) y adáptalo (`LINES`, cámara `cam_at`, posiciones, insets, música `seq`, voces).
   Reutiliza `motor.py`, `escena.py`, `audio.py`; si necesitas algo nuevo, añádelo al motor, no lo dupliques.
   - Cada fotograma es función pura de `t` (se paraleliza). Render base 640×360, ×2 a 1280×720, 30 fps.
   - Frente de los modelos = +Z, cámara en +Z. Detalles y fallos conocidos: `juegos/animal-crossing/CONOCIMIENTO.md`.
4. **Prueba rápida**: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py --solo-frames t1,t2,...`
   → PNG en `proyectos/<slug>/trabajo/frames/`; ábrelos.
5. **Render completo**: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py` → `salida/<slug>/…mp4` (H.264 yuv420p + AAC).
6. **Revisión**: skill `revisar-video`.
7. **Entrega**: como en `crear-video`. Si se aprendió algo nuevo, añádelo a `juegos/animal-crossing/CONOCIMIENTO.md`.
