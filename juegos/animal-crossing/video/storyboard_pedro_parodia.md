# Pedro en Animal Crossing — parodia ficticia

Vídeo vertical, 1080×1920, 30 fps, 53 segundos. Diálogo del encargo, dividido en bocadillos de tres líneas como máximo. Se conserva «estás es» y «ostia» del texto original. Tildes normalizadas en Ábalos, lío y cárcel. Las alusiones judiciales son diálogo satírico ficticio del encargo; no se presentan datos ni afirmaciones documentales. Rótulo permanente «PARODIA · FICCIÓN».

| Tiempo | Plano | Acción / texto |
|---|---|---|
| 0–2 | General del pueblo | Pedro en Animal Crossing; Nook y vecino humano con cara de Pedro |
| 2–11 | Pedro / general / Pedro | «BRO AYUDA POR FAVOR VOY JODIDO CON LAS ELECCIONES ESTAS» |
| 11–17 | Nook / general | «estás es un lío de la ostia primo,» |
| 17–20,5 | Nook | «lo de Ábalos para empezar,» |
| 20,5–24 | Reacción de Pedro | «lo de tu hermano para seguir» |
| 24–28 | Nook | «y lo de tu mujer para culminar» |
| 28–32 | Capitán, primer plano | Canta «PEDRO SANCHEZ, HIJO DE PUTA,» con sílabas SDAT afinadas |
| 32–36 | General con Capitán | Repite «PEDRO SANCHEZ, HIJO DE PUTA» |
| 36–40 | Nook | «vas a ir a la cárcel mano» |
| 40–46 | Orilla, sentado | Pedro mira hacia el sol al atardecer; arpegio triste en La menor |
| 46–53 | Orilla / cierre | «que te vote txapote»; fundido final |

Assets: ROM europea ADMP, modelos PBody/boy, PHead/0/0 con paleta PPal/0/0 para la nuca en el cierre, npc_sp/model/rcn (Tom Nook), npc_sp/model/wip (Capitán), ropa cloth012, escenario Village, arena grd_ssa y agua grd_riv.0. Fuente font/fontA, nube a_mes, audio sound_dataEUR.sdat, instrumentos banco 12 y voces de ondas 17–19 (asignación aproximada). Sin modificación de la ROM ni de assets_extraidos.

Excepción externa solicitada por el usuario: biblioteca/animal-crossing/personalizados/pedro/cara.png, cabeza pixelada generada con la herramienta integrada imagegen. Prompt: «single transparent front-facing pixel-art cutout head of Pedro Sánchez, recognizable likeness, short dark hair, clean shaven, neutral worried expression, Nintendo DS / Animal Crossing aesthetic, no neck, no torso, no text». Se guarda el original; el motor lo muestrea a 128×128 y lo aplica como decal 3D sobre el cuerpo humano del juego.

Audio: voces Animal Crossing (no voz real ni clonada), estribillo compuesto con sílabas afinadas y subtítulos completos; instrumental dembow propio y coda triste original usando muestras ROM. Regeneración: `python -I video/pedro_parodia.py`. Revisión de muestras: `python -I video/pedro_parodia.py --solo-frames 1,3,6,12,18,22,26,30,34,38,43,49`.

Revisión final: PNG abiertos a resolución completa en diálogo, Capitán y cierre; hoja del MP4 `salida/_f/pedro/hoja_final.png` abierta y revisada. ffprobe: H.264 yuv420p, 1080×1920, 30 fps, 53,000 s, AAC estéreo 44,1 kHz, 29.602.052 bytes. Audio del MP4: pico -1,1 dB, media -22,4 dB; silencedetect no detecta silencios de 0,5 s a -45 dB. Audio comprobado técnicamente, no escuchado. Comprobación de independencia de orden de render: frame(49), frame(3), frame(49), ambos fotogramas 49 idénticos por SHA-256.
