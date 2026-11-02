---
name: cinematica-inazuma-eleven
description: Crea y renderiza escenas de Inazuma Eleven con su motor, recursos de la ROM, capas, cámara y audio nativo.
---

# Cinemáticas de Inazuma Eleven

Usa el flujo crear-video. Lee juegos/inazuma-eleven/AGENTS.md, CONOCIMIENTO.md y conocimiento/motor-video-nds.md.
Motor: juegos/inazuma-eleven/video/motor.py. Formatos horizontal 1280x720 y vertical 1080x1920.

## Crear el proyecto

Importa valedores.rutas desde nucleo/, añade rutas.motor_dir('inazuma-eleven') a sys.path e importa Video, Recursos,
Clip, Superposicion e interpolar desde motor. El guion vive en proyectos/<slug>/video.py.
Usa Recursos().buscar() para elegir orígenes exactos del catálogo; no copies ids de otros juegos o regiones.

Escenas 2D con mapas PAC y **sprites RPG pequeños** para los personajes del escenario, fuente NFTR y voz SADL.
Usa `Recursos().personaje('Mark', direccion='este', accion='caminar')` o `accion='quieto'`.
`personajes()` lista nombres e ids de unitbase. Cabeza y paleta se resuelven desde esa tabla; el cuerpo por defecto
es el 100 con paleta 1 (uniforme Raimon). Elige `cuerpo=` y `paleta_cuerpo=` explícitamente para otro vestuario.
Hay ocho direcciones (las de la derecha reflejan las cinco vistas nativas), cuatro frames de caminar y velocidad
configurable `fps=8`; esta cadencia es del montaje, no una interpretación de los scripts de la ROM.
Usa `Recursos().escenario('mr01b01')` para el fondo real de Raimon, no su minimapa `*_mn`. Compón con
`Video.plano_rpg()` y `EscenaRPG`: fondo y sprite comparten lienzo lógico y una única ampliación entera.
Calibra `pixeles_por_unidad` del escenario (32 por defecto) y el zoom de cámara, nunca el tamaño del actor como porcentaje
de pantalla. Conserva el ancla de pies. No muevas un retrato grande como si fuera un jugador.
`Recorrido` y `ActorDireccional` eligen la vista según el movimiento, incluidas diagonales y pausas. El personaje
personalizado debe tener las ocho animaciones `caminar_<direccion>` y `quieto_<direccion>`; compruébalas antes de renderizar.
Las fotos se adaptan a estos sprites: sigue `conocimiento/personajes-desde-fotos.md` y carga con
`rec.personaje_personalizado(nombre, animacion)`. Los retratos PAC se reservan para diálogos cuando proceda.

La API y el ejemplo completo están en conocimiento/motor-video-nds.md. Puedes probar el motor con:

```
python -I juegos/inazuma-eleven/video/demo.py --solo-frame
python -I juegos/inazuma-eleven/video/demo.py --formato vertical
```

Para los vídeos de proyecto usa siempre python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py.
Comprueba las capacidades y límites del lector en CONOCIMIENTO.md antes de prometer personajes/animaciones.
La alternativa 3D del juego está en `video/jugador.py`; úsala cuando se solicite 3D, no como sustituto del sprite RPG.
Si no hay fuente del juego compatible, compón sin texto añadido o implementa antes su lector; nunca sustituyas por una fuente externa.
Abre los fotogramas y revisa el MP4 con revisar-video antes de entregar.
