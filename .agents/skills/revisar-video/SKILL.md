---
name: revisar-video
description: Revisa un vídeo ya renderizado (imagen, texto, audio, duración, formato) con hojas de contactos, fotogramas a tamaño real y espectrograma, y lo corrige hasta que no haya fallos. Úsala antes de entregar cualquier vídeo, o cuando el usuario pida revisar uno existente.
---

# Revisar un vídeo

Hay que **mirar** las imágenes generadas con la herramienta de lectura de imágenes (Read en Claude Code,
view_image en Codex). Generarlas no es revisar. Y mirar un espectrograma no es oír: no digas que has escuchado algo.

## Herramientas (valen para cualquier juego)
```
python valedores.py revisar info  <video>                 resolución, fps, duración, códecs, pico/media, silencios
python valedores.py revisar hoja  <video> [paso_s] [cols] hoja de contactos (por defecto 1 fotograma cada 3 s, 5 columnas)
python valedores.py revisar frame <video> <segundo>       fotograma suelto a tamaño completo
python valedores.py revisar audio <video>                 espectrograma + onda y niveles
```
Con un proyecto activo (`python valedores.py ejecutar <slug> -- ...`) las imágenes caen en
`proyectos/<slug>/trabajo/revision/`; si no, en `.cache/_general/trabajo/revision/`. Se sobrescriben: copia las
de cada entrega si quieres conservarlas.

## Lista de comprobación
1. **Archivo**: `info` → resolución y fps esperados (vertical 1080×1920 o el del juego), duración correcta,
   H.264 `yuv420p` + AAC, tiene audio, pico por debajo de 0 dB (objetivo ≈ −1 dB), sin silencios largos accidentales.
   Decodifica entero: `ffmpeg -v error -i <video> -f null -` (en Windows también vale `NUL`).
2. **Hoja de contactos**: abre `hoja` y busca huecos negros, personajes fuera de plano, saltos, cortes feos,
   rótulos tapados, texturas rotas, ritmo (planos eternos o demasiado rápidos).
3. **Fotogramas a tamaño real** en: título (primeros 3 s), cada cambio de plano/escena, cada tipo de rótulo o
   gráfico, cada diálogo (¿se ve la frase completa antes de cambiar de página?), efectos y el cierre.
   En vertical: ¿se lee todo en un móvil? ¿hay algo bajo la interfaz de la red (arriba ~22 px y abajo ~60 px
   sobre 360×640)?
4. **Texto**: ortografía, tildes y eñes con la fuente del juego, frases del guion íntegras y en orden.
5. **Audio**: `audio` → ¿cortes, saturación, meseta, silencios no previstos? ¿música y voz equilibradas? ¿cada
   efecto cae en su evento visual? Si no puedes escucharlo, dilo en la entrega.
6. **Contra el guion y el storyboard**: ¿está todo lo aprobado y nada más?

## Después
Corrige en el script o en el motor, vuelve a renderizar solo lo necesario y repite hasta que no haya fallos.
Resume en `proyectos/<slug>/revision.md`: qué se comprobó, qué se corrigió y qué no se pudo comprobar.
No hace falta volver a renderizar si solo cambian instrucciones o documentación.
