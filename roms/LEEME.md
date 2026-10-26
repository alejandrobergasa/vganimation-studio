# Librería de ROMs

Copia aquí tus ROMs de Nintendo DS (`.nds`). Se reconocen por el código de la cabecera, así que el nombre del fichero da igual:

| Juego | Código | Id |
|---|---|---|
| Animal Crossing: Wild World (Europa) | `ADMP` | `animal-crossing` |
| New Super Mario Bros. (Europa, español) | `A2DP` | `nsmb` |
| Mario Kart DS (Europa) | `AMCP` | `mkds` |
| Pokémon Platino (`CPUS` español, y otras regiones) | `CPUS`… | `pokemon-platino` |

`python valedores.py roms` muestra lo que se ha encontrado. Las ROMs **no se suben a Git** y nunca se modifican.
Después: `python valedores.py extraer` para sacar los assets a `biblioteca/<juego>/extraidos/`.
