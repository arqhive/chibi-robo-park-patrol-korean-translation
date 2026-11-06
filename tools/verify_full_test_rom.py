"""Independent final-ROM text, NFTR link, ARM9 and source integrity checks."""
import json,struct,sys
VER=sys.argv[1] if len(sys.argv)>1 else 'v01'
from pathlib import Path
import ndspy.rom,ndspy.bmg,ndspy._common
from inspect_roms import ROOT,INPUTS,sha,save
from analyze_resources import nftr

def main():
    report=json.loads((ROOT/f'metadata/full_test_build_{VER}.json').read_text(encoding='utf-8'));raw=Path(report['output']).read_bytes();rom=ndspy.rom.NintendoDSRom(raw)
    maps={row['hangul']:int(row['code'],16).to_bytes(2,'big').decode('shift_jis') for row in report['text']['mapping']};reverse={v:k for k,v in maps.items()}
    def encode(s):return ''.join(maps.get(c,c) for c in s)
    # particle markers decode back to their written form (을(를) ...); the ARM9 patch picks the particle at runtime
    from particle_patch import PLACEHOLDER,from_placeholders
    for k,code in enumerate(report['text'].get('particles',{}).get('markers',[])):reverse[int(code,16).to_bytes(2,'big').decode('shift_jis')]=chr(PLACEHOLDER+k)
    def decode(s):return from_placeholders(''.join(reverse.get(c,c) for c in s))
    sources=json.loads((ROOT/'translations/ko.json').read_text(encoding='utf-8'));bmg={};count=0
    for r in sources:
        if r['file'] not in bmg:bmg[r['file']]=ndspy.bmg.BMG(rom.files[rom.filenames.idOf(r['file'])])
        msg=bmg[r['file']].messages[r['index']];actual=[decode(p) if isinstance(p,str) else {'type':p.type,'data':p.data.hex()} for p in msg.stringParts]
        expected=[p for p in r['translation_parts'] if p!=''];assert actual==expected,(r['file'],r['index'],actual,expected);count+=1
    fontchecks=[]
    for font in report['text']['fonts']:
        data=rom.files[rom.filenames.idOf(font['file'])];r,m,w,t=nftr(data);f=next(b['offset'] for b in r['blocks'] if b['magic']=='FNIF');cg,cw,cm=struct.unpack_from('<III',data,f+16)
        assert data[cg-8:cg-4]==b'PLGC' and data[cw-8:cw-4]==b'HDWC' and data[cm-8:cm-4]==b'PAMC'
        assert struct.unpack_from('<I',data,cw+4)[0]==0 and struct.unpack_from('<I',data,cm+8)[0]==0
        for ch,sj in maps.items():assert int.from_bytes(sj.encode('shift_jis'),'big') in m
        fontchecks.append({'file':font['file'],'linked_blocks_valid':True,'all_new_characters_mapped':True})
    extras=json.loads((ROOT/'translations/extra-ko.json').read_text(encoding='utf-8'));placements={r['offset']:r for r in report['text']['arm9']}
    for r in extras:
        target=b''.join(encode(p).encode('shift_jis') if isinstance(p,str) else bytes.fromhex(p['escape_hex']) for p in r['translation_parts'])+b'\0';rec=placements[r['offset']];at=rec['new_offset'];assert rom.arm9[at:at+len(target)]==target
        for off in rec.get('pointer_offsets',[]):assert struct.unpack_from('<I',rom.arm9,off)[0]==0x02000000+at
    assert ndspy._common.crc16(raw[:0x15e])==struct.unpack_from('<H',raw,0x15e)[0]
    assert sha((ROOT/INPUTS['jp']).read_bytes())==report['source_sha256']
    result={'output_sha256':sha(raw),'bmg_messages_roundtrip_to_exact_translation':count,'embedded_strings_exact':len(extras),'fonts':fontchecks,'header_crc_valid':True,'source_unchanged':True,'runtime_verified':False}
    save(ROOT/f'metadata/full_test_verification_{VER}.json',result);print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
