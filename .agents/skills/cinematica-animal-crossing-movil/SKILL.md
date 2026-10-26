---
name: cinematica-animal-crossing-movil
description: Crea un vídeo vertical (1080x1920) de Animal Crossing Wild World para redes sociales en móvil (TikTok, Reels, Shorts) con el motor de juegos/animal-crossing/video. Úsala (dentro del flujo de crear-video) cuando el usuario pida un vídeo/corto/cinemática para móvil o redes, o un vídeo explicativo con gráficos de datos, música propia y diálogo de personajes.
---

# Cinemática móvil: vídeo vertical para redes

Argumento: tema/idea del vídeo (y, si hay, duración, personajes, estilo de música). Si falta algo, elige un valor razonable, anótalo y sigue; no preguntes salvo bloqueo real.
Parte de la skill `cinematica-animal-crossing` (reglas de `juegos/animal-crossing/AGENTS.md`: solo assets de la ROM más lo que el usuario aporte en `entrada/`, texto en español con `font/fontA`, no tocar la ROM, `python -I`, revisar fotogramas abriendo los PNG como imagen). Esta añade lo específico del formato móvil y se usa dentro del flujo por fases de `crear-video`. **El ejemplo de referencia es `juegos/animal-crossing/video/gasto.py`** (copiarlo a `proyectos/<slug>/video.py`, poner la cabecera estándar de `crear-video` con `JUEGO = 'animal-crossing'` y `os.environ.setdefault('VIDEO_VERTICAL', '1')` antes de importar el motor, y adaptar).

## Formato y zonas seguras (base 360×640, ×3 = 1080×1920, 30 fps)
- El guion pone `os.environ.setdefault('VIDEO_VERTICAL', '1')` **antes** de `from motor import *`.
- Zonas libres de interfaz de la red: arriba ≥ 22 px (base), abajo ≥ 60 px. Contenido clave entre y=22 y y=580.
- Distribución en planos con datos: **cuadro arriba (y 22–298) · personajes (≈300–440) · bocadillo abajo (y≈448–578)**.
- Planos con cortes duros (función `current_shot`/`SHOTS` de `gasto.py`): `wide` (presentación y cierre), `nook`/`vil` (primer plano de quien reacciona), `board` (cuadro de datos). Cambiar de plano cada 2–5 s; las tandas del mismo plano mueven la cámara despacio.
- FOV 34° recorta los lados: dos personajes a ±1,25 caben con cámara a z ≥ 15; para primeros planos z≈6–7.

## Legibilidad (lo que más importa en móvil)
- Diálogo: `font.draw(..., scale=2, bold=True)`; nube `make_bubble(rom, 13, extra_rows=5)` (344×130). **≤ 3 líneas y ≈ 18 caracteres por línea** → frases de ≤ 50 caracteres; `schedule` hace `assert` si no caben. Una idea por línea; si no cabe, divide en dos líneas de guion.
- Cifras clave a ×3, rótulos a ×2, texto de apoyo a ×1 (solo secundario o resúmenes). Nunca información esencial a ×1.
- Texto tecleado a 22 car/s, pausa 0,9 s al acabar. Colores reales con `Font.draw(color=...)` (oscuro sobre blanco, blanco con sombra sobre color).
- Título en los primeros 3 s (`big_text`, ×3, auto-ajusta al ancho) con una pregunta o gancho.

## Gráficos propios en el estilo del juego
Reutiliza de `gasto.py`: `panel` (borde naranja, sombra, puntitos), `rrect` (esquinas redondeadas), cinta de título verde, `draw_icon` (ficha con icono pixel 9×9 definido como cadenas), `sparkle`, columna apilada con brillo, tarjeta de la categoría actual, resumen final. Un gráfico por idea: **una tarjeta grande con lo que se está diciendo ahora** y el contexto (columna/serie) pequeño al lado. Se revela al ritmo del texto: `LINES` lleva `(fragmento, n)` y `schedule` calcula el instante exacto en que se teclea ese fragmento. Paleta distinta por categoría, entrada con `ease`, destello 0,8 s al aparecer.
- Datos reales: cita la fuente en el panel o en el diálogo, verifica cifras (búsqueda y lectura web; PDF → `pdftotext` o PyMuPDF por posiciones) y redondea con el mismo `fmt` en gráfico y diálogo. Dilo en el storyboard si el redondeo no suma exacto.

## Música (`juegos/animal-crossing/video/reggaeton.py` como plantilla)
- Música propia con `AudioBank.notes(notas, segundos, banco)` → `synth.tocar_notas`: notas `(inicio_s, dur_s, tecla, vel, programa, pan, vol)`. Banco 12: p0 bombo, p1 caja, p2 hi-hat, p6 bajo, p3 punteo, p13 campanilla (una octava arriba). Para otro género, mide instrumentos con el espectro (centroide, decaimiento, plano) antes de elegirlos; otros bancos en `juegos/animal-crossing/CONOCIMIENTO.md`. Receta general: `conocimiento/audio.md`.
- Mezcla: música ×0,5 con *ducking* a 0,62 mientras hay voz (suaviza 0,15 s), voces = sílabas SDAT (Nook onda 18 ×0,78; vecino onda 19 ×1,35), «ding» en cada revelado, fundido de salida 1,8 s. Pico ≈ −1 dB, sin silencios (`silencedetect`).

## Procedimiento
1. Datos/guion (fases `idea` y `guion` de `crear-video`): reúne cifras verificadas; escribe `LINES` (≤ 50 car., ritmo de 2–4 s por línea, reacciones del vecino con emotes `niko/happy/hatena/ha`). Total 45–65 s.
2. Música (fase `musica`): muestra de audio en `proyectos/<slug>/musica/muestra.wav` antes de montar nada visual (receta en `conocimiento/audio.md`).
3. Storyboard `proyectos/<slug>/storyboard.md` (tabla escena/tiempo/plano/contenido, fuente de datos, música).
4. Copia `juegos/animal-crossing/video/gasto.py` → `proyectos/<slug>/video.py`; adapta datos (`CATS`…), iconos, `LINES`, música.
5. `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py --solo-frames t1,t2,...` en: título, un plano de cada tipo, cada tipo de tarjeta, resumen, cierre. Copia los PNG elegidos a `proyectos/<slug>/previsualizacion/`. Míralos a tamaño real (no solo miniaturas): ¿se lee todo a ×1 en un móvil? ¿el bocadillo tapa algo? ¿cabezas bajo el cuadro?
6. Render: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py` → `salida/<slug>/…mp4` (~2,5 min). Revisión con la skill `revisar-video` (`valedores.py revisar hoja|frame|audio|info`).
7. Entrega: ruta, duración, assets, fuente de datos, comando; qué no se ha podido comprobar (p. ej. audio no escuchado). Añade a `juegos/animal-crossing/CONOCIMIENTO.md` lo nuevo.

## Efectos, transiciones y sonido (referencia: `juegos/animal-crossing/video/pesca.py`)
- Si piden «efectos chulos»/transiciones: `pesca.py` trae transiciones por corte (`transition`: barras, zoom con flash, iris, barrido), rótulos con rebote (`pop_text`), bocadillos sobre la cabeza (`bubble_pop`), temblor, golpes de zoom, líneas de velocidad, confeti y cifras que cuentan. Copia solo lo que haga falta.
- Efectos de sonido: `juegos/animal-crossing/video/sfx.py` (`SFX(AudioBank)`: `whoosh`, `splash`, `ding`, `fanfarria`, `golpe`…) hechos con el banco 12; los SFX 99-171 del SDAT no sirven sueltos. Sincroniza cada uno con el evento visual en `build_audio`.
- «Sin título» si lo piden: no pintes rótulo inicial; abre con iris y la primera frase.
- Personaje propio recoloreado: `juegos/animal-crossing/video/personajes/lincelucas.py` (lince ibérico) es la plantilla; por defecto usa un vecino normal del juego.

