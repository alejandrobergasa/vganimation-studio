# Biblioteca de assets por juego

- `<juego>/extraidos/`: lo que sale de la ROM. **No se versiona**; se regenera con `python valedores.py extraer <juego>`.
- `<juego>/personalizados/`: assets propios (logos, personajes estilizados, texturas). Se versionan.
  Las **fotos de personas reales** (`psan.jpg`, `abalos.jpg`, `oscarpuente.jfif`, `pedro/cara_foto.png`) están en `.gitignore`: existen en local
  pero no se suben a Git. Quien clone el repo y quiera usar esas escenas debe poner fotos propias con esos nombres.
