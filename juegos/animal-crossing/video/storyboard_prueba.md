# Storyboard — vídeo de prueba (≈ 60 s)

**Idea**: Tom Nook (modelo `npc_sp/model/rcn`) le explica a un vecino (modelo `npc/model/16/17`) cómo se
construyó este repositorio. Escenario: el pueblo delante de la tienda Super Nook (`str/shop/*/obj_ngSs`),
con césped (`bg/ct0/grd_set0a`), árboles (`fg/tree`) y flores (`fg/flower`).
Formato: 1280×720 (render base 640×360 ×2, vecino más cercano), 30 fps, H.264 yuv420p.
Fuente: `font/fontA`. Ventana de diálogo: `a_mes/*`. Voces: sílabas del SDAT (archivo de ondas 18 y 19).
Música: secuencia 37 del SDAT (`sound_dataEUR.sdat`), sintetizada por `tools/ww/synth.py`.

| Escena | Tiempo | Contenido | Assets |
|---|---|---|---|
| 1. Título | 0–5 s | El vecino camina hasta Nook. Título «Animal Crossing: Wild World – De la ROM al vídeo». Cámara avanza. | modelos + anim `walk1`, `wait1`, fuente |
| 2. Diálogo | 5–52 s | 10 líneas alternando Nook / vecino. Cada una con una pizarra lateral que muestra datos reales: cabecera de la ROM, rutas de ficheros, texturas decodificadas, forma de onda de una sílaba de voz, estructura del repo. Emotes `mr_*`, parpadeo y boca por texturas. | `a_mes`, fuente, texturas, ondas SDAT |
| 3. Cierre | 52–60 s | Cámara se aleja, ambos se despiden con `mr_happy`, texto final, fundido a negro y música que se apaga. | todo |

Región: la ROM es **europea (ADMP)**; los rótulos de tienda salen en español (variante `S`).
