"""Remove the specifically indicated top-edge ghost pixels; no rerendering."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/title-touch-top-ghost-cleanup-v1'
def main():
 OUT.mkdir(exist_ok=False)
 source=ROOT/'work/graphics-draft/title-touch-imagegen-fit-v2/title-touch.png';a=np.array(Image.open(source).convert('RGBA'));b=a.copy()
 points=[(17,1),(25,1),(26,1),(47,1),(48,1),(49,1),(112,1),(113,1),(114,1)]+[(x,2) for x in range(7,13)]
 for x,y in points:
  p=a[y,x];assert p[3]==255 and max(p[:3])-min(p[:3])==0 and p[0]>=140
  b[y,x]=0
 change=np.any(a!=b,axis=2);assert change.sum()==len(points);assert np.array_equal(a[3:],b[3:]);assert np.array_equal(a[:,120:],b[:,120:])
 for n,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr);im.save(OUT/(n+'.png'));im.resize((816,144),Image.Resampling.NEAREST).save(OUT/(n+'-6x.png'))
 Image.fromarray(b).save(OUT/'title-touch.png');Image.fromarray(change.astype('uint8')*255).save(OUT/'changed-mask.png')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>윗선 잔상 픽셀만 정리</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>위로 튀어나온 잔상 픽셀만 정리</h1>'
 for z in [1,4,6]:
  page+=f'<section><h2>전체 {z}배 비교</h2><div class="row">'
  for n,t in [('before','이미지젠 축소본'),('after','위쪽 잔상 15픽셀 제거')]:page+=f'<div>{t}<br><img src="{n}.png" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 page+='<section><h2>윗선 10배</h2><div class="row">'
 for n,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr).crop((2,0,120,7));im.save(OUT/(n+'-top.png'));page+=f'<div>{"제거 전" if n=="before" else "제거 후"}<br><img src="{n}-top.png" width="1180" height="70"></div>'
 page+='</div></section>';(OUT/'index.html').write_text(page,encoding='utf8')
 report={'source':str(source.relative_to(ROOT)),'removed_pixels':len(points),'coordinates':points,'all_other_pixels_identical':True,'rows_3_down_identical':True,'punctuation_identical':True,'rom_built':False,'manifest_changed':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report)
 sheet=Image.new('RGB',(840,320),'white')
 for j,n in enumerate(['before','after']):
  im=Image.open(OUT/(n+'-6x.png'));sheet.paste(im,(10,8+j*160),im)
 sheet.save(OUT/'compare-white.png')
if __name__=='__main__':main()
