---
name: anadir-juego
description: Añade un videojuego nuevo al repo (manifiesto, extractor, motor, skills, conocimiento e imágenes de ejemplo para el estudio). Úsala cuando el usuario quiera soportar otro juego o consola.
---

# Añadir un juego

Un juego es una carpeta autocontenida `juegos/<id>/` (id en minúsculas con guiones). Todo lo demás
(ROMs, biblioteca, proyectos, estudio, CLI) lo descubre solo a partir de su `juego.json`.

## Estructura mínima
```
juegos/<id>/
  juego.json        manifiesto (abajo)
  AGENTS.md         reglas y mapa del código del juego (+ CLAUDE.md con «@AGENTS.md»)
  CONOCIMIENTO.md   formatos de la ROM, decisiones, fallos ya resueltos
  tools/            extractor y lectores de formatos
  <motor>/          el motor de vídeo (la carpeta que diga `motor` en el manifiesto)
  skills/<nombre>/SKILL.md   al menos `cinematica-<id>` (cómo se hace un vídeo con este motor)
  vistas/           3–5 imágenes JPG/PNG (≈ 640 px) que salen en la tarjeta del estudio
biblioteca/<id>/personalizados/   assets propios del usuario (versionados)
```
## `juego.json`
```json
{
  "id": "mi-juego", "nombre": "Mi Juego", "corto": "Mi Juego", "plataforma": "Nintendo DS",
  "descripcion": "Una o dos frases para la tarjeta del estudio.",
  "rom": {"codigos": ["ABCD"], "region": "Europa", "ejemplo": "Mi Juego.nds"},
  "depende": [],
  "extractor": {"comandos": [["tools/extraer.py", "--rom", "{rom}", "--salida", "{extraidos}"]],
                "rapido": ["--rapido"], "duracion_aprox": "5 min"},
  "formatos": [{"id": "vertical", "nombre": "Vertical 1080x1920", "skill": "cinematica-mi-juego"}],
  "motor": "video/", "vistas": []
}
```
- `rom.codigos`: los 4 caracteres de la cabecera NDS (offset 0xC). `python valedores.py roms` los muestra.
- `extractor.comandos`: argv relativos a `juegos/<id>/`, ejecutados con `python -I`. `{rom}` y `{extraidos}` se
  sustituyen. Debe escribir en `{extraidos}` (= `biblioteca/<id>/extraidos/`) y ser **repetible**.

## Reglas de código para que encaje
- Nunca rutas relativas al propio script hacia ROMs, assets o salidas: usa `valedores.rutas`
  (`rutas.rom(id)`, `extraidos(id)`, `personalizados(id)`, `cache(id)`, `salida(id)`, `trabajo(id)`). Para importarlo
  desde un script del juego, sube por carpetas hasta `valedores.toml` y añade `nucleo/` a `sys.path`
  (ver `juegos/mkds/tools/mkds/mkrom.py`).
- Los fotogramas de revisión y el audio intermedio van a `rutas.trabajo(id)`; los vídeos a `rutas.salida(id)`.
- El motor debe poder importarse desde `proyectos/<slug>/video.py` con `sys.path.insert(0, rutas.motor_dir(id))`.

## Cierre
1. `python valedores.py extraer <id>` y comprueba que sale lo esperado (skill `extraer-assets`).
2. Un vídeo de prueba de principio a fin con la skill `crear-video` y revísalo (`revisar-video`).
3. Saca 3–5 fotogramas bonitos a `juegos/<id>/vistas/` y rellena `vistas` si quieres un orden concreto.
4. `python valedores.py skills` y `python valedores.py doctor`.
