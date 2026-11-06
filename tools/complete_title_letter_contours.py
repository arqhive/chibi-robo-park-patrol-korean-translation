"""Complete the existing letter contours after colour-band cleanup."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as nd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-touch-letter-contours-v1'
def main():
 OUT.mkdir(exist_ok=False)
 src=ROOT/'work/graphics-draft/title-touch-flat-bands-v1/after.png';a=np.array(Image.open(src).convert('RGBA'))
 reference=ROOT/'work/graphics-draft/title-touch-spot-cleanup-v2/after.png';old=np.array(Image.open(reference).convert('RGBA'))
 rgb=old[:,:,:3].astype(int);y,x=np.indices(a.shape[:2]);sat=np.ptp(rgb,axis=2)
 white=(rgb.min(axis=2)>210)&(sat<30)&(x<120)&(a[:,:,3]>0)
 possible=(a[:,:,3]>0)&(x<120)&((sat<30)|((rgb.max(axis=2)<210)&(sat<=100)))
 labels,_=nd.label(possible);ids=np.unique(labels[white]);glyph=np.isin(labels,ids[ids>0])
 contour=glyph&~nd.binary_erosion(glyph,structure=nd.generate_binary_structure(2,1))
 b=a.copy();b[contour]=(0,0,0,255)
 changed=np.any(a!=b,axis=2)
 assert np.array_equal(a[white],b[white]);assert np.array_equal(a[~contour],b[~contour])
 assert np.array_equal(a[:,120:],b[:,120:]);assert np.array_equal(a[:,:,3],b[:,:,3])
 for n,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr);im.save(OUT/(n+'.png'));im.resize((816,144),Image.Resampling.NEAREST).save(OUT/(n+'-6x.png'))
 Image.fromarray(changed.astype('uint8')*255).save(OUT/'changed-mask.png')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>터치 해서 시작 · 끊긴 글자 테두리 연결</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>터치 해서 시작 · 끊긴 글자 테두리 연결</h1>'
 for z in (1,4,6):
  page+=f'<section><h2>전체 {z}배 비교</h2><div class="row">'
  for n,t in [('before','색 띠 정리 후'),('after','글자 테두리 연결')]:page+=f'<div>{t}<br><img src="{n}.png" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 for i,rect in enumerate([(6,12,17,20),(20,2,32,12),(19,14,28,21),(60,4,69,17),(54,15,62,22)],1):
  page+=f'<section><h2>첨부 {i}번 부근 · 10배</h2><div class="row">'
  for n,arr in [('before',a),('after',b)]:
   im=Image.fromarray(arr).crop(rect);name=f'{n}-detail-{i}.png';im.save(OUT/name);page+=f'<div>{"연결 전" if n=="before" else "연결 후"}<br><img src="{name}" width="{im.width*10}" height="{im.height*10}"></div>'
  page+='</div></section>'
 (OUT/'index.html').write_text(page,encoding='utf8')
 report={'source':str(src.relative_to(ROOT)),'contour_reference':str(reference.relative_to(ROOT)),'changed_pixels':int(changed.sum()),'white_and_light_AA_changed_pixels':0,'outside_contour_changed_pixels':0,'punctuation_changed_pixels':0,'alpha_changed_pixels':0,'manifest_changed':False,'rom_built':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 sheet=Image.new('RGB',(840,320),'white')
 for j,n in enumerate(['before','after']):
  im=Image.open(OUT/(n+'-6x.png'));sheet.paste(im,(10,8+j*160),im)
 sheet.save(OUT/'compare-white.png');print(report)
if __name__=='__main__':main()
