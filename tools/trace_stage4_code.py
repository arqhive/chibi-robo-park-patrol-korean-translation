"""Read-only reference index and annotated ARM9 Thumb disassembly for stage 4."""
import json
import struct
import hashlib
from collections import defaultdict
from pathlib import Path
import capstone
from inspect_roms import ROOT, save
from investigate_stage4 import thumb_literal_refs

BASE=0x02000000


class Audit:
    def __init__(self):
        self.b=(ROOT/'work/extracted/jp/arm9.bin').read_bytes()
        self.md=capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_THUMB)
        self.ptrs=defaultdict(list);self.calls=defaultdict(list)
        for p in range(0,len(self.b)-3,4):self.ptrs[self.word(p)].append(p)
        for p in range(0,0x10a000,2):
            hi,lo=struct.unpack_from('<HH',self.b,p)
            if hi&0xf800!=0xf000 or lo&0xe800!=0xe800:continue
            ins=next(self.md.disasm(self.b[p:p+4],BASE+p),None)
            if ins is not None and ins.mnemonic in ['bl','blx'] and ins.op_str.startswith('#0x'):
                self.calls[int(ins.op_str[1:],16)-BASE].append(p)

    def word(self,p):return struct.unpack_from('<I',self.b,p)[0]

    def text(self,address):
        p=address-BASE
        if not 0x110000<=p<len(self.b):return None
        raw=self.b[p:p+160].split(b'\0')[0]
        try:s=raw.decode('cp932')
        except UnicodeDecodeError:return None
        return s if s and all(c.isprintable() or c in '\r\n\t' for c in s) else None

    def refs(self,p):
        pools=self.ptrs[BASE+p]
        return {'offset':p,'address_literals':pools,
                'thumb_load_candidates':[{'instruction':x,'pool':pool} for pool,rows in thumb_literal_refs(self.b,set(pools)).items() for x in rows],
                'direct_call_candidates':self.calls[p&~1]}

    def disasm(self,start,end):
        lines=[]
        for ins in self.md.disasm(self.b[start:end],BASE+start):
            p=ins.address-BASE;comment=''
            w=struct.unpack_from('<H',self.b,p)[0]
            if w&0xf800==0x4800:
                at=((p+4)&~3)+(w&255)*4
                v=self.word(at);comment=f' ; pool +0x{at:x} = 0x{v:x}'
                s=self.text(v)
                if s:comment+=' '+repr(s)
            lines.append(f'{ins.address:08x} {ins.mnemonic:8} {ins.op_str}{comment}')
        return '\n'.join(lines)


if __name__=='__main__':
    a=Audit();out=ROOT/'work/stage4-code';out.mkdir(exist_ok=True)
    targets=[0x114d5c,0x114d8c,0x1386e4,0x138a68,0x11d218,0x103e4,0x10578,0x6c1ec,0x4db74,0x85cc0,0x86038,0xb5b0]
    save(out/'reference-index.json',[a.refs(p) for p in targets])
    for start,end in [(0xdaa60,0xdaab4),(0xdad90,0xdae30),(0x8fc04,0x8fcee),
                      (0x8cee8,0x8cf78),(0x882bc,0x88398),(0xe86e,0xe888)]:
        (out/f'{start:06x}.txt').write_text(a.disasm(start,end),encoding='utf-8')
    events={82:0x4db74,101:0xb5b0,117:0x103e4,118:0x10578,
            137:0x66524,138:0x69224,139:0x69e78,140:0x6c1ec,
            141:0x6c250,142:0x6f530,143:0x6f8ec}
    for event,callback in events.items():
        assert a.word(0x11d218+event*4)==BASE+callback+1
    banks=[]
    for mode,table,filename,method,pool,call,constructor in [
        (0,0x114d5c,'FldTexBank.nsbtx',0xdaa60,0xdaab4,0xdaa68,0xda9a4),
        (1,0x114d8c,'FldTexEditBank.nsbtx',0xdad90,0xdae30,0xdad98,0xdac9c)]:
        assert a.text(a.word(table))==filename
        assert a.word(pool)==BASE+table
        assert call in a.calls[0x8fc04]
        banks.append(dict(mode=mode,resource_table=table,bank=filename,
                          load_method=method,table_literal_pool=pool,
                          common_loader_call=call,constructor=constructor))
    assert a.word(0x883bc)==BASE+0x11d218
    assert 0xe882 in a.calls[0x75f40]
    assert struct.unpack_from('<H',a.b,0xe87e)[0]==0x2065
    result={
        'arm9_sha256':hashlib.sha256(a.b).hexdigest(),
        'offset_basis':'JP AJBJ Rev 0 ARM9 file offsets; memory address = offset + 0x02000000',
        'method':'Static Thumb disassembly, literal pool and callback-table cross-checks',
        'bank_factory':0x8cee8,'common_bank_loader':0x8fc04,'bank_profiles':banks,
        'event_dispatcher':0x882bc,'event_callback_table':0x11d218,
        'events':[dict(event_id=k,callback=v,pointer_offset=0x11d218+k*4) for k,v in events.items()],
        'shop_event_queue':dict(event_id=101,load_id=0xe87e,call=0xe882,target=0x75f40),
        'runtime_verified':False,
        'limits':['Conditional bank selection does not establish every model instance binding.',
                  'Registered callbacks and queue calls do not establish player accessibility.',
                  'Linear call search yields candidates, not a complete control-flow graph.'],
        'evidence_directory':'work/stage4-code',
    }
    save(ROOT/'metadata/stage4_code_connections.json',result)
    print(json.dumps({'bank_profiles':len(banks),'event_callbacks_checked':len(events),
                      'static_checks':'passed','runtime_verified':False},ensure_ascii=False))
