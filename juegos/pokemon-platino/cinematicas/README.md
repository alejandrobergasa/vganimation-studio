# Motor de cinemáticas (sprites de Pokémon Platino)

Genera escenas con los gráficos reales del juego: personajes del mapa, tiles, ventana de diálogo
y fuente originales, y la burbuja «!». Resultado: GIF + MP4 + hoja de contacto.

```
cd cinematicas
python escenas/demo_parque.py        # -> salida/pokemon-platino/demo_parque.gif / .mp4 / _hoja.png
```

Requiere Python con `pillow` y `numpy`; para el MP4, `ffmpeg` en el PATH.

## Escribir una escena

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from motor import Escena, Mapa

mapa = Mapa("""
..........
====......
..........
""", {'.': 'cesped', '=': 'baldosas'})
mapa.poner('arbol', 2, 0)

esc = Escena(mapa)                                   # 256x192 a 30 fps, exporta x3
lucas = esc.personaje('heroe_andar_correr', 0, 1, mira='derecha')
chica = esc.personaje('girl1', 6, 1, mira='izquierda')
esc.camara_sigue(lucas)

esc.hacer(esc.fundido(entrada=True))
esc.hacer(lucas.andar('derecha', 5))                 # un paso = una acción
esc.hacer(esc.dialogo('¡Hola!\nBonito día, ¿verdad?'))
esc.hacer(chica.emocion('!'), chica.saltar())        # varias acciones a la vez
esc.hacer(chica.correr('derecha', 8))
esc.esperar(30)
esc.hacer(esc.fundido(entrada=False))
esc.renderizar(os.path.join(SALIDA, 'mi_escena'))
```

### Mapa real del juego (recomendado)
Los mapas de Platino no son tiles 2D: cada trozo de 32x32 tiles es un modelo 3D (árboles por capas,
orillas del agua, vallas, edificios). `MapaReal` lo renderiza desde el ROM con la proyección del juego
y lo guarda en `.cache/pokemon-platino/` (la primera vez tarda unos segundos).

```python
from motor import Escena, MapaReal
mapa = MapaReal('aromaflor', hora=12)        # zonas en motor/mapa_real.py (ZONAS)
mapa = MapaReal(fila=26, col=3, filas=2, cols=1)   # o cualquier trozo de la matriz de Sinnoh
```
- Plano con la rejilla de tiles y en rojo lo que no se puede pisar:
  `python herramientas.py mapa aromaflor` -> `<trabajo>/_mapa_aromaflor.png`. Las coordenadas de los
  personajes son esos tiles. Si un personaje pisa un tile bloqueado, el render avisa por consola.
- Los árboles, tejados y arcos que quedan delante tapan a los personajes automáticamente, y el
  personaje sube y baja con el relieve.
- `hora`: luz del juego (7 amanecer, 12 día, 18 tarde, 22 noche).
- Interiores (casas, guaridas...): `MapaReal('celda')` (nombres en `INTERIORES`) o `MapaReal(land=<id>)`.
  Plano: `python herramientas.py mapa celda` o `mapa land <id>`. Si la sala es más pequeña que la
  pantalla, la cámara la centra con negro alrededor, como en el juego.
- Limitación: el mapa es estático (el agua y las flores no se animan todavía).

### Mapa 2D de tiles (antiguo)
Aproximación hecha a mano con texturas sueltas; los árboles y el agua no encajan como en el juego.
Úsalo solo para escenas abstractas.
- `Mapa(texto, leyenda, fondo='cesped')`: cada carácter es un tile de 16x16. La leyenda asigna un
  suelo (`'cesped'`), o un suelo y un objeto (`('cesped', 'arbol')`).
- `mapa.poner(objeto, tx, ty)`: el objeto se apoya en ese tile y se ordena en profundidad con los personajes.
- Suelos y objetos disponibles: `motor/catalogo.py` (vista previa con `python herramientas.py catalogo`).
  Ahí mismo se añaden más, apuntando a cualquier textura de `biblioteca/pokemon-platino/extraidos/tilesets_mapa/`.

### Personajes (`esc.personaje(sprite, tx, ty, mira)`)
`sprite` es una carpeta de `biblioteca/pokemon-platino/extraidos/personajes_mapa/`. Vale el nombre completo, su número
(`'090'`) o un trozo único (`'babyboy1'`, `'gingaboss'`, `'leader3'`).
Para verlos todos: `python herramientas.py personajes`; para ver uno: `python herramientas.py personaje boy1`.

| Acción | Qué hace |
|---|---|
| `p.andar(dir, n, modo='andar')` | Camina n tiles (`'andar'` 8 f/tile, `'correr'` 4, `'sprint'` 2, `'lento'` 16) |
| `p.correr(dir, n)` | Igual que andar en modo correr (usa los frames de correr si el sprite los tiene) |
| `p.ruta(('derecha',3), ('arriba',2))` | Varios tramos seguidos |
| `p.mirar(dir \| otro_personaje)` | Gira |
| `p.saltar(altura, frames)` | Saltito de sorpresa |
| `p.emocion('!', frames)` | Burbuja «!» sobre la cabeza |
| `p.golpear(otro, sonido='SEQ_SE_DP_KOUKA_H')` | Puñetazo: se lanza hacia `otro`, destello de impacto (`efectos_ataques/33`), la víctima retrocede y la pantalla tiembla (24 f) |
| `p.teletransportar(tx, ty)` / `p.desaparecer()` / `p.aparecer()` | Colocar, ocultar o volver a mostrar |
| `p.posar(i \| img \| None)` | Pose fija: frame extra del sprite (los custom traen 16 = agachado, 17 = sentado...), una imagen de cualquier tamaño (se apoya centrada en el tile) o `None` para volver a andar |
| `p.cambiar_sprite('nombre')` | Cambia de ropa/sprite sin moverse |
| `p.llevar(img, dx=0, dy=-12)` | Dibuja un objeto encima (caja sobre la cabeza, palo en la mano, cascos); `None` lo quita. `dx, dy` en px desde la esquina superior del sprite, centrado |
| `p.mover(dx, dy, frames, arco=0, animar=False)` | Desplazamiento libre en px; `arco` = altura de parábola (lanzar, saltar un bordillo) |
| `p.desvanecer(entrada, frames)` / `p.tenir(color, fuerza)` / `p.temblar(frames, amplitud)` | Fundido del personaje, tinte de color y temblor en el sitio |

`esc.objeto(img, tx, ty, visible=True)` pone un objeto (banco, caja, saco, sofá...) que se ordena en profundidad con los
personajes y admite sus mismas acciones (`mover`, `aparecer`, `temblar`...).

### Sonido
La música y los efectos salen del ROM (`data/sound/sound_data.sdat`). No son audio grabado sino
secuencias tipo MIDI con instrumentos del juego; `tools/sonido.py` las sintetiza y el resultado se guarda en
`.cache/pokemon-platino/audio/`. Solo el MP4 lleva sonido (el GIF no puede).
- Lista de nombres: `python ../tools/sonido.py "../3787 - Pokemon Edicion Platino (S)(iND).nds" --lista`.
- Escuchar una suelta: `python ../tools/sonido.py <rom> SEQ_EYE_GINGA prueba.wav 20`.
- Música útil: `SEQ_CITYxx_D/_N` (ciudades de día/noche; 01 = Jubileo), `SEQ_TOWNxx_D` (pueblos),
  `SEQ_ROAD_*` (rutas), `SEQ_EYE_*` (cuando te ve un entrenador; `EYE_GINGA` = Equipo Galaxia),
  `SEQ_BA_*` (combates), `SEQ_D_AGITO` (guarida Galaxia, inquietante), `SEQ_PC_01` (Centro Pokémon).
- Efectos útiles: `SEQ_SE_DP_SELECT` (pasar diálogo), `SEQ_SE_DP_KOUKA_H/M/L` (golpe en combate),
  `SEQ_SE_DP_NIGERU` (huir), `SEQ_SE_DP_KI_GASYAN` (golpe metálico), `SEQ_SE_DP_DOOR_OPEN`,
  `SEQ_SE_DP_KAIDAN2` (escaleras), `SEQ_SE_DP_DANSA` (salto de bordillo).

### Escena
| Acción | Qué hace |
|---|---|
| `esc.hacer(a, b, ...)` | Añade un paso con esas acciones en paralelo |
| `esc.esperar(frames)` | Pausa (30 frames = 1 s) |
| `esc.dialogo(texto, espera=45, velocidad=1, sonido=True)` | Ventana de mensaje del juego. `\n` separa líneas (2 por ventana). Suena el «clic» del juego al pasar cada página |
| `esc.musica('SEQ_CITY01_D', volumen=0.55)` | Empieza un tema del juego en bucle (sustituye al que sonara) |
| `esc.parar_musica(frames=30)` | Baja la música a silencio en esos frames (no detiene la escena) |
| `esc.sonido('SEQ_SE_DP_KOUKA_H', volumen=0.8)` | Efecto de sonido del juego |
| `esc.fundido(entrada=True/False, frames)` | Fundido desde o hacia negro |
| `esc.camara_sigue(p)` / `esc.camara_fija(tx, ty)` | Cámara |
| `esc.cambiar_mapa(mapa, sigue=p \| fija=(tx, ty))` | Cambia de escenario a mitad de escena (con la pantalla en negro); coloca antes a los personajes con `teletransportar` |
| `esc.renderizar(ruta, gif, mp4, hoja_contacto, cada)` | Exporta |
| `esc.accion(f)` | Ejecuta `f()` en ese momento del guion (p. ej. `esc.accion(lambda: esc.camara_sigue(p))`) |
| `esc.en_paralelo(a, b, ...)` | Lanza acciones de fondo que siguen corriendo mientras avanzan los pasos siguientes (humo, fuego, forcejeo) |
| `esc.mostrar(nombre, img, x, y, frames, efecto, orden)` | Capa fija en pantalla (inserto, título, rótulo). `efecto`: `'fundido'`, `'subir'`, `'zoom'` o `None`; `x/y=None` centra |
| `esc.ocultar(nombre, frames, efecto)` / `esc.cambiar_capa(nombre, img)` / `esc.mover_capa(nombre, dx, dy, frames)` | Quitar (`'fundido'` o `'bajar'`), cambiar la imagen o desplazar una capa |
| `esc.tenir_pantalla(color, alfa, frames)` / `esc.destello(color, frames, pico)` | Tinte de toda la imagen (`None` lo quita) y fogonazo |
| `esc.poner_filtro('crt' \| 'sepia' \| func \| None)` | Filtro final de toda la pantalla (tele vieja, sepia) |
| `esc.animacion(imgs, x, y, frames, cada, pantalla=False)` | Efecto animado en px de mapa (o de pantalla) |
| `esc.camara_mover(tx, ty, frames)` / `esc.temblor_pantalla(frames, amplitud)` | Paneo suave y vibración |

**Escenas sincronizadas con un audio externo** (vídeos largos con voces): `Escena(mapa, t0=segundo_inicial)` y
- `esc.hasta(seg)`: espera hasta ese segundo absoluto (avisa con `AVISO` si ya ha pasado); `esc.ahora` da el segundo actual.
- `esc.subtitulos([(t_ini, t_fin, texto[, tipo_ventana]), ...])`: diálogos que se escriben solos en su momento, sin
  parar la escena; el texto se parte solo (`envolver`) y las páginas se reparten el tiempo.
- `esc.exportar(ruta, duracion, audio_base=wav, desde=None)`: render en streaming (minutos sin llenar la memoria). Mete en
  el MP4 el trozo `[t0, t0+duracion]` de `audio_base` mezclado con los efectos, y deja `<ruta>_sfx.wav` y `<ruta>_hoja.png`.
- Las capas de `mostrar` quedan **debajo** del negro de `fundido`: para un título sobre negro, pon una capa negra con
  `orden` menor y quita el fundido.
Ejemplo completo: `escenas/rewindlimbo2/` (14 tramos y su `montaje.py` en `trabajo/rewindlimbo2/`).

`Escena(mapa, fps=30, escala=3, tipo_ventana=1)`: `tipo_ventana` va de 0 a 19 y corresponde a los
marcos de mensaje del juego (`biblioteca/pokemon-platino/extraidos/interfaz/marcos_mensaje/`).

## Convenciones de los sprites del mapa
- Frames 0-15: arriba (0-3), abajo (4-7), izquierda (8-11), derecha (12-15), con el ciclo
  [quieto, paso, quieto, paso]. Los protagonistas tienen además los frames 16-31 (correr), en el mismo orden.
- El sprite es de 32x32 y los pies quedan en el borde inferior del tile que ocupa.
- Los tiles de césped vienen en cian del juego (el 3D los tiñe), así que el motor los pasa a verde
  (`cian_a_verde` en el catálogo).


## Motor v2
`from motor_v2 import Escena, MapaReal`: misma API que `motor`, con la sombra sin glitch y los escenarios animados
(`MapaReal(..., animado=False)` para desactivarlo). Skill: `/cinematica_v2`. Plantilla: `escenas/demo_parque_v2.py`.
