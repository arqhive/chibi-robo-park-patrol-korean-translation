from pathlib import Path
import json,hashlib,html,shutil,math
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from scipy.ndimage import label,binary_dilation
from edit_neicon_galmuri7 import glyphs
ROOT=Path(__file__).resolve().parents[1];OLD=ROOT/'work/graphics-draft/neicon-galmuri7';OUT=ROOT/'work/graphics-draft/neicon-v2'
SPLITS={'NEIconGeoCuctus':['수염','무성무성'],'NEIconGeoFBed':['벽돌','벽돌'],'NEIconGeoGrass':['풀','무성무성'],'NEIconGeoGreen':['피어','나세요'],'NEIconGeoHillL':['큰','봉긋'],'NEIconGeoRiver':['강','내기'],'NEIconGeoRoad':['길','내기'],'NEIconGeoRock':['큰','바위'],'NEIconGeoStone':['작은','바위'],'NEIconGeoTree':['잎','무성무성']}
FEEL='NEIconFeelMSG/cell/0'
def main():
 OUT.mkdir(exist_ok=True);p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed'];checks=[];updates={};sheets=[];changed=[]
 for i,r in enumerate(rows):
  key=r['key'];family=key.split('/')[0];stem=key.replace('/','-');loc=r['localization'];assert loc['approval']!='approved';src=Image.open(ROOT/r['path']).convert('RGBA');before=np.array(src);prev=Image.open(OLD/f'{stem}-korean.png').convert('RGBA');icon_end=0 if key==FEEL else 32
  old=before[:,:,3]>0;old[:icon_end]=False;ys,xs=np.where(old);bbox=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1));erased=before.copy();erased[old]=0;erased=Image.fromarray(erased)
  method=loc['editing_method'];lines=loc['lines'];gap=loc.get('letter_gap_px',1);abbreviated=False;placements=[]
  if family in SPLITS:
   lines=SPLITS[family].copy();gap=1
   lines=['무성' if t=='무성무성' and glyphs(t,gap).width+2>src.width else t for t in lines];abbreviated=lines!=SPLITS[family]
   gs=[glyphs(t,gap) for t in lines];hs=[g.height+2 for g in gs];height=sum(hs)+len(hs)-1;y=max(32,min((bbox[1]+bbox[3]-height)//2,src.height-height));ink=Image.new('L',src.size)
   for t,g,h in zip(lines,gs,hs):
    x=(src.width-g.width-2)//2;assert x>=0 and y+h<=src.height;ink.paste(g,(x+1,y+1));placements.append({'line':t,'bbox':[x,y,x+g.width+2,y+h]});y+=h+1
   border=ink.filter(ImageFilter.MaxFilter(3));result=erased.copy();result.paste((16,49,123,255),(0,0,*src.size),border);result.paste((255,255,255,255),(0,0,*src.size),ink)
   assert ''.join(loc['korean_proposal'].split())==''.join(lines) or abbreviated
  elif key==FEEL:
   a=np.array(Image.open(OUT/'feel-imagegen.png').convert('RGBA'));labs,n=label(a[:,:,3]>=128);counts=np.bincount(labs.ravel());keep=counts>=1000;keep[0]=False;support=binary_dilation(keep[labs],iterations=2);a[~support]=0;master=Image.fromarray(a);crop=master.crop(master.getbbox())
   scale=min(126/crop.width,14/crop.height);w,h=round(crop.width*scale),round(crop.height*scale);small=crop.resize((w,h),Image.Resampling.LANCZOS);a=np.array(small);a[a[:,:,3]<8]=0;small=Image.fromarray(a);x=(src.width-w)//2;y=max(0,min((bbox[1]+bbox[3]-h)//2,src.height-h));result=Image.new('RGBA',src.size);result.paste(small,(x,y));method='imagegen';lines=[loc['korean_proposal']];placements=[{'line':lines[0],'bbox':[x,y,x+w,y+h]}]
  else:result=prev.copy()
  after=np.array(result);mask=old|(after[:,:,3]>0);mask[:icon_end]=False
  assert result.size==src.size and np.array_equal(before[:icon_end],after[:icon_end]) and np.array_equal(before[~mask],after[~mask])
  edited=family in SPLITS or key==FEEL
  if not edited:assert np.array_equal(np.array(prev),after)
  if edited:changed.append(key)
  for suffix,im in [('original',src),('previous',prev),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
  path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();sha=hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
  rec={'key':key,'text':loc['korean_proposal'],'lines':lines,'editing_method':method,'changed_this_revision':edited,'size':list(src.size),'letter_gap_px':gap if method=='galmuri' else None,'placements':placements,'abbreviated':abbreviated,'original_dimensions_preserved':True,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'sha256':sha,'runtime_verified':False};checks.append(rec)
  update={'output':path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'neicon-v2','editing_method':method,'lines':lines,'requires_resource_width_expansion':False}
  if family in SPLITS:update.update({'letter_gap_px':1,'method_reason':'사용자 지정 줄바꿈, Galmuri7 정규8px. 무성무성은 외곽선 포함31px로 원본32px 안에 유지','note':'지정 줄바꿈: '+' / '.join(lines)+' · 그림·원본크기 보존. 게임실행 미확인.'})
  if key==FEEL:update.update({'font':None,'font_px':None,'letter_gap_px':None,'method_reason':'사용자 지정 이미지젠 재생성: 흰 글씨·검정 외곽선·굵고 넓은 오른쪽 기울기','note':'이미지젠 원본 참조 재생성. 원본128x16 유지, 팔레트변환·게임실행 미확인.'})
  if r['pixel_sha256'] not in updates:updates[r['pixel_sha256']]=update
  if i%24==0:sheets.append(Image.new('RGB',(1280,1080),'#d3d5cc'))
  sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%24;cx=(j%4)*320;cy=(j//4)*180;d.text((cx+5,cy+3),key+(' [UPDATED]' if edited else ''),fill='black');z=min(2,140//src.width)
  for k,im in enumerate([src,result]):
   big=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST);sheet.paste(big,(cx+5+k*155,cy+25),big)
 for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 report={'references':len(checks),'changed_references':len(changed),'unchanged_references':len(checks)-len(changed),'abbreviations':sum(c['abbreviated'] for c in checks),'items':checks};(ROOT/'metadata/neicon_v2_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 page='<meta charset="utf-8"><title>NEIcon 전체 · 최신 수정</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:18px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}header{position:sticky;top:0;background:#eef1e8;padding:10px;z-index:1}input{font:inherit;padding:6px;width:300px}.badge{color:#176b38}</style><header><b>NEIcon 전체 · 최신 수정</b> · <a href="../../graphics-review/dashboard.html">전체 현황판</a><br><input id="search" placeholder="이름 또는 자원 검색"><span id="count"></span></header><p>전체139개 사용처를 표시합니다. 오늘 기분은?은 이미지젠으로 재제작했고10개 이름의 컬러·회색20도안은 지정한 위치에서 줄을 나눴습니다. 무성무성은31px로 원본폭에 들어가므로 그대로 유지했습니다. 나머지118개 결과는 이전과 같습니다.</p><p>모든 원본 크기·아이콘 보존. 팔레트변환·게임실행 미확인. <a href="../../../metadata/neicon_v2_prompt.json">이미지젠 프롬프트</a></p>'
 for rec in checks:
  stem=rec['key'].replace('/','-');w,h=rec['size'];label_name='이미지젠' if rec['editing_method']=='imagegen' else '갈무리7';page+=f'<section id="{stem}" data-find="{html.escape(rec["key"]+" "+rec["text"],quote=True)}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2><p>'+html.escape(' / '.join(rec['lines']))+' · '+label_name+(' <b class="badge">이번 수정</b>' if rec['changed_this_revision'] else '')+'</p>'
  for z in (1,4):
   page+=f'<p>{z}배 비교</p><div class="row">'
   for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','최신 결과 · '+label_name)]:page+=f'<div>{title}<br><img loading="lazy" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
   page+='</div>'
  page+='</section>'
 page+='<script>const sections=[...document.querySelectorAll("section")];function filter(){const q=document.querySelector("#search").value.toLowerCase();let n=0;for(const s of sections){s.hidden=!s.dataset.find.toLowerCase().includes(q);if(!s.hidden)n++;}document.querySelector("#count").textContent=` ${n}개 전체 표시`;}document.querySelector("#search").addEventListener("input",filter);filter();</script>'
 (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'},ensure_ascii=False))
if __name__=='__main__':main()
