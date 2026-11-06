from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from edit_graphics_batch02 import glyphs,FONT_PATH
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/batch06-v2'
KEYS=['NEIconBreak/cell/0','NEIconBreak/cell/1','NEIconEndMSG/cell/0','NEIconEndMSG/cell/1']
def main():
 OUT.mkdir(exist_ok=True);p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'};checks=[];updates={};rendered={}
 sheet=Image.new('RGB',(1100,4*270),'#d3d5cc');draw=ImageDraw.Draw(sheet)
 for i,key in enumerate(KEYS):
  r=rows[key];assert r['localization']['approval']!='approved';stem=key.replace('/','-');src=Image.open(ROOT/r['path']).convert('RGBA');before=np.array(src)
  old=before[:,:,3]>0;old[:32]=False;ys,xs=np.where(old);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1));erased=before.copy();erased[old]=0;erased=Image.fromarray(erased)
  text=r['localization']['korean_proposal'];g=glyphs(text);w,h=g.width+2,g.height+2;x=(src.width-w)//2;y=(box[1]+box[3]-h)//2
  assert x>=0 and x+w<=src.width and y>=32 and y+h<=src.height
  ink=Image.new('L',src.size);ink.paste(g,(x+1,y+1));outline=ink.filter(ImageFilter.MaxFilter(3));result=erased.copy();result.paste((16,49,123,255),(0,0,*src.size),outline);result.paste((255,255,255,255),(0,0,*src.size),ink)
  after=np.array(result);mask=old|(np.array(outline)>0);assert np.array_equal(before[:32],after[:32]);assert np.array_equal(before[~mask],after[~mask]);assert outline.getbbox()==(x,y,x+w,y+h)
  if text in rendered:assert np.array_equal(rendered[text][32:],after[32:])
  rendered[text]=after
  previous=Image.open(ROOT/'work/graphics-draft/batch06-v1'/f'{stem}-korean.png').convert('RGBA')
  for suffix,im in [('previous',previous),('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':key,'text':text,'size':list(src.size),'font':'Galmuri7','font_px':8,'glyph_size':list(g.size),'resized':False,'original_text_bbox':box,'result_text_bbox':[x,y,x+w,y+h],'original_text_center_y':(box[1]+box[3])/2,'result_text_center_y':y+h/2,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'requires_resource_width_expansion':False,'sha256':digest,'runtime_verified':False};checks.append(rec)
  updates[r['pixel_sha256']]={'output':path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch06-v2','editing_method':'galmuri','method_reason':'원본은 흰 획·남색1px 테두리의 명확한 도트 글씨. Galmuri7 정규8px, 확대·축소 없음','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'컬러·회색 도구 그림과 원본크기 유지, 원본 텍스트 세로중심 일치. 같은 문구의 두 상태 글자 동일. 팔레트 변환·게임실행 미확인.'}
  draw.text((10,i*270+5),key+' / original | Galmuri9 10px | Galmuri7 8px',fill='black')
  for j,im in enumerate([src,previous,result]):
   q=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(q,(10+j*360,i*270+35),q)
 sheet.save(OUT/'overview.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(ROOT/'metadata/graphics_batch06_v2_checks.json').write_text(json.dumps({'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>여섯 번째 묶음 · 지워요 / 부탁해요</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>여섯 번째 묶음 · 지워요 / 부탁해요</h1><p>갈무리7 정규8px · 흰 글씨와 원본 남색 테두리. 컬러·회색 상태의 도구 그림은 그대로 보존하고 같은 문구의 글자 위치와 크기를 통일했습니다. 원본 캔버스 유지, 글자 리사이즈 없음.</p><p>팔레트 변환·게임실행은 미확인입니다.</p><a href="../../graphics-review/dashboard.html">현황판</a>'
 for rec in checks:
  stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}"><h2>{rec["key"]} · {rec["text"]}</h2>'
  for z in (1,4):
   page+=f'<p>{z}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('previous','갈무리9 10px'),('korean','갈무리7 8px')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
   page+='</div>'
  page+='</section>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))
if __name__=='__main__':main()
