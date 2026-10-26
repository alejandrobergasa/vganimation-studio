---
name: cinematica-nsmb
description: Crea, modifica, renderiza y revisa las cinemáticas de New Super Mario Bros. (DS) del repositorio, incluidos vídeos verticales, escenas, diálogos y música con los bancos del juego. Úsala dentro del flujo de crear-video para cualquier vídeo de NSMB; para regenerar o elegir assets de la ROM, usa recursos-nsmb; para Mario Kart DS, cinematica-mkds.
---

# Cinemáticas NSMB

Trabajar desde la raíz del repo con Python y ffmpeg; el código del juego está en `juegos/nsmb/`. Se usa dentro del flujo por
fases de `crear-video`. Esta skill es compartida por Claude Code y Codex: se edita aquí
(`juegos/nsmb/skills/`) y se sincroniza con `python valedores.py skills`.

## Alcance y recursos

- La ROM se lee y nunca se modifica. Usar sus assets por defecto, conforme a `juegos/nsmb/AGENTS.md`. Lo que el usuario aporte en `entrada/` (fotos, logos) es una excepción concreta, anotada en el brief.
  Respetar las excepciones concretas que el usuario pida o aporte en la conversación;
  documentar su procedencia sin extender esa autorización a otros recursos o vídeos.
- Antes de declarar que falta una imagen adjunta, buscar su nombre real en `entrada/` y en `biblioteca/nsmb/personalizados/`
  y abrirla. Un error anterior de lectura no prueba que siga ausente. Conservar el original.
- Si un recurso no existe en la ROM y el usuario no ha pedido una excepción, explicar
  la limitación y proponer el recurso del juego más cercano; no presentarlo como auténtico.
- Texto en español con `font_a.NFTR`, a través de `juegos/nsmb/video/text.py`.
  Conservar las frases y restricciones de texto del pedido actual. Los rótulos, HUD,
  comentarios y contadores son decisiones del guion, no requisitos de la skill.

## Elegir el montaje

Los ejemplos están en `juegos/nsmb/video/` (se ejecutan con `python -I juegos/nsmb/video/<x>.py`; desde un proyecto, con
`python valedores.py ejecutar <slug> -- ...`).

| Montaje | Código y comando desde la raíz |
|---|---|
| Paseo original por 1-1 | `world.py`, `sim.py`, `engine.py`, `audio.py`; `python -I juegos/nsmb/video/make_video.py` |
| Cinemática vertical RENFE existente | `renfe.py`, `renfe_audio.py`; `python -I juegos/nsmb/video/make_video.py --renfe` |
| Cinemática vertical del casino | `casino_3d.py`; `python -I juegos/nsmb/video/make_video.py --casino` (guía: `video/CASINO.md`) |
| Previsualización vertical sin codificar el MP4 | `python -I juegos/nsmb/video/renfe.py --preview` → `.cache/nsmb/renfe/storyboard_visual.png` |

El paseo sale en `salida/nsmb/nsmb_paseo_mundo_1-1.mp4`; el montaje RENFE en
`salida/nsmb/mario_renfe_vertical.mp4` (con un proyecto activo, en `salida/<slug>/`). Para otro guion, reutilizar las piezas útiles sin
acoplarlo a estos nombres o al reparto de escenas del ejemplo.

## Preparar y modificar

1. Leer el storyboard y el montaje actual (`juegos/nsmb/video/storyboard*.md` como ejemplos; el del proyecto es
   `proyectos/<slug>/storyboard.md`). Actualizarlo antes
   de cambiar código: escenas, formato, duración, diálogo íntegro, música y transiciones.
2. Consultar `biblioteca/nsmb/extraidos/README.md` y las hojas de contactos. Si sólo falta
   una categoría, extraerla con `recursos-nsmb`; no repetir la extracción completa.
3. Al ampliar un diálogo, derivar de una única cronología compartida el cierre,
   la muerte, el iris, el final, los efectos y la duración total. No dejar tiempos
   antiguos en el compositor o en la mezcla. Admitir duraciones fraccionarias.
4. Fijar los saltos de línea con la frase completa antes de animar su escritura.
   Mantener juntos los remates y dar tiempo de lectura con el texto ya completo.
   Si hace falta, alargar la escena; no cortar la frase para conservar la duración anterior.
5. Previsualizar los puntos modificados antes del render completo. En el paseo
   simulado, mantener la validación `make_video.plan()` sin eventos `HIT`/`FALL`.
   Esa validación no se aplica a una derrota o choque escritos en otro guion.

Para formato vertical, acabado visual, fotos/logos y diálogo con música original,
leer [producción y sincronía](references/produccion.md). Los detalles de formatos
de la ROM siguen en `juegos/nsmb/CONOCIMIENTO.md`. Para un vídeo nuevo, copia el montaje de referencia más
cercano a `proyectos/<slug>/video.py` con la cabecera estándar de `crear-video` (`JUEGO = 'nsmb'`).

## Revisar el archivo que se va a entregar

Usar la skill `revisar-video` indicando **siempre la ruta del MP4**. Ejemplo; elegir segundos pertinentes al cambio actual:

```powershell
python valedores.py revisar hoja salida/<slug>/<video>.mp4 2 5
python valedores.py revisar frame salida/<slug>/<video>.mp4 38
python valedores.py revisar audio salida/<slug>/<video>.mp4
```

- Abrir la hoja, los planos completos afectados y el espectrograma con la onda;
  si hay fallos, corregir y volver a revisar el resultado. No basta generar las imágenes.
- Comprobar frases completas antes de cada cambio de página, márgenes, escala,
  recortes del tren/personajes/logo, y continuidad al desaparecer el retrato.
- Revisar el audio del MP4 final, después de AAC: pico inferior a 0 dB, sin mesetas
  de saturación ni silencios accidentales. Las pausas del guion son deliberadas.
  Escuchar cuando haya reproducción disponible; no confundir mirar un espectrograma con oírlo.
- Verificar con ffprobe resolución, fps, duración, audio y número de fotogramas;
  decodificar el MP4 completo con `ffmpeg -v error -i <video> -f null NUL` en Windows.
- `trabajo/revision/` se sobrescribe: guardar las pruebas de cada entrega en una
  carpeta de revisión de esa versión. Conservar el MP4 anterior si se entrega una revisión.
- Entregar un enlace al MP4 comprobado, los cambios, limitaciones relevantes y
  el comando para regenerarlo, directamente o mediante el documento de entrega.
