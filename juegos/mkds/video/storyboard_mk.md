# Storyboard — «CIRCUITO MARIO» (Mario Kart DS) · demo del motor `video/mk/`

Formato: vertical 1080x1920, 30 fps, 38 s. Salida: `salida/mkds/mk_circuito_mario.mp4`. Todo procede de la ROM de Mario Kart DS
(modelos, texturas, animaciones, circuito, línea de carrera, fuente `marioFont`, sonido). Los efectos (partículas, bloom,
líneas de velocidad, aberración, iris) son de código propio.

| t (s) | Plano | Qué ocurre | Efectos |
|---|---|---|---|
| 0,0–3,8 | A. Sobrevuelo | Grúa descendente sobre el castillo de Peach; entra el título «CIRCUITO MARIO» con rebote elástico | bloom fuerte, fundido de entrada |
| 3,8–8,0 | B. Parrilla | Órbita frontal sobre Mario, Luigi y Peach; cuenta atrás 3-2-1 y «¡YA!» | humo de escape, destello al cortar |
| 8,0–11,6 | C. Persecución | Cámara alta detrás de Mario; salida con polvo; turbo (seta) | llamas, líneas de velocidad, zoom radial, FOV ↑ |
| 11,6–15,0 | D. Travelling lateral | Cámara baja en paralelo, derrapes | chispas azules → naranjas |
| 15,0–18,4 | E. Concha roja | Cámara sobre la concha; impacto en Luigi (giro 720°, estrellitas) | explosión (bombcore), onda, humo, sacudida, destello |
| 18,4–23,0 | F. Adelantamiento | Dron: Mario con turbo pasa a Luigi | líneas de velocidad |
| 23,0–28,6 | G. Tramo final | Cámara baja frontal → persecución | derrapes, turbo |
| 28,6–31,6 | H. Meta | Cruce de la línea; rótulo «¡META!» | destello, confeti, fuegos artificiales |
| 31,6–38,0 | I. Victoria | Órbita lenta con Mario en pose de victoria (`P_MR_win`); «¡VICTORIA!» | confeti, bloom, cierre en iris |

Los tiempos de la concha y del adelantamiento salen de la simulación (`mk/carrera.py`): el impacto ocurre cuando la concha
alcanza a Luigi y Mario cruza la meta en `T_META`. Cambiar corredores o velocidades reajusta todo.
