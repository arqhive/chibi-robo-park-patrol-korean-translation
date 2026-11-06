"""Fill only the interrupted outside rim of the approved Piweora word."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image
from scipy import ndimage as nd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/piweora-outer-black-v2'
def main():
 OUT.mkdir(parents=True,exist_ok=False)
 src=ROOT/'work/graphics-approved/full-test-v01/TitleLogo-cell-0.png'
 a=np.array(Image.open(src).convert('RGBA'))
 word=np.array(Image.open(ROOT/'work/graphics-draft/title-top-original-v1/top-layer.png').convert('RGBA'))[:,:,3]>0
 assert np.all(a[:,:,3][word]==255)
 filled=nd.binary_fill_holes(word)
 rim=filled&~nd.binary_erosion(filled,structure=nd.generate_binary_structure(2,1))
 d=nd.distance_transform_edt(filled)
 neutral=np.ptp(a[:,:,:3],axis=2)<=30
 # Recolour the existing dark rim and its gray interruptions; keep the
 # coloured strip as a hard exclusion, even along diagonal edge pixels.
 allowed=word&rim
 b=a.copy();b[allowed]=(0,0,0,255)
 changed=np.any(a!=b,axis=2)
 assert not changed[~word].any() and not changed[~allowed].any()
 assert np.array_equal(a[:,:,3],b[:,:,3])
 assert not changed[40:].any()
 assert np.all(b[:,:,:3][rim]==0)
 Image.fromarray(a).save(OUT/'before.png');Image.fromarray(b).save(OUT/'after.png')
 Image.fromarray(changed.astype('uint8')*255).save(OUT/'changed-mask.png')
 for n,im in [('before',Image.fromarray(a)),('after',Image.fromarray(b))]:
  im.crop((27,5,142,42)).save(OUT/(n+'-word.png'))
  im.crop((27,5,142,42)).resize((690,222),Image.Resampling.NEAREST).save(OUT/(n+'-word-6x.png'))
 report={'source':str(src.relative_to(ROOT)),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'changed_pixels':int(changed.sum()),'outside_word_changes':0,'alpha_changes':0,'rows_40_down_changes':0,'outer_rim_all_black':True,'glyph_and_colour_preservation':'Only the single outermost pixel contour is recoloured. All pixels inside it, including gray band, remain identical.','manifest_changed':False,'rom_built':False}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>피워라 · 바깥 검은 외곽선 채우기</title><style>body{font:16px system-ui;margin:22px;background:#f2f3ed;color:#1e2921}img{image-rendering:pixelated;background:white}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}h1,h2{margin:0 0 12px}</style><h1>피워라 · 바깥 검은 외곽선 채우기</h1>'
 for z in [1,4]:
  page+=f'<section><h2>전체 {z}배</h2><div class="row">'
  for n,title in [('before','현재 확정본'),('after','바깥 검은 선 채움')]:page+=f'<div>{title}<br><img src="{n}.png" width="{192*z}" height="{104*z}"></div>'
  page+='</div></section>'
 page+='<section><h2>피워라 6배</h2><div class="row">'
 for n,title in [('before','현재 확정본'),('after','바깥 검은 선 채움')]:page+=f'<div>{title}<br><img src="{n}-word-6x.png" width="690" height="222"></div>'
 page+='</div></section>'
 (OUT/'index.html').write_text(page,encoding='utf8');print(report)
if __name__=='__main__':main()
