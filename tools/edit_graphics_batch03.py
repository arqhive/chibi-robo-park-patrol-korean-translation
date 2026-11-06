from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label,binary_dilation
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch03-v1'
ITEMS=[('DayResultKuro/cell/15','kuro'),('DayResultPark/cell/21','park'),('DayResultPKuro/cell/15','pinkuro')]
def main():
 p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
 prepared=[]
 for key,name in ITEMS:
  r=rows[key];src=Image.open(ROOT/r['path']).convert('RGBA');master=Image.open(OUT/(name+'-imagegen.png')).convert('RGBA');a=np.array(master)
  labs,n=label(a[:,:,3]>=128);counts=np.bincount(labs.ravel());keep=counts>=1000;keep[0]=False;support=binary_dilation(keep[labs],iterations=2)
  a[~support]=0;clean=Image.fromarray(a);crop=clean.crop(clean.getbbox());prepared.append((r,name,src,crop))
 height=min(26,*[int((src.width-2)*crop.height/crop.width) for _,_,src,crop in prepared])
 checks=[];updates={};sheet=Image.new('RGB',(1100,3*180),'#d3d5cc');draw=ImageDraw.Draw(sheet)
 for i,(r,name,src,crop) in enumerate(prepared):
  stem=r['key'].replace('/','-');w=round(crop.width*height/crop.height);small=crop.resize((w,height),Image.Resampling.LANCZOS)
  # Remove alpha below 8/255 after reduction; preserve meaningful antialiasing.
  a=np.array(small);a[a[:,:,3]<8]=0;small=Image.fromarray(a)
  box=src.getbbox();x=(src.width-w)//2;y=(box[1]+box[3]-height)//2
  assert 0<=x and x+w<=src.width and 0<=y and y+height<=src.height
  result=Image.new('RGBA',src.size);result.paste(small,(x,y));erased=Image.new('RGBA',src.size)
  old=np.array(src)[:,:,3]>0;new=np.array(result)[:,:,3]>0;mask=old|new
  assert np.array_equal(np.array(src)[~mask],np.array(result)[~mask])
  for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':r['key'],'text':r['localization']['korean_proposal'],'size':list(src.size),'source_bbox':list(box),'result_bbox':list(result.getbbox()),'common_height_px':height,'uniform_scale':True,'outside_mask_changed_pixels':0,'sha256':digest,'runtime_verified':False};checks.append(rec)
  updates[r['pixel_sha256']]={'output':path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch03-v1','editing_method':'imagegen','method_reason':'장식 결과 제목: 원본 참조 이미지젠 생성 후 동일 높이·비율 유지 합성','work_status':'review','approval':'pending','note':'원본 투명 캔버스 크기 유지. 색 구분·흰 테두리·아래 그림자를 참고해 재현한 검토 시안. 게임 삽입·팔레트 변환 미검증.'}
  draw.text((10,i*180+5),r['key']+' / original -> Korean',fill='black')
  for j,im in enumerate([src,result]):
   z=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(z,(10+j*550,i*180+30),z)
 sheet.save(OUT/'overview.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (ROOT/'metadata/graphics_batch03_checks.json').write_text(json.dumps({'tool':'built-in image_gen + precision composition','items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>세 번째 묶음 · 결과 화면 제목</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>세 번째 묶음 · 결과 화면 제목 3종</h1><p>원본을 참고한 이미지젠 시안입니다. 원본 이미지 크기를 유지하고 세 제목은 같은 높이로 배치했습니다. 원본 | 글자 지운 뒤 | 한글을 비교해 주세요.</p><p>게임 삽입·팔레트 변환·실행은 아직 확인하지 않았습니다.</p><a href="../../graphics-review/dashboard.html">현황판</a> · <a href="../../../metadata/graphics_batch03_prompts.json">생성 프롬프트</a>'
 for rec in checks:
  stem=rec['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2>'
  w,h=rec['size']
  for zoom in (1,4):
   page+=f'<p>{zoom}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
   page+='</div>'
  page+='</section>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
