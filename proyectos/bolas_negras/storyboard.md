# Storyboard — BOLAS NEGRAS

Formato: vertical 1080×1920, 30 fps, **36 s** · Juego: `mkds` · Música: pop-rock de carretera → suspense cómico → lamento → golpe
(`musica.md`, La mayor/menor, 120 → 92 → 60 bpm). Todo el estado es función pura de `t` (render paralelo).

## Escenario (cambio respecto al brief, con motivo)
El brief proponía `ridge_course`; **lo descarto**: lo medí y la recta (s 515–635) va por el borde de un acantilado, con vacío a un lado
y talud al otro; no hay un solo tramo llano junto a la calzada donde poner un aparcamiento y un cine. Uso **`mario_course`** (Circuito Mario):
calzada de asfalto de ≈ 16 u y, en s ≈ 950–1150, **200 u de terreno llano y a nivel a la derecha** (medido: altura del suelo ±1,2 u
en los 12–52 u laterales). Es la misma pista que ya usa el ejemplo «Ábalos», con el cielo parcheado (`X.parchear_cielo()`).

**Posición del cine** (coordenadas de `Pista.muestra(s, lateral)`, lateral > 0 = derecha):
- Calzada: se conduce por s ≈ 560 → 1000. Los karts salen de la pista hacia la derecha a partir de s ≈ 1000.
- Aparcamiento: plazas en s ≈ 1018–1034, lateral 24–28 (marcas blancas con cajas planas).
- **Fachada del cine**: lateral ≈ 46, de s 1010 a 1050 (40 u de ancho, 16 u de alto), mirando a la calzada. Puerta de 6 × 9 u centrada en s ≈ 1030
  (hueco negro con marco rojo), marquesina sobre la puerta con **«BOLAS NEGRAS»** (fuente del juego, textura), pilares y focos amarillos.
- **Esquina de Santos**: un volumen saliente en el extremo derecho de la fachada (s ≈ 1052, cuerpo de 8 × 16 u). Santos está **tras ese borde**,
  asoma la cabeza y medio cuerpo.
- El cine se monta con cajas (`X.caja`) y materiales de la propia ROM/sólidos; no hay modelo de cine en el juego.

## Reparto y modelos
| Personaje | Modelo | Cara (textura de la foto, recorte a 128 px) | Cuerpo |
|---|---|---|---|
| Alega | cajas/cilindros: cabeza cúbica con la foto en la cara frontal, tronco, brazos, piernas (estilo `X.Peaton`, pero sin piloto de la ROM) | `entrada/bolas_negras/alega.jpeg` | camiseta y pantalón negros; cabeza calva (resto de la cabeza color piel) |
| Vivi | ídem | `entrada/bolas_negras/vivi.jpg` | negro; pelo oscuro (cubo de pelo sobre la cabeza) |
| Santos | ídem | `entrada/bolas_negras/santos.jpeg` | sudadera gris; pelo castaño |
| Pedro Sánchez | ídem, algo más alto | `entrada/bolas_negras/pedrosanchez.jpg` | traje oscuro, camisa blanca, corbata azul (cajas de color); pelo canoso |
| Karts («coches») | `Kart(m,'luigi','b')` (Alega, verde) y `Kart(m,'wario','b')` (Vivi, amarillo); solo carrocería y ruedas (`X.cuerpo_kart`), el personaje va sentado encima | — | — |

- Expresiones: solo hay una foto por persona, así que la emoción va en el **cuerpo** (cabeceo, rebote, brazos, mano a la frente) y en la cámara.
- Cuerpos de cajas = «geometría sencilla». Se valida en la fase `escenas` con fotogramas reales; si la cara no se reconoce, se ajusta el recorte.
- Alega y Vivi en los karts: cara visible hacia delante (de ahí los planos frontales).

## Escenas
| # | Tiempo | Plano / cámara | Contenido | Assets | Audio |
|---|---|---|---|---|---|
| 1 | 0,0–2,0 | **Persecución alta**, 9 u detrás y 6 u arriba, FOV 60, ligero temblor | Los dos karts lado a lado (Alega izquierda, Vivi derecha) por la recta. Rótulo **BOLAS NEGRAS** (rebote elástico, ≈ 25 % de altura). Fundido de entrada | `mario_course`; karts luigi-b y wario-b; `mk/texto.py` (`marioFont`) | entra la música; motor de karts |
| 2 | 2,0–5,0 | **Frontal baja**, delante de los karts mirando atrás, FOV 50, órbita lenta | Ambos en cuadro con la cara de frente. Ventana ALEGA | ídem | blips de voz de Alega |
| 3 | 5,0–8,0 | **Primer plano Vivi**, 3/4 frontal, FOV 38 | Rebota en el asiento. Ventana VIVI | ídem | blips de Vivi |
| 4 | 8,0–10,0 | **Primer plano Alega**, 3/4 desde el otro lado | Mira de reojo. Ventana ALEGA | ídem | blips de Alega |
| 5 | 10,0–12,0 | **Travelling lateral** paralelo a los karts → al final, la cámara sube (grúa) y **descubre el cine** al fondo | Vivi levanta el puño. Ventana VIVI. Marquesina iluminada. Zoom radial al llegar | cine de cajas | blips de Vivi; sube la música |
| 6 | 12,0–16,0 | **Dron alto 3/4 trasero** que acompaña | Los karts salen de la calzada, **derrapan** y se paran en dos plazas (humo, marcas); Alega y Vivi saltan al suelo y caminan (piernas) hacia la puerta. Pedro ya está en ella | `fx.Particulas` (humo, polvo); marcas con `X.cinta` | derrape SSAR 0 · 465 (comprobado en «Ábalos»); pasos |
| 7 | 16,0–19,0 | **Contraplano**: cámara tras Alega y Vivi (de espaldas, a un lado) mirando a Pedro, con travelling de entrada lento | Pedro en la puerta, brazos cruzados/mano extendida. Ventana PEDRO | fachada y puerta | blips de Pedro; la música baja a suspense |
| 8 | 19,0–22,0 | **Dos planos medios laterales** (19,0–20,9 Alega · 20,9–22,0 Vivi) | Cada uno entrega un billete verde (caja con textura «10») que vuela a la mano de Pedro. Ventanas ALEGA y VIVI | billete: caja con material propio | arpegio de «moneda» (en la música) |
| 9 | 22,0–24,0 | **Plano medio de Pedro**, ligero dolly-in | Se aparta; Alega y Vivi pasan tras él y **entran por la puerta** (desaparecen en el hueco negro). Ventana PEDRO | — | cadencia de metales; puerta |
| 10 | 24,0–26,0 | **Deslizamiento lateral** desde la puerta hacia la esquina (travelling hacia la derecha, 24 u) | Cae el color: la imagen se enfría. **Santos asoma tras la esquina**, observando; baja la cabeza (decepción). Sin texto | volumen de la esquina | corte de la música a lamento |
| 11 | 26,0–28,0 | **Plano medio frontal de Santos**, FOV 42 | Se lleva la mano a la frente y niega con la cabeza. Ventana SANTOS «ESTO ES UNA LOCURA.» | — | blips de Santos |
| 12 | 28,0–32,5 | **Dolly-in lento a su cara** (FOV 42 → 26), viñeta que se cierra | Dos ventanas seguidas: «NO PUEDE SER QUE DOS / HOMBRES CRECIDOS» (28,0–31,0) y «PAGUEN POR VER / BOLAS NEGRAS.» (31,0–32,5). Cuerpo quieto, cabeza ligeramente inclinada | — | latido de bombo creciente |
| 13 | 32,5–34,0 | **Golpe de zoom** sobre la cara, flash blanco al inicio | «¿QUÉ BUSCAN?» (rótulo grande, rebote) | — | **golpe final** + platillo |
| 14 | 34,0–36,0 | **Corte a primer plano de QUEBUSCA**, imagen del usuario a pantalla completa, zoom muy lento 100 → 106 % | Se mantiene hasta el final; fin en seco (la cola de la música se apaga) | **`QUEBUSCA` — pendiente de aportar (no está en `entrada/`)** | cola de la música (fundido 1,5 s) |

Texto: ventanas con la fuente del juego a ≈ 24 caracteres por línea máximo (ya aprobado en el guion), en la franja 62–80 % de la altura; nombre del
personaje en un color propio sobre cada ventana. Comprobar legibilidad real en móvil en los fotogramas de la fase `escenas`.

## Ajuste de tiempos respecto al guion
- El corte a QUEBUSCA cae a **34,0 s** (el guion decía ≈ 33,5): así la ventana «¿QUÉ BUSCAN?» dura sus 1,5 s completos y la imagen se queda 2 s.
  La duración total no cambia (36 s).

## Transiciones y efectos
- Cortes secos entre planos de diálogo; barrido de **desenfoque radial** en el 5 → 6; **flash** al cortar a 13; **iris/viñeta** cerrándose en 12.
- Gradación: cálida y saturada en carretera (escenas 1–9) → fría y apagada desde la 10 (Santos).
- Partículas: humo y polvo al derrapar (6), destello suave de bloom en la marquesina.

## Qué falta o es una decisión mía
- **Imagen QUEBUSCA**: sigue sin estar. Bloquea la escena 14; sin ella genero el resto y dejo un marcador.
- Cambio de circuito (ridge → mario_course) y los karts concretos (luigi verde / wario amarillo) son decisión mía; se cambian sin impacto en el resto.
- Cosas que no se pueden comprobar hasta la fase `escenas`: que las caras se reconozcan sobre el cubo, la altura de los personajes respecto al kart (asiento) y la
  legibilidad del texto en móvil.

## Previsualización (fase `escenas`)
- Fotogramas clave previstos: 1,0 · 3,5 · 6,5 · 11,5 · 14,0 · 17,5 · 20,0 · 23,0 · 25,0 · 27,0 · 30,0 · 33,0 · 35,0 → `previsualizacion/` y hoja de contactos.

## Cambios hechos al montar las escenas (fase `escenas`, tras aprobar el storyboard)
- **QUEBUSCA.jpeg ya está aportada** y se usa en la escena 14 (imagen entera a ancho completo, fondo desenfocado por encima y debajo, zoom 100 → 106 %).
- **Ubicación real del cine**: lado **izquierdo** de la recta posterior a la meta (s ≈ 108, lateral −26), no en s ≈ 1030 a la derecha: al medir de nuevo,
  la recta de meta tiene vallas, farolas y carteles junto a la calzada; la recta de s ≈ 75–150 tiene 25–40 u de hierba despejada a la izquierda. Los karts
  conducen por la recta de meta, la curva y llegan a esa recta (escenas 1–5).
- **Escala**: cine y coordenadas locales a 0,72; personas a 0,55 (≈ 6 u, como un kart).
- **Karts**: el de Alega (Luigi, clase b) sale **rojo** y el de Vivi (Wario, clase b) **azul** (no verde/amarillo como escribí); es lo que da el modelo.
- **Escena 5** pasa a persecución desde atrás que descubre el cine al salir de la curva (la cámara lateral quedaba fuera de la calzada, entre vallas).
- **Escena 8**: la cámara está dentro del vestíbulo del cine y mira hacia fuera, para ver las caras de Alega y Vivi (de frente a Pedro, de espaldas a la cámara en la 7).
- **Audio**: por ahora el vídeo solo lleva la música aprobada; las voces («blips») y los efectos (derrape, pasos, moneda) se montan en la fase `render`.
- **Personajes (cambio tras ver las primeras escenas)**: ya no son cajas. Cada uno es el **piloto de Mario de la ROM** (cabeza, cuerpo y animaciones del juego) con su foto
  como cara (mapeada por ojos/barbilla/centro de la cara) y la ropa recoloreada: Alega calvo con camiseta negra, Vivi con pelo negro, Santos con pelo castaño y sudadera gris,
  Pedro con pelo canoso, traje oscuro, camisa blanca y corbata azul. Mismo estilo que el ejemplo de Ábalos. Sentados en el kart usan `drive`; Vivi levanta el puño (`win`);
  Santos se cubre con las manos (`lose`).
- **Escena 8**: Pedro se aparta del eje (izquierda para el plano de Alega, derecha para el de Vivi) y la cámara se coloca en el vestíbulo, en diagonal.
- **Escenas 3, 4, 11–13**: cámaras bajadas a la altura real de la cara.
