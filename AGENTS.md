# valedores-studio — vídeos a partir de assets de videojuegos

Repositorio único para crear vídeos con los gráficos, la música y las voces de videojuegos (de momento Nintendo DS:
Animal Crossing: Wild World, New Super Mario Bros., Mario Kart DS y Pokémon Platino). Lo leen Claude Code (vía `CLAUDE.md`),
Codex y Copilot. Todo está en español.

## Mapa del repo
| Carpeta | Qué es | ¿Git? |
|---|---|---|
| `entrada/` | **Bandeja de entrada**: ficheros del usuario (fotos, vídeos, audios, assets). `entrada/<slug>/` = los de un proyecto. | no |
| `salida/` | **Bandeja de salida**: vídeos resultado, en `salida/<slug>/`. | no |
| `roms/` | **Librería de ROMs** (`.nds`). Se reconocen por su cabecera; el nombre da igual. | no |
| `biblioteca/<juego>/extraidos/` | Assets sacados de la ROM (regenerables con `python valedores.py extraer`). | no |
| `biblioteca/<juego>/personalizados/` | Assets propios (fotos, personajes hechos a mano). | **sí** |
| `juegos/<juego>/` | Código de cada juego: extractor, motor de vídeo, ejemplos, `juego.json`, `AGENTS.md`, `CONOCIMIENTO.md`, `skills/`, `vistas/`. | sí |
| `conocimiento/` | Base de conocimiento común (flujo, vídeo vertical, audio, revisión, plantillas). | sí |
| `skills/` | Skills transversales. Las de cada juego están en `juegos/<juego>/skills/`. | sí |
| `proyectos/<slug>/` | Un vídeo: `proyecto.json` (estado por fases), brief, guion, música, storyboard, `video.py`. | sí (menos `trabajo/`) |
| `nucleo/` + `valedores.py` | CLI y librería común (rutas, extracción, proyectos, skills, revisión). | sí |
| `estudio/` | Interfaz gráfica con chat de agente (`python valedores.py estudio`). | sí |
| `.claude/skills/`, `.agents/skills/` | Copias **generadas** de las skills para Claude Code y Codex. No editar. | sí |

Juegos: `animal-crossing`, `nsmb`, `mkds`, `pokemon-platino`. Estado: `python valedores.py estado`.

## Antes de empezar cualquier tarea
1. Si piden un vídeo/escena/animación → skill **`crear-video`** (flujo por fases con validación del usuario). Las skills del juego
   (`cinematica-<juego>`) dan el motor concreto. Para revisar un vídeo → `revisar-video`. Para extraer assets → `extraer-assets`.
   Para soportar un juego nuevo → `anadir-juego`.
2. Lee `juegos/<id>/AGENTS.md` y `juegos/<id>/CONOCIMIENTO.md` del juego implicado y el índice `conocimiento/README.md`.
3. Comprueba el entorno si algo falla: `python valedores.py doctor` (Python, ffmpeg, agentes, ROMs, assets, skills).

## Reglas globales
- **Las ROMs no se modifican nunca** y no se suben a Git. Los assets de un vídeo salen de la ROM del juego; lo que aporte el usuario
  (`entrada/`) es una excepción concreta que se anota en el brief y no se extiende a otros vídeos.
- **Nada se da por bueno sin verlo**: abre las imágenes generadas con la herramienta de lectura de imágenes (Read en Claude Code,
  view_image en Codex). Generar una hoja de contactos no es revisarla. No digas que has oído algo que solo has medido.
- Texto de los vídeos en español, con la fuente del propio juego. Comentarios y mensajes del código en español; respeta el estilo existente.
- Ejecuta los scripts de juego con `python -I`. Nunca rutas relativas al propio script hacia ROMs/assets/salidas: usa `valedores.rutas`.
- Un vídeo = un proyecto en `proyectos/<slug>/`. Se ejecuta con `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py`
  para que la salida caiga en `salida/<slug>/` y los temporales en `proyectos/<slug>/trabajo/`.
- Si necesitas algo nuevo del motor, añádelo al motor del juego, no lo dupliques en el script del proyecto. Lo aprendido va a
  `juegos/<id>/CONOCIMIENTO.md` (o a `conocimiento/` si vale para varios juegos).
- Skills: se editan en `skills/` o `juegos/<id>/skills/`; después `python valedores.py skills` regenera `.claude/skills/` y `.agents/skills/`
  (`--check` solo comprueba). Los nombres de skill son únicos en todo el repo.
- No hagas commit de vídeos (`.gitignore` los excluye) ni de ROMs. Los assets extraídos tampoco se versionan: se regeneran.

## Comandos habituales
```
python valedores.py estado                        juegos, ROMs, assets, proyectos
python valedores.py extraer [juego ...]           extrae/actualiza assets (sin argumentos pregunta cuáles)
python valedores.py proyecto nuevo "Título" --juego animal-crossing --formato vertical
python valedores.py fase <slug> <fase> <estado>   (el agente marca el avance; ver crear-video)
python valedores.py ejecutar <slug> -- <comando>  ejecuta con el proyecto activo
python valedores.py revisar info|hoja|frame|audio <video>
python valedores.py skills [--check]
python valedores.py estudio                       interfaz gráfica con chat (Claude Code / Codex)
```
