# Storyboard — «¿A dónde va tu dinero público?» (vertical 1080×1920, ≈ 59 s)

**Idea**: Tom Nook (`npc_sp/model/rcn`) le cuenta a un vecino (`npc/model/16/17`) cómo se reparten 100 € de gasto público en España.
Formato móvil: render base 360×640 ×3, 30 fps (`VIDEO_VERTICAL=1`, lo fija `gasto.py`). Fuente `font/fontA`, nube `a_mes`.
**Datos**: IGAE, *Gasto público 2019-2023*, COFOG, total Administraciones Públicas 2023 (provisional): 680.952 M€.
Intereses de la deuda: 35.707 M€ (5,2 %), incluidos en «Servicios generales». Los porcentajes redondeados suman 100,1.
**Música**: reggaeton instrumental (`video/reggaeton.py`, 92 bpm, La menor, dembow) con el banco 12 del SDAT:
bombo p0, caja p1, hi-hat p2, bajo p6, punteo p3, campanilla p13. Voces: sílabas SDAT (ondas 18 y 19).

| Escena | Tiempo | Plano | Contenido |
|---|---|---|---|
| Título | 0–3,4 s | general | Vecino entra caminando; rótulo «¿A dónde va tu dinero público?» |
| Intro | 3,4–15 s | general / vecino / Nook | Saludo, «ni idea», 681.000 M€ |
| Reparto | 14–52 s | cuadro de datos + Nook/vecino abajo, cortes a primer plano | Columna de 100 € que se llena categoría a categoría con chispas; tarjeta grande con icono, valor (×3), nombre (×2) y descripción de la categoría actual; intereses rayados; resumen con las 10 filas al final; «ding» por categoría. Diálogo con texto ×2 (≤ 3 líneas) |
| Cierre | 53–59 s | general | Fuente (IGAE), chiste de la hipoteca, fundido |
