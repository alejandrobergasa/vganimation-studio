---
name: extraer-assets
description: Extrae o actualiza los assets de las ROMs a biblioteca/<juego>/extraidos/ con el comando del repo, y comprueba el resultado. Úsala cuando falten assets, el extractor haya cambiado, falle una extracción o el usuario pida «extraer assets».
---

# Extraer assets de las ROMs

Las ROMs se leen y **nunca se modifican**. Van en `roms/` (ignoradas por Git, cada persona pone las suyas); se
reconocen por el código de la cabecera, así que el nombre del fichero da igual (`python valedores.py roms`).
Extraer no gasta tokens: son scripts deterministas que tardan minutos.

## Comandos
```
python valedores.py estado                        qué juegos tienen ROM y si sus assets están al día
python valedores.py extraer                       pregunta de qué juegos extraer (si hay terminal)
python valedores.py extraer animal-crossing nsmb  los que digas
python valedores.py extraer --pendientes          solo los sin extraer o con extractor nuevo
python valedores.py extraer --todos [--rapido]    todos (--rapido: muestras, si el juego lo admite)
```
Siempre se ejecuta la **última versión** del extractor y se deja un sello (`.extraccion.json`) con su huella: si el
código del extractor cambia, `estado` marca «el extractor ha cambiado» y basta repetir `extraer`.

## Qué hacer
1. `python valedores.py estado`. Si falta una ROM, avisa al usuario (no la busques por Internet).
2. Extrae lo pendiente. Para una sola categoría de un juego, usa la skill de recursos del juego
   (`recursos-nsmb`, `recursos-mkds`, o el `README.md` de `biblioteca/<id>/extraidos/`) en lugar de repetir todo.
3. **Valida**: lee el `README.md`/catálogo que genera el extractor y los avisos (`errores.log`, fallos en el
   catálogo) aunque el proceso termine bien; abre las hojas de contactos y un recurso a tamaño real (alfa,
   recortes, paletas, escala). Un WAV puede existir y estar mudo: comprueba duración y nivel.
4. Si cambias un extractor: repite solo lo afectado, mira la salida y no retoques a mano los resultados para
   tapar un fallo del código. Documenta el formato nuevo en el `CONOCIMIENTO.md` del juego.

Lo regenerable (`biblioteca/*/extraidos/`) no se versiona. Lo que el usuario aporte (fotos, logos, personajes
propios) va en `biblioteca/<id>/personalizados/` y sí se versiona; no lo mezcles con lo extraído.
