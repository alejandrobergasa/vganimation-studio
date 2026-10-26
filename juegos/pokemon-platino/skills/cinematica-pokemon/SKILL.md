---
name: cinematica-pokemon
description: Crea una cinemática animada estilo Pokémon Platino (GIF + MP4) a partir de un nombre y un guion, con los mapas, sprites, fuente y diálogos reales del juego y con personajes custom (p. ej. EL PANA). Úsala dentro del flujo de crear-video cuando el usuario pida una animación, cinemática, escena o vídeo con sprites de Pokémon.
---

# Crear una cinemática de Pokémon Platino

Se usa dentro del flujo por fases de `crear-video`. El usuario da un **nombre** y un **guion** (texto libre en español
con lo que pasa, quién habla y qué dice). Entregas `salida/<slug>/<nombre>.mp4` y `.gif` **revisados frame a frame**.
El listón es «perfecta»: nada de personajes atravesando árboles, ni diálogos cortados, ni gente hablando
de espaldas, ni huecos negros.

## 0. Contexto obligatorio (léelo antes de nada)
1. `juegos/pokemon-platino/AGENTS.md`: estructura y reglas.
2. `juegos/pokemon-platino/CONOCIMIENTO.md`: formatos, proyección, oclusión, fallos ya resueltos y cómo crear personajes custom.
3. `juegos/pokemon-platino/cinematicas/README.md`: API del motor (`Escena`, `MapaReal`, `Personaje`).
4. `juegos/pokemon-platino/cinematicas/escenas/demo_parque_v2.py`: plantilla de referencia.

**Motor**: usa `motor_v2` (`from motor_v2 import Escena, MapaReal`): misma API que `motor/` pero con la sombra de los
personajes bien dibujada y escenarios animados (flores, espuma del agua; `MapaReal(..., animado=False)` los
desactiva). `motor/` se conserva para las escenas antiguas.

Comandos de herramientas (con el proyecto activo, así las imágenes caen en `proyectos/<slug>/trabajo/`):
`python valedores.py ejecutar <slug> -- python juegos/pokemon-platino/cinematicas/herramientas.py <orden> ...`
(abajo: `herramientas.py <orden>`).

`<nombre>` en minúsculas y con `_` (sin espacios ni tildes).

## 1. Desglosa el guion (antes de escribir código)
Escribe una lista de **beats**, uno por acción: quién, qué hace, hacia dónde, cuántos tiles, qué dice y
cuánto dura. Decide:
- **Escenario**: elige de `ZONAS` en `motor/mapa_real.py` el que mejor encaje (pueblo, prado de flores,
  ruta con estanques...). Si ninguno encaja, busca otra zona en la matriz de Sinnoh (ver `CONOCIMIENTO.md`),
  renderízala con `herramientas.py mapa <fila> <col> <filas> <cols>`, mírala y, si sirve, añádela a `ZONAS`.
- **Hora**: según el guion (7 amanecer, 12 día, 18 atardecer, 22 noche).
- **Reparto**:
  - Personajes custom: los de `biblioteca/pokemon-platino/personalizados/` (`ls`), por su nombre de carpeta, p. ej. `'el_pana'`.
  - Personajes del juego: `herramientas.py personajes` y mira `_personajes.png`. Comprueba los frames de uno con
    `herramientas.py personaje <nombre>`. No uses los `ketsuban` (huecos vacíos del juego).
  - Si el guion nombra a alguien que no existe como custom («mi amigo Luis» con fotos en `entrada/`), créalo con
    la skill `personaje-pokemon` antes de seguir: incluye enseñarle los sprites al usuario. Si no hay fotos ni descripción, pregunta.
- **Diálogos**: el texto exacto del guion. Máximo unos 26 caracteres por línea, 2 líneas por ventana, cortes
  con `\n` entre palabras. Si una frase no cabe, pártela en varias ventanas, nunca la recortes.
  Con varios personajes hablando, empieza cada ventana con el nombre: `'EL PANA: ¡Hola!'`.

Si el guion es ambiguo en algo que cambia el resultado (quién es quién, dónde pasa), pregunta. Si no, decide tú
con buen criterio y dilo al entregar.

## 2. Plano y coordenadas
1. `herramientas.py mapa <zona> [hora]` → `_mapa_<zona>.png`: rejilla con coordenadas `x,y` y en rojo los tiles que no se
   pueden pisar. **Míralo** (recorta y amplía la parte que vas a usar).
2. Elige las posiciones de salida y los recorridos completos tile a tile. Ninguno puede pisar un tile rojo
   ni salirse del mapa (salvo que alguien salga del plano a propósito y luego se oculte con `desaparecer()`).
3. Al hablar, los personajes deben estar adyacentes o a 1-2 tiles, **mirándose** (`mirar(otro)`).
4. La cámara: `camara_sigue(protagonista)` o `camara_fija(tx, ty)` en el centro de la acción. Todo lo
   importante tiene que verse en los 256x192 de pantalla (16x12 tiles).

## 3. Escribe la escena
`proyectos/<slug>/video.py`, copiando la estructura de `demo_parque_v2.py` y su cabecera: `sys.path.insert(0, rutas.motor_dir('pokemon-platino'))`
(ver cabecera estándar en `crear-video`) y `from motor.recursos import SALIDA`:
- Docstring con el guion original.
- `mapa = MapaReal(...)`, `esc = Escena(mapa)` y el reparto.
- Un `esc.hacer(...)` por beat. Las acciones de un mismo `hacer` van en paralelo.
- Ritmo: empieza con `esc.fundido(entrada=True)` y termina con `esc.fundido(entrada=False)`. Deja
  `esc.esperar(8-20)` entre beats para que se lean las reacciones. Andar = 8 frames/tile y correr = 4
  (30 fps). Usa `emocion('!')` y `saltar()` para la sorpresa.
- El bloque `if __name__ == '__main__': esc.renderizar(os.path.join(SALIDA, '<nombre>'))` al final, como en la demo.
  Con el proyecto activo `SALIDA` es `salida/<slug>/`. `renderizar` deja `.gif` y `.mp4` allí y la hoja de contactos en la
  carpeta de trabajo.
- Sonido (solo va en el MP4): pon música del juego con `esc.musica('SEQ_...')` según el ambiente (ciudad,
  ruta, `SEQ_EYE_*` cuando aparece un rival, interiores...), cámbiala en los giros del guion y bájala con
  `esc.parar_musica()` en los fundidos. Añade efectos con `esc.sonido('SEQ_SE_DP_...')` en golpes,
  huidas, puertas... Los diálogos ya suenan solos. Nombres útiles en `cinematicas/README.md` («Sonido»).
  Para música propia con los instrumentos del juego mira `conocimiento/audio.md` y `juegos/pokemon-platino/ejemplos/`.

Si el guion pide algo que el motor no tiene (otra burbuja de emoción, un sprite que aparece, temblor de
pantalla, flash, un combate...), **añádelo al motor** (`juegos/pokemon-platino/cinematicas/motor/escena.py`) como una
acción nueva con el mismo patrón de generador. Usa gráficos de `biblioteca/pokemon-platino/extraidos/` (p. ej.
`efectos_mapa/`, `combate/`) y documenta la acción en `cinematicas/README.md`. No la simules con apaños en la escena.

## 4. Renderiza y revisa (obligatorio, itera hasta que esté perfecta)
1. `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py` → `.gif`, `.mp4` y hoja. Lee la salida de
   consola: cualquier `AVISO: ... pisa un tile bloqueado` es un error que hay que arreglar.
2. Lee la hoja `proyectos/<slug>/trabajo/<nombre>_hoja.png` entera.
3. Saca frames ampliados de los momentos clave (entradas, cruces con árboles y edificios, cada diálogo,
   reacciones y salidas): `herramientas.py frames proyectos/<slug>/video.py <i> <j> ...` (ruta desde la raíz del repo)
   → `_frames_video.png`. Sin índices saca 12 repartidos. Copia lo que quieras que valide el usuario a `previsualizacion/`.
4. Repasa esta lista en cada iteración y no entregues hasta que todo cumpla:
   - [ ] Nadie camina sobre árboles, edificios, agua o vallas (sin `AVISO`).
   - [ ] Los árboles, tejados y arcos que están delante tapan bien a los personajes, y nadie queda oculto
         justo cuando habla o reacciona.
   - [ ] Quien habla y quien escucha se miran; las direcciones de andar son coherentes con el sprite.
   - [ ] Cada diálogo se ve completo, sin cortes, con la flecha al final y tiempo para leerlo (`espera` ≥ 45).
   - [ ] La acción importante está dentro de pantalla y la cámara no muestra zonas negras ni bordes del mapa.
   - [ ] El ritmo respira: sin cortes bruscos ni esperas muertas largas.
   - [ ] El guion se cumple entero y en orden.
   - [ ] La sombra es una elipse sólida, también bajo árboles y tejados (motor_v2).
   - [ ] Los personajes custom se ven como en `biblioteca/pokemon-platino/personalizados/<nombre>/_vista.png`.
5. Si algo falla, corrige y vuelve al paso 1. La revisión final del archivo: skill `revisar-video`.

## 5. Entrega
- Dile al usuario dónde están `salida/<slug>/<nombre>.mp4` y `.gif`, la duración y el escenario.
- Enumera las decisiones que tomaste por tu cuenta (zona, hora, cámara, reparto) y lo que no se pudo hacer.
- Si aprendiste algo nuevo (una zona útil, una limitación, un fallo resuelto), añádelo a
  `juegos/pokemon-platino/CONOCIMIENTO.md`. Si añadiste acciones al motor, documéntalas en `cinematicas/README.md`.
