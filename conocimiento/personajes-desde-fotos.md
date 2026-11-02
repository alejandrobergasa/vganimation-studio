# Personajes a partir de fotos

Una foto de una persona es una **referencia de identidad**. Salvo que el usuario pida otra cosa,
transfórmala en un personaje coherente con los assets del juego. Mantén sus rasgos reconocibles,
peinado, vello facial y tono de piel. No basta con reducir una foto ni pegarla en un cuerpo dibujado.
Una foto usada explícitamente como prueba, documento o fotografía dentro de la escena conserva ese uso.

## Elegir el formato correcto

| Juego / uso | Adaptación por defecto | Referencia y control |
|---|---|---|
| Inazuma Eleven, personajes en el escenario | Sprite RPG pequeño, cuerpo entero y frames para caminar | `Recursos().personaje('Mark', ...)`, `spr/char/{pcb,pch,ppb,pph}`. Cabeza y cuerpo comparten píxel, perspectiva y pies; no usar un retrato flotante como actor. |
| Phoenix Wright 3 | Busto anime a resolución DS, con las poses y expresiones necesarias | Poses nativas de `data.bin` (por ejemplo índices 61 y 78 en YG3Y), paleta, contornos y encuadre. No una cara fotográfica sobre un busto procedural. |
| Pokémon Platino | Sprites de mapa y, si hace falta, combate | Skill `personaje-pokemon`; cada uso tiene su resolución y hoja propia. |
| Profesor Layton | Personaje dibujado y expresiones compatibles con sus clips | Cuerpo ARC y capas de ojos/boca, respetando sus anclas. |
| Animal Crossing, MKDS, NSMB, Mario Party DS, SM64DS | Modelo **real del juego** con rostro personalizado como textura | Inspeccionar modelo, material facial, atlas y UV; adaptar cara y piel al sombreado y resolución nativos. Conservar malla y animaciones. En Mario Party DS, `rec.personaje(nombre, foto=...)` lo hace con una calca sobre la cabeza, sin efecto espejo y con boca y expresiones; aplana el relieve de la zona de la cara y cambia así la malla solo ahí (`aplanar=0` lo evita). Límites por personaje en su `CONOCIMIENTO.md`. |

El formato lo determina el asset del plano, no la etiqueta general del juego: un juego puede tener sprites,
retratos y modelos. En Inazuma usa los sprites pequeños por defecto; un plano 3D debe pedirse o justificarse
en el brief. Un retrato de diálogo separado puede usar su formato nativo.

En Inazuma prepara las ocho direcciones antes de animar: cinco vistas dibujadas y tres reflejadas, con `caminar_<direccion>`
y `quieto_<direccion>`. Usa `Recorrido`/`ActorDireccional` para orientar según el vector de movimiento, manteniendo
la mirada al parar. El fondo de juego se obtiene con `Recursos.escenario()` y se compone con `EscenaRPG`; un minimapa
no tiene la escala del escenario. Calibra la geometría y aplica el zoom sobre la composición completa.

## Proceso del agente

1. Abre la foto y uno o varios assets **decodificados de la ROM local**. Comprueba proporciones, tamaño visible,
   paleta, contornos, vistas y poses. No es suficiente leer los nombres de archivo.
2. Anota en el brief quién es el personaje, su foto, juego, tipo de adaptación y referencias nativas. Registra
   un elemento `personaje` en fase `escenas`. Los assets personalizados son la excepción autorizada del proyecto.
3. Con la herramienta de generación de imágenes disponible, usa la foto para identidad y el asset nativo para
   estilo. Especifica resolución lógica, paleta, vista, vestuario, transparencia, rejilla exacta y ancla. No
   inventes un estilo genérico «pixel» o «anime» sin comparar con el juego. Conserva el prompt final.
4. Guarda originales intactos y derivados en `entrada/<slug>/personajes/<nombre>/`. No reutilices la identidad
   en otros vídeos por defecto. No modifiques la ROM. Etiqueta los derivados como personalizados.
5. Importa el atlas al lienzo lógico del motor. En sprites, mantén escala común, alfa binario, paleta común y
   ancla de pies estable. Genera todos los frames/poses que exige el guion: no declares una imagen estática
   como animación de caminar o hablar. En 3D aplica la textura **al material**, nunca como capa plana encima
   del vídeo; comprueba frente, perfil y giro con las animaciones del modelo.
6. Abre una comparación a resolución nativa y ampliada: parecido, tamaño relativo al personaje nativo,
   anatomía, bordes, paleta, transparencia, pies, continuidad de la animación y encaje en el escenario.
   Regenera si falla. Marca `revisado: true` solo después de verlo. Esto no equivale a aprobación del usuario;
   se mantienen las puertas de validación del proyecto.
7. Si falta generador, lector, modelo o UV compatible, implementa la capacidad o explica el límite antes de
   prometerla. No uses foto directa, siluetas o cuerpos procedurales como alternativa silenciosa.

## Carga reutilizable

`valedores.personajes` importa derivados ya creados; **no llama a una IA ni estiliza fotos automáticamente**.
Los motores basados en `activos_video_nds.Recursos` exponen `personaje_personalizado()` y `textura_personalizada()`;
los demás pueden importar `cargar()` y `textura()` directamente. `perfil(juego)` ofrece el criterio por defecto.

Manifiesto `entrada/<slug>/personajes/alega/personaje.json` (rutas de imagen relativas a esa carpeta):

```json
{
  "version": 1,
  "juego": "inazuma-eleven",
  "modo": "pixel_art",
  "referencia_identidad": "entrada/<slug>/alega.jpeg",
  "referencia_rom": "data_iz/spr/char/{pcb,pch,ppb,pph}.pkb: Mark Evans",
  "imagen": "atlas-generado-v1.png",
  "rejilla": [4, 1],
  "lienzo": [32, 48],
  "ajuste": "pies",
  "tamano_visible": [16, 30],
  "colores": 16,
  "revisado": false,
  "animaciones": {
    "quieto": {"frames": [0]},
    "caminar_sur": {"frames": [0, 1, 2, 3], "duraciones": [0.125, 0.125, 0.125, 0.125]}
  }
}
```

Para anime usa `modo: "anime"`, lienzo acorde al busto nativo y poses nombradas (`quieto`, `objecion`, etc.).
No fuerces paleta de 16 colores ni proporciones chibi a un retrato anime. La rejilla puede ser `[1,1]` para
una pose quieta. El importador normaliza escala y pies solo si se solicita `ajuste: "pies"`.
Para los bustos DS de Phoenix usa `muestreo: "vecino"`, `alfa_binario: true` y una paleta común apropiada
(por ejemplo `colores: 128`), comprobando el resultado. La prueba de Alega usa lienzo 164×160, igual al busto nativo recortado.

Una animación puede indicar `imagen` y `rejilla` propias (poses adicionales sin reemplazar la imagen aprobada) y
`reflejar: true`. Para atlas generados con separaciones irregulares, declara `cajas: [[x0,y0,x1,y1], ...]` en orden
de lectura y comprueba todas las celdas: una rejilla aproximada puede introducir píxeles de la fila anterior.
`ajustar_rejilla: true` permite redondear bordes fraccionarios, pero no detecta por sí solo la separación de los sprites.
Si se amplía un personaje pixel art ya aprobado, usa `paleta: [[r,g,b], ...]` para importar todas las vistas con
sus colores exactos; conserva el frontal aprobado con una imagen propia de esa animación. Esto evita cambios
de piel o uniforme al girar aunque las vistas procedan de generaciones distintas.

```python
actor = rec.personaje_personalizado('alega', 'caminar_sur')  # proyecto activo
plano.sprite(actor, x=120, y=170, escala=4)
# O desde cualquier motor:
from valedores.personajes import cargar
actor = cargar('phoenix-wright-3', ruta_manifiesto, 'quieto')
```

Una textura 3D usa `modo: "textura_3d"`, `imagen`, `material` (nombre real de textura) y las mismas referencias
y revisión. `material, imagen = rec.textura_personalizada('alega')`; en `VistaModelo` se aplica con
`modelo.reemplazar_textura(material, imagen)`. Esta operación conserva geometría, UV y animaciones, y requiere
un atlas previamente ajustado a esas UV; no localiza ojos ni despliega UV por sí sola. En Inazuma, la alternativa
3D de `video/jugador.py` admite una textura `face00` mediante `foto=`; su uso no reemplaza el sprite RPG por defecto.

`exigir_revision=False` permite preparar previsualizaciones antes de marcar la revisión. Una petición explícita
de foto directa se documenta como `modo: "foto_directa"` y requiere `permitir_foto=True` al cargarla.
