---
name: cinematica-mario-party-ds
description: Crea y renderiza escenas de Mario Party DS con su motor, recursos de la ROM, capas, cámara y audio nativo.
---

# Cinemáticas de Mario Party DS

Usa el flujo crear-video. Lee juegos/mario-party-ds/AGENTS.md, CONOCIMIENTO.md y conocimiento/motor-video-nds.md.
Motor: juegos/mario-party-ds/video/motor.py. Formatos horizontal 1280x720 y vertical 1080x1920.

## Crear el proyecto

Importa valedores.rutas desde nucleo/, añade rutas.motor_dir('mario-party-ds') a sys.path e importa desde motor lo que necesites:
Video, Recursos, Escena3D, Camara, Particulas, CaraFoto, Hitos, Pista, efectos, interfaz, personajes.
El guion vive en proyectos/<slug>/video.py. Usa Recursos().buscar() para elegir orígenes exactos del catálogo.

El motor monta escenas 3D con tableros y personajes reales: animaciones nativas ANMF, caras de foto sobre el modelo, cámara con encuadres,
órbitas y temblor, partículas, transiciones, efectos de imagen, interfaz nativa (diálogos, carteles, marcadores, iconos), música, voces y efectos.
API, ejemplo y límites en CONOCIMIENTO.md (sección «Motor de vídeo»). Modelo a copiar: juegos/mario-party-ds/video/demo_completa.py.

```
python valedores.py ejecutar <slug> -- python -I juegos/mario-party-ds/video/demo_completa.py --foto a.jpg --foto2 b.jpg --fotogramas
```

Para los vídeos de proyecto usa siempre python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py.
Antes de prometer un plano, comprueba:
- Nombres de animación: son etiquetas visuales y algunos huecos cambian según el personaje. Míralos con personajes.hoja_animaciones.
- Caras de foto: Wario, Waluigi y Yoshi dan el peor resultado en primer plano; de perfil la foto se estira.
- Efectos de sonido: sus nombres son números. Medirlos no es oírlos: genera rec.muestrario(prefijo) y pide al usuario que elija.
Si no hay fuente del juego compatible, compón sin texto añadido o implementa antes su lector; nunca sustituyas por una fuente externa.
Abre los fotogramas y revisa el MP4 con revisar-video antes de entregar.
