# Mario Party DS: recursos de la ROM

## Cobertura inicial

- La ROM A8TP contiene 706 entradas FAT; la mayoría de los recursos con nombre están en `data/*.bin`.
- Los archivos BIN pueden ser flujos LZ10 completos o tablas de miembros. Las tablas contienen cantidad u32 y pares offset/longitud; el offset es relativo al byte 4.
- Los miembros pueden contener a su vez recursos comprimidos; se recorren hasta seis niveles.
- SDAT: se conservan secuencias, bancos, archivos de ondas y streams nativos. Los WAV son muestras de instrumentos; no canciones sintetizadas.
- Pendiente: la lógica de tableros y minijuegos, y la fuente grande de los mensajes. El motor ya lee geometría HBDF, materiales, texturas, jerarquía y animaciones ANMF.

## Uso

```powershell
python valedores.py extraer mario-party-ds
python valedores.py extraer mario-party-ds --rapido
```

Resultado: biblioteca/mario-party-ds/extraidos/. El catálogo relaciona cada original con su nombre NitroFS, SHA-256, contenedor, método de compresión y derivados. Los formatos pendientes se conservan como binarios; no se sustituyen por gráficos inventados.

README.md explica la estructura de salida. Revisa catalogo.json, avisos.log, errores.log y los PNG a tamaño real. Los WAV son muestras, no una banda sonora renderizada. --rapido deja el sello de extracción parcial; los errores de conversión impiden un sello nuevo.

## Validación

La integración se prueba con datos sintéticos y lectura en memoria de las ROMs locales. La extracción completa se ha ejecutado y el motor dispone de una prueba de integración en proyectos/prueba_motor_mario_party_ds/.

## Referencias de formatos

- [Mario Party DS Editor: sistema de archivos y compresión](https://github.com/aleokdev/mario-party-editor)

## Motor de vídeo

Entrada: `video/motor.py`. Ejemplo que usa todo: `video/demo_completa.py` (`--foto a.jpg --foto2 b.jpg --formato vertical`).
Implementación: `nucleo/valedores/` (`escena3d`, `raster3d`, `anmf_party`, `caras_foto`, `efectos_video`, `video_nds`, `modelos_video_nds`)
y `video/` (`personajes`, `interfaz`). `demo.py` y la ruta `personajes.clip` con poses procedurales siguen para vídeos antiguos.

```python
rec = Recursos(); video = Video(formato='horizontal')
esc = Escena3D(tamano=(640, 360), fondo=(120, 170, 225))
esc.actor(rec.escenario('jardin', y=-2, z=-40, escala=0.55))
a = esc.actor(rec.personaje('mario', foto='entrada/<slug>/foto.jpg', x=-13, giro=math.pi / 2))
a.anim('correr', 0).anim('saludar', 4, bucle=False).anim('quieto', 5.5)
a.cara.hablar(6, 8); a.cara.expresion('enfado', 8, 10)
esc.camara = Camara(); esc.camara.encuadre('primer_plano', a, 6, angulo=-.4, corte=True)
plano = video.plano_escena(10, esc, transicion=('estrella', .7))
video.sonido(rec.efecto(rec.voces('mario')[0]), desde=4)
```

- **Personajes**: `mario luigi wario yoshi peach daisy waluigi toad`. `a.mirar(otro, desde, hasta)` gira la cabeza.
- **Animaciones**: `personajes.ANIMACIONES`, 27 huecos ANMF comunes a los ocho. Cualquier otra de la ROM: `rec.animacion(origen)`.
- **Cámara**: `clave`, `corte`, `encuadre` (`detalle primer_plano medio americano entero general gran_general`), `dos_personajes`,
  `orbita`, `temblor`. Los planos se alejan solos en vertical.
- **Escenarios**: `fuente jardin musica jungla biblioteca pinball`; `rec.objeto(origen)` para cualquier otro modelo. `rec.dado()`.
- **Partículas**: `Particulas` con `rec.textura_efecto(...)` (ver `motor.EFECTOS_TEXTURA`).
- **Imagen**: `efectos.transicion` (fundido, negro, blanco, pixelado, iris, estrella, barridos, cortina, persiana, diagonal) y
  `destello fundido vineta tinte desaturar franjas_cine lineas_velocidad temblor_2d`.
- **Interfaz**: `rec.icono(nombre)` (`motor.ICONOS`), `rec.interfaz(contenedor).hoja()` como catálogo, `rec.fuente_juego()`,
  `interfaz.Dialogo`, `Cartel`, `Contador`, `Barra`.
- **Sonido**: `rec.efectos(prefijo)`, `rec.efecto(nombre)`, `rec.voces(personaje)`, `rec.musica`, `video.sonido(...)`.

### Caras de foto

`rec.personaje(nombre, foto=..., hitos=None, gorra=True, pelo=None, brillo, contraste, ajuste, aplanar)`. Los hitos se detectan con
OpenCV (`requirements-opcional.txt`) o se pasan con `Hitos(ojo_i, ojo_d, boca, barbilla)`. La foto se alinea en una tarjeta de 256 px y
se dibuja como calca sobre la malla, de modo que gira con la cabeza y recibe su luz. La boca y los ojos se deforman a partir de la foto:
son una aproximación (`hablar`, `hablar_audio`, `expresion`: `enfado`, `alegria`, `ojos_abiertos`...; parpadeo automático).
Una foto sirve de referencia para un vídeo concreto: anótala en su brief y no la reutilices en otros.

Qué se ha visto al probarlo con los ocho personajes:
- Mejor resultado: Mario, Luigi, Toad, Peach y Daisy. El relieve de la cara se aplana (`aplanar=0` lo conserva).
- Wario y Waluigi conservan pliegues de bigote y nariz a los lados de la foto; Yoshi no tiene cabeza humana y la foto se deforma.
  Evita sus primeros planos o rehaz la malla antes de prometerlos.
- `gorra=False` queda bien en Mario y Luigi. En Peach queda una banda de la corona; Daisy conserva mechones afilados sobre la frente;
  en Toad el color también tiñe el chaleco, porque comparte textura.
- De perfil (más de ~1 rad) la foto se estira: es una calca, no un modelo de la cabeza.

### Formato ANMF

Sin documentación pública; deducido de la ROM (detalle en `nucleo/valedores/anmf_party.py`). En la rotación, las claves usan 4096 = una
vuelta y las constantes 65536 = una vuelta. Algunos modos de datos poco frecuentes (0, 1, 5) se ignoran y el canal queda en reposo.

### Límites

- Los **nombres de animación son etiquetas visuales** puestas al ver a Mario; la ROM no los guarda. Algunos son aproximados, y los huecos
  `p6`, `p7` y `p10` cambian de movimiento y duración según el personaje. Comprueba con `personajes.hoja_animaciones(rec, nombre)`.
- **Fuente**: solo se ha localizado la 8×8 ASCII del ejecutable (ARM9, offset 539456). Las tildes y la ñ se componen con sus píxeles.
  La fuente grande de los mensajes sigue sin encontrarse.
- **Efectos de sonido**: los nombres son numéricos y su significado no se conoce. Se sabe si suenan y cuánto duran, no qué son:
  `rec.muestrario(prefijo)` los une en una pista para que una persona los escuche y elija.
- Textos del juego: UTF-16 en `data/SP/mpd_*`. Iconos en `data/SP/mbgui_dep_LZ.bin`, miembro 3 con `paleta_i=0`.

## Poses procedurales y caras antiguas

`ModeloParty.pose(rotaciones, traslaciones)` y `personajes.clip` generan clips 2D con poses a mano y `caras_video.py` proyecta la foto en
la textura, con UV reflejadas (cara simétrica) y huecos. Se conservan solo para `proyectos/persecucion_en_el_campo`; en vídeos nuevos usa
`rec.personaje`.
