---
name: cinematica-super-mario-64-ds
description: Crea y renderiza escenas de Super Mario 64 DS con su motor, recursos de la ROM, capas, cámara y audio nativo.
---

# Cinemáticas de Super Mario 64 DS

Usa el flujo crear-video. Lee juegos/super-mario-64-ds/AGENTS.md, CONOCIMIENTO.md y conocimiento/motor-video-nds.md.
Motor: juegos/super-mario-64-ds/video/motor.py. Formatos horizontal 1280x720 y vertical 1080x1920.

## Crear el proyecto

Importa valedores.rutas desde nucleo/, añade rutas.motor_dir('super-mario-64-ds') a sys.path e importa Video, Recursos,
Clip, Superposicion e interpolar desde motor. El guion vive en proyectos/<slug>/video.py.
Usa Recursos().buscar() para elegir orígenes exactos del catálogo; no copies ids de otros juegos o regiones.

Escenas con modelos 3D BMD, materiales y texturas nativos, cámara animada, capas y música SDAT.

La API y el ejemplo completo están en conocimiento/motor-video-nds.md. Puedes probar el motor con:

```
python -I juegos/super-mario-64-ds/video/demo.py --solo-frame
python -I juegos/super-mario-64-ds/video/demo.py --formato vertical
```

Para los vídeos de proyecto usa siempre python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py.
Comprueba las capacidades y límites del lector en CONOCIMIENTO.md antes de prometer personajes/animaciones.
Los modelos HBDF/BMD se cargan en pose de reposo; el movimiento de cámara y de capas sí se anima.
Las animaciones esqueléticas ANMF/BCA no están implementadas. Los clips ARC de Layton sí conservan sus tiempos.
Si no hay fuente del juego compatible, compón sin texto añadido o implementa antes su lector; nunca sustituyas por una fuente externa.
Abre los fotogramas y revisa el MP4 con revisar-video antes de entregar.
