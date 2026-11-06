"""Review-only contour repair for the approved Korean lettering, at native resolution."""
import json,sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as nd
from extract_graphics import palette
from build_full_graphics import quantize
ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'work/graphics-draft/title-redo-v2'
PREV=ROOT/'work/graphics-draft/title-redo-v1'
KEYS=['TitleLogo/cell/1','TitleSave/cell/50','TitleSave/cell/51']
CAP=['터치 해서 시작!','여기를','터치!']
# Trace the missing syllable on the native grid, following the rounded source
# artwork (batch01-v1/here-imagegen.png); no font or downsampled image in output.
REUL=['.#######..','......##..','.#######..','.##.......','.#######..','..........','#########.','..........','.#######..','......##..','.#######..','.##.......','.#######..']
def main():
 DEST.mkdir(exist_ok=False)
 inv={r['path']:r for r in json.loads((ROOT/'metadata/inventory_jp.json').read_text('utf8'))['files']}
 sections=[];report=[]
 for i,key in enumerate(KEYS):
  stem=key.replace('/','-')
  src=Image.open(PREV/(stem+'-original.png')).convert('RGBA');approved=Image.open(ROOT/'work/graphics-approved/full-test-v01'/(stem+'.png')).convert('RGBA')
  a=np.array(approved);h,w=a.shape[:2]; yy,xx=np.indices((h,w))
  pal=palette((ROOT/'work/extracted/jp'/inv[key.split('/')[0]+'.NCLR']['disk_file']).read_bytes())
  sw=np.array(sorted(set(c[:3] for c in src.get_flattened_data() if c[3]) & {p[:3] for p in pal[1:]}),int)
  def rgba(rgb):return tuple(sw[((sw-np.array(rgb))**2).sum(1).argmin()])+(255,)
  out=np.zeros_like(a)
  if i:out[:]=255
  orig_ink=(a[:,:,3]>0)&(a[:,:,:3].min(axis=2)>=213)&(np.ptp(a[:,:,:3],axis=2)<=27)
  repair=(xx>=26) if i==1 else np.zeros((h,w),bool)
  core=orig_ink&~repair
  if i==1:
   for j,row in enumerate(REUL):
    for x,ch in enumerate(row):
     if ch=='#':core[6+j,26+x]=True
  translucent=np.zeros((h,w),bool)
  for left,right,col in ([(0,39,(255,172,65)),(39,80,(255,246,98)),(80,120,(197,222,74)),(120,136,(246,164,65))] if i==0 else [(0,w,((246,238,65) if i==1 else (246,164,65)))]):
   select=(xx>=left)&(xx<right);ink=np.pad(core&select,8);dist=nd.distance_transform_edt(~ink)
   silhouette=np.pad(select&(a[:,:,3]>0)&~repair,8)
   # Keep Korean plaque shape, only smooth very small rim steps. A minimum
   # two-pixel band around ink prevents any dark rim from touching white.
   band=(nd.gaussian_filter(silhouette.astype(float),.78)>.53)|(dist<=2.75)
   band=nd.binary_fill_holes(band)
   band=nd.binary_closing(band,structure=(np.hypot(*np.ogrid[-2:3,-2:3])<=2))|band
   edge=nd.distance_transform_edt(~band)
   near=nd.convolve(band.astype(int),np.ones((3,3),int))
   def put(mask,c):
    mask=mask[8:-8,8:-8]&select
    out[mask]=rgba(c)
   put(edge<=1.42,(164,164,164));put((edge<=1.42)&(near<=1),(189,189,189))
   put(edge<=1,(32,32,32));put((edge==1)&(near<=2),(65,65,65));put(band,col)
   put((dist<=1.5),(26,26,26));put((dist<=1),(0,0,0));put(ink,(255,255,255))
  protected=orig_ink&~repair
  out[protected]=a[protected]
  assert np.array_equal(out[protected],a[protected])
  colors=Image.fromarray(out).getcolors(w*h);delta=sum(n for n,p in colors if p[3] and pal[quantize(p,pal,8,0,{})][:3]!=p[:3]);assert delta==0
  if i:assert np.all(out[:,:,3]==255)
  report.append({'key':key,'size':[w,h],'retained_white_and_AA_pixels':int(protected.sum()),'changed_among_retained':0,'letter_repair':'를' if i==1 else None,'palette_changes':delta})
  new=Image.fromarray(out);new.save(DEST/(stem+'.png'));imgs=[src,approved,new]
  titles=['일본판 원본','기존 한글 확정본','기존 글씨 + 외곽선 수정']
  cells=''
  for j,(im,title) in enumerate(zip(imgs,titles)):
   file=[f'../title-redo-v1/{stem}-original.png',f'../title-redo-v1/{stem}-approved.png',f'{stem}.png'][j]
   cells+=f'<div><b>{title}</b>'
   for z in (1,4):
    cells+=f'<small>{z}배</small><img src="{file}" width="{w*z}" height="{h*z}" style="--bg:url(../title-redo-v1/{stem}-game-background.png);--s:{w*z}px {h*z}px">'
   cells+='</div>'
  sections.append(f'<section><h2>{CAP[i]}</h2><p>{key} · {w}×{h}px</p><div class="rows">{cells}</div></section>')
 page="""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name=viewport content="width=device-width, initial-scale=1"><title>타이틀 글씨 · 기존 한글 획 보존</title><style>body{font:16px/1.5 system-ui;background:#f0f2ec;color:#202a25;margin:22px}h1,h2,p{margin:0 0 8px}section{background:white;border-radius:10px;padding:16px;margin:16px 0}.rows{display:flex;flex-wrap:wrap;gap:18px}small,b,img{display:block}small{margin:8px 0 2px}img{image-rendering:pixelated;background:white;outline:1px solid #ddd}body.game img{background-image:var(--bg);background-size:var(--s)}label{background:#e1e7da;padding:6px}</style><h1>타이틀 글씨 · 1차 세 문구</h1><p>기존 한글 확정본의 흰 획과 위치를 유지했습니다. 회색으로 뭉친 ‘를’만 다시 그렸습니다.</p><label><input type=checkbox onchange="document.body.classList.toggle('game',this.checked)">게임 화면 배경으로 보기</label>"""
 (DEST/'index.html').write_text(page+''.join(sections)+'</html>',encoding='utf8')
 (DEST/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
 print(report)
if __name__=='__main__':main()
