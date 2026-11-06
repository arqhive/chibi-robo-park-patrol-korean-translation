from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from preview_titlesave_galmuri9 import glyphs, FONT_PATH
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/batch05-v2'
ITEMS=[('EditPointA/cell/0','here',18),('EditPointA/cell/1','this',16)]
def main():
 OUT.mkdir(exist_ok=True)
 p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'};prepared=[]
 for key,name,icon_y in ITEMS:
  r=rows[key];src=Image.open(ROOT/r['path']).convert('RGBA');crop=glyphs(r['localization']['korean_proposal']);prepared.append((r,name,icon_y,src,crop))
 height=13;checks=[];updates={}
 sheet=Image.new('RGB',(700,2*340),'#d3d5cc');draw=ImageDraw.Draw(sheet)
 for i,(r,name,icon_y,src,crop) in enumerate(prepared):
  stem=r['key'].replace('/','-');before=np.array(src);old=before[:,:,3]>0;old[icon_y:]=False;ys,xs=np.where(old);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
  erased=before.copy();erased[old]=0;erased=Image.fromarray(erased);ink_width=crop.width;height=crop.height+4;w=ink_width+4;x=(src.width-w)//2;y=(box[1]+box[3]-height)//2
  assert 0<=x and x+w<=src.width and y+height<icon_y
  g=crop
  ink=Image.new('L',(w,height));ink.paste(g,(2,2));black=ink.filter(ImageFilter.MaxFilter(3));white=black.filter(ImageFilter.MaxFilter(3))
  small=Image.new('RGBA',(w,height));small.paste((255,255,255,255),(0,0,w,height),white);small.paste((0,0,0,255),(0,0,w,height),black);small.paste((255,238,0,255),(0,0,w,height),ink);a=np.array(small)
  result=erased.copy();result.paste(small,(x,y));after=np.array(result);new=np.zeros(old.shape,dtype=bool);new[y:y+height,x:x+w]=a[:,:,3]>0;mask=old|new
  assert np.array_equal(before[icon_y:],after[icon_y:]);assert np.array_equal(before[~mask],after[~mask])
  previous=Image.open(ROOT/'work/graphics-draft/batch05-v1'/f'{stem}-korean.png').convert('RGBA')
  for suffix,im in [('previous',previous),('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();sha=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':r['key'],'text':r['localization']['korean_proposal'],'size':list(src.size),'source_text_bbox':box,'placed_text_bbox':[x,y,x+w,y+height],'common_art_height':height,'font':'Galmuri9','font_px':10,'glyph_size':list(g.size),'resized':False,'protected_icon_start_y':icon_y,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'requires_resource_width_expansion':False,'sha256':sha,'runtime_verified':False};checks.append(rec)
  updates[r['pixel_sha256']]={'output':path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch05-v2','editing_method':'galmuri','method_reason':'사용자 지정: Galmuri9 정규10px, 글자 리사이즈 없음, 검정1px·흰색1px 테두리. 아래 도형 원본 픽셀 보존','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'원본 캔버스 유지, 글자만 교체. 화살표·원 변경0. 게임 팔레트 변환·실행 미확인.'}
  draw.text((10,i*340+5),r['key']+' / original -> Korean',fill='black')
  for j,im in enumerate([src,result]):
   q=im.resize((im.width*6,im.height*6),Image.Resampling.NEAREST);sheet.paste(q,(10+j*350,i*340+35),q)
 sheet.save(OUT/'overview.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'metadata/graphics_batch05_v2_checks.json').write_text(json.dumps({'tool':'Galmuri9 native 10px + precision masking','font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>다섯 번째 묶음 · 편집 위치 안내</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>다섯 번째 묶음 · 여기 / 이것</h1><p>노란 글씨 → 검은 테두리 → 흰 바깥 테두리. 갈무리9 정규10px로 교체했습니다. 글자를 확대·축소하지 않고 검은 테두리와 흰 테두리를 각각1px로 넣었습니다. 원래 화살표와 원은 그대로 보존했습니다. 두 이미지 모두 원본 크기이며 확장이 없습니다.</p><p>팔레트 변환·게임 실행은 아직 확인하지 않았습니다.</p><a href="../../graphics-review/dashboard.html">현황판</a>'
 for rec in checks:
  stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}"><h2>{rec["key"]} · {rec["text"]}</h2>'
  for z in (1,4):
   page+=f'<p>{z}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('previous','이전 결과'),('korean','갈무리9 10px')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
   page+='</div>'
  page+='</section>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
