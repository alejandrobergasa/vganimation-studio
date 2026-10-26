"""Renderizado de mapas con las texturas animadas del juego (agua, flores...). Usado por motor_v2.

El juego anima el terreno cambiando la textura por otra del mismo nombre: los materiales del mapa
traen 'lakep.1', 't3_fl_b.1'... y data/fldtanime.narc guarda 'lakep.1'..'lakep.4' (y sus paletas
'lakep.2_pl'...). data/fld_anime<N>.bin dice cuánto dura cada una (9 ticks casi siempre).
mapa3d.py no se toca: aquí solo se sustituyen los materiales antes de rasterizar.
"""
import copy
import re
import struct

import ndspy.narc

import mapa3d
import ndsgfx as G
import nsbmd as N


class MundoAnim(mapa3d.Mundo):
    def __init__(self, rom_path, matriz=0):
        super().__init__(rom_path, matriz)
        archivos = ndspy.narc.NARC(self.rom.getFileByName('data/fldtanime.narc')).files
        self.anims = {}      # base -> (n_frames, [datos BTX0 donde buscarla])
        for f in archivos:
            b = bytes(f)
            sec = G.find_tex0(b) if b[:4] == b'BTX0' else None
            if not sec:
                continue
            nombres = [nm for nm, _ in G._dict3d(sec, struct.unpack_from('<H', sec, 0xE)[0], 8)]
            for nm in nombres:
                m = re.fullmatch(r'(.+)\.(\d+)', nm)
                if m:
                    n, datos = self.anims.get(m.group(1), (0, []))
                    if b not in datos:
                        datos.append(b)
                    self.anims[m.group(1)] = (max(n, int(m.group(2))), datos)

    def base_anim(self, textura):
        """Base de la animación a la que pertenece una textura 'X.1', o None."""
        m = re.fullmatch(r'(.+)\.1', textura or '')
        return m.group(1) if m and m.group(1) in self.anims else None

    def animadas(self, fila0, col0, filas, cols):
        """Bases de animación presentes en la zona: {base: n_frames}."""
        out = {}
        for r in range(filas):
            for c in range(cols):
                idx = self.matrix[(fila0 + r) * self.mw + col0 + c]
                if idx == 0xFFFF:
                    continue
                m, _ = self.chunk_model(idx)
                for mt in m.materials:
                    b = self.base_anim(mt.texture)
                    if b:
                        out[b] = self.anims[b][0]
        return out

    def render_estado(self, fila0, col0, filas, cols, estado, K=1.0, hora=12.0):
        """Como render(completo=True) pero con cada animación en el frame (estado % n_frames)."""
        tt, te, tc_t, bset = self.triangles(fila0, col0, filas, cols, True)
        luz = N.parse_arealight(self.luz_txt, hora)
        extra = []
        for b in self.animadas(fila0, col0, filas, cols):
            for d in self.anims[b][1]:
                if d not in extra:
                    extra.append(d)
        tc_t.src = list(tc_t.src) + extra

        cache_mat = {}

        def mat(m):
            b = self.base_anim(m.texture)
            if not b:
                return m
            k = estado % self.anims[b][0] + 1
            clave = (id(m), k)
            if clave not in cache_mat:
                m2 = copy.copy(m)
                m2.texture = '%s.%d' % (b, k)
                m2.palette = m.palette.replace('%s.1' % b, '%s.%d' % (b, k))
                cache_mat[clave] = m2
            return cache_mat[clave]

        allt = [(mat(m), vs, tc_t) for m, vs in tt]
        caches = {}
        for m, vs, mid in te:
            if mid not in caches:
                caches[mid] = N.TexCache([bytes(self.builds[mid])] + ([bset] if bset else []))
            allt.append((m, vs, caches[mid]))
        r = N.render_multi(allt, K=K, luz=luz, bounds=(0, -mapa3d.Y0, cols * mapa3d.CHUNK, filas * mapa3d.CHUNK),
                           con_z=True)
        return r[0]
