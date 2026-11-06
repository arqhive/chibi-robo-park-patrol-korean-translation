"""Reassemble from extracted spans, reserialize FNT/FAT/BMG/NARC, compare ROM."""
import json,struct
import ndspy.fnt,ndspy.bmg,ndspy.narc
from inspect_roms import ROOT,save,sha
def main():
 reports=[]
 for original in json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8')):
  ed=original['edition'];base=ROOT/f'work/extracted/{ed}';source=ROOT/original['file']
  b=source.read_bytes();assert sha(b)==original['sha256']
  rebuilt=bytearray(len(b));cursor=0
  for part in json.loads((base/'parts.json').read_text(encoding='utf-8')):
   assert part['start']==cursor;chunk=(base/part['disk']).read_bytes();assert len(chunk)==part['end']-part['start']
   rebuilt[part['start']:part['end']]=chunk;cursor=part['end']
  assert cursor==len(b)
  inv=json.loads((ROOT/f'metadata/inventory_{ed}.json').read_text(encoding='utf-8'));s=inv['summary']
  fo,fs=s['fnt_offset'],s['fnt_size'];fnt=ndspy.fnt.save(ndspy.fnt.load(rebuilt[fo:fo+fs]));assert len(fnt)==fs
  rebuilt[fo:fo+fs]=fnt
  fat=b''.join(struct.pack('<II',r['offset'],r['end']) for r in inv['files']);assert len(fat)==s['fat_size']
  rebuilt[s['fat_offset']:s['fat_offset']+s['fat_size']]=fat
  processed={'bmg':0,'narc':0}
  for r in inv['files']:
   payload=(base/r['disk_file']).read_bytes();assert sha(payload)==r['sha256']
   if payload.startswith(b'MESGbmg1'):out=ndspy.bmg.BMG(payload).save();processed['bmg']+=1
   elif payload.startswith(b'NARC'):out=ndspy.narc.NARC(payload).save();processed['narc']+=1
   else:continue
   assert len(out)==r['size'];rebuilt[r['offset']:r['end']]=out
  assert rebuilt==b and sha(source.read_bytes())==original['sha256']
  reports.append({'edition':ed,'bytes':len(b),'sha256':sha(rebuilt),'byte_identical':True,'reserialized':['FNT','FAT','all BMG','all top-level NARC'],'counts':processed,'opaque_preserved':['ARM9/ARM7','NFTR','graphics/model/sound','NARC member payloads','gaps/padding'],'translated_rom_built':False,'rebuilt_rom_saved':False})
 save(ROOT/'metadata/roundtrip_verification.json',reports);print(json.dumps(reports,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
