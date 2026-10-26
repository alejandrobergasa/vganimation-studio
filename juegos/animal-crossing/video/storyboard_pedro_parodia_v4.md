# Pedro — montaje natural v4

46,4 s, 1080×1920, 30 fps. Misma parodia ficticia y mismo diálogo de v3. Bocadillos completos, sin efectos sobre el texto. Foto del usuario a 64×64 proyectada sobre la cabeza redonda del vecino de la ROM.

| Tiempo | Acción | Cámara / sonido |
|---|---|---|
| 0–19,6 | Petición de Pedro y respuesta de Nook | Cortes normales entre quien habla y general; movimientos suaves de cámara, voz Animal Crossing y pops discretos |
| 19,6–23,4 | Final de la enumeración de Nook | Se abre un plano general estable antes de la entrada del caminante |
| 20,8–34 | Capitán recorre una trayectoria de izquierda a derecha, por delante de ambos | Animación walk1 continua, pasos ligados al ciclo de piernas; entra y sale fuera de encuadre, sin aparición repentina |
| 23,4–31,4 | Capitán canta dos veces el estribillo original | Plano general continuo, voz y pasos se desplazan de izquierda a derecha |
| 24,25–25,45 | Pedro se echa al suelo de lado llorando | La rotación de caída se combina con mr_naku1/mr_naku2; apoyo calculado sobre el suelo; impacto suave |
| 25,45–35,4 | Pedro permanece en el suelo llorando; Nook dice la última frase | Lágrimas ligadas a los ojos, temblor de la animación y sollozos SDAT; nunca vuelve a levantarse |
| 35,4–42,9 | Misma pose de llanto tumbado, al atardecer | Único fundido breve; órbita continua desde detrás hasta el frente, acercándose; música triste |
| 41,4–46,4 | Mensaje final original; Pedro continúa llorando | Cara reconocible y visible al completar la órbita; fundido final |

Se eliminan los flashes, separaciones RGB, glitches, barridos, confeti, rótulos con rebote, contadores, ventanas de reacción y microtransiciones. Se conserva el ritmo de diálogo mediante cortes normales. Plano general continuo durante el paso y la caída.

Capitán: modelo wip de la ROM. Trayectoria x=-5,2..5,2 entre 20,8 y 34 s, z=2,8; Nook y Pedro están detrás en z≈1. Su animación walk1 se superpone solo con talk1 durante el canto. El sonido usa el mismo kappa_x(t) para panoramizar voces y pasos.

Pedro: mismo modelo osezno cbr01 y misma textura fotográfica de v3. Cae girando 90° sobre el eje Z mientras hace mr_naku, y mantiene mr_naku2 en bucle tumbado hasta el final. Cada fotograma ajusta la altura a la cota del suelo a partir del mínimo de los vértices transformados. Las gotas se calculan desde los puntos locales de los ojos con el nodo head, pose y matriz de mundo del fotograma. Se ocultan cuando la cámara mira la nuca.

Assets y fuente de imagen: ROM europea ADMP, con la excepción solicitada de la foto original del usuario `biblioteca/animal-crossing/personalizados/psan.jpg`, preparada en `biblioteca/animal-crossing/personalizados/pedro/cara_foto.png` y sin cambiar el original. Fuente fontA, nube a_mes, ropa cloth065, modelos rcn/wip/cbr01 y banco SDAT. Sin cambios en ROM ni assets_extraidos. Voces y sollozos de sílabas del juego; no hay voz humana real.

Regenerar: `python -I video/pedro_parodia_v4.py`. Entrega `salida/animal-crossing/pedro_parodia_v4.mp4`. Muestras y revisión en `salida/_f/pedro_v4/`. Las versiones anteriores se conservan.

Revisión final: PNG y hoja del MP4 abiertos; comprobados entrada gradual de Capitán, cruce, caída, permanencia tumbado y órbita con cara visible en el cierre a 44 s. MP4 H.264 yuv420p 1080×1920, 30 fps, 1392 fotogramas, 46,400 s y 22.304.051 bytes; AAC estéreo 44,1 kHz. Pico -1,1 dB, media -22,0 dB; sin silencios de 0,5 s a -45 dB. Audio comprobado técnicamente, no escuchado. El mínimo Y de Pedro es 0 en el pueblo a 25,5/29/34,5 s y -0,18 en la playa a 36/42/45 s. Frame(28) tiene SHA-256 idéntico antes/después de frame(45). La posición X de Capitán pasa de -5,2 a 5,2 sin saltos.
