# Motor de vídeo para los cinco juegos añadidos

Los motores se importan desde `juegos/<id>/video/motor.py`. Comparten composición y exportación;
los gráficos y el audio se leen de la extracción de **su propio juego**. La ROM sólo se abre para lectura.

| Juego | Recursos del motor | Límites actuales |
|---|---|---|
| Inazuma Eleven | Escenarios Nitro de Raimon, cámara RPG y sprites pequeños en ocho direcciones; PAC, PCB/PCH, PPB/PPH; NFTR; SADL | Proyección de montaje y escala lógica común. No emula cámaras, colisiones, oclusiones de scripts ni partidos. Cadencia de sprites configurable; scripts PAC pendientes. Jugador 3D por piezas en `video/jugador.py`. |
| Mario Party DS | Modelos HBDF, animaciones ANMF, tableros, cámara 3D (`Escena3D`), caras de foto sobre el modelo, interfaz 2D nativa, efectos y voces SDAT | Fuente grande de mensajes sin localizar (usa la 8×8 del ejecutable). Nombres de animación y de efectos sin semántica en la ROM. Ver `juegos/mario-party-ds/CONOCIMIENTO.md`. |
| Phoenix Wright 3 | 1953 gráficos autocontenidos detectados en la ROM YG3Y, poses y escenarios; pantallas LZ10; audio SSEQ/SDAT | No reconstruye todavía todos los gráficos sin cabecera ni los guiones originales. La fuente de diálogo se reconstruye con `fuente_rom.py` a partir de las descripciones del Expediente (sin NFTR). |
| Profesor Layton | Fondos; clips ARC con tiempos nativos; personajes con boca/ojos montados solos (`personaje_layton`); NFTR con hueco entre letras; SDAT y SADL | ARJ, Huffman y scripts GDS no se interpretan; unos pocos personajes (p. ej. `officer`, `scum`, `gardenman`) no se alinean solos y piden `posicion=(x, y)`. |
| Super Mario 64 DS | Modelos BMD propios, huesos de reposo, materiales, texturas, listas GX; audio SSEQ/SDAT | BCA no se aplica aún. Los modelos por piezas necesitan montar explícitamente la cabeza; `b_mario_all.bmd` es completo. |

Estas limitaciones corresponden a lectores concretos. Los cinco motores pueden componer y exportar vídeos
horizontales 1280×720 y verticales 1080×1920 con capas animadas, cámara y audio.

## Ejemplo de proyecto

```python
from pathlib import Path
import sys
for carpeta in Path(__file__).resolve().parents:
    if (carpeta / 'valedores.toml').is_file():
        sys.path.insert(0, str(carpeta / 'nucleo'))
        break
from valedores import rutas
JUEGO = 'profesor-layton'
sys.path.insert(0, rutas.motor_dir(JUEGO))
from motor import Video, Recursos, Superposicion, interpolar

rec = Recursos()
video = Video(formato='horizontal', fps=30)
plano = video.plano(6, fondo=rec.imagen('data/bg/choice_bg.arc'))
actor = rec.personaje_layton('layton', 'talk')   # cuerpo + capa facial (boca) ya situada
plano.sprite(actor, x=interpolar(550, 700, 6), y=650, escala=2.5)
rotulo = rec.fuente().texto('Una nueva aventura', escala=3, color='#3b2210', ancho=1100)
plano.sprite(rotulo, x=640, y=140, ancla=(.5, .5), pantalla=True)
audio, frecuencia = rec.audio('data/stream/BGM_09.SAD', segundos=6)
video.audio(audio, frecuencia)
video.renderizar('escena.mp4')
```

Guárdalo en `proyectos/<slug>/video.py` y ejecuta:

```
python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py
```

Los MP4 van a `rutas.salida()` y los intermedios a `rutas.trabajo()`. Nunca calcules esas rutas a partir del script.
`video.renderizar()` acepta un nombre de MP4, sin directorio, para respetar el proyecto activo.

## API

- `Recursos().buscar(texto='', tipo=None)` devuelve orígenes exactos de `catalogo.json`. Los miembros usan `::`.
- `datos(origen)` devuelve el contenido descomprimido cuando existe, o el original.
- `imagen(origen, indice=0)` obtiene PNG del catálogo o decodifica PAC, BMD o HBDF compatibles.
- Phoenix: `graficos_phoenix()` devuelve `(offset, imagen)`; el offset permite registrar la procedencia. `fondos_phoenix()` lee pantallas en tiles.
- Los gráficos de fondo pueden tener margen alfa hasta completar la potencia de dos: recorta con `imagen.crop(imagen.getbbox())` antes de usarlos como fondo a pantalla completa.
- `clip(origen, animacion='todos')` conserva los fotogramas y tiempos ARC. Revisa los nombres de las animaciones disponibles.
- Layton: `personaje_layton(nombre, animacion='talk', posicion=None)` une `data/ani/<nombre>.arc` con `<nombre>_e_face.arc` y deduce dónde encaja la capa facial; `posicion=(x, y)` la fuerza. Si no encaja con claridad falla en vez de colocarla a ojo.
- Inazuma: `personajes()` lista unidades y `personaje('Mark',direccion='este',accion='caminar',fps=8)` compone los sprites pequeños nativos (cuerpo 100/paleta 1 por defecto; otros vestuarios explícitos).
- Inazuma: `escenario('mr01b01')`, `Video.plano_rpg()`, `Recorrido` y `ActorDireccional` reconstruyen el fondo real y sincronizan orientación/posición/cámara. No montar al actor sobre el minimapa con escalados independientes.
- `personaje_personalizado(nombre,animacion='quieto')` carga el personaje adaptado desde fotos; consulta [personajes-desde-fotos.md](personajes-desde-fotos.md). La generación la realiza el agente antes del montaje.
- `textura_personalizada(nombre)` devuelve nombre de textura e imagen UV; `VistaModelo.reemplazar_textura(nombre,imagen)` la aplica sobre la malla conservando la resolución nativa.
- `modelo(origen, bancos=(), animacion=None, giro=..., tamano=(256,256))` produce un actor 3D. `giro` son radianes y puede ser una función del tiempo. `bancos` enlaza las texturas que vienen en otro miembro del archivo.
- `fuente(origen=None)` carga NFTR del propio juego. `texto()` verifica cada glifo y el ancho; no usa una fuente externa como sustituto.
- `canciones()` y `musica(nombre, segundos)` sintetizan las SSEQ con sus bancos nativos. `audio(origen, segundos)` decodifica SADL IMA/Procyon.
- `Video().plano(duracion, fondo=None, color=...)` añade un plano. Los planos se encadenan con cortes.
- `plano.sprite(imagen_o_actor, x=..., y=..., escala=..., desde=0, hasta=..., opacidad=..., giro=..., ancla=(.5,1))` añade una capa.
- Las propiedades de una capa admiten números o funciones del tiempo local desde su `desde`. La cámara usa `plano.camara_x`, `camara_y` y `zoom`, evaluados en el tiempo del plano.
- `pantalla=True` deja un rótulo fuera del movimiento de cámara. Los fundidos se hacen animando `opacidad`.
- `Clip(imagenes, duraciones, repetir=True)` conserva duraciones por fotograma. `Superposicion(base, encima, posicion)` une dos actores con sus tiempos independientes.
- `video.frame(segundo)` genera un fotograma para revisión. `video.audio(muestras, frecuencia, desde=0, volumen=1)` mezcla mono/estéreo y remuestrea.

## Pruebas y revisión

`juegos/<id>/video/demo.py` sirve como prueba pequeña de integración, no como plantilla narrativa obligatoria.
Las pruebas de aceptación se guardan en `proyectos/prueba_motor_<id_con_guiones_bajos>/`.
Se comprueban H.264/yuv420p, AAC, dimensiones, duración, decodificación completa y niveles de audio;
los fotogramas deben abrirse para revisar encuadres, texto y materiales. Medir audio no equivale a escucharlo.

## Detalles de los formatos

- HBDF: los grupos de MESH dan inicio y longitud en **palabras de 32 bits del flujo GX**. No son índices de triángulos: confundirlo asignaba mal los ojos de Mario.
- Los modelos SM64DS BMD no son BMD0 de Nitro. Se leen sus tablas de huesos, polígonos, materiales y texturas específicas.
- Phoenix: las pantallas LZ10 de 49664 bytes llevan 512 bytes de paleta y tiles 8×8; interpretarlas como píxeles lineales producía bandas.
- Layton: `layton.arc` y `layton_e_face.arc` tienen tiempos independientes. `*_e_face.arc` es un parche con la boca (y en otros personajes ojos/cejas) que sustituye la cara por defecto del cuerpo; el ARC no guarda su posición (los 30 bytes reservados son ceros), así que `alinear_cara_layton` busca el par cuerpo/parche que coincide píxel a píxel. Layton: `(38,57)`; el `(38,37)` antiguo ponía la boca en la frente.

Referencias de estructuras: [MPLibrary HBDF](https://github.com/KillzXGaming/MPLibrary/tree/master/MPLibrary/DS/HBDF),
[SM64DSe](https://github.com/Gota7/SM64DSe-Ultimate), [Tinke Layton](https://github.com/pleonex/tinke/tree/master/Plugins/LAYTON/LAYTON),
[Tinke SADL](https://github.com/pleonex/tinke/blob/master/Plugins/Sounds/Sounds/SADL.cs),
[Phoenix Tools](https://github.com/Missingmew/phoenixtools).
