# Pokémon Platino: cinemáticas con sprites del juego

## Estructura (`juegos/pokemon-platino/`)
- La ROM va en `roms/` (no se modifica). `tools/`: extractor (`extract.py`, `ndsgfx.py`, `msg.py`, `names.py`) y sintetizador de la música y
  los efectos del juego (`sonido.py`). Regenerar todo: `python valedores.py extraer pokemon-platino`.
- `biblioteca/pokemon-platino/extraidos/`: todos los gráficos en PNG (ver su `README.md`; regenerable). La fuente del juego y los marcos de
  diálogo están en `extraidos/interfaz/`.
- `biblioteca/pokemon-platino/personalizados/`: personajes propios en estilo Platino (ver su `README.md`), p. ej. `el_pana`. Se generan con
  scripts en `tools/custom/` y el motor los usa por nombre: `esc.personaje('el_pana', x, y)`. Para crear uno nuevo: skill `personaje-pokemon`
  (fotos en `entrada/<nombre>/`).
- `cinematicas/`: motor de cinemáticas en Python (`motor/`, y `motor_v2/` con sombra arreglada y escenarios animados) y escenas de
  referencia (`escenas/`). API completa en `cinematicas/README.md`.
- `ejemplos/`: recetas de música con el banco de Platino, transcripción y montaje de vídeos anteriores (referencia; escriben junto a sí mismos).
- `NOTAS_ROM.md`: dónde está cada gráfico dentro de la ROM.

**Lee `CONOCIMIENTO.md`** antes de tocar el motor, los mapas o crear personajes: recoge formatos, decisiones y fallos ya resueltos.

## Cómo hacer una cinemática nueva
Flujo por fases: skill `crear-video`; motor y revisión: skill `cinematica-pokemon`. Resumen:
1. Elige personajes: `python juegos/pokemon-platino/cinematicas/herramientas.py personajes` y mira la imagen (`_personajes.png` en la carpeta de trabajo).
2. Elige un escenario real con `MapaReal` y genera su plano: `herramientas.py mapa <zona>`. Coloca personajes solo en tiles que no estén en rojo.
3. Copia `cinematicas/escenas/demo_parque_v2.py` como plantilla en `proyectos/<slug>/video.py` (cabecera estándar de `crear-video`).
4. Renderiza: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py`.
5. **Revisa siempre**: la hoja de contactos y los frames clave (`herramientas.py frames ...`). Ajusta posiciones y tiempos e itera.
6. Entrega el `.mp4` o el `.gif` de `salida/<slug>/`.

## Reglas
- Usa solo gráficos del juego. Para escenarios usa `MapaReal` (mapas renderizados desde el ROM), no el `Mapa` 2D de tiles.
- `tools/mapa3d.py` + `tools/nsbmd.py` renderizan los modelos 3D de los mapas; las zonas con nombre están en
  `cinematicas/motor/mapa_real.py` (ZONAS). Si añades una, compruébala con `herramientas.py mapa`.
- El texto de los diálogos va en español, con la fuente del juego (admite á é í ó ú ñ ¡ ¿). Máximo unos 26 caracteres por línea y 2 líneas por ventana; usa `\n` para cortar.
- El tiempo va en frames a 30 fps. Andar = 8 frames/tile, correr = 4.
- Los personajes cuyo nombre interno es `ketsuban` son huecos vacíos del juego: no los uses.
