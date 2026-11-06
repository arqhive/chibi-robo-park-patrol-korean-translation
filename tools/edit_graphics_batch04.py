from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label,binary_dilation
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/batch04-v1'
ITEMS=[('DayResultKuro/cell/14','flowers'),('DayResultPKuro/cell/14','flowers'),('DayResultPark/cell/22','people')]
def main():
 p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
 checks=[];updates={};sheet=Image.new('RGB',(720,3*160),'#d3d5cc');draw=ImageDraw.Draw(sheet)
 for i,(key,name) in enumerate(ITEMS):
  r=rows[key];assert r['localization']['approval']!='approved'
  src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(Image.open(OUT/(name+'-imagegen.png')).convert('RGBA'))
  labs,n=label(a[:,:,3]>=128);counts=np.bincount(labs.ravel());keep=counts>=1000;keep[0]=False;support=binary_dilation(keep[labs],iterations=2);a[~support]=0
  master=Image.fromarray(a);crop=master.crop(master.getbbox());box=src.getbbox();height=14;w=round(crop.width*height/crop.height)
  small=crop.resize((w,height),Image.Resampling.LANCZOS);a=np.array(small);a[a[:,:,3]<8]=0;small=Image.fromarray(a)
  x=box[0] if w>src.width-2 else (src.width-w)//2;y=(box[1]+box[3]-height)//2
  canvas=(max(src.width,x+w),src.height);expanded=canvas!=src.size
  result=Image.new('RGBA',canvas);result.paste(small,(x,y));erased=Image.new('RGBA',src.size)
  padded=np.zeros((canvas[1],canvas[0],4),dtype=np.uint8);padded[:,:src.width]=np.array(src)
  mask=(padded[:,:,3]>0)|(np.array(result)[:,:,3]>0)
  assert np.array_equal(padded[~mask],np.array(result)[~mask]);assert y>=0 and y+height<=src.height
  stem=key.replace('/','-')
  for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':key,'text':r['localization']['korean_proposal'],'original_size':list(src.size),'preview_size':list(canvas),'source_bbox':list(box),'result_bbox':list(result.getbbox()),'common_height_px':height,'requires_resource_width_expansion':expanded,'uniform_scale':True,'outside_mask_changed_pixels':0,'sha256':digest,'runtime_verified':False};checks.append(rec)
  updates[r['pixel_sha256']]={'output':None if expanded else path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch04-v1','editing_method':'imagegen','method_reason':'수량 단위 원본 참조 이미지젠 생성, 송이 두 화면은 같은 마스터 사용','work_status':'review','approval':'pending','requires_resource_width_expansion':expanded,'note':'원본 세로 중심과 14px 높이 유지, 비율 유지 축소. '+('송이 두 글자 폭 확장 필요, 미리보기만 제공.' if expanded else '원본16x16 크기 유지.')+' 팔레트 변환·실행 미검증.'}
  draw.text((10,i*160+5),key+' / original -> Korean',fill='black')
  for j,im in enumerate([src,result]):
   z=im.resize((im.width*6,im.height*6),Image.Resampling.NEAREST);sheet.paste(z,(10+j*350,i*160+35),z)
 sheet.save(OUT/'overview.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'metadata/graphics_batch04_checks.json').write_text(json.dumps({'tool':'built-in image_gen + precision composition','items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>네 번째 묶음 · 수량 단위</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.note{color:#8a4911}</style><h1>네 번째 묶음 · 송이 2종 / 명</h1><p>이미지젠 시안을 원본 글자 높이14px와 세로 중심에 맞췄습니다. 송이 두 화면은 같은 글자 모양을 사용합니다.</p><p>송이는 폭 확장이 필요한 미리보기입니다. 실제 리소스 확장·팔레트 변환·게임 실행은 미확인입니다.</p><a href="../../graphics-review/dashboard.html">현황판</a> · <a href="../../../metadata/graphics_batch04_prompts.json">생성 프롬프트</a>'
 for rec in checks:
  stem=rec['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2>'
  if rec['requires_resource_width_expansion']:page+=f'<p class="note">원본 폭16px → 미리보기 폭{rec["preview_size"][0]}px. 리소스 확장 필요.</p>'
  for zoom in (1,4):
   page+=f'<p>{zoom}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:
    with Image.open(OUT/f'{stem}-{suffix}.png') as im:w,h=im.size
    page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
   page+='</div>'
  page+='</section>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
