from pathlib import Path
import json,hashlib,shutil
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'work/graphics-draft/batch04-v2';OUT=ROOT/'work/graphics-draft/batch04-v3'
def main():
 OUT.mkdir(exist_ok=True)
 for p in OLD.glob('DayResult*.png'):shutil.copy2(p,OUT/p.name)
 stem='DayResultPark-cell-22';src=Image.open(OLD/f'{stem}-korean.png').convert('RGBA');a=np.array(src)
 mask=np.zeros((16,16),dtype=bool);mask[11,3:11]=True;mask[12:16,3:13]=True
 layer=np.zeros_like(a);layer[mask]=a[mask];b=a.copy();b[mask]=0
 shifted=np.zeros_like(layer);shifted[:,1:]=layer[:,:-1]
 # Only selected bottom consonant pixels are moved. Keep transparent RGB clean.
 selected=shifted[:,:,3]>0;b[selected]=shifted[selected]
 changed=np.any(a!=b,axis=2);allowed=mask.copy();allowed[:,1:]|=mask[:,:-1]
 assert not np.any(changed&~allowed)
 assert np.array_equal(a[:11],b[:11])
 assert np.array_equal(a[11,12:],b[11,12:])
 assert not layer[:,-1,3].any()
 result=Image.fromarray(b);result.save(OUT/f'{stem}-korean.png')
 original=np.array(Image.open(OUT/f'{stem}-original.png').convert('RGBA'))
 Image.fromarray((((original[:,:,3]>0)|(b[:,:,3]>0))*255).astype('uint8')).save(OUT/f'{stem}-mask.png')
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 report={'key':'DayResultPark/cell/22','edit':'Move only bottom ㅇ one pixel right','size':[16,16],'offset':[1,0],'selection_rows':{'11':[3,11],'12:16':[3,13]},'upper_rows_0_through_10_unchanged':True,'outside_edit_mask_changed_pixels':0,'clipped_pixels':0,'changed_pixels':int(changed.sum()),'sha256':sha(OUT/f'{stem}-korean.png'),'runtime_verified':False}
 (ROOT/'metadata/graphics_batch04_v3_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
 for r in m['graphics']:
  l=r.get('localization',{})
  if r['edition']=='jp' and l.get('draft_version')=='batch04-v2':
   for field in ['output','preview','erased','edit_mask','comparison']:
    if l.get(field):l[field]=l[field].replace('batch04-v2','batch04-v3')
   l['draft_version']='batch04-v3'
   if r['key']=='DayResultPark/cell/22':l['note']='v2의 아래 ㅇ만 오른쪽1px 이동. 위쪽 며와16x16 크기 유지. 게임실행 미확인.'
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page=(OLD/'index.html').read_text(encoding='utf-8')
 for f in OLD.glob('DayResult*-korean.png'):shutil.copy2(f,OUT/f.name.replace('-korean','-previous'))
 page=page.replace('수정 결과 · 16×16','최신 수정 · 16×16').replace('<h1>네 번째 묶음 · 송이 2종 / 명</h1>','<h1>네 번째 묶음 · 송이 2종 / 명</h1><p><b>명 아래 ㅇ만 오른쪽으로1px 이동했습니다. 송이 두 종류는 이전과 같습니다.</b></p>')
 (OUT/'index.html').write_text(page,encoding='utf-8')
 sheet=Image.new('RGB',(580,210),'#d3d5cc');d=ImageDraw.Draw(sheet)
 for i,(title,im) in enumerate([('Before',src),('After',result)]):
  d.text((i*290+10,5),title,fill='black');q=im.resize((160,160),Image.Resampling.NEAREST);sheet.paste(q,(i*290+10,35),q)
 sheet.save(OUT/'people-comparison.png');print(json.dumps(report))
if __name__=='__main__':main()
