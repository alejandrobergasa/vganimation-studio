# Flujo de trabajo de un vídeo

La skill `crear-video` es la norma; esto explica el porqué y los detalles de la integración con el estudio.

## Por qué por fases
Un vídeo tiene partes caras de rehacer (render completo, música compuesta). Validar el guion antes de componer la música,
y la música antes de montar la imagen, evita rehacer trabajo. Cada fase produce **un artefacto que el usuario puede
mirar o escuchar sin abrir código**.

| # | Fase | Artefacto | Qué valida el usuario |
|---|---|---|---|
| 1 | `idea` | `brief.md` | Que se ha entendido lo que quiere: formato, duración, tono, reparto. |
| 2 | `guion` | `guion.md` | El texto exacto y el reparto de frases. |
| 3 | `musica` | `musica.md` + `musica/muestra.wav` | Que la música encaja (se escucha en el estudio). |
| 4 | `storyboard` | `storyboard.md` | Escenas, planos, tiempos. |
| 5 | `escenas` | `previsualizacion/*.png` + `video.py` | Cómo se ve. |
| 6 | `render` | `salida/<slug>/*.mp4` | El vídeo completo. |
| 7 | `revision` | `revision.md` | Que el archivo final está comprobado. |

Se puede **pedir una parte suelta** («sácame solo la música»): se hace esa fase y se para. Se puede ir **de una**: todo seguido y solo
se valida la revisión final. El orden no es sagrado: si un vídeo no lleva música, esa fase se marca `omitida`.

## Estado compartido: `proyectos/<slug>/proyecto.json`
El agente y el estudio no se hablan directamente: comparten este fichero.
- El **agente** lo actualiza con `python valedores.py fase <slug> <fase> <estado> [--archivo ...] [--nota "..."]`.
- El **estudio** lo muestra (línea de fases, ficheros de cada fase) y, con los botones de validar o pedir cambios, manda un mensaje
  al chat («✅ Fase guion aprobada» / «Cambios en la fase guion: …»). El agente cambia entonces el estado.
- Estados: `pendiente`, `en_curso`, `validar` (esperando al usuario), `aprobada`, `cambios`, `omitida`.

## Sesiones del agente
El estudio lanza el agente elegido (Claude Code o Codex, con el modelo elegido) en la raíz del repo, con
`VALEDORES_PROYECTO=<slug>` en el entorno y un primer mensaje que incluye el contexto del proyecto. La sesión se reanuda en cada
mensaje (el id se guarda en `.estudio/chats/`, que no se versiona). Por eso el agente puede perder el hilo si se borra: lo que cuenta está
en los ficheros del proyecto, no en la conversación. **Escribe las decisiones en `brief.md`/`guion.md`/`storyboard.md`.**

## Entradas y salidas
- Lo que el usuario deja en `entrada/` se lee, no se modifica. Si se reutiliza → `biblioteca/<juego>/personalizados/`.
- El vídeo final va a `salida/<slug>/`. Con varias versiones, `<nombre>_v2.mp4`: no se borra la anterior sin decirlo.
- Temporales (fotogramas de revisión, audio intermedio, caché de render) → `proyectos/<slug>/trabajo/` (ignorado por Git).

## Cuándo preguntar
Solo si falta algo que cambia el resultado y no se puede decidir con criterio razonable (quién es quién, qué foto, qué tono). En el
resto de casos: decide, anótalo en el artefacto como «decisión tomada» y sigue; el usuario lo ve al validar.
