# Audio: música propia, voces, efectos y mezcla

Los juegos de DS no traen audio grabado: la música y los efectos son **secuencias tipo MIDI (SSEQ) que tocan instrumentos
(SBNK) hechos de muestras (SWAR/SWAV)**, todo dentro de `sound_data.sdat`. Cada juego tiene su sintetizador
(`juegos/<id>/tools/.../synth.py` o `sonido.py`) que lo convierte a PCM. No hace falta un soundfont externo.

## Componer música propia con los instrumentos del juego
Idea común: lista de notas `(inicio_s, duración_s, tecla_MIDI, velocidad, programa, panorama, volumen)` tocada con un banco del SDAT.

| Juego | Cómo |
|---|---|
| Animal Crossing | `AudioBank.notes(notas, segundos, banco)` → `synth.tocar_notas`. Banco 12: p0 bombo, p1 caja, p2 hi-hat, p6 bajo, p3 punteo, p13 campanilla (una octava arriba). Plantilla: `juegos/animal-crossing/video/reggaeton.py`, `musica_pesca.py`. |
| NSMB | `sonido.tocar_notas(son, 'BANK_CHIJO_BGM', notas, segundos)`. Ejemplo y receta: `juegos/nsmb/skills/cinematica-nsmb/references/produccion.md`. |
| Mario Kart DS | `mk/audio.py`: `bgm(i)`, `sfx_id(ssar, k)`, `Mezcla`. La SDAT no tiene nombres: elegir por `catalogo_audio.csv`. |
| Pokémon Platino | `esc.musica('SEQ_...')` para pistas del juego; para música nueva, `juegos/pokemon-platino/ejemplos/*/musica_*.py` (tocar un banco con notas propias o transcritas). |

Pasos:
1. **Inspecciona el banco**: qué programas existen y cómo suenan. Un número de programa vacío da silencio. Mide con el
   espectro (centroide, decaimiento) en vez de fiarte del nombre.
2. **Prueba unas notas** antes de componer todo.
3. Compón por secciones (motivo, armonía, tempo, instrumentación) acordes con el guion; guarda las notas y programas en
   JSON (`partitura.json`) y los WAV de cada pieza: así se rehace la mezcla sin perder la composición.
4. Escribe en `musica.md`: género, tempo (BPM), tonalidad, instrumentos (banco y programas), estructura con marcas de tiempo.
5. Entrega una **muestra de 20–40 s** en `proyectos/<slug>/musica/muestra.wav` para que el usuario la escuche en el estudio.

Cambiar o recortar una BGM del juego no es componer música original: dilo así en el brief si se usa una pista tal cual.
Respeta la frecuencia de muestreo del sintetizador (p. ej. 32768 Hz en `sonido.FS`): no reinterpretes sus muestras como 44,1/48 kHz.

## Voces
Los personajes no hablan: se usan **sílabas** o granos vocales del SDAT sincronizados con el texto que se teclea (un grano por
letra o grupo, con variación de tono y pausas en la puntuación). Nada de imitar la voz real de una persona. Granos de ≈ 80 ms
con rampas de entrada/salida y sin offset DC evitan clics; una cadencia fija en cada espacio suena mecánica.

## Efectos
- Reutiliza los WAV extraídos (`biblioteca/<id>/extraidos/audio/...`) o las secuencias de efectos del juego.
- Algunos efectos son bucles que el juego corta por código: recorta su duración y suaviza la cola.
- En AC, las secuencias 99–171 no sirven sueltas: usa `video/sfx.py` (hechos con el banco 12).
- Sincroniza cada efecto con su evento visual en la construcción del audio.

## Mezcla y niveles
- Música ≈ ×0,5 con **ducking** (≈ ×0,62 de ese nivel) mientras hay voz, con rampas de ≈ 0,15 s.
- Un «ding» o similar en cada revelado de datos ayuda a leer el ritmo.
- Fundido de salida de ≈ 1,8 s; nada de cortes secos al final.
- Objetivo: **pico ≈ −1 dB** (nunca ≥ 0 dB) medido en el MP4 final, ya codificado en AAC (los picos pueden cambiar). Sin silencios
  accidentales (`ffmpeg -af silencedetect`). Para redes, `loudnorm=I=-16:TP=-1.5:LRA=8` como punto de partida, midiendo después.
- Espectrograma y onda detectan cortes, saturación y silencios; **no prueban que algo suene bien**. Si nadie ha podido escucharlo,
  la entrega lo dice.

## Analizar audio o vídeo de referencia (opcional)
Con `requirements-opcional.txt` (librosa, faster-whisper, demucs, soundfile) hay recetas en `juegos/pokemon-platino/ejemplos/`
(`transcribir.py`, `segmentar.py`, `analizar_musica.py`, `musica_platino*.py`): separar pistas, transcribir diálogos, sacar tempo,
tono y acordes de una canción y rehacerla con el banco del juego.
