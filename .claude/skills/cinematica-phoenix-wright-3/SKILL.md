---
name: cinematica-phoenix-wright-3
description: Crea y renderiza escenas de Phoenix Wright 3 con su motor, recursos de la ROM, capas, cámara y audio nativo.
---

# Cinemáticas de Phoenix Wright: Ace Attorney – Trials and Tribulations

Si el usuario aporta una foto de alguien, crea sus bustos y poses anime en el estilo de los personajes DS
de `data.bin`, usando esos assets como referencia. Sigue `conocimiento/personajes-desde-fotos.md`.
Carga el resultado con `rec.personaje_personalizado(nombre, pose)`; no pegues una cara fotográfica sobre un cuerpo
dibujado ni inventes una animación a partir de una única pose. Foto directa solo si la pide el usuario.

Usa el flujo crear-video. Lee juegos/phoenix-wright-3/AGENTS.md, CONOCIMIENTO.md y conocimiento/motor-video-nds.md.
Motor: juegos/phoenix-wright-3/video/motor.py. Formatos horizontal 1280x720 y vertical 1080x1920.

## Crear el proyecto

Importa valedores.rutas desde nucleo/, añade rutas.motor_dir('phoenix-wright-3') a sys.path e importa Video, Recursos,
Clip, Superposicion e interpolar desde motor. El guion vive en proyectos/<slug>/video.py.
Usa Recursos().buscar() para elegir orígenes exactos del catálogo; no copies ids de otros juegos o regiones.

Escenas 2D con gráficos y poses de data.bin, capas, cámara animada y música SDAT.

La API y el ejemplo completo están en conocimiento/motor-video-nds.md. Puedes probar el motor con:

```
python -I juegos/phoenix-wright-3/video/demo.py --solo-frame
python -I juegos/phoenix-wright-3/video/demo.py --formato vertical
```

Para los vídeos de proyecto usa siempre python valedores.py ejecutar <slug> -- python -I proyectos/<slug>/video.py.
Comprueba las capacidades y límites del lector en CONOCIMIENTO.md antes de prometer personajes/animaciones.
Los bustos personalizados usan poses dibujadas, no animación esquelética. `Busto` gestiona hablar/quieto;
`impacto` y `rotulo_impacto` añaden golpes breves sin tapar el diálogo. `banda_sonora` programa pistas de la ROM
por momento y reduce música alrededor de los impactos. `Video.renderizar(...,audio_redes=True)` ajusta sonoridad
en dos pasadas; mide el MP4 final y declara si no pudiste escucharlo. Conserva siempre el personaje aprobado
como pose canónica y crea sus expresiones en imágenes adicionales.
Si no hay fuente del juego compatible, compón sin texto añadido o implementa antes su lector; nunca sustituyas por una fuente externa.
Abre los fotogramas y revisa el MP4 con revisar-video antes de entregar.
