# Pedro en apuros — montaje v2

53 segundos, vertical 1080×1920, 30 fps. Encargo satírico ficticio, sin datos documentales. Fuente fontA y rótulo permanente PARODIA · FICCIÓN.

| Tiempo | Diálogo / acción | Cámara y edición |
|---|---|---|
| 0–2 | Gancho «PEDRO EN APUROS» | Primer plano de la foto sobre el vecino, apertura en iris, pop de título |
| 2–5,5 | «BRO, AYUDA POR FAVOR.» | Golpe de zoom, alerta sonora, ráfaga radial breve |
| 5,5–11 | «VOY JODIDO CON LAS ELECCIONES ESTAS.» | Página completa; barrido al general; golpe de zoom a Pedro a 7,8 s conservando el bocadillo |
| 11–17 | «Estás en un lío de la ostia, primo.» | Página completa; barras de color; primer plano de Nook; reacción general a 14,2 s |
| 17–20,5 | «Lo de Ábalos para empezar,» | Cláusula completa; barrido, rótulo e impacto grave |
| 20,5–24 | «lo de tu hermano para seguir,» | Cláusula completa; reacción de Pedro; barras, rótulo e impacto |
| 24–28 | «y lo de tu mujer para culminar.» | Final completo de la enumeración; barrido, rótulo e impacto |
| 28–32 | «PEDRO SANCHEZ, HIJO DE PUTA,» | Entrada lateral de Capitán, iris, fanfarria, rayos y confeti; letra completa |
| 32–36 | Repetición del estribillo | Barrido al general, rótulos al ritmo, frenazo tonal antes de la réplica |
| 36–40 | «Vas a ir a la cárcel, mano.» | Zoom e impacto; rótulo; doble golpe grave final |
| 40–46 | Vecino sentado frente al atardecer | Transición a color oscuro, música original triste en La menor |
| 46–53 | «que te vote txapote» | Mensaje completo, campanilla suave, fundido final |

La frase inicial de Nook corrige el error gramatical «estás es» del primer encargo. Se conserva «ostia». Las páginas son frases o cláusulas completas. Ninguna cambia antes de acabar de teclearse y tener al menos 0,9 s de pausa; las páginas largas permanecen durante los cortes de cámara internos. Texto a ×2, no más de tres líneas.

Personaje: modelo de vecino osezno cbr01 `npc/model/24/29.nsbmd` con `29.nsbtx`, camiseta `cloth/4/cloth065.nsbtx`. Se conserva cabeza, orejas, cuerpo, manos y patas del modelo original. La foto se proyecta sobre los triángulos de ojos, boca y frente de esa cabeza, siguiendo volumen y animación. No se usa la cabeza humana plana de v1. Foto externa autorizada explícitamente: `biblioteca/animal-crossing/personalizados/psan.jpg`, proporcionada por el usuario, sin modificar. `biblioteca/animal-crossing/personalizados/pedro/cara_foto.png` es el recorte RGBA preparado con imagegen; en memoria se ajusta a 64×64. Prompt registrado en el README del asset.

Resto de assets: Tom Nook rcn y Capitán wip, Village, arena grd_ssa, agua grd_riv.0, font/fontA, nube a_mes y sonidos del SDAT europeo ADMP. No se modifica ROM ni assets_extraidos.

Sonido: sílabas SDAT, canto con notas, música dembow original y coda triste original. SFX de `video/sfx.py`, muestras del banco 12: whoosh, pop, alerta, golpe, trino, fanfarria, tick, frenazo por remuestreo, sting y ding. La música baja bajo las voces y más durante el canto. Cada sonido está programado con el mismo tiempo que su efecto visual. No hay voz humana ni clonación.

Regenerar: `python -I video/pedro_parodia_v2.py`. Salida `salida/animal-crossing/pedro_parodia_v2.mp4`; conserva la v1. Fotogramas y hoja de revisión en `salida/_f/pedro_v2/`.

Revisión: muestras abiertas a 1080×1920 del vecino, diálogo, Capitán, atardecer y transiciones; hoja del MP4 abierta. Se corrigió el solapamiento del título durante su entrada. Las nueve páginas ocupan como máximo dos líneas a ×2 y dejan entre 1,92 y 4,15 segundos tras completar la escritura. Fotograma 3,7 repetido antes/después de renderizar 49: SHA-256 idéntico. Mezcla masterizada con loudnorm para móvil. MP4 H.264 yuv420p, AAC estéreo 44,1 kHz, 53 s. Audio codificado: pico real -1,0 dBFS, sin saturación; silencedetect sin silencios de 0,5 s a -45 dB. Audio validado técnicamente, no escuchado.
