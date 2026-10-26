"""Lectores comunes de recursos DS, sin modificar las ROMs.

La extracción conserva siempre el fichero original. Estos lectores sólo abren
contenedores cuyo índice completo se puede validar; nunca adivinan offsets.
"""
import struct


LIMITE = 64 * 1024 * 1024


def u32(datos, offset=0):
    return struct.unpack_from('<I', datos, offset)[0]


def descomprimir(datos, level5=False):
    """(bytes, método). LZ10/LZ11, RLE BIOS y envoltorios LZ77/Level-5.

    Devuelve el original cuando no tiene cabecera de compresión. Una cabecera
    reconocida pero dañada produce ValueError, para dejar constancia en el catálogo.
    """
    datos = bytes(datos)
    prefijo = ''
    if datos.startswith(b'LZ77'):
        datos = datos[4:]
        prefijo = 'LZ77/'
    elif level5 and len(datos) >= 8 and u32(datos) in (1, 2, 3, 4):
        # Level-5 antepone un u32 al flujo de la BIOS.
        datos = datos[4:]
        prefijo = 'Level-5/'
    if len(datos) < 4 or datos[0] not in (0x10, 0x11, 0x30):
        if prefijo:
            raise ValueError('Compresión del envoltorio aún no compatible')
        return datos, None
    tipo = datos[0]
    tam = int.from_bytes(datos[1:4], 'little')
    pos = 4
    if tam == 0 and tipo == 0x11:
        tam, pos = u32(datos, 4), 8
    if not 0 < tam <= LIMITE:
        raise ValueError('Tamaño descomprimido fuera de límites')
    salida = bytearray()
    try:
        while len(salida) < tam:
            marcas = datos[pos]
            pos += 1
            if tipo == 0x30:
                n = (marcas & 127) + (3 if marcas & 128 else 1)
                n = min(n, tam - len(salida))
                if marcas & 128:
                    salida.extend(bytes([datos[pos]]) * n)
                    pos += 1
                else:
                    if pos + n > len(datos):
                        raise ValueError('RLE truncado')
                    salida.extend(datos[pos:pos + n])
                    pos += n
                continue
            for bit in range(7, -1, -1):
                if len(salida) >= tam:
                    break
                if not marcas & (1 << bit):
                    salida.append(datos[pos])
                    pos += 1
                    continue
                a, b = datos[pos:pos + 2]
                pos += 2
                if tipo == 0x10:
                    n, distancia = (a >> 4) + 3, ((a & 15) << 8 | b) + 1
                elif a >> 4 == 0:
                    c = datos[pos]
                    pos += 1
                    n = ((a & 15) << 4 | b >> 4) + 0x11
                    distancia = ((b & 15) << 8 | c) + 1
                elif a >> 4 == 1:
                    c, d = datos[pos:pos + 2]
                    pos += 2
                    n = ((a & 15) << 12 | b << 4 | c >> 4) + 0x111
                    distancia = ((c & 15) << 8 | d) + 1
                else:
                    n, distancia = (a >> 4) + 1, ((a & 15) << 8 | b) + 1
                if distancia > len(salida):
                    raise ValueError('Referencia LZ anterior al inicio del flujo')
                for _ in range(min(n, tam - len(salida))):
                    salida.append(salida[-distancia])
    except (IndexError, struct.error) as exc:
        raise ValueError('Flujo comprimido truncado') from exc
    # Algunos juegos rellenan los bloques con FF o ceros.
    if len(datos) - pos > 16 and any(x not in (0, 255) for x in datos[pos:]):
        raise ValueError('Datos adicionales tras el flujo; puede ser un contenedor')
    nombre = {0x10: 'LZ10', 0x11: 'LZ11', 0x30: 'RLE'}[tipo]
    return bytes(salida), prefijo + nombre


def tabla_pares(datos, relativo=0):
    """Tabla u32 cantidad + (offset, tamaño); PAC y archivos de Mario Party.

    En Mario Party DS el offset se mide desde el final del contador (relativo=4).
    None significa que el fichero no es una tabla válida, no una extracción vacía.
    """
    if len(datos) < 12:
        return None
    n = u32(datos)
    if not 0 < n <= 10000 or 4 + 8 * n > len(datos):
        return None
    entradas = []
    fin = 4 + 8 * n
    anterior = fin
    for i in range(n):
        off, tam = struct.unpack_from('<II', datos, 4 + 8 * i)
        off += relativo
        if tam and (off < fin or off + tam > len(datos)):
            return None
        if tam and off < anterior:
            return None
        entradas.append(('%05d.bin' % i, off, bytes(datos[off:off + tam])))
        if tam:
            anterior = off + tam
    return entradas


def paquete_inazuma(cabecera, datos):
    """PKH PackNum + PKB: tipos 0 (offset/tamaño), 2 y 3 (bloques fijos)."""
    if not cabecera.startswith(b'PackNum ') or len(cabecera) < 0x30:
        raise ValueError('Cabecera PKH no compatible')
    tipo = struct.unpack_from('<H', cabecera, 0x12)[0]
    n = struct.unpack_from('<H', cabecera, 0x16)[0]
    bloque = u32(cabecera, 0x1C)
    if tipo not in (0, 2, 3) or not n:
        raise ValueError('Tipo PKH no compatible: %d' % tipo)
    paso = {0: 12, 2: 8, 3: 4}[tipo]
    if 0x30 + n * paso > len(cabecera):
        raise ValueError('Tabla PKH truncada')
    salida = []
    for i in range(n):
        ident = u32(cabecera, 0x30 + i * paso)
        if tipo == 0:
            off, tam = struct.unpack_from('<II', cabecera, 0x34 + 12 * i)
        else:
            off, tam = i * bloque, bloque
        if off + tam > len(datos):
            raise ValueError('Miembro PKB fuera de límites')
        salida.append(('%05d_%08x.pac' % (i, ident), off, bytes(datos[off:off + tam])))
    return salida


def scripts_phoenix(datos):
    """mes_all.bin guarda cantidad, offsets y longitudes intercalados."""
    entradas = tabla_pares(datos)
    if entradas is None:
        raise ValueError('Índice mes_all.bin no válido')
    return entradas
