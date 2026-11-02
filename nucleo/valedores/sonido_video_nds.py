"""Audio SADL nativo (IMA ADPCM y Procyon), mono o estéreo intercalado."""
import struct
import numpy as np
from .recursos_nds import lectores


def sadl(datos, segundos=None):
    if len(datos)<256 or datos[:4]!=b'sadl':
        raise ValueError('Cabecera SADL no válida')
    canales,cod=datos[0x32],datos[0x33]
    frecuencia={2:16364,4:32728}.get(cod&6)
    if canales not in (1,2) or frecuencia is None or cod&0xF0 not in (0x70,0xB0):
        raise ValueError('Canales, frecuencia o compresión SADL no compatibles')
    fin=struct.unpack_from('<I',datos,0x40)[0]
    if not 256<=fin<=len(datos):
        raise ValueError('Longitud SADL fuera de límites')
    n_bloques=(fin-256)//(16*canales)
    por_bloque=32 if cod&0xF0==0x70 else 30
    if segundos is not None:
        if segundos<=0:raise ValueError('La duración de audio debe ser positiva')
        n_bloques=min(n_bloques,int(np.ceil(segundos*frecuencia/por_bloque)))
    salidas=[]
    for ch in range(canales):
        bloques=[datos[256+(i*canales+ch)*16:256+(i*canales+ch+1)*16] for i in range(n_bloques)]
        if cod&0xF0==0x70:
            # Estado inicial cero, persistente entre los bloques de un canal.
            sonido=lectores()[2]
            salida=sonido._adpcm(b'\0\0\0\0'+b''.join(bloques))
        else:
            coefs=((0,0),(60,0),(115,-52),(98,-55),(122,-60))
            muestras=[]
            h1=h2=0
            for bloque in bloques:
                cab=bloque[15]^128
                indice=cab>>4
                if indice>=len(coefs):raise ValueError('Predictor Procyon fuera de límites')
                a,b=coefs[indice]
                escala=12-(cab&15)
                for valor in bloque[:15]:
                    valor^=128
                    for nibble in (valor&15,valor>>4):
                        s=(nibble if nibble<8 else nibble-16)*4096
                        s=s>>escala if escala>=0 else s<<-escala
                        s=int((h1*a+h2*b+32)/64)+s*64
                        h2,h1=h1,s
                        pcm=max(-32768,min(32767,int((s+32)/64)))
                        muestras.append(pcm/32768)
            salida=np.asarray(muestras,dtype='float32')
        salidas.append(salida)
    if not salidas[0].size:raise ValueError('SADL sin muestras')
    salida=np.stack(salidas,axis=1)
    if segundos is not None:salida=salida[:round(segundos*frecuencia)]
    return salida,frecuencia
