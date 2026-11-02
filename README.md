# VGAnimation Studio

Crea vídeos con los gráficos, la música y las voces de videojuegos de Nintendo DS ([nueve juegos soportados](#extraer-assets)) trabajando con un
agente de IA: **Claude Code** o **Codex**, desde una interfaz con chat o desde la terminal.

Unifica tres repos anteriores en uno: bandejas de entrada y salida, librería de ROMs, assets por juego, base de conocimiento y skills.

## Puesta en marcha

Necesitas Python 3.10+, `ffmpeg`/`ffprobe` en el PATH y, para el chat, `claude` y/o `codex` instalados y con sesión iniciada.

```
pip install -r requirements.txt
python valedores.py doctor        # comprueba el entorno
```

1. **Pon tus ROMs en `roms/`** (`.nds`; el nombre da igual, se reconocen por la cabecera). *Este repositorio no las incluye ni las incluirá.*
2. **Extrae los assets** de tus juegos: `python valedores.py extraer` te pregunta de cuáles (ver [Extraer assets](#extraer-assets)).
3. **Abre el estudio**: `python valedores.py estudio`.

## Extraer assets

Una sola orden sirve para cualquier juego soportado. Necesita su ROM en `roms/` y deja los assets en `biblioteca/<juego>/extraidos/`.

```
python valedores.py extraer                      # menú: muestra los juegos y su estado, y pregunta cuáles
python valedores.py extraer mario-party-ds       # un juego, por su id
python valedores.py extraer nsmb mkds            # varios
python valedores.py extraer --pendientes         # los que no están extraídos o tienen el extractor cambiado
python valedores.py extraer --todos              # todos
python valedores.py extraer profesor-layton --rapido   # muestra parcial, si el juego lo admite
```

| Juego | Id | Código de ROM | `--rapido` |
|---|---|---|---|
| Animal Crossing: Wild World | `animal-crossing` | `ADMP` | sí |
| Inazuma Eleven | `inazuma-eleven` | `YEES` | sí |
| Mario Party DS | `mario-party-ds` | `A8TP` | sí |
| Mario Kart DS | `mkds` | `AMCP` | no |
| New Super Mario Bros. | `nsmb` | `A2DP` | no |
| Phoenix Wright: Trials and Tribulations | `phoenix-wright-3` | `YG3Y` | sí |
| Pokémon Platino | `pokemon-platino` | `CPUS` y otras regiones | no |
| El profesor Layton y la villa misteriosa | `profesor-layton` | `A5FP` | sí |
| Super Mario 64 DS | `super-mario-64-ds` | `ASMP` | sí |

- **Comprobar el estado**: `python valedores.py estado` indica de cada juego si tiene ROM y si sus assets están al día, y avisa si un extractor
  ha cambiado desde la última extracción. `python valedores.py roms` lista las ROMs reconocidas; el nombre del fichero da igual.
- **Si falla**: la orden termina con un código distinto de 0 y dice qué juego ha fallado (por ejemplo, si falta su ROM o el id no existe), pero
  sigue con los demás. `python valedores.py doctor` revisa el entorno.
- **Git**: los assets no se suben; cada persona los regenera en local con la última versión del extractor. Las ROMs nunca se modifican.
- **Modo rápido**: `--rapido` deja la extracción marcada como parcial; vuelve a extraer sin esa opción para tenerla completa. En los juegos
  que no lo admiten se extrae todo.

En Inazuma Eleven, Mario Party DS, Phoenix Wright, Layton y Super Mario 64 DS, los formatos propietarios pendientes se conservan como binarios
originales. Consulta `README.md`, `catalogo.json` (nombres originales y SHA-256), `avisos.log` y `errores.log` en su carpeta para conocer la cobertura
real. Los WAV extraídos son muestras de instrumentos; los motores pueden sintetizar las canciones SSEQ para los vídeos. La API y los límites de
esos motores están en [motor-video-nds.md](conocimiento/motor-video-nds.md).

## El estudio

Una página local (`127.0.0.1`, sin dependencias externas):

- **Juegos**: tarjetas con imágenes de ejemplo y el estado de su ROM/assets (con botón de extraer).
- **Nuevo vídeo**: título, formato, tu idea o guion, agente, modelo y esfuerzo, y el ritmo:
  - *Paso a paso*: el agente se detiene al terminar cada fase para que la valides.
  - *De una*: lo hace todo seguido.
- **Chat** con el agente elegido, que trabaja en este repo siguiendo la skill `crear-video`. Atajos para pedir solo una parte
  («solo el guion», «solo la música»…).
- **Fases** (idea → guion → música → storyboard → previsualización → render → revisión): cada una enseña su resultado
  (texto, audio de muestra, fotogramas, vídeo) con botones *Aprobar* / *Pedir cambios*.
- **Mapa del vídeo**: las fases como un grafo (música y storyboard en paralelo tras el guion) con los elementos de cada una (personajes, escenas,
  voces…), indicadores de carga y barras de progreso con el tiempo estimado. El chat es un panel plegable a la derecha, con Markdown.
- **Consumo**: tokens de entrada/salida y precio del proyecto siempre visibles en la cabecera, con desglose por fase (el precio lo informa Claude Code;
  para Codex defínelo en `valedores.toml`, sección `[precios]`).
- **Ahorro de tokens**: el chat enseña el tamaño del contexto (`ctx`); al cambiar de fase con la conversación grande, el agente sigue en una sesión
  nueva con un resumen del proyecto (ajustable, botón ↻ para forzarlo).
- **Aprendizajes**: el agente anota como regla lo que corriges y que vale para otros vídeos; en la pestaña *Aprendizajes* decides qué se guarda en el
  conocimiento del juego. `python valedores.py madurez` enseña cómo evoluciona cada juego.
- **Pedir cambios**: sobre cualquier fase o elemento y en cualquier momento; el estudio marca lo que hay que rehacer (y lo posterior afectado).
- **Trabajo en paralelo**: «⇉ En paralelo» lanza un agente aparte para una fase que no dependa de las que están en marcha.
- **Adjuntos en el chat**: botón 📎, arrastrar ficheros sobre el chat o pegar una captura. Se guardan en `entrada/<proyecto>/` y el agente recibe
  sus rutas (fotos, vídeos de referencia, audios, assets).
- **Entrada y salida**: todo lo subido y los vídeos resultado.

## Carpetas

| Carpeta | Contenido | Git |
|---|---|---|
| `entrada/` | Ficheros tuyos para la IA (`entrada/<proyecto>/` para uno concreto) | no |
| `salida/` | Vídeos resultado | no |
| `roms/` | Tus ROMs | no |
| `biblioteca/<juego>/extraidos/` | Assets sacados de la ROM (regenerables) | no |
| `biblioteca/<juego>/personalizados/` | Assets propios (fotos, personajes custom) | sí |
| `juegos/<juego>/` | Extractor, motor de vídeo, ejemplos, skills y conocimiento de cada juego | sí |
| `conocimiento/`, `skills/` | Base de conocimiento y skills comunes | sí |
| `proyectos/<slug>/` | Un vídeo: estado por fases, guion, música, storyboard, `video.py` | sí |
| `nucleo/`, `estudio/`, `valedores.py` | CLI, librería común e interfaz | sí |

## Línea de comandos

```
python valedores.py estado                       juegos, ROMs, assets, proyectos
python valedores.py extraer [juego ...]          extrae/actualiza assets (sin argumentos: pregunta; --todos, --pendientes, --rapido)
python valedores.py proyecto nuevo "Título" --juego animal-crossing --formato vertical
python valedores.py fase <slug> <fase> <estado>  el agente marca el avance
python valedores.py ejecutar <slug> -- <cmd>     ejecuta con la salida redirigida al proyecto
python valedores.py revisar info|hoja|frame|audio <video>
python valedores.py skills [--check]             sincroniza skills para Claude Code (.claude/) y Codex (.agents/)
python valedores.py doctor
```

## Para agentes de IA

Empieza por [`AGENTS.md`](AGENTS.md) (Claude Code lo lee vía `CLAUDE.md`; Copilot vía `.github/copilot-instructions.md`).
Las skills se editan en `skills/` y `juegos/<juego>/skills/`; `.claude/skills/` y `.agents/skills/` se generan.

## Añadir un juego

Skill `anadir-juego`: crear `juegos/<id>/` con `juego.json` (código de ROM, extractor, formatos), extractor, motor y skills.

## Aviso legal

Los juegos, sus gráficos, música y voces son propiedad de sus titulares. Este repositorio no distribuye ROMs ni assets extraídos: cada
persona usa sus propias copias. Las imágenes de `juegos/*/vistas/` son capturas pequeñas solo para ilustrar la interfaz.
