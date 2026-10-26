# BOLAS NEGRAS

## Idea
Alega y Vivi van cada uno en su coche por la carretera, comentando las ganas que tienen de ver «la bola negra». Llegan a un cine,
aparcan, bajan y se acercan a la puerta, donde está Pedro Sánchez: la entrada cuesta 10 euros. Pagan encantados y entran.
La cámara se va a Santos, que lo observa todo desde detrás de una esquina, decepcionado: «esto es una locura, no puede ser que dos
hombres hechos y derechos paguen por ver bolas negras, ¿qué buscan?». Corte a primer plano de la imagen QUEBUSCA.

## Formato
- Juego: `mkds` · Formato: vertical 1080×1920
- Duración objetivo: ≈ 30–35 s · Plataforma: TikTok / Reels / Shorts
- Tono: humor absurdo / parodia entre colegas; remate seco con la imagen QUEBUSCA

## Reparto y escenarios
- **Alega** — conduce un kart, va de copiloto de la conversación; luego paga y entra.
- **Vivi** — conduce otro kart, el más ilusionado; luego paga y entra.
- **Pedro Sánchez** — portero/taquillero del cine, cobra 10 € en la puerta.
- **Santos** — espectador oculto tras una esquina del cine; hace de voz de la razón y da el remate.
- Escenario: un único circuito de la ROM para la carretera (**`mario_course`**, ver storyboard; `ridge_course` descartado). El **cine** (fachada, marquesina con el cartel «BOLAS NEGRAS», puerta, esquina
  donde se esconde Santos y zona de aparcamiento) se monta con geometría simple (cajas) junto a la carretera, con texturas
  de la propia ROM, para no cambiar de circuito. La decisión final se confirma en el storyboard.
- «Coches» = los karts del juego, con un piloto de modelo propio (ver abajo), uno de cada color/clase para distinguirlos.

## Material del usuario (`entrada/bolas_negras/`)
Excepción a «solo assets de la ROM» únicamente para este vídeo:
- `alega.jpeg` (283×353) — cara de Alega (calvo, perilla corta, camiseta negra) → textura de la cabeza de su modelo.
- `vivi.jpg` (199×238) — cara de Vivi (pelo oscuro, jersey/camiseta negra) → textura de la cabeza de su modelo.
- `santos.jpeg` (483×613) — cara de Santos (pelo castaño, sudadera gris) → textura de la cabeza de su modelo.
- `pedrosanchez.jpg` (305×457) — cara de Pedro Sánchez (pelo canoso, traje oscuro, camisa blanca y corbata azul) → textura de la cabeza de su modelo.
- `QUEBUSCA.jpeg` (1024×1536, portada de revista satírica «¿QUE BUSCAN??» con las caras de los cuatro) — aportada después de la validación de la idea; plano final a pantalla completa (la imagen entera, con el resto del fotograma relleno con ella misma desenfocada).

Cuerpos: geometría sencilla (cajas/cilindros del motor, estilo `Peaton`/`caja` de `mk/extra.py`) con colores de ropa sacados de cada
foto (Alega camiseta negra, Vivi negro, Santos gris, Pedro traje oscuro + corbata azul). La foto, recortada a la cara y reducida a 128 px,
va de textura frontal en la cabeza; el resto de la cabeza, con el color de pelo/piel.

## Datos a verificar
- Ninguno factual. El precio de entrada (10 €) y los diálogos son los del usuario.

## Decisiones tomadas por el agente
- Coches = karts de MKDS (único «coche» que ofrece la ROM), con el modelo propio de cada uno en el asiento.
- Un solo circuito para toda la historia (carretera + cine con cajas) — evita cortes y deja el presupuesto de render para el diálogo.
- Santos aparece por primera vez en el plano de «se enfoca a Santos» (pequeño paneo desde la puerta hasta la esquina), no antes.
- Pedro Sánchez se trata como personaje de parodia inocua (solo cobra la entrada); ningún texto lo ridiculiza más allá de la idea original.
- Música: sin decidir aún (fase `musica`); se propone algo de carretera/alegre que se corta en seco con Santos.
- Texto de diálogo con la fuente del juego, fuera del 12 % superior y el 18 % inferior de la pantalla.

## Dudas abiertas
- (resuelta) La imagen QUEBUSCA ya está en `entrada/bolas_negras/QUEBUSCA.jpeg`.
- ¿Te vale que los «coches» sean los karts del juego, o prefieres otro vehículo?
