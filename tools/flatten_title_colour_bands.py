"""Flatten colour-band shading without changing black contours or white artwork."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage as nd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-touch-flat-bands-v1'
def main():
 OUT.mkdir(exist_ok=False)
 source=ROOT/'work/graphics-draft/title-touch-spot-cleanup-v2/after.png';a=np.array(Image.open(source).convert('RGBA'));b=a.copy();rgb=a[:,:,:3].astype(int);y,x=np.indices(a.shape[:2]);sat=np.ptp(rgb,axis=2);band=np.zeros(sat.shape,bool)
 # Flood the chromatic strip from each known flat face. Black contours and
 # neutral white/gray letter artwork are barriers, not repainting candidates.
 groups=[]
 for left,right,c in [(0,39,(246,156,57)),(39,80,(255,238,90)),(80,120,(189,213,65))]:
  area=(x>=left)&(x<right)&(a[:,:,3]>0);possible=area&(sat>30)&(rgb.max(axis=2)>80);seed=area&np.all(rgb==c,axis=2)
  part=nd.binary_propagation(seed,mask=possible);band|=part;b[part]=(*c,255)
  groups.append({'x_range':[left,right-1],'base_colour':list(c),'band_pixels':int(part.sum()),'recoloured_pixels':int((part&np.any(a!=b,axis=2)).sum())})
 changed=np.any(a!=b,axis=2)
 assert np.array_equal(a[~band],b[~band]) and np.array_equal(a[:,:,3],b[:,:,3])
 black=(a[:,:,3]>0)&(rgb.max(axis=2)<=80);assert np.array_equal(a[black],b[black])
 assert np.array_equal(a[:,120:],b[:,120:])
 for n,arr in [('before',a),('after',b)]:
  im=Image.fromarray(arr);im.save(OUT/(n+'.png'));im.resize((816,144),Image.Resampling.NEAREST).save(OUT/(n+'-6x.png'))
 Image.fromarray(changed.astype('uint8')*255).save(OUT/'changed-mask.png')
 report={'source':str(source.relative_to(ROOT)),'changed_pixels':int(changed.sum()),'groups':groups,'black_contour_changed_pixels':0,'outside_band_mask_changed_pixels':0,'punctuation_changed_pixels':0,'alpha_changed_pixels':0,'rom_built':False,'manifest_changed':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>색 띠 · 그림자 정리</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>주황·노랑·초록 색 띠의 그림자 정리</h1>'
 for z in [1,4,6]:
  page+=f'<section><h2>{z}배 비교</h2><div class="row">'
  for n,t in [('before','색 띠 정리 전'),('after','색 띠를 기본색으로 통일')]:page+=f'<div>{t}<br><img src="{n}.png" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 (OUT/'index.html').write_text(page,encoding='utf8')
 sheet=Image.new('RGB',(840,320),'white')
 for j,n in enumerate(['before','after']):
  im=Image.open(OUT/(n+'-6x.png'));sheet.paste(im,(10,8+j*160),im)
 sheet.save(OUT/'compare-white.png');print(report)
if __name__=='__main__':main()
