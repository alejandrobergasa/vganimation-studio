---
name: crear-video
description: Flujo completo para crear un vídeo con assets de un videojuego del repo (Animal Crossing, NSMB, Mario Kart DS, Pokémon Platino), por fases con validación del usuario: idea, guion, música, storyboard, previsualización, render y revisión. Úsala siempre que el usuario pida un vídeo, corto, escena o animación nueva, y cuando el estudio abra un proyecto. Las skills de cada juego aportan el motor concreto.
---

# Crear un vídeo, por fases y con validación

Skill neutral respecto al agente (Claude Code y Codex). «Ver una imagen» = la herramienta de lectura de imágenes
que tengas (Read en Claude Code, view_image en Codex). **Nada se da por bueno sin verlo u oírlo medido.**

## 0. Orientarse (siempre, antes de producir nada)
1. Lee `AGENTS.md` (reglas del repo) y `conocimiento/README.md` (índice de la base de conocimiento).
2. ¿Hay proyecto? Mira `proyectos/<slug>/proyecto.json` y `brief.md`. Si el usuario pide un vídeo y no existe,
   créalo: `python valedores.py proyecto nuevo "<título>" --juego <id> [--formato <id>] [--ritmo paso_a_paso|de_una]`.
   Ids de juego: `python valedores.py estado`.
3. Skill del juego: `juego.json → formatos[].skill` (p. ej. `cinematica-animal-crossing-movil`). Léela entera y
   `juegos/<id>/AGENTS.md` + `juegos/<id>/CONOCIMIENTO.md` antes de tocar el motor.
4. Assets: `python valedores.py estado`. Si el juego está «sin extraer», `python valedores.py extraer <id>`
   (no gasta tokens, tarda minutos). Si falta la ROM, díselo al usuario: va en `roms/`.
5. Ficheros del usuario: `entrada/<slug>/` y `entrada/` (fotos, vídeos, audios, assets). **Ábrelos y míralos**
   antes de decir que falta algo. Nunca los modifiques; si son reutilizables, copia a `biblioteca/<id>/personalizados/`.

## 1. Ritmo y puertas de validación
`proyecto.json → ritmo`:
- **paso_a_paso** (por defecto): al acabar cada fase te **detienes** y esperas la respuesta del usuario.
- **de_una**: encadenas todas las fases; solo `revision` queda esperando validación.
- Si el usuario pide **una parte** («sácame primero la música», «solo el guion»), haz solo esa parte aunque
  el ritmo sea `de_una`, y para.

Estados por fase: `pendiente · en_curso · validar · aprobada · cambios · omitida`. Los marcas tú:
```
python valedores.py fase <slug> <fase> en_curso
python valedores.py fase <slug> <fase> validar --archivo musica.md musica/muestra.wav --nota "Reggaetón 96 bpm en La menor, 38 s"
python valedores.py fase <slug> <fase> aprobada
```
Protocolo al terminar una fase en `paso_a_paso`:
1. Escribe el artefacto en `proyectos/<slug>/` (tabla abajo). Rutas de `--archivo` relativas a esa carpeta.
2. Marca la fase `validar` con una nota de una o dos frases.
3. En el chat: resumen de ≤ 6 líneas, **qué debe mirar o escuchar** el usuario (el estudio muestra los ficheros)
   y una pregunta concreta («¿apruebas el guion o cambio algo?»). Y **para**. No empieces la siguiente fase.
4. El usuario aprueba (el estudio envía «✅ Fase X aprobada») → `aprobada` y sigue. Pide cambios → `cambios`
   con la nota, rehaz y vuelve a `validar`. Si un cambio invalida fases ya aprobadas (el guion cambió y la
   música ya estaba hecha), márcalas `cambios` y dilo.
5. Una fase que no aplica (vídeo sin música) → `omitida` con nota. Pregunta solo si algo te bloquea de verdad;
   si no, decide con criterio, anótalo en el artefacto y sigue.

## 2. Las fases y qué entregan
| Fase | Artefacto (en `proyectos/<slug>/`) | Contenido |
|---|---|---|
| `idea` | `brief.md` | Idea final concreta: formato, duración, tono, reparto, datos a verificar, assets de `entrada/` que se usarán, decisiones tomadas por ti. Plantilla: `conocimiento/plantillas/brief.md`. |
| `guion` | `guion.md` | Texto completo: tabla tiempo · quién · texto · acción/emoción. Respeta los límites de texto del juego (caracteres por línea, líneas por ventana). Cifras con fuente. Plantilla: `conocimiento/plantillas/guion.md`. |
| `musica` | `musica.md` + `musica/muestra.wav` | Género, tempo, tonalidad, instrumentos del juego usados, estructura con marcas de tiempo; y un audio de muestra de 20–40 s que el usuario pueda oír. Receta: `conocimiento/audio.md`. |
| `storyboard` | `storyboard.md` | Tabla escena · tiempo · plano/cámara · contenido · assets (rutas reales). Plantilla: `conocimiento/plantillas/storyboard.md`. |
| `escenas` | `previsualizacion/*.png` + `video.py` | El script del vídeo y fotogramas clave a tamaño real y una hoja de contactos. Lo que el usuario valida es **cómo se ve**. |
| `render` | `salida/<slug>/<nombre>.mp4` | Render completo con el script del proyecto. |
| `revision` | `revision.md` | Resultado de la revisión del archivo final (ver skill `revisar-video`) y qué se corrigió. Marca `validar`: el vídeo está listo para entregar. |

## 3. El script del vídeo vive en el proyecto
`proyectos/<slug>/video.py`, copiado de la plantilla/ejemplo que indique la skill del juego. Cabecera estándar
(sustituye a los `HERE`/`sys.path` del ejemplo):
```python
import os, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'nucleo'))
from valedores import rutas
JUEGO = 'animal-crossing'                       # id del juego
sys.path.insert(0, rutas.motor_dir(JUEGO))      # el motor del juego (motor.py, escena.py, ...)
```
Ejecútalo siempre con el proyecto activo, así el vídeo cae en `salida/<slug>/` y los temporales en
`proyectos/<slug>/trabajo/` (no se versiona):
```
python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py [opciones]
```
Si necesitas algo nuevo del motor, añádelo **al motor del juego** (`juegos/<id>/...`), no lo dupliques en el
script; documéntalo en el `CONOCIMIENTO.md` del juego.

## 4. Reglas
- Solo assets de la ROM del juego, más lo que el usuario aporte en `entrada/` (excepción concreta, anotada en el
  brief; no se extiende a otros vídeos). Si falta un recurso, dilo y propón el más cercano; no lo presentes como auténtico.
- No modificar nunca las ROMs. Texto en español con la fuente del juego.
- Los vídeos no se versionan (`.gitignore`); los assets propios sí (`biblioteca/<id>/personalizados/`).
- Si aprendes algo reutilizable (un truco, un fallo resuelto, una cifra del formato), añádelo al
  `CONOCIMIENTO.md` del juego o a `conocimiento/`. Si tocas una skill: `python valedores.py skills`.

## 5. Entrega
Ruta del vídeo en `salida/<slug>/`, duración, assets usados, fuente de los datos, decisiones propias,
lo que no se pudo comprobar (p. ej. audio no escuchado) y el comando para regenerarlo.
