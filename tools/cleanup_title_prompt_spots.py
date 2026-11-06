"""Small coordinate-based cleanup; retain the approved letter drawing and shading."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-touch-spot-cleanup-v1'
def main():
 OUT.mkdir(exist_ok=True)
 assert not (OUT/'after.png').exists()
 source=ROOT/'work/graphics-draft/title-touch-mirror-left-v1/after.png';a=np.array(Image.open(source).convert('RGBA'));b=a.copy()
 green=(189,213,65);yellow=(205,189,65)
 edits=[
 (115,7,green,'작 오른쪽 색 띠 속 어두운 점'),(116,7,green,'같은 위치의 탁한 경계색'),
 (117,9,green,'작 오른쪽 초록 띠 속 어두운 점'),(115,11,green,'검은 획 밖 초록 띠 속 점'),
 (114,14,green,'작 옆 띠의 어두운 잔상'),(114,18,green,'작 끝 옆의 고립된 어두운 점'),
 (99,17,green,'세로 획 옆으로 튀어나온 올리브색'),
 (52,12,(222,222,222),'세로 획의 회색 가장자리 중간에 낀 올리브색'),
 (55,10,(57,57,57),'좁은 세로 그림자 선 중간의 튀는 올리브색'),
 (70,16,(164,156,74),'서 세로 올리브 그림자 중간의 갑작스러운 회색'),
 (67,17,yellow,'노랑 띠 안에 섞인 초록색'),(68,17,yellow,'노랑 띠 안에 섞인 초록색'),
 (60,12,(230,222,82),'해 옆 노랑 띠 안에 섞인 초록색'),
 (62,6,(205,189,65),'노랑 가장자리에 튀는 초록색'),
 (68,8,(205,189,65),'노랑 가장자리에 튀는 초록색')]
 records=[]
 for x,y,color,reason in edits:
  assert a[y,x,3]==255
  records.append({'x':x,'y':y,'before':a[y,x].tolist(),'after':list(color)+[255],'reason':reason});b[y,x]=(*color,255)
 changed=np.any(a!=b,axis=2);assert changed.sum()==len(edits)
 assert np.array_equal(a[:,120:],b[:,120:]);assert np.array_equal(a[:,:,3],b[:,:,3])
 white=np.all(a[:,:,:3]==255,axis=2)&(a[:,:,3]>0)
 assert np.array_equal(a[white],b[white])
 for n,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr);im.save(OUT/(n+'.png'));im.resize((816,144),Image.Resampling.NEAREST).save(OUT/(n+'-6x.png'))
 Image.fromarray(changed.astype('uint8')*255).save(OUT/'changed-mask.png')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>터치 해서 시작 · 눈에 띄는 픽셀 정리</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>터치 해서 시작 · 눈에 띄는 픽셀만 정리</h1>'
 for z in [1,4,6]:
  page+=f'<section><h2>전체 {z}배 비교</h2><div class="row">'
  for n,t in [('before','대칭 복사본'),('after','튀는 픽셀 15개 정리')]:page+=f'<div>{t}<br><img src="{n}.png" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 for label,rect in [('작 옆 초록 띠',(110,4,120,20)),('튀어나온 올리브 픽셀',(94,13,102,21)),('해 가장자리',(50,8,58,18)),('서 그림자',(66,10,76,20))]:
  page+=f'<section><h2>{label} · 10배</h2><div class="row">'
  for n,arr in [('before',a),('after',b)]:
   name=f'{n}-detail-{rect[0]}.png';im=Image.fromarray(arr).crop(rect);im.save(OUT/name);page+=f'<div>{"정리 전" if n=="before" else "정리 후"}<br><img src="{name}" width="{im.width*10}" height="{im.height*10}"></div>'
  page+='</div></section>'
 (OUT/'index.html').write_text(page,encoding='utf8')
 report={'source':str(source.relative_to(ROOT)),'changed_pixels':int(changed.sum()),'white_letter_changed_pixels':0,'alpha_changed_pixels':0,'punctuation_changed_pixels':0,'edits':records,'rom_built':False,'manifest_changed':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print({k:v for k,v in report.items() if k!='edits'})
 sheet=Image.new('RGB',(840,320),'white')
 for j,n in enumerate(['before','after']):
  im=Image.open(OUT/(n+'-6x.png'));sheet.paste(im,(10,8+j*160),im)
 sheet.save(OUT/'compare-white.png')
if __name__=='__main__':main()
