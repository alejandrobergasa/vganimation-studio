# Inazuma Eleven: recursos de la ROM

## Personajes del escenario: sprites RPG pequeños

Usa `Recursos().personaje('Mark', direccion='este', accion='caminar')`. `personajes()` consulta nombres e ids
de `data_iz/logic/sp/unitbase.dat` (filas de 96 bytes en YEES; cabeza en 0x48, paleta en 0x4A). La cabeza nativa
es ese id multiplicado por 100. `spr/char/pcb.pkb` guarda cuerpos, `pch` cabezas; `ppb` y `pph`, paletas de 32 bytes.
Los PAC de cuerpo/cabeza contienen metadatos y píxeles **lineales 4bpp**, no tiles de 8×8. Las piezas y el ancla
se componen juntas; recortar cabeza y cuerpo por separado descoloca el personaje. Índice 0 transparente.

Cinco vistas nativas: sur, suroeste, oeste, noroeste y norte; las de la derecha se reflejan. Quieto: celdas 0/4/8/12/17.
Caminar: cuatro celdas por vista desde 20 hasta 39. Se usa una cadencia de montaje configurable (8 fps por defecto);
los scripts de animación del PAC todavía no se interpretan. Lienzo estable 32×48 con margen superior transparente.
El cuerpo 100/paleta 1 corresponde al uniforme Raimon usado en la prueba; para otros vestuarios hay que elegir
ambos explícitamente. No se ha inferido automáticamente el cuerpo de cada unidad.

Las fotos se adaptan a estos sprites por defecto, conservando identidad y estilo. `personaje_personalizado()`
carga el atlas revisado según `conocimiento/personajes-desde-fotos.md`. Los retratos `face2d` sirven para diálogo;
no sustituyen al personaje que camina. `video/jugador.py` es una alternativa 3D para planos que lo requieran.

## Cobertura inicial

- La ROM YEES tiene 1846 entradas FAT; las entradas sin nombre incluyen overlays.
- `data_iz/` contiene PKB con índices PKH `PackNum 20080626`. Tipos 0: registros de 12 bytes (id, offset, longitud); tipos 2/3: bloques fijos.
- Los PAC contienen cantidad y pares offset/longitud absolutos. La extensión `.pac_` suele señalar LZ10.
- Los modelos Nitro BMD0 y BTX0 permiten exportar texturas con el lector existente de NSMB. Revisar las paletas elegidas antes de usar las imágenes.
- Pendiente: interpretar scripts de sprite SPD/SPL/SPF, MODS y el montaje automático de piezas de jugador 3D. Los sprites RPG completos, PAC de rostros/mapas y audio SADL ya se leen desde el motor.

## Uso

```powershell
python valedores.py extraer inazuma-eleven
python valedores.py extraer inazuma-eleven --rapido
```

Resultado: biblioteca/inazuma-eleven/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa se ha ejecutado y el motor dispone de una prueba de integración en proyectos/prueba_motor_inazuma_eleven/.

## Referencias de formatos

- [Tinke: estructuras PAC y PKB/PKH](https://github.com/pleonex/tinke/blob/master/Plugins/INAZUMA11/INAZUMA11/Packs.cs)

## Motor de vídeo

### Escala, escenario y ocho orientaciones

`Recursos().escenario('mr01b01')` reconstruye Raimon desde los modelos `mr01b01m*` de `mr_nsbmd.pkb`
y sus texturas de `mr_nsbtx.pkb`. No usa `map2d/*_mn`, que es un minimapa y hace que el personaje parezca gigante.
`pixeles_por_unidad=32` calibra la geometría al lienzo lógico del sprite; es configurable por escenario. La proyección
ortográfica elegida para montaje no interpreta la cámara original del juego ni las colisiones/oclusiones de scripts.

`Video.plano_rpg(duracion, fondo)` devuelve plano y `EscenaRPG`. Fondo y actores se componen en píxeles lógicos;
se recorta la cámara y se aplica una **única ampliación entera** con vecino al resultado. Nunca escales al sprite
según un porcentaje de pantalla mientras el fondo usa un cover independiente. `escala_salida` controla el zoom
del conjunto. `escena.actor(actor, seguir=True)` sigue al personaje y limita el recorte a los bordes del escenario.

`Recorrido([(0,x0,y0),(t1,x1,y1),...])` deriva ocho orientaciones del vector de cada tramo. Los tramos con posición
repetida son pausas y conservan la mirada. `ActorDireccional(rec,nombre,ruta,personalizado=True)` exige
`caminar_<direccion>` y `quieto_<direccion>` para las ocho vistas; no permite deslizar siempre un frontal.
Usa cinco vistas dibujadas y tres reflejadas en el manifiesto personalizado, con lienzo, escala y paleta comunes.

Prueba: `python valedores.py ejecutar bolas_inazuma -- python -I juegos/inazuma-eleven/video/demo_rpg.py`.

Escenas 2D con mapas y retratos PAC, capas animadas, fuente NFTR y voz SADL de la ROM.

Entrada: video/motor.py (Video, Recursos, Plano, Clip, Fuente, Superposicion, interpolar).
Implementación compartida en nucleo/valedores/video_nds.py, activos_video_nds.py, modelos_video_nds.py y sonido_video_nds.py.
Consulta conocimiento/motor-video-nds.md para la API, un ejemplo y las limitaciones de cada formato.
Prueba: python -I juegos/inazuma-eleven/video/demo.py [--formato vertical].
La geometría 3D HBDF/BMD se carga en pose de reposo; ANMF/BCA siguen pendientes. Esto no impide animar la cámara y las capas.

## Hallazgos del vídeo «La bola negra» (motor)

- **Objetos móviles del escenario:** `FondoRPG(..., separar_materiales=('mr02b07t67',))` excluye los dos coches de mr02b07 de la rasterización del fondo; `objeto(material, selector, giro)` devuelve geometría/textura nativa aislada, ancla y posición originales, con giro alrededor de su centro. Las mitades se seleccionan por signo de X. El material contiene 64 triángulos entre ambos coches. `suelo_bajo_objeto(..., muestra=(x0,y0,x1,y1))` rellena solo huecos alfa y siluetas negras bajo la carrocería con una muestra de suelo del mismo escenario: seleccionar suelo limpio, sin edificios ni marcas de calzada. No es una reconstrucción del suelo oculto de la ROM.
- **Oclusión y objetos RPG:** `EscenaRPG.oclusion(imagen, posicion)` pone recortes nativos delante de los actores, en coordenadas lógicas. Los actores admiten `ancla=(x,y)` en píxeles y `visible(t)`; `centro` puede ser una función. Fondo, objetos, máscaras y personajes se amplían juntos. Una máscara no debe alcanzar un coche ni tapar el punto de pago.

- **Fuente con español:** las cuatro NFTR (`FONT12`, `FONT12N`, `FONT12T`, `FONT8`) son Shift-JIS, pero guardan las letras latinas acentuadas en 0xA1–0xDF
  (¿ A5, Ñ A9, ñ C2, á B2, é BA, í BE, ó C4, ú CA, ¡ DF, € CE…). `motor.LATINO` lo mapea y `Recursos.fuente()` lo aplica (`Fuente(datos, extra=...)`); `FONT12` es la fina de los diálogos.
  FONT12 tiene avances iguales al ancho de tinta (por ejemplo A=7, e=5, i=1), sin separación. `Recursos.fuente()` usa `espaciado=1` para dejar un píxel lógico entre glifos; conserva el avance nativo del espacio. Verifica el ancho de cada línea después de componer, antes de ampliar con vecino.
- **Ventana de diálogo:** la caja nativa (borde marrón sobre blanco) está en `data_iz/pic2d/sp/srd_s02.pac_` (recorte 6,46–250,146). `Recursos.ventana(ancho, alto, borde)` la trocea en 9 partes a píxeles DS (usar ×4 en 1080×1920).
- **Mapas:** `data_iz/map2d/*_mn.pac_` son cenitales de 256×256 (`mr02b07_mn.pac_`: calle comercial con edificio de entrada en rayo, pasos de cebra y calzada). Un tramo recto repetido en espejo da un scroll lateral sin costuras.
- **Música:** no hay banco SDAT catalogado (`canciones()` devuelve `[]`); la música son SADL: `TITLE.SAD` (do mayor, ≈113 bpm, 42 s), `J18.SAD` (re menor lento, 15 s), `bg_end.SAD`, `op00.SAD`, `am*.SAD`. Se decodifican con `Recursos.audio()` (32 728 Hz estéreo).
- **Rostros PAC (`face2d`)**: 3006 imágenes de 64×64 decodifican; no se han usado en este vídeo (los retratos eran fotos del usuario).
