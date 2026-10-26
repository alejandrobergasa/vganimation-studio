---
name: recursos-mario-party-ds
description: Extrae y consulta los recursos base de Mario Party DS; distingue originales, conversiones y formatos aún pendientes.
---

# Recursos de Mario Party DS

Lee juegos/mario-party-ds/AGENTS.md, CONOCIMIENTO.md y conocimiento/README.md.

1. Comprueba la detección con python valedores.py roms o estado: código A8TP.
2. Si el usuario autoriza extraer, usa python valedores.py extraer mario-party-ds. --rapido limita los archivos y miembros; no es una extracción completa.
3. Consulta biblioteca/mario-party-ds/extraidos/README.md y catalogo.json. Relaciona cada derivado con su origen; revisa avisos.log y errores.log incluso si el proceso termina bien.
4. Abre los PNG y la hoja con la herramienta de imágenes. Para audio, comprueba duración/nivel y escucha cuando haya reproducción disponible. No afirmes haber escuchado sólo por medir.
5. Documenta formatos nuevos en CONOCIMIENTO.md y añade sus lectores al núcleo compartido si sirven para más de un juego.

Alcance: extracción base; Contenedores BIN, descompresión LZ, recursos Nitro y bancos SDAT. Modelos y animaciones propios conservados sin reconstruir.

No hay motor de vídeo disponible. No trates formatos propietarios como Nitro estándar por su extensión y no prometas reconstrucción de personajes o escenas hasta implementar y revisar sus lectores.
