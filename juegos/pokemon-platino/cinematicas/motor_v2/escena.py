"""Escena y Personaje con la sombra bien dibujada."""
from motor import escena as _e
from motor.escena import TILE, imagen, _tenir


class Personaje(_e.Personaje):
    """Arregla el glitch de la sombra: Personaje.dibujar() repintaba el suelo (que está «delante» de los pies
    en la z del mapa) sobre las filas de la sombra que caen por debajo del tile, y la última fila quedaba
    suelta y encima de todo. Aquí la sombra tiene su propia tolerancia de profundidad y el sprite solo
    repinta lo que tapa de verdad por encima de sus pies."""

    TOL_SOMBRA = 6   # px de z que el suelo puede estar por delante de los pies sin tapar la sombra

    def dibujar(self, lienzo, camx, camy):
        if not self.visible:
            return
        img = self.frame_actual()
        if self.tinte:
            img = _tenir(img, self.tinte)
        if self.alfa < 1:
            img = img.copy()
            img.putalpha(img.getchannel('A').point(lambda v: int(v * self.alfa)))
        sx, sy = self._origen(camx, camy, img)
        tapar = getattr(self.escena.mapa, 'tapar', None)
        salto = int(self.salto)
        if self.sombra and self.alfa > 0.5:
            k = imagen('efectos_mapa/017/kage.png')
            kx = sx + img.width // 2 - k.width // 2
            ky = sy + img.height - k.height // 2 - 2
            lienzo.alpha_composite(k, (kx, ky))
            if tapar:   # solo lo que está claramente delante (copas, tejados) tapa la sombra
                tapar(lienzo, camx, camy, (kx, ky, kx + k.width, ky + k.height), self.y + TILE + self.TOL_SOMBRA)
        lienzo.alpha_composite(img, (sx, sy - salto))
        for e, dx, dy in self.encima:
            lienzo.alpha_composite(e, (sx + img.width // 2 - e.width // 2 + dx, sy - salto + dy))
        if tapar:   # la caja acaba en los pies: por debajo no hay sprite que tapar y estaría la sombra
            tapar(lienzo, camx, camy, (sx - 8, sy - salto - 2 - 24, sx + img.width + 8, sy + img.height),
                  self.y + TILE)


class Escena(_e.Escena):
    def personaje(self, sprite, tx, ty, mira='abajo', **kw):
        p = Personaje(self, sprite, tx, ty, mira, **kw)
        self.personajes.append(p)
        return p

    def objeto(self, img, tx, ty, sombra=False, visible=True):
        if isinstance(img, str):
            img = imagen(img)
        p = Personaje(self, 'objeto', tx, ty, 'abajo', sombra=sombra, frames=[img] * 16)
        p.pose = img
        p.visible = visible
        self.personajes.append(p)
        return p
