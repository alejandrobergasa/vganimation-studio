# Pedro — edición dinámica v3

46,4 s · 1080×1920 · 30 fps. Parodia ficticia con rótulo permanente. Conserva la foto del usuario sobre el osezno 3D y el diálogo de v2, con páginas completas. Ningún corte de cámara interno reinicia ni recorta la página.

| Tiempo | Contenido | Ritmo / efectos |
|---|---|---|
| 0–0,51 | Cara en primer plano; abre el iris | Apertura inmediata; no hay tarjeta de título previa al diálogo |
| 0,51–3,3 | «BRO, AYUDA POR FAVOR.» | Alerta, rótulo BRO, impacto RGB, cambio al general a 1,95 s |
| 3,3–7,7 | «VOY JODIDO CON LAS ELECCIONES ESTAS.» | General, vecino y reacción de Nook; texto continuo |
| 7,7–12,4 | «Estás en un lío de la ostia, primo.» | Nook, reacción de Pedro, general; rótulo VAYA LÍO |
| 12,4–16 | «Lo de Ábalos para empezar,» | Contador 1/3, miniatura de reacción, golpe grave, microcorte a Pedro |
| 16–19,6 | «lo de tu hermano para seguir,» | Contador 2/3, reacción y cambio al general |
| 19,6–23,4 | «y lo de tu mujer para culminar.» | Contador 3/3, rótulo, reacción, glitch de entrada de Capitán |
| 23,4–27,4 | Primer estribillo de Capitán | Entrada lateral, iris, fanfarria, rayos, notas y confeti; close/general/close |
| 27,4–31,4 | Repetición del estribillo | Nueva ráfaga de confeti, bordes de color al ritmo, rótulos; general/close/general |
| 31,4–35,4 | «Vas a ir a la cárcel, mano.» | Frenazo tonal, breve desaturación, Nook/Pedro/Nook, rótulo LA CÁRCEL |
| 35,4–41,4 | Vecino sentado ante el sol | Cambio de ritmo y color, música triste original |
| 41,4–46,4 | «que te vote txapote» | Mensaje completo y campanilla; fundido final |

12 transiciones principales y 14 microtransiciones. Las microtransiciones solo afectan al escenario y personajes: el diálogo permanece estable sobre ellas. Barridos, zoom, iris, separación RGB, rayos, temblor breve, glitch horizontal, confeti, cintas que pulsan, contador y ventanas con render real del personaje. Los impactos y barridos tienen SFX sincronizados de muestras SDAT. Fotogramas deterministas, sin integrar estado de animación.

Assets: los mismos de v2. Foto original `biblioteca/animal-crossing/personalizados/psan.jpg`, recorte fotográfico preparado con imagegen `biblioteca/animal-crossing/personalizados/pedro/cara_foto.png`, muestreado a 64×64 y proyectado en la malla cbr01 `npc/model/24/29`. Prenda cloth065, Nook rcn, Capitán wip, Village, arena y agua de la ROM, fuente fontA, nube a_mes, voces e instrumentos SDAT. La foto es la excepción externa pedida por el usuario; los efectos restantes son gráficos procedurales y sonidos del juego. El prompt de preparación de la foto está en `biblioteca/animal-crossing/personalizados/pedro/README.md`.

Regenerar: `python -I video/pedro_parodia_v3.py`. Salida `salida/animal-crossing/pedro_parodia_v3.mp4`. Revisión en `salida/_f/pedro_v3/`. Se conservan v1 y v2.

Revisión final: abiertos los PNG a 1080×1920 y la hoja extraída del MP4 final, incluida apertura a 0,8 s. Vecino, foto, enumeración, reacción, coro, transición y cierre revisados. H.264 yuv420p 1080×1920 a 30 fps, 1392 fotogramas, duración 46,400 s; AAC estéreo 44,1 kHz; 41.391.929 bytes. Audio codificado: pico -1,0 dB y media -21,8 dB, sin silencios de 0,5 s a -45 dB. Audio comprobado técnicamente, no escuchado. Primera voz a 0,51 s; pausa mínima tras teclear 1,835 s; páginas de 1 o 2 líneas; 26 transiciones. SHA-256 de frame(13,6) idéntico antes/después de frame(44): render independiente del orden.
