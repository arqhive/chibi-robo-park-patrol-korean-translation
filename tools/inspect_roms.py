"""Inspect user's original DS images read-only; fixed-layout FAT roundtrip.

This does not test translated-length relocation or nested archive repacking.
"""
import hashlib,json,struct,zlib
from pathlib import Path
from collections import Counter
import ndspy.fnt
ROOT=Path(__file__).resolve().parents[1]
INPUTS={'jp':'Sakasete! Chibi-Robo! (Japan).nds','us':'Chibi-Robo! - Park Patrol (USA).nds'}
def sha(b):return hashlib.sha256(b).hexdigest()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 originals=[];summaries=[]
 for edition,name in INPUTS.items():
  source=ROOT/name;b=source.read_bytes();base=ROOT/'work/extracted'/edition;base.mkdir(parents=True,exist_ok=True)
  fo,fs,ao,asz=struct.unpack_from('<4I',b,0x40);assert asz%8==0
  filenames=ndspy.fnt.load(b[fo:fo+fs]);fat=[struct.unpack_from('<2I',b,ao+i) for i in range(0,asz,8)]
  originals.append({'edition':edition,'file':name,'size':len(b),'sha256':sha(b),'sha1':hashlib.sha1(b).hexdigest(),'crc32':f'{zlib.crc32(b)&0xffffffff:08x}','title':b[:12].rstrip(b'\0').decode('ascii'),'game_code':b[12:16].decode('ascii'),'revision':b[30]})
  records=[]
  for i,(start,end) in enumerate(fat):
   assert 0<=start<=end<=len(b)
   path=filenames.filenameOf(i);payload=b[start:end]
   disk=f'files/{i:04}.bin';target=base/disk;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(payload)
   records.append({'id':i,'path':path,'offset':start,'end':end,'size':end-start,'sha256':sha(payload),'magic_hex':payload[:16].hex(),'disk_file':disk})
  # Cover the whole image with separately saved nonoverlapping FAT payloads
  # and opaque gap/header spans. Rebuild FAT entries from parsed integers.
  intervals=sorted(set((r['offset'],r['end']) for r in records if r['size']))
  cursor=0;parts=[];overlaps=[]
  for start,end in intervals:
   if start<cursor:overlaps.append([start,end,cursor]);continue
   if start>cursor:
    disk=f'gaps/{cursor:08x}.bin';(base/disk).parent.mkdir(parents=True,exist_ok=True);(base/disk).write_bytes(b[cursor:start]);parts.append({'start':cursor,'end':start,'disk':disk})
   row=next(r for r in records if r['offset']==start and r['end']==end)
   parts.append({'start':start,'end':end,'disk':row['disk_file']});cursor=end
  assert not overlaps,overlaps
  if cursor<len(b):
   disk=f'gaps/{cursor:08x}.bin';(base/disk).parent.mkdir(parents=True,exist_ok=True);(base/disk).write_bytes(b[cursor:]);parts.append({'start':cursor,'end':len(b),'disk':disk})
  rebuilt=bytearray(len(b))
  for part in parts:
   chunk=(base/part['disk']).read_bytes();assert len(chunk)==part['end']-part['start'];rebuilt[part['start']:part['end']]=chunk
  rebuilt[ao:ao+asz]=b''.join(struct.pack('<2I',r['offset'],r['end']) for r in records)
  assert rebuilt==b and sha(source.read_bytes())==sha(b)
  save(base/'parts.json',parts)
  for key,off in [('arm9',0x20),('arm7',0x30)]:
   pos,entry,ram,size=struct.unpack_from('<4I',b,off);assert pos+size<=len(b);(base/(key+'.bin')).write_bytes(b[pos:pos+size])
  (base/'header.bin').write_bytes(b[:0x200])
  summary={'edition':edition,'files':len(records),'named_files':sum(r['path'] is not None for r in records),'extensions':dict(Counter(Path(r['path']).suffix.lower() if r['path'] else '(unnamed)' for r in records)),'duplicate_ranges':len(fat)-len(set(fat)),'fnt_offset':fo,'fnt_size':fs,'fat_offset':ao,'fat_size':asz,'roundtrip':{'identical':True,'bytes':len(b),'sha256':sha(rebuilt),'parts':len(parts),'fat_reserialized':True,'fnt_and_nested_resources':'opaque preserved; nested reserialization not tested','translation_injected':False,'rebuilt_rom_saved':False}}
  save(ROOT/f'metadata/inventory_{edition}.json',{'summary':summary,'files':records});summaries.append(summary)
 save(ROOT/'metadata/originals.json',originals);save(ROOT/'metadata/disc_comparison.json',summaries)
 print(json.dumps(summaries,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
