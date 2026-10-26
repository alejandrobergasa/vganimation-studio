import struct
CH = {}
for i in range(10): CH[0x121+i]=chr(48+i)
for i in range(26): CH[0x12B+i]=chr(65+i); CH[0x145+i]=chr(97+i)
CH.update({0x1DE:' ',0x1AB:'!',0x1AC:'?',0x1AD:',',0x1AE:'.',0x1BE:'-',0xE000:'\n',0x25BC:'\n',0x25BD:'\n'})
def decode_msg(data, raw=False):
    cnt, seed = struct.unpack_from('<HH', data, 0)
    out=[]
    for i in range(cnt):
        key=(seed*0x2FD*(i+1))&0xFFFF; k2=key|(key<<16)
        off,ln=struct.unpack_from('<II',data,4+i*8); off^=k2; ln^=k2
        key=(0x91BD3*(i+1))&0xFFFF; chars=[]
        for j in range(ln):
            c=struct.unpack_from('<H',data,off+j*2)[0]^key; key=(key+0x493D)&0xFFFF; chars.append(c)
        if raw: out.append(chars); continue
        s=''; j=0
        while j<len(chars):
            c=chars[j]
            if c==0xFFFF: break
            if c==0xFFFE: s+='{VAR}'; j+=2+chars[j+2] if j+2<len(chars) else 1; j+=1; continue
            s+=CH.get(c,'<%04X>'%c); j+=1
        out.append(s)
    return out
