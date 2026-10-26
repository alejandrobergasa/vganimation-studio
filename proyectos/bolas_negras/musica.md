# Música — BOLAS NEGRAS

Pieza **original** (no es una BGM del juego): compuesta con notas propias y tocada con los instrumentos del banco 50 de la SDAT de
Mario Kart DS (bajo, acordes, melodía, pad, campanilla, metales y batería). Muestra = la pieza completa, 36 s, **solo música**
(sin voces ni efectos): `musica/muestra.wav`. Código: `musica_bn.py`; notas en `musica/partitura.json`.

## Resumen
- Género: pop-rock de carretera, alegre, que se vuelve cómico-suspense y luego triste/dramático.
- Tonalidad: La mayor (carretera) → La menor (portero y Santos). Tempos: 120 bpm (carretera) · 92 bpm (portero) · 60 bpm (Santos).
- Instrumentos (banco 50): programa 5 bajo, 3 acordes, 13 melodía, 14 pad, 15 metales, 4 campanilla; kit 127 (bombo 36, caja 40, charles 42, platillo 59).

## Estructura (alineada con el guion)
| Tiempo | Sección | Qué suena | Por qué |
|---|---|---|---|
| 0:00–0:12 | Carretera | A–D–E–D, bajo saltarín, acordes a contratiempo, bombo/caja/charles, melodía pegadiza (octava más aguda en el 2.º ciclo) | Ganas de ver la bola negra; energía de conducción (planos 1–5). |
| 0:12–0:16 | Aparcar | Mismo pulso sin melodía ni bombo/caja, solo bajo, acordes y charles | Frenan, bajan y caminan hacia la puerta (plano 6). |
| 0:16–0:24 | Portero | Bajo serio y pad en La menor, bombo suave. Arpegio de campanilla al pagar (0:19 y 0:20,9) y cadencia de metales en 0:22 («PASEN, PASEN») | Pedro deadpan; el pago suena a «moneda» (planos 7–10). |
| 0:24–0:32,5 | Santos | Lamento lento: Am–F–C–E con pad, melodía descendente, latido de bombo creciente desde 0:28 | Decepción y zoom lento a su cara (planos 11–14). |
| 0:32,5–0:36 | Golpe final | Acorde de La menor con novena + platillo + bombo, cola con fundido de 1,5 s | Remate de «¿QUÉ BUSCAN?» y corte a QUEBUSCA (plano 15). |

## Efectos y voces previstos (se montan en la fase de escenas/render, no en la muestra)
- Voces: «blip» tipo máquina de escribir con el mismo banco, un grano por letra y tono distinto por personaje (Alega, Vivi, Pedro, Santos); sin imitar voces reales.
- Efectos de la ROM (ids ya usados y comprobados en el ejemplo «Abalos»; SSAR 0): derrape al aparcar → 465 · turbo/arranque → 546 · cuenta → 501. Los de pasos, puerta y monedas se eligen del catálogo (`catalogo_audio.csv`) en el storyboard.
- Mezcla: música ×0,5 con ducking (×0,62) mientras hay texto; pico final ≈ −1 dB medido en el MP4.

## Comprobaciones hechas (medidas, no escuchadas)
- WAV de 36,00 s, pico −0,7 dB, sin silencios intermedios (hueco de ≈ 0,1 s en cada compás del portero corregido; solo calla el último 0,1 s de la cola).
- Espectrograma revisado: las 5 secciones se ven con el perfil esperado. **No he podido oír la pieza**: la valoración del gusto es tuya.

## Decisiones propias
- Música propia y no una BGM del juego, para poder cortarla exactamente en los puntos del guion.
- Lo que cambie en el guion (tiempos) obliga a retocar las constantes `T_*` de `musica_bn.py`; tiempos en la cabecera del script.
