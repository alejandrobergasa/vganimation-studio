---
name: cinematica-profesor-layton
description: Crea y renderiza escenas de Profesor Layton con su motor, recursos de la ROM, capas, cámara y audio nativo.
---

# Cinemáticas de El profesor Layton y la villa misteriosa

Usa el flujo crear-video. Lee juegos/profesor-layton/AGENTS.md, CONOCIMIENTO.md y conocimiento/motor-video-nds.md.
Motor: juegos/profesor-layton/video/motor.py. Formatos horizontal 1280x720 y vertical 1080x1920.

## Crear el proyecto

Importa valedores.rutas desde nucleo/, añade rutas.motor_dir('profesor-layton') a sys.path e importa Video, Recursos,
Clip, Superposicion e interpolar desde motor. El guion vive en proyectos/<slug>/video.py.
Usa Recursos().buscar() para elegir orígenes exactos del catálogo; no copies ids de otros juegos o regiones.

Escenas 2D con fondos, personajes ARC animados, fuente NFTR, música SDAT y audio SADL.

La API y el ejemplo completo están en conocimiento/motor-video-nds.md. Puedes probar el motor con:

```
python -I juegos/profesor-layton/video/demo.py --solo-frame
python -I juegos/profesor-layton/video/demo.py --formato vertical
```

Para los vídeos de proyecto usa siempre python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py.
Comprueba las capacidades y límites del lector en CONOCIMIENTO.md antes de prometer personajes/animaciones.
Los modelos HBDF/BMD se cargan en pose de reposo; el movimiento de cámara y de capas sí se anima.
Las animaciones esqueléticas ANMF/BCA no están implementadas. Los clips ARC de Layton sí conservan sus tiempos.
Para personajes usa `rec.personaje_layton(nombre, animacion)`: monta cuerpo + capa facial (`*_e_face`, la boca) en su posición real. No pongas `Superposicion` con coordenadas a ojo. El texto con `rec.fuente().texto()` ya lleva el espaciado correcto de las NFTR de Layton.
Si no hay fuente del juego compatible, compón sin texto añadido o implementa antes su lector; nunca sustituyas por una fuente externa.
Abre los fotogramas y revisa el MP4 con revisar-video antes de entregar.
