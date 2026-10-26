---
name: recursos-mkds
description: Explora y cataloga los recursos de la ROM de Mario Kart DS (pilotos, karts, circuitos, objetos, fuentes, audio) con hojas de contactos y catálogos. Usar cuando haya que elegir o comprobar un recurso, regenerar las hojas o localizar un efecto de sonido; para montar el vídeo usa cinematica-mkds.
---

# Extraer y catalogar assets de Mario Kart DS

La ROM de Mario Kart DS (`roms/`) es sólo lectura. Los modelos no se copian a disco: se leen bajo demanda con
`juegos/mkds/tools/mkds/modelos.py` (NitroFS → `.carc` = NARC con LZ10 → NSBMD/NSBTX/NSBCA). Aquí sólo se generan **hojas y catálogos** en
`biblioteca/mkds/extraidos/` (regenerable).

```powershell
python valedores.py extraer mkds                      # todo (≈ 1-3 min; audio es lo más lento)
cd juegos/mkds && python -I tools/extraer_mkds.py --solo circuitos      # pilotos, karts, objetos, circuitos, fuentes, audio
```

Salidas: `pilotos/hoja_pilotos.png`, `karts/hoja_karts.png`, `objetos/hoja_objetos.png`, `circuitos/hoja_circuitos.png` +
`catalogo.json`, `fuentes/fuentes.png`, `audio/catalogo_audio.csv`. **Abrir las hojas y mirarlas** antes de elegir.

## Mapa de la ROM (`data/`)

- `KartModelSub.carc` pilotos sentados (`P_xx.nsbmd/nsbtx` + animaciones `drive`, `win`, `lose`, `spin`); `KartModelMain/A/B/Menu.carc` karts (`kart_xx_a|b|c`).
- `Course/<nombre>.carc` geometría, colisión (`.kcl`), mapa (`.nkm`), objetos `MapObj/`; `Course/<nombre>Tex.carc` texturas (algunos circuitos las llevan dentro del modelo).
- `MainRace.carc` objetos y efectos de carrera (`Item/it_*`, `effect/bombcore`, sombra, caja de objetos); `MapObj.carc`.
- `Main2D.carc` fuentes (`marioFont.NFTR` título, `LC_Font_m/s.NFTR`). `Sound/sound_data.sdat` sin símbolos (ver abajo).
- `Scene/*.carc`: títulos, créditos, podio (no explorados aún).

## Audio

La SDAT no tiene nombres. 76 secuencias de música (`audio.bgm(i)`) y 5 archivos SSAR de efectos (`audio.sfx_id(ssar, k)`).
`catalogo_audio.csv` da duración, pico y rms de cada una (pico > 3 = secuencia desbocada: descartar). Para elegir: filtrar por duración
(< 1,5 s suelen ser efectos de interfaz/golpes; > 20 s bucles de música) y renderizar a WAV las candidatas para confirmar por forma de onda.
Anotar los ids elegidos en el guion y en `juegos/mkds/CONOCIMIENTO.md`.
