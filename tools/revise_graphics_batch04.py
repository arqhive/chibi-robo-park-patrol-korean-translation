from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from edit_graphics_batch02 import glyphs as native_glyphs
from scipy.ndimage import label,binary_dilation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/batch04-v2'
ITEMS=[('DayResultKuro/cell/14','flowers'),('DayResultPKuro/cell/14','flowers'),('DayResultPark/cell/22','people')]
def main():
 p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
 checks=[];updates={};sheet=Image.new('RGB',(720,3*160),'#d3d5cc');draw=ImageDraw.Draw(sheet)
 for i,(key,name) in enumerate(ITEMS):
  r=rows[key];assert r['localization']['approval']!='approved'
  src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(Image.open(OUT/(name+'-imagegen.png')).convert('RGBA'))
  labs,n=label(a[:,:,3]>=128);counts=np.bincount(labs.ravel());keep=counts>=1000;keep[0]=False;support=binary_dilation(keep[labs],iterations=2);a[~support]=0
  master=Image.fromarray(a);crop=master.crop(master.getbbox());box=src.getbbox();height=min(14,int(14*crop.height/crop.width));w=round(crop.width*height/crop.height)
  small=crop.resize((w,height),Image.Resampling.LANCZOS);a=np.array(small);a[a[:,:,3]<8]=0;small=Image.fromarray(a)
  x=box[0] if w>src.width-2 else (src.width-w)//2;y=(box[1]+box[3]-height)//2
  canvas=src.size;expanded=False
  assert x+w<=src.width and y+height<=src.height
  result=Image.new('RGBA',canvas);result.paste(small,(x,y));erased=Image.new('RGBA',src.size)
  if name=='flowers':
   # Readable native dot strokes for the approved compact layout; no glyph resizing.
   ink=Image.new('L',src.size)
   for text,xy in [('송',(1,2)),('이',(8,8))]:ink.paste(native_glyphs(text),xy)
   outline=ink.filter(ImageFilter.MaxFilter(3));outer=outline.filter(ImageFilter.MaxFilter(3))
   yy,xx=np.indices((src.height,src.width));accent=(np.array(outer)>0)&(np.array(outline)==0)&(((xx+yy)%3)==0)
   result=Image.new('RGBA',src.size)
   result.paste((164,106,0,255),(0,0,*src.size),Image.fromarray(accent.astype('uint8')*255))
   result.paste((24,24,24,255),(0,0,*src.size),outline);result.paste((255,255,255,255),(0,0,*src.size),ink)

  padded=np.zeros((canvas[1],canvas[0],4),dtype=np.uint8);padded[:,:src.width]=np.array(src)
  mask=(padded[:,:,3]>0)|(np.array(result)[:,:,3]>0)
  assert np.array_equal(padded[~mask],np.array(result)[~mask]);assert y>=0 and y+height<=src.height
  stem=key.replace('/','-')
  previous=Image.open(ROOT/'work/graphics-draft/batch04-v1'/f'{stem}-korean.png').convert('RGBA')
  for suffix,im in [('previous',previous),('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':key,'text':r['localization']['korean_proposal'],'original_size':list(src.size),'preview_size':list(canvas),'source_bbox':list(box),'result_bbox':list(result.getbbox()),'art_height_px':result.getbbox()[3]-result.getbbox()[1],'requires_resource_width_expansion':expanded,'uniform_scale':name!='flowers','native_dot_refinement':name=='flowers','outside_mask_changed_pixels':0,'sha256':digest,'runtime_verified':False};checks.append(rec)
  updates[r['pixel_sha256']]={'output':None if expanded else path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch04-v2','editing_method':'galmuri' if name=='flowers' else 'imagegen','method_reason':'이미지젠으로 대각선·색 구조 재생성 후 작은 송이 획은 Galmuri7 정규8px 도트로 정리. 명은 이미지젠 축소. 원본16x16 유지','work_status':'review','approval':'pending','requires_resource_width_expansion':expanded,'note':'흰 글씨·검은 외곽선·색 장식. 원본16x16 유지. 송이는7px 획 대각선 배치, 명은14px 높이. '+('송이 두 글자 폭 확장 필요, 미리보기만 제공.' if expanded else '원본16x16 크기 유지.')+' 팔레트 변환·실행 미검증.'}
  draw.text((10,i*160+5),key+' / original -> Korean',fill='black')
  for j,im in enumerate([src,result]):
   z=im.resize((im.width*6,im.height*6),Image.Resampling.NEAREST);sheet.paste(z,(10+j*350,i*160+35),z)
 sheet.save(OUT/'overview.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'metadata/graphics_batch04_v2_checks.json').write_text(json.dumps({'tool':'built-in image_gen + precision composition','items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>네 번째 묶음 · 수량 단위</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.note{color:#8a4911}</style><h1>네 번째 묶음 · 송이 2종 / 명</h1><p>흰 글씨 → 검은 외곽선 → 주황색/녹색 장식 픽셀 순서로 수정했습니다. 송이는 왼쪽 위 송 / 오른쪽 아래 이로 배치했습니다. 송이의 작은 획은 갈무리7 정규 도트로 정리했으며 명은 이미지젠 결과입니다. 세 이미지 모두 원본16×16 크기입니다.</p><p>캔버스·리소스 폭 확장 없이 배치했습니다. 팔레트 변환·게임 실행은 아직 확인하지 않았습니다.</p><a href="../../graphics-review/dashboard.html">현황판</a> · <a href="../../../metadata/graphics_batch04_v2_prompts.json">생성 프롬프트</a>'
 for rec in checks:
  stem=rec['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2>'
  if rec['requires_resource_width_expansion']:page+=f'<p class="note">원본 폭16px → 미리보기 폭{rec["preview_size"][0]}px. 리소스 확장 필요.</p>'
  for zoom in (1,4):
   page+=f'<p>{zoom}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('previous','이전 결과'),('korean','수정 결과 · 16×16')]:
    with Image.open(OUT/f'{stem}-{suffix}.png') as im:w,h=im.size
    page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
   page+='</div>'
  page+='</section>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
