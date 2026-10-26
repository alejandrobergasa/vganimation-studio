"""Reproduce la música y los efectos de sonido de Platino (SSEQ del sound_data.sdat) a audio PCM.

El juego no trae audio grabado: la música y los efectos son secuencias tipo MIDI (SSEQ) que tocan
instrumentos (SBNK) hechos con muestras (SWAR/SWAV). Aquí se interpreta la secuencia a 192 pasos por
segundo (el «sound frame» de la DS, 5,2 ms) con las mismas fórmulas de envolvente, volumen y tono
que el driver de Nintendo, y luego se sintetiza cada nota con numpy.

Uso:  python sonido.py <rom> <SEQ_NOMBRE> <salida.wav> [segundos]
      python sonido.py <rom> --lista            (nombres de todas las secuencias)
"""
import functools
import math
import struct
import sys
import wave

import numpy as np
import ndspy.rom
import ndspy.soundArchive

FS = 32768                                  # frecuencia de salida (la DS mezcla a ~32,7 kHz)
FRAME = 64 * 2728 / 33513982                # 5,2095 ms: un paso del driver de sonido
ARM7_CLOCK = 16756991                       # reloj de los temporizadores de canal
MIN_DB = -723                               # décimas de dB; por debajo, silencio

_ATTACK_TBL = [0x00, 0x01, 0x05, 0x0E, 0x1A, 0x26, 0x33, 0x3F, 0x49, 0x54,
               0x5C, 0x64, 0x6D, 0x74, 0x7B, 0x7F, 0x84, 0x89, 0x8F]


def cnv_attack(a):
    return _ATTACK_TBL[0x7F - a] if a >= 0x6D else 0xFF - a


def cnv_fall(f):
    if f == 0x7F:
        return 0xFFFF
    if f == 0x7E:
        return 0x3C00
    if f < 0x32:
        return (f << 1) + 1
    return 0x1E00 // (0x7E - f)


def cnv_sust(v):
    """Volumen 0-127 -> décimas de dB (ley cuadrática, como la tabla del driver)."""
    if v <= 0:
        return -32768
    return max(MIN_DB, int(round(400 * math.log10(v / 127))))


def _sin_lfo(fase):
    """Fase 0-127 por cuarto de onda, como la tabla de seno del driver: devuelve -127..127."""
    fase &= 0x7F
    return int(round(127 * math.sin(2 * math.pi * fase / 128)))


# ====================================================================== datos del ROM

class Banco:
    def __init__(self, sdat):
        self.sdat = sdat

    @functools.lru_cache(maxsize=None)
    def muestra(self, swar_id, swav_id):
        """(float32 array, rate, loop_start | None)"""
        swav = self.sdat.waveArchives[swar_id][1].waves[swav_id]
        d = swav.data
        t = int(swav.waveType)
        if t == 0:      # PCM8
            s = np.frombuffer(d, np.int8).astype(np.float32) / 128
            ls = swav.loopOffset * 4
        elif t == 1:    # PCM16
            s = np.frombuffer(d[:len(d) // 2 * 2], '<i2').astype(np.float32) / 32768
            ls = swav.loopOffset * 2
        else:           # IMA-ADPCM
            s = _adpcm(d)
            ls = max(0, (swav.loopOffset * 4 - 4) * 2)
        rate = ARM7_CLOCK / swav.time if swav.time else swav.sampleRate
        return s, rate, (ls if swav.isLooped and ls < len(s) else None)


_IMA_STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66,
             73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408,
             449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
             2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630,
             9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794,
             32767]
_IMA_IDX = [-1, -1, -1, -1, 2, 4, 6, 8]


def _adpcm(d):
    pred, idx = struct.unpack_from('<hB', d, 0)
    idx = min(idx, 88)
    out = np.empty((len(d) - 4) * 2, np.float32)
    k = 0
    for b in d[4:]:
        for n in (b & 0xF, b >> 4):
            st = _IMA_STEP[idx]
            diff = st >> 3
            if n & 1:
                diff += st >> 2
            if n & 2:
                diff += st >> 1
            if n & 4:
                diff += st
            pred = max(-32767, min(32767, pred - diff if n & 8 else pred + diff))
            idx = max(0, min(88, idx + _IMA_IDX[n & 7]))
            out[k] = pred / 32768
            k += 1
    return out


class Sonido:
    def __init__(self, rom_path, sdat='sound_data.sdat'):
        rom = ndspy.rom.NintendoDSRom.fromFile(rom_path)
        self.sdat = ndspy.soundArchive.SDAT(rom.getFileByName(sdat))
        self.nombres = {n: i for i, (n, s) in enumerate(self.sdat.sequences) if n and s is not None}
        self.banco = Banco(self.sdat)

    def efecto(self, nombre, segundos=None):
        """Efecto de sonido (secuencia dentro de un SSAR). Audio estéreo float32 (n, 2) a FS Hz."""
        for _, ar in self.sdat.sequenceArchives:
            if ar is None:
                continue
            for n, q in ar.sequences:
                if n == nombre:
                    class _S:
                        eventsData = ar.eventsData
                        bankID = q.bankID
                        volume = q.volume
                    sbnk = self.sdat.banks[q.bankID][1]
                    return _Reproductor(self, _S, sbnk, q.firstEventOffset).tocar(segundos)
        raise KeyError(nombre)

    def efectos(self):
        return [n for _, ar in self.sdat.sequenceArchives if ar is not None for n, _q in ar.sequences]

    def secuencia(self, nombre):
        return self.sdat.sequences[self.nombres[nombre]][1]

    def renderizar(self, nombre, segundos=None, bucles=1):
        """Audio estéreo float32 (n, 2) a FS Hz. Si la secuencia tiene bucle infinito, se corta a
        'segundos' (por defecto, 'bucles' vueltas completas o 180 s)."""
        sseq = self.secuencia(nombre)
        sbnk = self.sdat.banks[sseq.bankID][1]
        return _Reproductor(self, sseq, sbnk).tocar(segundos)


# ====================================================================== secuenciador

class _Pista:
    def __init__(self, n, pc):
        self.n = n
        self.pc = pc
        self.espera = 0
        self.pila = []          # (pc de retorno, inicio de bucle, vueltas)
        self.fin = False
        self.prog = 0
        self.vol = 127
        self.expr = 127
        self.pan = 64
        self.transp = 0
        self.bend = 0
        self.bend_rango = 2
        self.mod_prof = 0
        self.mod_vel = 16
        self.mod_tipo = 0
        self.mod_rango = 1
        self.mod_retardo = 0
        self.porta = False
        self.porta_tiempo = 0
        self.porta_tecla = 60
        self.ataque = self.decay = self.sust = self.release = 0xFF
        self.espera_nota = True     # «mono»: la pista espera a que acabe cada nota
        self.tie = False
        self.cond = True
        self.canal_tie = None


class _Canal:
    """Una nota sonando. Registra, paso a paso, ganancia L/R y tono para sintetizarla después."""

    def __init__(self, pista, nd, tecla, vel, dur, paso0, muestra):
        self.pista, self.nd, self.tecla, self.vel = pista, nd, tecla, vel
        self.dur = dur
        self.paso0 = paso0
        self.muestra = muestra
        a = pista.ataque if pista.ataque != 0xFF else nd.attack
        d = pista.decay if pista.decay != 0xFF else nd.decay
        s = pista.sust if pista.sust != 0xFF else nd.sustain
        r = pista.release if pista.release != 0xFF else nd.release
        self.a, self.d, self.s, self.r = cnv_attack(a), cnv_fall(d), cnv_sust(s) << 7, cnv_fall(r)
        self.ampl = MIN_DB << 7
        self.fase_env = 0          # 0 ataque, 1 decay, 2 sustain, 3 release
        self.mod_cont = 0
        self.mod_ret = pista.mod_retardo
        self.porta_desde = None
        self.porta_pasos = 0
        self.porta_total = 0
        self.vivo = True
        self.gl, self.gr, self.tono = [], [], []    # por paso de 5,2 ms

    def soltar(self):
        if self.fase_env != 3:
            self.fase_env = 3

    def paso_envolvente(self):
        if self.fase_env == 0:
            self.ampl = -((-self.ampl * self.a) >> 8)
            if self.ampl == 0:
                self.fase_env = 1
        elif self.fase_env == 1:
            self.ampl -= self.d
            if self.ampl <= self.s:
                self.ampl = self.s
                self.fase_env = 2
        elif self.fase_env == 3:
            self.ampl -= self.r
            if self.ampl <= MIN_DB << 7:
                self.vivo = False


class _Reproductor:
    def __init__(self, son, sseq, sbnk, inicio=0):
        self.son, self.sseq, self.sbnk = son, sseq, sbnk
        self.datos = sseq.eventsData
        self.tempo = 120
        self.vol_global = 127
        self.var = [0] * 32
        self.pistas = [_Pista(0, inicio)]
        self.canales = []
        self.terminados = []
        self.ticks = 0
        self.bucle_visto = False     # la pista 0 ha vuelto atrás con un salto (bucle infinito)

    # ---------------------------------------------- lectura

    def _u8(self, p):
        return self.datos[p], p + 1

    def _vl(self, p):
        v = 0
        while True:
            b = self.datos[p]
            p += 1
            v = (v << 7) | (b & 0x7F)
            if not b & 0x80:
                return v, p

    def _arg(self, p, tipo):
        if tipo == 'u8':
            return self.datos[p], p + 1
        if tipo == 's8':
            return struct.unpack_from('<b', self.datos, p)[0], p + 1
        if tipo == 's16':
            return struct.unpack_from('<h', self.datos, p)[0], p + 2
        if tipo == 'u16':
            return struct.unpack_from('<H', self.datos, p)[0], p + 2
        if tipo == 'vl':
            return self._vl(p)

    # ---------------------------------------------- instrumentos

    def _nota_def(self, prog, tecla):
        if prog >= len(self.sbnk.instruments):
            return None
        ins = self.sbnk.instruments[prog]
        if ins is None:
            return None
        if hasattr(ins, 'noteDefinition'):
            return ins.noteDefinition
        if hasattr(ins, 'firstPitch'):
            i = tecla - ins.firstPitch
            if 0 <= i < len(ins.noteDefinitions):
                return ins.noteDefinitions[i]
            return None
        for r in ins.regions:
            if tecla <= r.lastPitch:
                return r.noteDefinition
        return None

    def _nota(self, pista, tecla, vel, dur):
        tecla = max(0, min(127, tecla + pista.transp))
        nd = self._nota_def(pista.prog, tecla)
        if nd is None:
            return
        if pista.tie and pista.canal_tie is not None and pista.canal_tie.vivo:
            c = pista.canal_tie       # en modo tie la nota sigue en el mismo canal y cambia de tono
            c.porta_desde = c.tecla
            c.tecla, c.vel = tecla, vel
            c.porta_pasos = 0
            c.porta_total = max(1, dur)
            return
        tipo = int(nd.type)
        if tipo == 1:
            try:
                swar = self.sbnk.waveArchiveIDs[nd.waveArchiveIDID]
                muestra = self.son.banco.muestra(swar, nd.waveID)
            except Exception:
                return
        else:
            muestra = ('psg', nd.dutyCycle & 7) if tipo == 2 else ('ruido', 0)
        c = _Canal(pista, nd, tecla, vel, (-1 if pista.tie else dur), len(self._pasos_marca), muestra)
        if pista.porta:
            c.porta_desde = pista.porta_tecla
            c.porta_total = max(1, pista.porta_tiempo or dur)
        pista.porta_tecla = tecla
        self.canales.append(c)
        if pista.tie:
            pista.canal_tie = c

    # ---------------------------------------------- un tick de secuencia

    def _tick_pista(self, t):
        if t.fin:
            return
        if t.espera > 0:
            t.espera -= 1
            if t.espera > 0:
                return
        guardia = 0
        while t.espera == 0 and not t.fin:
            guardia += 1
            if guardia > 20000:            # secuencia que salta en bucle sin esperar nunca: se corta la pista
                t.fin = True
                break
            cmd = self.datos[t.pc]
            t.pc += 1
            ejecutar = t.cond
            t.cond = True
            # A0 random / A1 variable: el valor del último argumento viene de otra fuente
            fuente = None
            if cmd == 0xA0:
                cmd = self.datos[t.pc]
                t.pc += 1
                fuente = 'rand'
            elif cmd == 0xA1:
                cmd = self.datos[t.pc]
                t.pc += 1
                fuente = 'var'
            elif cmd == 0xA2:
                t.cond = bool(getattr(self, 'flag', True))
                continue

            def ultimo(tipo):
                if fuente == 'rand':
                    mn, _ = self._arg(t.pc, 's16')
                    mx, _ = self._arg(t.pc + 2, 's16')
                    t.pc += 4
                    return int(np.random.randint(mn, mx + 1))
                if fuente == 'var':
                    v = self.datos[t.pc]
                    t.pc += 1
                    return self.var[v % 32]
                v, t.pc = self._arg(t.pc, tipo)
                return v

            if cmd < 0x80:
                vel = self.datos[t.pc]
                t.pc += 1
                dur = ultimo('vl')
                if ejecutar:
                    self._nota(t, cmd, vel, dur)
                    if t.espera_nota:
                        t.espera = dur
                continue
            if cmd == 0x80:
                v = ultimo('vl')
                if ejecutar:
                    t.espera = v
            elif cmd == 0x81:
                v = ultimo('vl')
                if ejecutar:
                    t.prog = v & 0xFFFF
            elif cmd == 0x93:
                n = self.datos[t.pc]
                off = int.from_bytes(self.datos[t.pc + 1:t.pc + 4], 'little')
                t.pc += 4
                if ejecutar:
                    self.pistas.append(_Pista(n, off))
            elif cmd == 0x94:
                off = int.from_bytes(self.datos[t.pc:t.pc + 3], 'little')
                t.pc += 3
                if ejecutar:
                    if off < t.pc and t.n == self.pistas[0].n and t is self.pistas[0]:
                        self.bucle_visto = True
                    t.pc = off
            elif cmd == 0x95:
                off = int.from_bytes(self.datos[t.pc:t.pc + 3], 'little')
                t.pc += 3
                if ejecutar:
                    t.pila.append(('call', t.pc))
                    t.pc = off
            elif 0xB0 <= cmd <= 0xBD:
                vid = self.datos[t.pc]
                t.pc += 1
                v = ultimo('s16')
                if ejecutar:
                    i = vid % 32
                    if cmd == 0xB0: self.var[i] = v
                    elif cmd == 0xB1: self.var[i] += v
                    elif cmd == 0xB2: self.var[i] -= v
                    elif cmd == 0xB3: self.var[i] *= v
                    elif cmd == 0xB4: self.var[i] = int(self.var[i] / v) if v else self.var[i]
                    elif cmd == 0xB5: self.var[i] = self.var[i] << v if v >= 0 else self.var[i] >> -v
                    elif cmd == 0xB6: self.var[i] = int(np.random.randint(0, v + 1)) if v > 0 else 0
                    elif cmd == 0xB8: self.flag = self.var[i] == v
                    elif cmd == 0xB9: self.flag = self.var[i] >= v
                    elif cmd == 0xBA: self.flag = self.var[i] > v
                    elif cmd == 0xBB: self.flag = self.var[i] <= v
                    elif cmd == 0xBC: self.flag = self.var[i] < v
                    elif cmd == 0xBD: self.flag = self.var[i] != v
            elif 0xC0 <= cmd <= 0xD6:
                tipo = 's8' if cmd in (0xC3, 0xC4) else 'u8'
                v = ultimo(tipo)
                if not ejecutar:
                    continue
                if cmd == 0xC0: t.pan = v
                elif cmd == 0xC1: t.vol = v
                elif cmd == 0xC2: self.vol_global = v
                elif cmd == 0xC3: t.transp = v
                elif cmd == 0xC4: t.bend = v
                elif cmd == 0xC5: t.bend_rango = v
                elif cmd == 0xC7: t.espera_nota = bool(v)
                elif cmd == 0xC8:
                    t.tie = bool(v)
                    if not t.tie and t.canal_tie is not None:
                        t.canal_tie.soltar()
                        t.canal_tie = None
                elif cmd == 0xC9:
                    t.porta_tecla = v + t.transp
                    t.porta = True
                elif cmd == 0xCA: t.mod_prof = v
                elif cmd == 0xCB: t.mod_vel = v
                elif cmd == 0xCC: t.mod_tipo = v
                elif cmd == 0xCD: t.mod_rango = v
                elif cmd == 0xCE: t.porta = bool(v)
                elif cmd == 0xCF: t.porta_tiempo = v
                elif cmd == 0xD0: t.ataque = v
                elif cmd == 0xD1: t.decay = v
                elif cmd == 0xD2: t.sust = v
                elif cmd == 0xD3: t.release = v
                elif cmd == 0xD4: t.pila.append(('loop', t.pc, v))
                elif cmd == 0xD5: t.expr = v
            elif cmd in (0xE0, 0xE1, 0xE3):
                v = ultimo('u16' if cmd == 0xE1 else 's16')
                if ejecutar:
                    if cmd == 0xE0: t.mod_retardo = v
                    elif cmd == 0xE1: self.tempo = v
            elif cmd == 0xFC:
                if ejecutar and t.pila and t.pila[-1][0] == 'loop':
                    _, ini, n = t.pila[-1]
                    if n == 0:                 # bucle infinito
                        if t is self.pistas[0]:
                            self.bucle_visto = True
                        t.pc = ini
                    elif n > 1:
                        t.pila[-1] = ('loop', ini, n - 1)
                        t.pc = ini
                    else:
                        t.pila.pop()
            elif cmd == 0xFD:
                if ejecutar:
                    while t.pila and t.pila[-1][0] != 'call':
                        t.pila.pop()
                    if t.pila:
                        t.pc = t.pila.pop()[1]
                    else:
                        t.fin = True
            elif cmd == 0xFE:
                t.pc += 2
            elif cmd == 0xFF:
                if ejecutar:
                    t.fin = True
            else:
                t.fin = True       # comando desconocido: se para la pista

    def _tick(self):
        for t in list(self.pistas):
            self._tick_pista(t)
        for c in self.canales:
            if c.dur > 0:
                c.dur -= 1
                if c.dur == 0:
                    c.soltar()
            if c.porta_desde is not None:
                c.porta_pasos += 1
        self.ticks += 1

    # ---------------------------------------------- paso de 5,2 ms: envolventes, LFO y mezcla

    def _paso_canales(self):
        if len(self.canales) > 32:          # la DS sólo tiene 16 canales: se sueltan las notas más antiguas
            for c in self.canales[:-32]:
                c.soltar()
        vivos = []
        for c in self.canales:
            t = c.pista
            c.paso_envolvente()
            if not c.vivo:
                self.terminados.append(c)
                continue
            # LFO
            lfo = 0
            if t.mod_prof:
                if c.mod_ret > 0:
                    c.mod_ret -= 1
                else:
                    c.mod_cont = (c.mod_cont + (t.mod_vel << 6)) & 0x7FFF
                    lfo = _sin_lfo(c.mod_cont >> 8) * t.mod_prof * t.mod_rango
            db = (c.ampl >> 7) + cnv_sust(c.vel) + cnv_sust(t.vol) + cnv_sust(t.expr) \
                + cnv_sust(self.vol_global) + cnv_sust(self.sseq.volume)
            if t.mod_tipo == 1:
                db += lfo >> 8
            db = max(MIN_DB, db)
            g = 10 ** (db / 200) if db > MIN_DB else 0.0
            pan = t.pan + c.nd.pan - 64
            if t.mod_tipo == 2:
                pan += lfo >> 8
            pan = max(0, min(127, pan))
            c.gl.append(g * (127 - pan) / 127)
            c.gr.append(g * pan / 127)
            # tono en 1/64 de semitono respecto a la nota raíz del instrumento
            tecla = c.tecla
            if c.porta_desde is not None and c.porta_pasos < c.porta_total:
                tecla = c.porta_desde + (c.tecla - c.porta_desde) * c.porta_pasos / c.porta_total
            p = (tecla - c.nd.pitch) * 64 + (t.bend * t.bend_rango * 64) / 128
            if t.mod_tipo == 0:
                p += lfo / 256 / 2
            c.tono.append(p)
            vivos.append(c)
        self.canales = vivos

    def tocar(self, segundos=None):
        self._pasos_marca = []
        acum = 0
        max_pasos = int((segundos or 180) / FRAME)
        for paso in range(max_pasos):
            acum += self.tempo
            while acum >= 240:
                acum -= 240
                self._tick()
            self._paso_canales()
            self._pasos_marca.append(paso)
            todas_fin = all(t.fin for t in self.pistas)
            if segundos is None and (todas_fin or self.bucle_visto) and not self.canales:
                break
            if segundos is None and self.bucle_visto and paso * FRAME > 30:
                break
        return self._sintetizar(len(self._pasos_marca))

    def _sintetizar(self, pasos):
        n = int(pasos * FRAME * FS) + 1
        out = np.zeros((n, 2), np.float32)
        spf = FRAME * FS
        for c in self.terminados + self.canales:
            k = len(c.gl)
            if k == 0:
                continue
            i0 = int(c.paso0 * spf)
            m = min(int(k * spf), n - i0)
            if m <= 0:
                continue
            x = np.arange(m) / spf                      # en pasos
            gl = np.interp(x, np.arange(k), c.gl).astype(np.float32)
            gr = np.interp(x, np.arange(k), c.gr).astype(np.float32)
            tono = np.interp(x, np.arange(k), c.tono)
            ratio = 2 ** (tono / 768)
            if isinstance(c.muestra[0], str) and c.muestra[0] == 'psg':
                f = 440 * ratio
                fase = np.cumsum(f / FS)
                duty = (c.muestra[1] + 1) / 8
                s = np.where((fase % 1) < duty, 1.0, -1.0).astype(np.float32) * 0.5
            elif isinstance(c.muestra[0], str):
                f = 440 * ratio * 8
                idx = np.cumsum(f / FS).astype(np.int64)
                ruido = np.random.RandomState(1).uniform(-1, 1, int(idx[-1]) + 2).astype(np.float32)
                s = ruido[idx] * 0.5
            else:
                datos, rate, ls = c.muestra
                pos = np.concatenate([[0.0], np.cumsum(rate * ratio / FS)[:-1]])
                L = len(datos)
                if ls is None:
                    m2 = int(np.searchsorted(pos, L - 1))
                    pos, gl, gr = pos[:m2], gl[:m2], gr[:m2]
                    if len(pos) == 0:
                        continue
                    r = min(64, len(pos))                   # sin bucle: rampa al final para que no chasque
                    gl, gr = gl.copy(), gr.copy()
                    gl[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
                    gr[-r:] *= np.linspace(1, 0, r, dtype=np.float32)
                else:
                    lon = L - ls
                    if lon <= 1:
                        pos = np.minimum(pos, L - 1)
                    else:
                        pos = np.where(pos >= L, ls + np.mod(pos - ls, lon), pos)
                i = pos.astype(np.int64)
                fr = (pos - i).astype(np.float32)
                i2 = i + 1
                if ls is not None:
                    i2 = np.where(i2 >= L, ls, i2)
                i2 = np.minimum(i2, L - 1)
                s = datos[i] * (1 - fr) + datos[i2] * fr
            m2 = len(s)
            out[i0:i0 + m2, 0] += s * gl[:m2]
            out[i0:i0 + m2, 1] += s * gr[:m2]
        return out


class _SeqVacia:
    eventsData = b'\xff'
    volume = 127


class _ReproductorNotas(_Reproductor):
    """Toca una lista de notas sueltas (como un MIDI) con los instrumentos de un banco del juego, con las mismas
    envolventes, volúmenes y síntesis que las secuencias. Un paso = 5,2 ms."""

    def __init__(self, son, sbnk, notas):
        super().__init__(son, _SeqVacia(), sbnk)
        self.notas = sorted(notas, key=lambda n: n[0])

    def tocar(self, segundos=None):
        self._pasos_marca = []
        pistas = {}
        fin = max((n[0] + n[1] for n in self.notas), default=0) + 2
        total = int((segundos or fin) / FRAME)
        k = 0
        for paso in range(total):
            while k < len(self.notas) and self.notas[k][0] <= paso * FRAME:
                t, dur, tecla, vel, prog, pan, vol = self.notas[k]
                clave = (prog, pan, vol)
                if clave not in pistas:
                    p = _Pista(len(pistas), 0)
                    p.prog, p.pan, p.vol, p.fin = prog, pan, vol, True
                    pistas[clave] = p
                self._nota(pistas[clave], int(tecla), int(vel), max(1, int(round(dur / FRAME))))
                k += 1
            for c in self.canales:
                if c.dur > 0:
                    c.dur -= 1
                    if c.dur == 0:
                        c.soltar()
            self._paso_canales()
            self._pasos_marca.append(paso)
        return self._sintetizar(len(self._pasos_marca))


def tocar_notas(son, banco, notas, segundos=None):
    """Audio estéreo (n, 2) a FS Hz de 'notas': [(inicio_s, dur_s, tecla_midi, velocidad 0-127, programa,
    pan 0-127, volumen 0-127), ...] tocadas con el banco 'banco' (nombre, p. ej. 'BANK_BGM_FIELD', o número)."""
    if isinstance(banco, str):
        banco = next(i for i, (n, b) in enumerate(son.sdat.banks) if n == banco)
    return _ReproductorNotas(son, son.sdat.banks[banco][1], notas).tocar(segundos)


def guardar_wav(ruta, audio, fs=FS):
    a = np.clip(audio, -1, 1)
    with wave.open(ruta, 'wb') as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(fs)
        w.writeframes((a * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    son = Sonido(sys.argv[1])
    if sys.argv[2] == '--lista':
        print('\n'.join(sorted(son.nombres)))
        sys.exit()
    seg = float(sys.argv[4]) if len(sys.argv) > 4 else None
    a = son.renderizar(sys.argv[2], seg)
    pico = np.abs(a).max()
    print('%.1f s, pico %.3f' % (len(a) / FS, pico))
    guardar_wav(sys.argv[3], a / max(pico, 1e-6) * 0.9)
