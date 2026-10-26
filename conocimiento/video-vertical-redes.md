# Vídeo vertical para redes (TikTok, Reels, Shorts)

Salida final **1080×1920, 30 fps, H.264 `yuv420p` + AAC, `+faststart`**. Los motores componen a baja resolución (estilo DS) y
amplían con vecino más cercano a un factor entero para conservar el píxel:

| Juego | Compositor | Ampliación |
|---|---|---|
| Animal Crossing | 360×640 | ×3 |
| NSMB | 216×384 | ×5 |
| Mario Kart DS | 3D a 1080×1920 con supermuestreo | — |

## Zonas seguras
La interfaz de la red tapa la parte alta y baja. Sobre una base de 360×640: **arriba ≥ 22 px, abajo ≥ 60 px** libres; el contenido
clave entre y = 22 y y = 580. En MKDS: evitar el 12 % superior y el 18 % inferior para rótulos importantes.

## Legibilidad en móvil (lo que más importa)
- Diálogo grande: ≤ 3 líneas y ≈ 18 caracteres por línea. Una idea por línea; si no cabe, dividir en dos líneas de guion.
- Jerarquía de texto: cifras clave a ×3, rótulos a ×2, apoyo a ×1 (nunca información esencial a ×1).
- Texto tecleado ≈ 20–22 caracteres/s, y una pausa de ≈ 1 s al completarlo para poder leerlo. No cortes una frase para encajar la duración: alarga la escena.
- Gancho en los primeros 3 s (pregunta o título). Contraste: oscuro sobre blanco, blanco con sombra sobre color.
- Cambia de plano cada 2–5 s; planos generales para situar y cercanos para la acción o la reacción.

## Duración
45–65 s para explicativos con datos; 20–40 s para cortos de humor. Todo lo que se pueda calcular de una cronología única
(`DURATION`, tiempos de cierre) debe derivarse de ella, no de segundos escritos a mano en varios sitios; las duraciones pueden ser fraccionarias.

## Técnica
- Cada fotograma es función pura de `t` (render paralelo y reproducible).
- Enviar la resolución lógica a ffmpeg y escalar allí (`scale=1080:1920:flags=neighbor`) evita mover fotogramas ampliados desde Python.
- Cachear sprites/texto reutilizados; no renderizar el mismo modelo 3D en cada fotograma.
- Detalles específicos de cada motor: skill `cinematica-<juego>` y `juegos/<id>/CONOCIMIENTO.md`.
