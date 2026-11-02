---
name: recursos-inazuma-eleven
description: Extrae y consulta los recursos base de Inazuma Eleven; distingue originales, conversiones y formatos aún pendientes.
---

# Recursos de Inazuma Eleven

Lee juegos/inazuma-eleven/AGENTS.md, CONOCIMIENTO.md y conocimiento/README.md.

1. Comprueba la detección con python valedores.py roms o estado: código YEES.
2. Si el usuario autoriza extraer, usa python valedores.py extraer inazuma-eleven. --rapido limita los archivos y miembros; no es una extracción completa.
3. Consulta biblioteca/inazuma-eleven/extraidos/README.md y catalogo.json. Relaciona cada derivado con su origen; revisa avisos.log y errores.log incluso si el proceso termina bien.
4. Abre los PNG y la hoja con la herramienta de imágenes. Para audio, comprueba duración/nivel y escucha cuando haya reproducción disponible. No afirmes haber escuchado sólo por medir.
5. Documenta formatos nuevos en CONOCIMIENTO.md y añade sus lectores al núcleo compartido si sirven para más de un juego.

Alcance: paquetes PKB/PKH PackNum, PAC, texturas Nitro y fuentes NFTR. Los originales se conservan.
El motor lee los sprites RPG pequeños de `spr/char/{pcb,pch,ppb,pph}` y SADL; MODS sigue pendiente.
Usa `Recursos().personajes()` y `personaje('Mark', direccion='sur', accion='caminar')` para inspeccionar
cuerpos, cabezas, paletas y frames reales. No confundas estos sprites con los retratos de `face2d`.

El motor de vídeo está disponible en video/motor.py; para componer usa la skill cinematica-inazuma-eleven. No trates formatos propietarios como Nitro estándar por su extensión y no prometas reconstrucción de personajes o escenas hasta implementar y revisar sus lectores.
