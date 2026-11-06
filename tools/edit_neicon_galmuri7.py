from pathlib import Path
from functools import lru_cache
import json,hashlib,html,math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from edit_graphics_batch02 import FONT,FONT_PATH
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/neicon-galmuri7'
@lru_cache(None)
def glyphs(text,gap=1):
 parts=[];x=0
 for char in text:
  if char==' ':x+=2;continue
  im=Image.new('L',(32,32));d=ImageDraw.Draw(im);d.fontmode='1';d.text((4,4),char,font=FONT,fill=255);box=im.getbbox();parts.append((im.crop(box),x,box[1]));x+=box[2]-box[0]+gap
 top=min(y for _,_,y in parts);bottom=max(y+g.height for g,_,y in parts);out=Image.new('L',(x-gap,bottom-top))
 for g,x,y in parts:out.paste(g,(x,y-top))
 return out
@lru_cache(None)
def wrap(text,width,gap):
 if not text:return (),0
 options=[]
 for n in range(1,len(text)+1):
  first=text[:n].rstrip();rest=text[n:].lstrip()
  if not first or glyphs(first,gap).width+2>width:continue
  tail=wrap(rest,width,gap)
  if tail is None:continue
  lines=(first,)+tail[0];split=int(n<len(text) and text[n-1]!=' ' and text[n]!=' ');breaks=split+tail[1]
  widths=[glyphs(t,gap).width+2 for t in lines]
  cost=(len(lines),breaks,max(widths)-min(widths),max(widths))
  options.append((cost,(lines,breaks)))
 return min(options,key=lambda x:x[0])[1] if options else None

def main():
 OUT.mkdir(exist_ok=True);p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed'];checks=[];updates={};sheets=[]
 for i,r in enumerate(rows):
  key=r['key'];stem=key.replace('/','-');loc=r['localization'];assert loc['approval']!='approved';text=loc['korean_proposal'];src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);icon_end=0 if src.height==16 else 32
  old=a[:,:,3]>0;old[:icon_end]=False;ys,xs=np.where(old);box=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1));erased=a.copy();erased[old]=0;erased=Image.fromarray(erased)
  for gap in (1,0):
   plan=wrap(text,src.width,gap)
   if plan is None:continue
   lines=plan[0];gs=[glyphs(t,gap) for t in lines];hs=[g.height+2 for g in gs];total=sum(hs)+len(hs)-1
   if total<=src.height-icon_end:break
  else:raise ValueError((key,text,'cannot fit'))
  assert ''.join(text.split())==''.join(''.join(lines).split())
  y=max(icon_end,min((box[1]+box[3]-total)//2,src.height-total));start_y=y
  ink=Image.new('L',src.size);placements=[]
  for line,g,h in zip(lines,gs,hs):
   x=(src.width-g.width-2)//2;assert x>=0;ink.paste(g,(x+1,y+1));placements.append({'line':line,'bbox':[x,y,x+g.width+2,y+h]});y+=h+1
  border=ink.filter(ImageFilter.MaxFilter(3));color=(0,0,0,255) if icon_end==0 else (16,49,123,255)
  result=erased.copy();result.paste(color,(0,0,*src.size),border);result.paste((255,255,255,255),(0,0,*src.size),ink);b=np.array(result);mask=old|(np.array(border)>0)
  assert src.size==result.size and np.array_equal(a[:icon_end],b[:icon_end]) and np.array_equal(a[~mask],b[~mask])
  assert all(0<=v['bbox'][0]<v['bbox'][2]<=src.width and icon_end<=v['bbox'][1]<v['bbox'][3]<=src.height for v in placements)
  for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();sha=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':key,'source_hash':r['pixel_sha256'],'text':text,'lines':list(lines),'font':'Galmuri7','font_px':8,'letter_gap_px':gap,'size':list(src.size),'placements':placements,'source_text_bbox':list(box),'source_center_y':(box[1]+box[3])/2,'result_center_y':start_y+total/2,'resized':False,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'clipped_pixels':0,'requires_resource_width_expansion':False,'sha256':sha,'runtime_verified':False};checks.append(rec)
  update={'output':path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'neicon-galmuri7','editing_method':'galmuri','method_reason':'사용자 지정 NEIcon 전체 Galmuri7 정규8px. 원본 크기 유지, 글자 리사이즈 없음','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'font':'Galmuri7','font_px':8,'lines':list(lines),'letter_gap_px':gap,'note':'흰 획·원본 계열 테두리, 그림 변경0. '+('긴 이름은 자간0px로 배치. ' if gap==0 else '')+' / '.join(lines)+' · 게임실행 미확인.'}
  if r['pixel_sha256'] in updates:assert update['lines']==updates[r['pixel_sha256']]['lines']
  else:updates[r['pixel_sha256']]=update
  if i%24==0:sheets.append(Image.new('RGB',(1280,1080),'#d3d5cc'))
  sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%24;cx=(j%4)*320;cy=(j//4)*180;d.text((cx+5,cy+3),key,fill='black');z=min(2,140//src.width)
  for k,im in enumerate([src,result]):
   big=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST);sheet.paste(big,(cx+5+k*155,cy+25),big)
 for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report={'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'references':len(rows),'unique_source_images':len(updates),'zero_gap_items':[c['key'] for c in checks if c['letter_gap_px']==0],'all_original_dimensions_preserved':True,'items':checks}
 (ROOT/'metadata/neicon_galmuri7_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>NEIcon 전체 · 갈무리7</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:18px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}header{position:sticky;top:0;background:#eef1e8;padding:10px;z-index:1}input{font:inherit;padding:6px;width:300px}</style><header><b>NEIcon 전체 · 갈무리7 정규8px</b> · <a href="../../graphics-review/dashboard.html">전체 현황판</a><br><input id="search" placeholder="이름 또는 자원 검색"><span id="count"></span></header><p>139개 사용처 / 중복 제외138도안. 전체 항목을 한 번에 표시합니다. 흰 글씨·원본 계열 테두리, 원본 크기와 아이콘 보존, 글자 리사이즈 없음. 긴 이름은 줄바꿈하고 치비 출발·도착점과 치비 매달리기 봉의4도안은 자간0px로 맞췄습니다. 팔레트 변환·게임실행은 미확인입니다.</p>'
 for rec in checks:
  stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}" data-find="{html.escape(rec["key"]+" "+rec["text"],quote=True)}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2><p>'+html.escape(' / '.join(rec['lines']))+f' · 자간{rec["letter_gap_px"]}px</p>'
  for z in (1,4):
   page+=f'<p>{z}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','갈무리7')]:page+=f'<div>{title}<br><img loading="lazy" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
   page+='</div>'
  page+='</section>'
 page+='<script>const sections=[...document.querySelectorAll("section")];function filter(){const q=document.querySelector("#search").value.toLowerCase();let n=0;for(const s of sections){s.hidden=!s.dataset.find.toLowerCase().includes(q);if(!s.hidden)n++;}document.querySelector("#count").textContent=` ${n}개 전체 표시`;}document.querySelector("#search").addEventListener("input",filter);filter();</script>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'},ensure_ascii=False))
if __name__=='__main__':main()
