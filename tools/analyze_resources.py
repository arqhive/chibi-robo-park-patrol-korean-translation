"""Inspect BMG/NFTR/NARC, with in-memory structure tests; no ROM injection."""
import copy,json,struct,hashlib,importlib.metadata
from collections import Counter
from pathlib import Path
import ndspy.bmg,ndspy.narc
from PIL import Image,ImageDraw,ImageFont
from inspect_roms import ROOT,save

def nftr(b):
 assert b[:4]==b'RTFN' and struct.unpack_from('<I',b,8)[0]==len(b)
 blocks=[];at=struct.unpack_from('<H',b,12)[0]
 for _ in range(struct.unpack_from('<H',b,14)[0]):
  size=struct.unpack_from('<I',b,at+4)[0];assert size>=8 and at+size<=len(b)
  blocks.append((at,size,b[at:at+4]));at+=size
 assert at==len(b)
 finf=next(a for a,s,m in blocks if m==b'FNIF');enc=b[finf+15]
 cg=next((a,s) for a,s,m in blocks if m==b'PLGC');a,size=cg
 w,h,cell,ascent,maxwidth,bpp,rotation=struct.unpack_from('<BBHBBBB',b,a+8)
 assert bpp==1 and rotation==0
 widths={};mapping={}
 for at,size,magic in blocks:
  if magic==b'HDWC':
   first,last,nxt=struct.unpack_from('<HHI',b,at+8)
   for i in range(first,last+1):widths[i]=struct.unpack_from('<bBB',b,at+16+(i-first)*3)
  if magic==b'PAMC':
   first,last,kind,reserved,nxt=struct.unpack_from('<4HI',b,at+8)
   if kind==0:
    start=struct.unpack_from('<H',b,at+20)[0];pairs=[(code,start+code-first) for code in range(first,last+1)]
   elif kind==1:pairs=[(code,struct.unpack_from('<H',b,at+20+(code-first)*2)[0]) for code in range(first,last+1)]
   else:
    assert kind==2;n=struct.unpack_from('<H',b,at+20)[0];pairs=[struct.unpack_from('<HH',b,at+22+i*4) for i in range(n)]
   for code,index in pairs:
    if index==65535:continue
    assert code not in mapping or mapping[code]==index;mapping[code]=index
 count=max(widths)+1;assert count*cell<=cg[1]-16 and cg[1]-16-count*cell<4
 assert max(mapping.values())<count
 advances=Counter(v[2] for v in widths.values())
 report={'encoding':{0:'UTF-8',1:'UTF-16',2:'Shift-JIS',3:'CP1252'}.get(enc,str(enc)),'cell':[w,h],'cell_bytes':cell,'bpp':bpp,'glyph_count':count,'mapped_codes':len(mapping),'advance_distribution':dict(sorted(advances.items())),'fixed_advance':len(advances)==1,'original_glyph_bytes':count*cell,'2350_hangul_bitmap_bytes':2350*cell,'blocks':[{'magic':m.decode(),'offset':a,'size':s} for a,s,m in blocks]}
 return report,mapping,widths,b[cg[0]+16:cg[0]+16+count*cell]

def message_repr(message):
 return {'attributes':message.info.hex(),'parts':[p if isinstance(p,str) else {'type':p.type,'data':p.data.hex()} for p in message.stringParts if p!=''],'is_null':message.isNull}

def main():
 allreports={};candidates=[]
 for ed in ['jp','us']:
  rows=json.loads((ROOT/f'metadata/inventory_{ed}.json').read_text(encoding='utf-8'))['files'];report={'messages':[],'fonts':[],'archives':[]}
  sheet=Image.new('RGB',(800,6*100),'#eeeeee');d=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',16);fontrow=0
  for r in rows:
   ext=Path(r['path']).suffix.lower()
   if ext not in ['.bmg','.nftr','.arc']:continue
   b=(ROOT/f'work/extracted/{ed}'/r['disk_file']).read_bytes()
   if ext=='.bmg':
    m=ndspy.bmg.BMG(b);assert m.save()==b,r['path']
    strings=[part for msg in m.messages for part in msg.stringParts if isinstance(part,str)]
    tags=Counter(f'{part.type:02x}:{len(part.data)}' for msg in m.messages for part in msg.stringParts if not isinstance(part,str))
    # Exercise longer and shorter content with all message attributes and tags
    # compared after serialization. This is a disposable synthetic BMG test.
    growth=[]
    for marker in ['あ'*31 if ed=='jp' else 'A'*31,'']:
     temp=copy.deepcopy(m);mi=next(i for i,x in enumerate(temp.messages) if any(isinstance(p,str) and p for p in x.stringParts));pi=next(i for i,p in enumerate(temp.messages[mi].stringParts) if isinstance(p,str) and p)
     temp.messages[mi].stringParts[pi]=marker;out=temp.save();parsed=ndspy.bmg.BMG(out)
     assert [message_repr(x) for x in parsed.messages]==[message_repr(x) for x in temp.messages]
     assert parsed.save()==out;growth.append(len(out)-len(b))
    item={'file':r['path'],'messages':len(m.messages),'nonempty_messages':sum(bool(x.stringParts) for x in m.messages),'encoding':m.encoding,'text_characters':sum(map(len,strings)),'nonwhitespace_characters':sum(not c.isspace() for s in strings for c in s),'escape_types_and_data_lengths':dict(tags),'unchanged_roundtrip_identical':True,'synthetic_variable_length_roundtrip':True,'synthetic_size_deltas':growth}
    report['messages'].append(item)
    for i,msg in enumerate(m.messages):candidates.append({'edition':ed,'file':r['path'],'index':i,**message_repr(msg)})
   elif ext=='.nftr':
    f,mapping,widths,tiles=nftr(b);f['file']=r['path'];report['fonts'].append(f)
    # Decode original one-bit glyphs only, for font design comparison.
    d.text((8,fontrow*100+3),r['path']+' '+str(f['cell'])+' '+str(f['glyph_count'])+' glyphs',font=font,fill='black')
    x=8;y=fontrow*100+28
    for ch in 'あいうえお漢字花公園ABC012!?':
     try:code=int.from_bytes(ch.encode('cp932'),'big') if f['encoding']=='Shift-JIS' else ord(ch)
     except UnicodeEncodeError:continue
     if code not in mapping:continue
     idx=mapping[code];cell=f['cell_bytes'];w,h=f['cell'];raw=tiles[idx*cell:(idx+1)*cell]
     glyph=Image.new('L',(w,h));glyph.putdata([0 if raw[i//8]&(128>>(i%8)) else 255 for i in range(w*h)])
     glyph=glyph.resize((w*2,h*2),Image.Resampling.NEAREST);sheet.paste(glyph,(x,y));x+=w*2+7
    fontrow+=1
   else:
    arc=ndspy.narc.NARC(b);rebuilt=arc.save()
    report['archives'].append({'file':r['path'],'members':len(arc.files),'unchanged_roundtrip_identical':rebuilt==b,'size':len(b),'rebuilt_size':len(rebuilt),'member_magics':dict(Counter(x[:4].hex() for x in arc.files))})
  report['message_totals']={k:sum(x[k] for x in report['messages']) for k in ['messages','nonempty_messages','text_characters','nonwhitespace_characters']}
  allreports[ed]=report
  out=ROOT/'work/analysis';out.mkdir(parents=True,exist_ok=True);sheet.save(out/f'fonts-{ed}.png')
 save(ROOT/'work/analysis/message_candidates.json',candidates)
 save(ROOT/'metadata/resource_analysis.json',allreports)
 save(ROOT/'metadata/tool_versions.json',{'python_dependency':'ndspy','ndspy':importlib.metadata.version('ndspy'),'Pillow':importlib.metadata.version('Pillow')})
 for ed,r in allreports.items():print(ed,json.dumps({'message_totals':r['message_totals'],'fonts':[{k:f[k] for k in ['file','cell','glyph_count','encoding']} for f in r['fonts']],'narc_roundtrip_failures':[x for x in r['archives'] if not x['unchanged_roundtrip_identical']]},ensure_ascii=False))
if __name__=='__main__':main()
