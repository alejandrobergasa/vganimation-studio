---
name: cinematica-mkds
description: Crea, modifica, renderiza y revisa cinemáticas 3D verticales de Mario Kart DS (karts, pilotos animados, circuitos, partículas, postproceso, música y efectos de la ROM) para redes sociales. Úsala dentro del flujo de crear-video para cualquier vídeo de Mario Kart DS; para NSMB usa cinematica-nsmb; para elegir recursos o regenerar catálogos de la ROM, recursos-mkds.
---

# Cinemáticas Mario Kart DS (vertical 1080x1920)

Trabajar desde la raíz con Python y ffmpeg; ejecutar siempre `python -I`. El código está en `juegos/mkds/` (reutiliza la librería Nitro de `juegos/nsmb/tools/nsmb`). La ROM (`roms/`) es sólo lectura.
Todo lo que sale en pantalla y en el audio viene de la ROM (regla de `juegos/mkds/AGENTS.md`) más lo que el usuario aporte en `entrada/`; los efectos son código propio de `video/mk/`.
Texto en español con la fuente del juego (`marioFont.NFTR`, vía `mk/texto.py`). Detalles de formatos: `juegos/mkds/CONOCIMIENTO.md`.
Se usa dentro del flujo por fases de `crear-video`. Skill compartida con Codex: se edita aquí (`juegos/mkds/skills/`) y se sincroniza con `python valedores.py skills`.

## Piezas (todas en `juegos/mkds/video/mk/` salvo que se indique)

| Módulo | Para qué |
|---|---|
| `tools/mkds/modelos.py` | Lee de la ROM: `piloto()`, `kart()`, `rueda()`, `objeto()`, `Circuito()`, `circuitos()`. |
| `tools/mkds/nkm.py` | Mapa del circuito: salida, línea de carrera (EPOI), checkpoints, cámaras, objetos. |
| `escena.py` | `Motor` (render por software, numba), `Instancia`, `Camara`, `Entorno`, `Malla`. |
| `circuito.py` | `Mundo(motor, nombre)`: circuito + cielo + niebla + `Suelo` (altura) + `Pista` (línea suave por distancia). |
| `kart.py` | `Kart(motor, 'mario', 'b')`: cuerpo, 4 ruedas que giran/dirigen y piloto animado (`drive`, `win`, `lose`, `spin`). |
| `carrera.py` | `Carrera`: simulación determinista de varios karts con turbos, golpes y derrapes automáticos. |
| `fx.py` | `Sprites` y `Particulas` (chispas, humo, llamas, confeti, fuegos) sin estado: cualquier `t` se evalúa solo. |
| `post.py` | bloom, desenfoque radial, aberración, líneas de velocidad, gradación, viñeta, iris, cortinas. |
| `camaras.py` | `Ruta` (keyframes), `orbita`, `persecucion`, `temblor`, easings. |
| `texto.py` | Títulos con la fuente del juego, rebote elástico y ajuste al ancho. |
| `audio.py` | Música (`bgm(i)`) y efectos (`sfx_id(ssar, k)`) por índice, `Mezcla` con sidechain y limitador. |
| `director.py` | Render paralelo + ffmpeg + mezcla de audio; opciones `--rapido --frame --hoja`. |
| `video/mk_demo.py` | Ejemplo completo (38 s). Copiarlo como plantilla para una cinemática nueva. |
| `video/mk_abalos*.py` | Ejemplo con personaje de textura propia (foto en `biblioteca/mkds/personalizados/`), mixins de escena/plano/audio. |

## Flujo de trabajo

1. Guion y storyboard del proyecto en `proyectos/<slug>/` (planos, tiempos, texto, música, efectos); ejemplo: `juegos/mkds/video/storyboard_mk.md`.
2. Elegir recursos con las hojas de `biblioteca/mkds/extraidos/` (pilotos, karts, circuitos, objetos). Si faltan, `python valedores.py extraer mkds` (skill `recursos-mkds`).
3. Crear `proyectos/<slug>/video.py` copiando `juegos/mkds/video/mk_demo.py`, con la cabecera estándar de `crear-video` (`JUEGO = 'mkds'`; `rutas.motor_dir` es `juegos/mkds/video`, donde está el paquete `mk`) y una clase que cumpla el contrato de `director.py` (`cuadro(t)` puro, `audio()` estático).
   Calcular **todo** el estado como función de `t` (simulación tabulada, partículas con semilla): así el render es paralelo y reproducible.
4. Previsualizar: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py --rapido --hoja 16` y **mirar** `.cache/mkds/hoja.png`;
   un instante concreto a resolución final: `--frame 12.5` → `.cache/mkds/frame.png`. Copia lo elegido a `proyectos/<slug>/previsualizacion/`. Nada se da por bueno sin verlo.
5. Render final: `python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py` → `salida/<slug>/`. Con 12 núcleos son unos minutos por 38 s a 1080x1920 (ss=1,5).
6. Revisar el MP4 y el audio con la skill `revisar-video` (picos, silencios, sincronía de efectos).

## Convenciones y trampas ya resueltas

- Unidades: 1 unidad = unidad del modelo del circuito; el NKM está a escala 16:1. Un kart mide ≈ 6,7 u con `escala=5`; la calzada ≈ 16 u.
- Ejes: Y arriba; el kart mira a +z con `yaw=0`; +x es su **izquierda**; `Pista.muestra(s, lateral)` usa lateral > 0 = derecha;
  `curv > 0` = curva a la izquierda; `volante` +1 = izquierda (fotograma 0 de `drive`), −1 = derecha (28).
- El kart incrustado en el modelo trae sus ruedas (`kart_tire`): `Kart` las separa y reutiliza su textura; no usar `kart_tire_*.nsbmd` con la tabla `kartoffsetdata.bin` (no coincide).
- Piloto sobre el kart: desplazamiento (y, z) por clase en `kart.ASIENTO`; comprobar visualmente con otros pilotos.
- Los circuitos de misión (`mini_*`, `MR_*`) no tienen línea de carrera: `Mundo.pista` es `None`.
- Luz: circuitos `luz='baked'` (color de vértice); karts, pilotos y objetos `luz='normal'`; sprites `luz='plana'`.
- Mezcla de materiales: alfa de textura 0/255 → recorte; alfa intermedio o alfa de polígono < 1 → mezcla; sprites aditivos para brillos.
- Cada material admite repetición/espejo y culling propios; ya se respetan en `raster.py`.
- Texto: la fuente no tiene `º`; usar «1», «2»… Mantener rótulos < 92 % del ancho (se ajusta solo).
- Audio sin nombres: la SDAT de MKDS no lleva símbolos; elegir por `biblioteca/mkds/extraidos/audio/catalogo_audio.csv` y documentar el id elegido.

## Calidad esperable

- Previsualización `--rapido` (540x960, ≈1 s/fotograma en un núcleo); final 1080x1920 con supermuestreo 1,5.
- Para planos rápidos subir `radial` y `lineas`; para planos de héroe, órbita lenta + bloom.
- Revisar siempre: texturas sin huecos negros inesperados, ruedas girando en sentido correcto, piloto sentado en el asiento,
  texto legible en móvil (zona segura: evitar el 12 % superior y el 18 % inferior para rótulos importantes).
