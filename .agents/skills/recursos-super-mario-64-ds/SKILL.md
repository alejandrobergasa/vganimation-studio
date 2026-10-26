---
name: recursos-super-mario-64-ds
description: Extrae y consulta los recursos base de Super Mario 64 DS; distingue originales, conversiones y formatos aún pendientes.
---

# Recursos de Super Mario 64 DS

Lee juegos/super-mario-64-ds/AGENTS.md, CONOCIMIENTO.md y conocimiento/README.md.

1. Comprueba la detección con python valedores.py roms o estado: código ASMP.
2. Si el usuario autoriza extraer, usa python valedores.py extraer super-mario-64-ds. --rapido limita los archivos y miembros; no es una extracción completa.
3. Consulta biblioteca/super-mario-64-ds/extraidos/README.md y catalogo.json. Relaciona cada derivado con su origen; revisa avisos.log y errores.log incluso si el proceso termina bien.
4. Abre los PNG y la hoja con la herramienta de imágenes. Para audio, comprueba duración/nivel y escucha cuando haya reproducción disponible. No afirmes haber escuchado sólo por medir.
5. Documenta formatos nuevos en CONOCIMIENTO.md y añade sus lectores al núcleo compartido si sirven para más de un juego.

Alcance: extracción base; Archivos NitroFS, miembros NARC, descompresión LZ77/LZ y bancos SDAT. Los BMD/BCA propios no son modelos Nitro estándar.

No hay motor de vídeo disponible. No trates formatos propietarios como Nitro estándar por su extensión y no prometas reconstrucción de personajes o escenas hasta implementar y revisar sus lectores.
