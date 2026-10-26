"""Simulación del paseo de Mario por el 1-1 (60 Hz). Mario es un autómata: corre, salta pozos/obstáculos/enemigos, coge monedas."""
import numpy as np

VX, G, VY0 = 1.5, 0.35, -6.8          # px por tick de 60 Hz
GOOMBA_V = 0.3
CLEAR_KOOPA = 46                       # a qué distancia salta sobre un koopa
STOMP_AT = 60                          # a qué distancia salta para pisar un goomba


class Enemy:
    def __init__(self, kind, tx, ty):
        self.kind, self.x, self.y = kind, tx * 16 + 8, (ty + 1) * 16
        self.alive, self.squash, self.active = True, 0, False


def run(w, ticks_max=60 * 75):
    foes = [Enemy('g', x, y) for x, y in w.goombas] + [Enemy('k', x, y) for x, y in w.koopas]
    x, y = 40.0, float(w.ground(40, 300))
    vy, air, facing = 0.0, False, 1
    coins = {c: True for c in w.coins}
    frames, events, ncoin = [], [], 0
    pole_x = w.pole[0] * 16 + 8
    state, st_t, slide_y = 'run', 0, 0
    jump_t = 0
    camy = 336.0
    for t in range(ticks_max):
        cam = max(0, min(x - 100, w.W * 16 - 256))
        camy += (max(0.0, min(336.0, y - 76)) - camy) * 0.15
        ev = []
        for e in foes:
            if not e.active and e.x < cam + 256 + 24: e.active = True
            if e.active and e.alive and e.squash == 0:
                gy = w.ground(e.x, e.y - 12, 40)
                if gy is None: e.y += 3
                else: e.y = gy if gy - e.y < 6 else e.y + 3
                if e.y < w.H * 16 + 40 and gy is not None or e.y < 600: e.x -= GOOMBA_V if e.kind == 'g' else 0.4
            if e.squash:
                e.squash += 1
                if e.squash > 30: e.alive = False
        if state == 'run':
            x += VX
            # ¿salto?
            if not air:
                gy = w.ground(x, y - 12, 30)
                if gy is None or gy - y > 6:
                    vy, air = VY0, True; ev.append('jump')
                else:
                    y = gy if abs(gy - y) <= 8 else y
                    jump = False
                    for dx in range(8, 34, 2):
                        g2 = w.ground(x + dx, y - 22, 40)
                        if g2 is not None and g2 < y - 9: jump = True
                    for dx in range(4, 16, 3):                         # pozo: salta en el borde
                        g2 = w.ground(x + dx, y - 12, 40)
                        if g2 is None or g2 > y + 20: jump = True
                    for e in foes:
                        if e.active and e.alive and e.squash == 0 and abs(e.y - y) < 20:
                            d = e.x - x
                            if (e.kind == 'g' and STOMP_AT - 2 <= d <= STOMP_AT) or (e.kind == 'k' and CLEAR_KOOPA - 2 <= d <= CLEAR_KOOPA):
                                jump = True
                            if 4 <= d <= 22: jump = True                  # emergencia: salta ya
                    if jump:
                        vy, air = VY0, True; ev.append('jump')
            if air:
                vy += G; y += vy
                if vy < 0 and any(w.solid[max(0, int(y) - 33):max(0, int(y) - 29), int(xx)].any() for xx in (x - 4, x, x + 4)):
                    vy = 0.6; ev.append('bump')                      # golpea un bloque con la cabeza
                if vy >= 0:
                    for xx in (x - 4, x, x + 4):
                        gy = w.ground(xx, y - vy - 2, int(vy) + 4)
                        if gy is not None and gy >= y - vy - 2:
                            y = gy; vy, air = 0.0, False; ev.append('land'); break
                if y > w.H * 16 + 60:
                    events.append((t, 'FALL', x)); break
                for e in foes:
                    if e.active and e.alive and e.squash == 0 and abs(e.x - x) < 14 and e.y - 22 < y < e.y + 4 and vy > 0 and e.kind == 'g':
                        e.squash = 1; vy = -4.2; ev.append('stomp')
            for e in foes:
                if e.active and e.alive and e.squash == 0 and abs(e.x - x) < 9 and e.y - 20 < y and y - 26 < e.y and not (air and vy > 0 and y < e.y - 6):
                    events.append((t, 'HIT ' + e.kind, x))
            # monedas
            for c in list(coins):
                if coins[c] and abs((c[0] * 16 + 8) - x) < 12 and c[1] * 16 < y + 2 and c[1] * 16 + 16 > y - 30:
                    coins[c] = False; ncoin += 1; ev.append('coin')
            if x >= pole_x - 10:
                state, st_t, y0 = 'pole', 0, y
                ev.append('flag')
        elif state == 'pole':
            st_t += 1; x = pole_x - 6
            base = w.pole[1] * 16 + w.pole[2] * 16 - 10          # base del mástil
            if st_t > 10: y = min(base - 0, y + 1.8) if y < base else base
            air = False
            if y >= base and st_t > 30: state, st_t = 'walk', 0; ev.append('fanfare')
        elif state == 'walk':
            st_t += 1
            x += 1.0 if st_t > 20 else 0
            if x > 264.5 * 16: events.append((t, 'END', x)); frames.append(dict(t=t, x=x, y=y, state=state, air=air, vy=vy, ncoin=ncoin, ev=ev, cam=cam, camy=camy, st=st_t, foes=[], coins=[])); break
        frames.append(dict(t=t, x=x, y=y, state=state, air=air, vy=vy, ncoin=ncoin, ev=ev, cam=cam, camy=camy, st=st_t,
                           foes=[(e.kind, e.x, e.y, e.squash) for e in foes if e.alive and e.active],
                           coins=[c for c in coins if coins[c]]))
    return frames, events


if __name__ == '__main__':
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import world, collections
    w = world.get(); fr, ev = run(w)
    print(len(fr), 'ticks =', len(fr) / 60, 's', ev[:20])
    print(collections.Counter(e for f in fr for e in f['ev']), 'monedas', fr[-1]['ncoin'])
