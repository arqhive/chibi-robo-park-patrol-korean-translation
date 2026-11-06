"""Encode Korean using new, valid Shift-JIS slots and append native NFTR glyphs."""
import json,struct,copy
from pathlib import Path
import ndspy.bmg
from PIL import Image,ImageDraw,ImageFont
from analyze_resources import nftr,message_repr
from prepare_output_probe import pack_cell,unpack_cell,FONT_DIR
from particle_patch import batchim_class,to_placeholders,PLACEHOLDER,MARKERS

def section(magic,body):
    body+=bytes((-len(body))%4)
    return magic+struct.pack('<I',len(body)+8)+body

def prepare(root,files,arm9):
    ko=json.loads((root/'translations/ko.json').read_text(encoding='utf-8'))
    extra=json.loads((root/'translations/extra-ko.json').read_text(encoding='utf-8'))
    # glyph codes run no-batchim, ㄹ-batchim, other-batchim so the particle patch can classify by code range
    chars=sorted({c for r in ko+extra for p in r['translation_parts'] if isinstance(p,str) for c in p if '\uac00'<=c<='\ud7a3' or c=='·'},key=lambda c:(batchim_class(c),c))
    fonts={name:nftr(data) for name,data in files.items() if name.endswith('.NFTR')}
    used=set().union(*(set(v[1]) for v in fonts.values()))
    for r in ko+extra:
        for c in r['source_text']:
            try:used.add(int.from_bytes(c.encode('shift_jis'),'big'))
            except UnicodeEncodeError:pass
    candidates=[]
    for code in range(0x8900,0xeffd):
        if code in used:continue
        raw=code.to_bytes(2,'big')
        try:ch=raw.decode('shift_jis')
        except UnicodeDecodeError:continue
        if len(ch)==1 and ch.encode('shift_jis')==raw:candidates.append((code,ch))
    assert len(candidates)>=len(chars)
    mapping={c:candidates[i] for i,c in enumerate(chars)}
    rest=candidates[len(chars):];run=next(i for i in range(len(rest)-8) if rest[i+7][0]-rest[i][0]==7)
    markers={chr(PLACEHOLDER+k):rest[run+k] for k in range(len(MARKERS))}
    def encode(s):return ''.join(mapping[c][1] if c in mapping else (markers[c][1] if c in markers else c) for c in to_placeholders(s))
    resources={};report={'hangul_count':sum('가'<=c<='힣' for c in chars),'additional_symbol_count':sum(not '가'<=c<='힣' for c in chars),'mapping':[{'hangul':c,'code':f'{code:04x}'} for c,(code,_) in mapping.items()],'particles':{'marker0':markers[chr(PLACEHOLDER)][0],'h0':min(mapping[c][0] for c in chars if '가'<=c<='힣'),'h1':max(mapping[c][0] for c in chars if '가'<=c<='힣'),'t1':min(mapping[c][0] for c in chars if batchim_class(c)==1),'t2':min(mapping[c][0] for c in chars if batchim_class(c)==2),'markers':[f'{markers[chr(PLACEHOLDER+k)][0]:04x}' for k in range(len(MARKERS))]},'fonts':[],'messages':[],'arm9':[]}
    for name,(r,oldmap,widths,tiles) in fonts.items():
        if name=='Font_LoadInfo.NFTR':continue
        source=files[name];w,h=r['cell'];spec={15:('Galmuri14.ttf',15,(-1,0)),11:('Galmuri11.ttf',12,(0,-1)),9:('Galmuri9.ttf',10,(0,-1)),7:('Galmuri7.ttf',8,(0,-1))}[w]
        font=ImageFont.truetype(str(FONT_DIR/spec[0]),spec[1]);newtiles=bytearray(tiles);newmap=dict(oldmap);newwidths=dict(widths);count=r['glyph_count']
        # Galmuri draws ㅓ/ㅕ-type syllables up to 2px narrower inside the same advance; centre those
        # narrow Hangul glyphs in the widest ink span so the gap after them matches (user choice B, 11/06)
        def ink_right(c):
            cv=Image.new('L',(64,64));ImageDraw.Draw(cv).text((16+spec[2][0],16+spec[2][1]),c,font=font,fill=255);return cv.getbbox()[2]
        rights={c:ink_right(c) for c in chars if '가'<=c<='힣'};widest=max(rights.values())
        for i,c in enumerate(chars):
            shift=(widest-rights[c])//2 if c in rights else 0
            canvas=Image.new('L',(64,64));ImageDraw.Draw(canvas).text((16+spec[2][0]+shift,16+spec[2][1]),c,font=font,fill=255)
            box=canvas.getbbox();assert box and box[0]>=16 and box[1]>=16 and box[2]<=16+w and box[3]<=16+h,(name,c,box)
            glyph=canvas.crop((16,16,16+w,16+h));packed=pack_cell(glyph,r['cell_bytes']);assert unpack_cell(packed,w,h).tobytes()==glyph.tobytes()
            newtiles+=packed;newwidths[count+i]=(1,w,w+1);newmap[mapping[c][0]]=count+i
        oldblocks={b['magic']:b for b in r['blocks']};b=oldblocks['FNIF'];finf=bytearray(source[b['offset']+8:b['offset']+b['size']]);b=oldblocks['PLGC'];cghead=source[b['offset']+8:b['offset']+16]
        cglp=section(b'PLGC',cghead+newtiles);cwdh=section(b'HDWC',struct.pack('<HHI',0,len(newwidths)-1,0)+b''.join(struct.pack('<bBB',*newwidths[i]) for i in range(len(newwidths))))
        cmap=section(b'PAMC',struct.pack('<4HIH',min(newmap),max(newmap),2,0,0,len(newmap))+b''.join(struct.pack('<HH',c,i) for c,i in sorted(newmap.items())))
        cg=16+len(section(b'FNIF',bytes(finf)));cw=cg+len(cglp);cm=cw+len(cwdh);struct.pack_into('<III',finf,8,cg+8,cw+8,cm+8)
        out=bytearray(source[:16]+section(b'FNIF',bytes(finf))+cglp+cwdh+cmap);struct.pack_into('<IHH',out,8,len(out),16,4)
        rr,mm,ww,tt=nftr(out);assert tt[:len(tiles)]==tiles and all(mm[c]==i for c,i in oldmap.items()) and all(ww[i]==v for i,v in widths.items())
        resources[name]=bytes(out);report['fonts'].append({'file':name,'before':len(source),'after':len(out),'glyphs':rr['glyph_count'],'original_glyphs_preserved':True})
    byfile={}
    for r in ko:byfile.setdefault(r['file'],[]).append(r)
    for name,rows in byfile.items():
        source=ndspy.bmg.BMG(files[name]);after=copy.deepcopy(source)
        for r in rows:
            msg=after.messages[r['index']];original=source.messages[r['index']];parts=r['translation_parts'];assert parts is not None
            strings=iter(encode(p) for p in parts if isinstance(p,str));msg.stringParts=[next(strings) if isinstance(p,str) else p for p in original.stringParts]
            assert next(strings,None) is None
            for p in msg.stringParts:
                if isinstance(p,str):p.encode('shift_jis')
        payload=after.save();parsed=ndspy.bmg.BMG(payload);assert [message_repr(m) for m in parsed.messages]==[message_repr(m) for m in after.messages]
        for a,b in zip(source.messages,parsed.messages):
            assert a.info==b.info and a.isNull==b.isNull
            assert [(p.type,p.data) for p in a.stringParts if not isinstance(p,str)]==[(p.type,p.data) for p in b.stringParts if not isinstance(p,str)]
        resources[name]=payload;report['messages'].append({'file':name,'count':len(rows),'before':len(files[name]),'after':len(payload),'roundtrip':True,'controls_preserved':True})
    # Keep ARM9 size and address layout. Shortened known strings provide storage
    # for the few longer translations; patch their exact aligned pointer literals.
    built=bytearray(arm9);holes=[];pending=[]
    for r in extra:
        off=r['offset'];old=bytes.fromhex(r['source_hex']);new=b''.join(encode(p).encode('shift_jis') if isinstance(p,str) else bytes.fromhex(p['escape_hex']) for p in r['translation_parts'])+b'\0'
        assert arm9[off:off+len(old)]==old
        end=off+len(old)
        while end%4 and arm9[end]==0:end+=1
        if len(new)<=end-off:
            built[off:end]=new+bytes(end-off-len(new));free=off+len(new)
            if end-free>=4:holes.append([free,end])
            report['arm9'].append({'offset':off,'new_offset':off,'bytes':len(new)})
        else:pending.append((r,new))
    placed={}
    for r,new in pending:
        off=r['offset']
        if new in placed:dst=placed[new]
        else:
            hole=next(h for h in holes if h[1]-h[0]>=len(new));dst=hole[0];built[dst:dst+len(new)]=new;hole[0]=dst+len(new);placed[new]=dst
        refs=[i for i in range(0,len(arm9)-3,4) if struct.unpack_from('<I',arm9,i)[0]==0x02000000+off]
        assert refs,(r,'No pointer reference')
        for i in refs:struct.pack_into('<I',built,i,0x02000000+dst)
        report['arm9'].append({'offset':off,'new_offset':dst,'pointer_offsets':refs,'bytes':len(new)})
    assert len(built)==len(arm9)
    return resources,bytes(built),report
