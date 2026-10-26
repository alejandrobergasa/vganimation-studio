# Valedores Studio

Crea vídeos con los gráficos, la música y las voces de videojuegos de Nintendo DS (Animal Crossing: Wild World, New Super Mario Bros.,
Mario Kart DS y Pokémon Platino) trabajando con un agente de IA: **Claude Code** o **Codex**, desde una interfaz con chat o desde la terminal.

Unifica tres repos anteriores en uno: bandejas de entrada y salida, librería de ROMs, assets por juego, base de conocimiento y skills.

## Puesta en marcha

Necesitas Python 3.10+, `ffmpeg`/`ffprobe` en el PATH y, para el chat, `claude` y/o `codex` instalados y con sesión iniciada.

```
pip install -r requirements.txt
python valedores.py doctor        # comprueba el entorno
```

1. **Pon tus ROMs en `roms/`** (`.nds`; el nombre da igual, se reconocen por la cabecera). *Este repositorio no las incluye ni las incluirá.*
2. **Extrae los assets**: `python valedores.py extraer` te pregunta de qué ROMs. Los assets no se suben a Git: cada uno los regenera en local con la
   última versión del extractor (`python valedores.py estado` avisa si un extractor ha cambiado desde la última extracción).
3. **Abre el estudio**: `python valedores.py estudio`.

## El estudio

Una página local (`127.0.0.1`, sin dependencias externas):

- **Juegos**: tarjetas con imágenes de ejemplo y el estado de su ROM/assets (con botón de extraer).
- **Nuevo vídeo**: título, formato, tu idea o guion, agente, modelo y esfuerzo, y el ritmo:
  - *Paso a paso*: el agente se detiene al terminar cada fase para que la valides.
  - *De una*: lo hace todo seguido.
- **Chat** con el agente elegido, que trabaja en este repo siguiendo la skill `crear-video`. Atajos para pedir solo una parte
  («solo el guion», «solo la música»…).
- **Fases** (idea → guion → música → storyboard → previsualización → render → revisión): cada una enseña su resultado
  (texto, audio de muestra, fotogramas, vídeo) con botones *Aprobar* / *Pedir cambios*.
- **Adjuntos en el chat**: botón 📎, arrastrar ficheros sobre el chat o pegar una captura. Se guardan en `entrada/<proyecto>/` y el agente recibe
  sus rutas (fotos, vídeos de referencia, audios, assets).
- **Entrada y salida**: todo lo subido y los vídeos resultado.

## Carpetas

| Carpeta | Contenido | Git |
|---|---|---|
| `entrada/` | Ficheros tuyos para la IA (`entrada/<proyecto>/` para uno concreto) | no |
| `salida/` | Vídeos resultado | no |
| `roms/` | Tus ROMs | no |
| `biblioteca/<juego>/extraidos/` | Assets sacados de la ROM (regenerables) | no |
| `biblioteca/<juego>/personalizados/` | Assets propios (fotos, personajes custom) | sí |
| `juegos/<juego>/` | Extractor, motor de vídeo, ejemplos, skills y conocimiento de cada juego | sí |
| `conocimiento/`, `skills/` | Base de conocimiento y skills comunes | sí |
| `proyectos/<slug>/` | Un vídeo: estado por fases, guion, música, storyboard, `video.py` | sí |
| `nucleo/`, `estudio/`, `valedores.py` | CLI, librería común e interfaz | sí |

## Línea de comandos

```
python valedores.py estado                       juegos, ROMs, assets, proyectos
python valedores.py extraer [juego ...]          extrae/actualiza assets (sin argumentos: pregunta; --todos, --pendientes, --rapido)
python valedores.py proyecto nuevo "Título" --juego animal-crossing --formato vertical
python valedores.py fase <slug> <fase> <estado>  el agente marca el avance
python valedores.py ejecutar <slug> -- <cmd>     ejecuta con la salida redirigida al proyecto
python valedores.py revisar info|hoja|frame|audio <video>
python valedores.py skills [--check]             sincroniza skills para Claude Code (.claude/) y Codex (.agents/)
python valedores.py doctor
```

## Para agentes de IA

Empieza por [`AGENTS.md`](AGENTS.md) (Claude Code lo lee vía `CLAUDE.md`; Copilot vía `.github/copilot-instructions.md`).
Las skills se editan en `skills/` y `juegos/<juego>/skills/`; `.claude/skills/` y `.agents/skills/` se generan.

## Añadir un juego

Skill `anadir-juego`: crear `juegos/<id>/` con `juego.json` (código de ROM, extractor, formatos), extractor, motor y skills.

## Aviso legal

Los juegos, sus gráficos, música y voces son propiedad de sus titulares. Este repositorio no distribuye ROMs ni assets extraídos: cada
persona usa sus propias copias. Las imágenes de `juegos/*/vistas/` son capturas pequeñas solo para ilustrar la interfaz.
