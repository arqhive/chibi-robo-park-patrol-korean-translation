"""Build the user's explicitly requested full Korean test ROM from readonly AJBJ."""
import json,struct,hashlib,sys
VER=sys.argv[1] if len(sys.argv)>1 else 'v01'
from pathlib import Path
import ndspy.rom,ndspy._common
from inspect_roms import ROOT,INPUTS,sha,save
from build_full_text import prepare as text_prepare
from build_full_graphics import prepare as graphics_prepare
import ndspy.code
from particle_patch import assemble as particle_assemble,patch_calls,ITCM_BASE

def main():
    state=json.loads((ROOT/'project.json').read_text(encoding='utf-8'));assert state['decisions']['build_requested']
    source=ROOT/INPUTS['jp'];original=source.read_bytes();digest=next(r['sha256'] for r in json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8')) if r['edition']=='jp');assert sha(original)==digest
    inventory=json.loads((ROOT/'metadata/inventory_jp.json').read_text(encoding='utf-8'))['files'];files={r['path']:original[r['offset']:r['end']] for r in inventory if r['path']};byname={r['path']:r for r in inventory}
    armoff,_,_,armsize=struct.unpack_from('<4I',original,0x20);arm=original[armoff:armoff+armsize]
    out=ROOT/f'work/full-build-{VER}';out.mkdir(parents=True,exist_ok=True)
    resources,newarm,textreport=text_prepare(ROOT,files,arm)
    # Korean particle selection: redirect formatter calls and add the fixer as an ITCM autoload block
    P=textreport['particles'];codes={r['hangul']:int(r['code'],16) for r in textreport['mapping']}
    blob,pinfo=particle_assemble(P['marker0'],P['h0'],P['h1'],P['t1'],P['t2'],lambda c:codes[c])
    src=ndspy.rom.NintendoDSRom(original);mcf=ndspy.code.MainCodeFile(patch_calls(newarm),src.arm9RamAddress,src.arm9CodeSettingsPointerAddress)
    mcf.sections.append(ndspy.code.MainCodeFile.Section(blob,ITCM_BASE,0));newarm=bytes(mcf.save(compress=False))
    textreport['particle_patch']=dict(pinfo,arm9_bytes=len(newarm))
    save(out/'text-checks.json',textreport);print('Text and fonts prepared',flush=True)
    manifest=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'));rows=[r for r in manifest['graphics'] if r['edition']=='jp' and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)>=552 and all(r['localization'].get('output') for r in rows)
    graphics,greport=graphics_prepare(ROOT,files,rows,out/'decoded');assert not set(graphics)&set(resources);resources.update(graphics);save(out/'graphics-checks.json',greport)
    for name,data in resources.items():(out/name).write_bytes(data)
    # the 12-byte Nitro footer (0xDEC00621, module params offset) follows ARM9 directly and moves with it
    arm7off=struct.unpack_from('<I',original,0x30)[0];footer=original[armoff+armsize:armoff+armsize+12];assert footer[:4]==bytes.fromhex('2106c0de')
    assert armoff+len(newarm)+12<=arm7off,'ARM9 grew past ARM7'
    built=bytearray(original);built[armoff:arm7off]=bytes(arm7off-armoff);built[armoff:armoff+len(newarm)]=newarm;built[armoff+len(newarm):armoff+len(newarm)+12]=footer;struct.pack_into('<I',built,0x2C,len(newarm))
    fatoff=struct.unpack_from('<I',original,0x48)[0];cursor=(max(max(r['end'] for r in inventory),struct.unpack_from('<I',original,0x80)[0])+511)&~511;changes=[]
    for name,payload in sorted(resources.items()):
        row=byname[name];start=row['offset'];relocated=len(payload)>row['size']
        if relocated:start=cursor;cursor=(cursor+len(payload)+511)&~511
        if start+len(payload)>len(built):built+=b'\xff'*(start+len(payload)-len(built))
        built[start:start+len(payload)]=payload;struct.pack_into('<II',built,fatoff+row['id']*8,start,start+len(payload))
        changes.append({'id':row['id'],'file':name,'old_bytes':row['size'],'new_bytes':len(payload),'relocated':relocated,'sha256':sha(payload)})
    used=max(struct.unpack_from('<I',original,0x80)[0],cursor);struct.pack_into('<I',built,0x80,used)
    # DS menu title: banner v1 has six language slots (UTF-16LE, 0x100 bytes each); all get the Korean title
    bo=struct.unpack_from('<I',original,0x68)[0];assert struct.unpack_from('<H',original,bo)[0]==1
    title='피워라! 치비로보!\nNintendo'.encode('utf-16le');assert len(title)<0x100
    for i in range(6):built[bo+0x240+i*0x100:bo+0x340+i*0x100]=title.ljust(0x100,b'\0')
    struct.pack_into('<H',built,bo+2,ndspy._common.crc16(built[bo+0x20:bo+0x840]))
    capacity=128*1024
    exponent=0
    while capacity<len(built):capacity*=2;exponent+=1
    built+=b'\xff'*(capacity-len(built));built[0x14]=exponent
    struct.pack_into('<H',built,0x15e,ndspy._common.crc16(built[:0x15e]))
    output=ROOT/f'build/ChibiRobo_AJBJ_KO_full-test_{VER}.nds';output.parent.mkdir(exist_ok=True)
    if output.exists():assert output.read_bytes()==built,'Refuse to overwrite a different ROM'
    else:output.write_bytes(built)
    parsed=ndspy.rom.NintendoDSRom(output.read_bytes());assert parsed.arm9==newarm and len(parsed.files)==len(inventory)
    for row in inventory:
        expect=resources.get(row['path'],original[row['offset']:row['end']]);assert parsed.files[row['id']]==expect,row['path']
    assert sha(source.read_bytes())==digest
    report={'build':f'full-test-{VER}','output':str(output),'source_sha256':digest,'output_sha256':sha(built),'rom_bytes':len(built),'used_bytes':used,'graphics_references':len(rows),'graphics_unique':len({r['pixel_sha256'] for r in rows}),'changed_files':changes,'text':textreport,'graphics':greport,'all_files_reextracted_verified':True,'original_unchanged':True,'runtime_verified':False,'cassette25':'Preserved at user request; unused status unconfirmed'}
    save(ROOT/f'metadata/full_test_build_{VER}.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ('text','graphics','changed_files')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
