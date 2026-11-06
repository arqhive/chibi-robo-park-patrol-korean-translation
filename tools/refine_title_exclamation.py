"""Refine only the title prompt exclamation mark on a symmetric native grid."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as nd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-touch-symmetric-v1'
def main():
 OUT.mkdir(exist_ok=False)
 source=ROOT/'work/graphics-draft/title-touch-outer-black-v1/after.png'
 a=np.array(Image.open(source).convert('RGBA'));b=a.copy();yy,xx=np.indices(a.shape[:2]);zone=xx>=122;b[zone]=0
 # A 12-pixel capsule centred at x=128.5, retaining the approved height.
 shape=np.zeros(a.shape[:2],bool)
 spans={1:(127,131),2:(125,133),3:(124,134),20:(124,134),21:(125,133),22:(127,131)}
 for y in range(1,23):
  l,r=spans.get(y,(123,135));shape[y,l:r]=True
 cross=nd.generate_binary_structure(2,1)
 b[shape]=(0,0,0,255);inside=nd.binary_erosion(shape,structure=cross);b[inside]=(246,156,57,255)
 core=np.zeros(shape.shape,bool)
 core[5,128:130]=True;core[6:12,127:131]=True;core[12,128:130]=True
 core[16:18,127:131]=True
 border=nd.binary_dilation(core,structure=cross)
 assert np.all(shape[border])
 b[border]=(0,0,0,255);b[core]=(255,255,255,255)
 assert np.array_equal(b[:,123:135],b[:,123:135][:,::-1])
 assert np.array_equal(a[:,:122],b[:,:122])
 for name,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr);im.save(OUT/(name+'.png'));im.crop((121,0,136,24)).resize((120,192),Image.Resampling.NEAREST).save(OUT/(name+'-mark-8x.png'))
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>느낌표 · 좌우대칭 정리</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#19271d}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>느낌표 · 좌우대칭과 내부 색 정리</h1>'
 for z in (1,4):
  page+=f'<section><h2>전체 {z}배</h2><div class="row">'
  for n,t in [('before','직전 수정본'),('after','느낌표 정리')]:page+=f'<div>{t}<br><img src="{n}.png" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 page+='<section><h2>느낌표 8배</h2><div class="row">'
 for n,t in [('before','직전 수정본'),('after','느낌표 정리')]:page+=f'<div>{t}<br><img src="{n}-mark-8x.png" width="120" height="192"></div>'
 page+='</div></section>';(OUT/'index.html').write_text(page,encoding='utf8')
 report={'source':str(source.relative_to(ROOT)),'symmetry_axis_x':128.5,'exact_horizontal_symmetry':True,'changed_pixels':int(np.any(a!=b,axis=2).sum()),'outside_punctuation_changed_pixels':0,'colours':['#000000','#f69c39','#ffffff'],'size':[136,24],'rom_built':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report)
 sheet=Image.new('RGB',(400,220),'white')
 for j,n in enumerate(['before','after']):
  im=Image.open(OUT/(n+'-mark-8x.png'));sheet.paste(im,(20+200*j,12),im)
 sheet.save(OUT/'compare-white.png')
if __name__=='__main__':main()
