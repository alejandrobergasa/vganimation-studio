---
name: recursos-nsmb
description: Extrae, explora y revisa recursos de la ROM de New Super Mario Bros. con su extractor. Usar cuando falten assets, falle su extracción o haya que regenerar una sola categoría; para extraer todo usa la skill general extraer-assets; para componer escenas, música nueva o montar el vídeo, usa cinematica-nsmb.
---

# Extraer assets de la ROM NSMB

La ROM (`roms/`) es sólo lectura y nunca se modifica. Trabajar desde `juegos/nsmb/`
con `tools/extraer_todo.py` y la librería `tools/nsmb/`. Salida: `biblioteca/nsmb/extraidos/`. Para extraer todo basta
`python valedores.py extraer nsmb`; esta skill es para categorías sueltas. Formatos y fallos conocidos: `juegos/nsmb/CONOCIMIENTO.md`.

## Elegir lo que falta

- Consultar primero `biblioteca/nsmb/extraidos/README.md`, `_catalogo.json` y las hojas de
  contactos. Reutilizar los PNG y WAV existentes si sirven al montaje.
- Los pasos de CLI son `modelos`, `jugadores`, `fondos`, `tilesets`, `fuentes`,
  `niveles` y `audio`. `enemigos`, `objetos` y `mapa_del_mundo` son directorios
  de salida de `modelos`, no valores admitidos de `--solo`.
- La extracción de una categoría conserva en el catálogo los pasos no repetidos.
  No borrar `biblioteca/nsmb/extraidos/` ni regenerarlo entero para recuperar un único paso.
- Una foto o logo que el usuario aporte pertenece a los recursos del montaje,
  fuera de esta salida regenerable (`biblioteca/nsmb/personalizados/`). No catalogarlo como recurso de la ROM.
  Antes de declararlo ausente, localizar su archivo real y abrirlo.
- Componer música nueva con el banco ya leído por `sonido.tocar_notas()` no requiere
  extraer todas las BGM ni descargar un soundfont externo; seguir `cinematica-nsmb`.

## Comandos

```powershell
python -I juegos/nsmb/tools/extraer_todo.py --solo jugadores,fondos
python -I juegos/nsmb/tools/extraer_todo.py --solo audio
python -I juegos/nsmb/tools/extraer_todo.py --sin-audio
python -I juegos/nsmb/tools/extraer_casino.py        # el casino (NARC aparte)
python -I juegos/nsmb/tools/extraer_todo.py          # todo (lo mismo que `python valedores.py extraer nsmb`)
```

El último comando extrae todo y puede tardar varios minutos, especialmente con audio.
Usar `python -I` para evitar importar datos descargados como módulos; los scripts
ya añaden sus rutas. Los efectos se sintetizan en procesos con tiempo límite
porque algunos SE no terminan sin el corte que realiza el juego.

## Validación de la categoría afectada

- Leer los fallos del catálogo aunque el proceso termine con código 0: el extractor
  captura errores por recurso. Separar ausencias conocidas de regresiones nuevas.
- Abrir las hojas de contactos regeneradas y un recurso representativo a resolución
  completa. Revisar alfa, recortes, paletas, escala y poses, no sólo que exista el PNG.
  El suelo real de 1-1 contiene huecos: distinguir esos datos de un fallo de extracción.
- Para audio, comprobar rate, duración, nivel y muestras activas; un WAV puede existir
  y estar mudo o contener un bucle largo. Recortar y mezclar para la escena en el motor
  de vídeo, conservando la extracción como fuente. Verificar onda/espectrograma y
  escuchar si hay reproducción disponible.
- Si se modifica el lector o extractor, repetir sólo los pasos afectados y ver su
  salida antes de darlo por bueno. No modificar los resultados del extractor a mano
  para ocultar un fallo del código.

Tras editar esta skill, sincronizar las copias de Claude y Codex con `python valedores.py skills`.
