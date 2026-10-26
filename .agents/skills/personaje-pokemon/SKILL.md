---
name: personaje-pokemon
description: Crea un personaje custom (sprites del mapa 32x32 de 16 frames y sprites de combate de frente y espalda 80x80) en estilo Pokémon Platino a partir de fotos o de una descripción de una persona real, listo para usarlo en las cinemáticas con esc.personaje('<nombre>', ...). Úsala cuando el usuario pida un sprite, personaje, avatar o «versión Pokémon» de alguien.
---

# Crear un personaje custom en estilo Platino

El usuario da un **nombre** (primer argumento) y, opcionalmente, una **descripción**. Las fotos de referencia
van en `entrada/<nombre>/` (créala y pídeselas si no existe). Entregas `biblioteca/pokemon-platino/personalizados/<nombre>/`, que el motor
de cinemáticas usa por nombre: `esc.personaje('<nombre>', tx, ty)`.

Argumentos recibidos: $ARGUMENTS

`<nombre>` en minúsculas y con `_` (sin espacios ni tildes): es la carpeta de salida, el nombre del script y
el que se usa en las escenas. Todos los comandos se ejecutan desde `juegos/pokemon-platino/`.

## 0. Contexto obligatorio
1. `juegos/pokemon-platino/AGENTS.md` y la sección «Personajes custom» de `juegos/pokemon-platino/CONOCIMIENTO.md`.
2. `biblioteca/pokemon-platino/personalizados/README.md` (formato de salida).
3. `tools/custom/el_pana.py`: el ejemplo completo y aprobado por el usuario. **Cópialo como plantilla.**
4. `tools/custom/comun.py`: utilidades (`frames_mapa`, `frente_base`, `espalda_base`, `recolorear`, `pon`,
   `pon_opaco`, `es_borde`, `colores`, `guardar_mapa`, `guardar_combate`, `vista`, `revision`).

## 1. Ficha del personaje (antes de tocar píxeles)
Mira todas las fotos de `entrada/<nombre>/` (léelas con Read) y la descripción, y apunta:
- **Pelo**: color (3 tonos: oscuro, medio y claro), largo y forma (corto, revuelto, rapado, coleta, melena,
  calvo...). **Barba o bigote**, **gafas** (de pasta, finas, de sol), **gorra o sombrero**.
- **Piel**: el juego tiene 2-3 tonos de piel; elige si conviene oscurecerlos.
- **Ropa**: la que más le identifica en las fotos: prenda de arriba (color, manga larga o corta), de abajo y
  calzado. Mira qué se repite entre fotos.
- **Complexión y edad aparente**: delgado o corpulento, alto, niño, adulto o mayor.
- **Rasgo distintivo**: lo que hace que se le reconozca a 32x32 (normalmente el pelo, las gafas o la barba).
  A ese tamaño caben 3 o 4 rasgos; prioriza.

Si no hay fotos ni descripción suficiente, **pregunta** antes de seguir. Si las fotos se contradicen (ropa
distinta), elige lo más característico y dilo al entregar.

## 2. Elegir las bases del juego
Nunca se dibuja desde cero: se parte del sprite del juego que más se parezca en **silueta** (pelo, gorra,
complexión), aunque los colores no se parezcan, porque recolorear es fácil y redibujar la silueta no.
```
python tools/custom/herramientas.py bases mapa       # biblioteca/pokemon-platino/personalizados/_bases/mapa.png
python tools/custom/herramientas.py bases frente     # frontales de combate (80x80)
python tools/custom/herramientas.py bases espalda    # espaldas (solo hay 11: protagonistas y parejas)
```
1. Mira las hojas y elige 2 o 3 candidatos de cada tipo.
2. Amplíalos: `python tools/custom/herramientas.py ampliar mapa 027 002 ...` (y `ampliar frente 024`,
   `ampliar espalda 02`). Salen con rejilla y coordenadas en `biblioteca/pokemon-platino/personalizados/_bases/`.
3. Elige uno de cada tipo. Las 16 direcciones del mapa deben venir de la **misma** base (si no, el personaje
   cambia de forma al girarse). No uses los `ketsuban` ni sprites de Pokémon u objetos.
4. Saca sus colores por zonas: `python tools/custom/herramientas.py paleta mapa 027` (y `paleta frente 024`).
   Con eso escribes las tablas de recoloreo.

## 3. Script del personaje
Copia `tools/custom/el_pana.py` en `tools/custom/<nombre>.py` y adapta:
- `NOMBRE`, `BASE_MAPA` y el docstring (rasgos y bases elegidas, con el porqué).
- **Tablas de recoloreo por zona** `{color_original: color_nuevo}`: cabeza (filas 0 a ~20), torso (~21-25)
  y piernas (~26-31) en el mapa; en combate, por cajas `(x0, y0, x1, y1)` medidas en la imagen ampliada.
  Recolorea siempre por zona: el juego reutiliza el mismo gris o marrón en el pelo, la ropa y las botas.
- Cada color nuevo con **rampa de 3 o 4 tonos** (claro, medio, oscuro y sombra) que conserve el contraste de
  los originales. Mantén el contorno negro `(0, 0, 0)` y no uses colores puros saturados.
- **Rasgos a mano** con `pon` (sobre píxeles ya opacos) o `pon_opaco` (para añadir silueta: un tupé o una
  coleta). Cada dirección tiene su posición: mira la ampliación. Por ejemplo, la barba se pinta en los 2
  píxeles de piel más bajos de la cara, las gafas en la fila de los ojos y nada de la cara mirando arriba.
- `combate()` con `frente()` (80x80) y `espalda()` (tira de 160x80 con 2 poses; la 2.ª está desplazada, mira
  `el_pana.py`). Si no hay espalda parecida, recolorea la que tenga la silueta de cabeza más cercana.
- Al final del `__main__`: `vista(NOMBRE)` y `revision(NOMBRE, BASE_MAPA)`.

Ejecuta `python tools/custom/<nombre>.py`.

## 4. Revisión (obligatoria, itera hasta que esté bien)
Lee `biblioteca/pokemon-platino/personalizados/<nombre>/_revision.png` (los 16 frames x6, nuevo encima de la base) y
`biblioteca/pokemon-platino/personalizados/<nombre>/_vista.png`. Comprueba:
- [ ] Se reconoce a la persona: los rasgos de la ficha se ven a tamaño real (mira también la fila pequeña de
      `_vista.png`, que es como se verá en las escenas).
- [ ] Las 16 direcciones son coherentes: mismos colores, rasgos en su sitio en cada frame, nada que aparezca
      y desaparezca al andar (compara los frames de paso 1 y 3 con los quietos).
- [ ] No hay fugas de color: ni piel teñida de ropa ni pelo en los zapatos (busca píxeles sueltos).
- [ ] Contorno cerrado y oscuro, sin huecos ni píxeles transparentes dentro de la figura.
- [ ] El frente y la espalda de combate son la misma persona que el sprite del mapa (pelo, ropa, rasgos).
- [ ] Colores por frame: el juego usa como mucho 15 (+ transparente). La revisión marca en rojo los que se
      pasan. No es obligatorio, pero si hay muchos más, unifica tonos parecidos.

Para medir coordenadas sobre el resultado: `python tools/custom/herramientas.py ampliar mapa <nombre>`
(los 16 frames x8 con rejilla, igual que con las bases).

## 5. Enseñar al usuario y probarlo en el motor
1. **Enséñale `_vista.png` antes de usar el personaje en ninguna escena** y pregunta si se parece. Si pide
   cambios, vuelve al paso 3. Lo mejor es ofrecer 2 o 3 variantes como imágenes de prueba etiquetadas (por
   ejemplo, dos colores de pelo) cuando dudes entre opciones.
2. Comprueba que el motor lo encuentra: `cd cinematicas && python herramientas.py personaje <nombre>`.

## 6. Documentar
- Añade una sección al final de `biblioteca/pokemon-platino/personalizados/README.md`: cómo se genera, rasgos, bases usadas.
- Si aprendiste algo reutilizable (una base que funciona bien para cierto tipo de persona, un truco de
  pixel art, un fallo), apúntalo en la sección «Personajes custom» de `juegos/pokemon-platino/CONOCIMIENTO.md`.
