"""Generate review-only native-size sprite candidates. Never writes an approved asset."""
from pathlib import Path
import json, sys, html, hashlib
import numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw, ImageFont
from extract_graphics import palette
ROOT=Path(__file__).resolve().parents[1]
READ=lambda p:json.loads((ROOT/p).read_text('utf-8'))
OUT=ROOT/'work/graphics-draft/title-redo-v1'
FONTS=Path.home()/'AppData/Local/Microsoft/Windows/Fonts'
KEYS=['TitleLogo/cell/1','TitleSave/cell/50','TitleSave/cell/51']
CAP=['터치 해서 시작!','여기를','터치!']
FONT_A=['Galmuri11-Bold','Galmuri9','Galmuri11-Bold']
FONT_B=['Mulmaru','Mulmaru','Mulmaru']
POINTS=[[(8,3),(48,4),(80,4)],[(12,5),(22,5)],[(8,4),(40,4)]]
def box(a):
 y,x=np.where(a);return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def write(p,s):p.write_text(s,encoding='utf-8')
def glyphs(word,fname):
 sz=10 if fname=='Galmuri9' else 12
 font=ImageFont.truetype(str(FONTS/(fname+'.ttf')),sz)
 assert all(font.getmask(c).getbbox() is not None for c in word)
 ims=[]
 for c in word:
  im=Image.new('L',(24,24));d=ImageDraw.Draw(im);d.fontmode='1';d.text((1,0),c,font=font,fill=255)
  b=im.getbbox();ims.append(im.crop((b[0],0,b[2],24)))
 return ims
def badge(ref,i,fname,allowed):
 a=np.array(ref);h,w=a.shape[:2];dst=np.zeros_like(a)
 if i:dst[:]=255
 words=[['터치','해서','시작'],['여기를'],['터치!']][i]
 colors=[[(255,172,65),(255,246,98),(197,222,74)],[(246,238,65)],[(246,164,65)]][i]
 # Centres, horizontal bounds of the source glyphs, and bottom of the white strokes (exclusive).
 layouts=[[(6,33,16),(46,66,16),(78,113,16)],[(5,34,17)],[(6,42,18)]][i]
 # Use the original cell's actual palette swatches (index 0 cannot represent opaque pixels).
 sw=np.array(sorted(allowed),int)
 def nearest(rgb):return sw[((sw-np.array(rgb))**2).sum(1).argmin()].tolist()+[255]
 for word,col,(l,r,bottom) in zip(words,colors,layouts):
  ims=glyphs(word,fname);ww=[im.width for im in ims]
  # Match the source groups without stretching ink or inventing gaps wider than one stroke cluster.
  gap=max(1,min(8 if i==2 else 4,(r-l-sum(ww))//max(1,len(ww)-1)))
  total=sum(ww)+(len(ww)-1)*gap
  x=(l+r-total)//2
  # First word and Save/51 retain the source left edge.
  if i!=1 and word==words[0]:x=l
  gb=[im.getbbox() for im in ims];base=bottom-max(b[3] for b in gb)
  canvas=Image.new('L',(w,h))
  for im in ims:
   canvas.paste(im,(x,base));x+=im.width+gap
  core=np.array(canvas)>0;dist=ndi.distance_transform_edt(~np.pad(core,8))
  # Build the coloured strip from a rounded, joined envelope. Inner black follows
  # actual glyph strokes (including counters); broad concavities keep band colour.
  dilation=dist<=3.0
  hull=ndi.binary_closing(dilation,structure=(np.hypot(*np.ogrid[-3:4,-3:4])<=3))
  hull=ndi.binary_fill_holes(hull)|dilation
  outside=ndi.distance_transform_edt(~hull)
  inside=ndi.distance_transform_edt(hull)
  def mask(m):return m[8:-8,8:-8]
  # One dark perimeter pixel, with gray AA only on diagonal turns;
  # 2px straight band, 1px black, and a white native glyph (original vertical scans).
  dst[mask(outside<=1.45)]=nearest((156,156,156))
  dst[mask(outside<=1.01)]=nearest((24,24,24))
  # Rim coverage at a stair-step comes from the neighbouring band, not noise.
  near=ndi.convolve(hull.astype(int),np.ones((3,3),int),mode='constant')
  dst[mask((outside==1)&(near<=2))]=nearest((65,65,65))
  dst[mask((outside>1)&(outside<=1.45)&(near<=1))]=nearest((189,189,189))
  dst[mask(hull)]=nearest(col)
  # The narrow transitional edge is limited to diagonal, not a mixed-colour inner outline.
  m=mask(hull&(inside<=1.0)&(dist>3.0))
  dst[m]=nearest([v*.87 for v in col])
  dst[mask(dist<=1.50)]=nearest((0,0,0))
  # Corners receive one near-black gray sample; straight strokes stay pure black.
  dst[mask((dist>1.40)&(dist<=1.50))]=nearest((32,32,32))
  dst[core]=nearest((255,255,255))
  # Tiny gray ink-side highlights only at a filled exterior corner; never erase a 1px stroke.
  count=ndi.convolve(core.astype(int),np.ones((3,3),int),mode='constant')
  dst[core&(count==4)&ndi.binary_erosion(ndi.binary_dilation(core))]=nearest((238,238,238))
 if i==0:
  # Identical punctuation remains at its actual coordinates with all original AA.
  dst[:,120:]=a[:,120:]
 return Image.fromarray(dst)
def main():
 if OUT.exists():raise FileExistsError(OUT)
 OUT.mkdir(parents=True)
 manifest=READ('metadata/extraction_manifest.json');inv={r['path']:r for r in READ('metadata/inventory_jp.json')['files']}
 shot=Image.open(ROOT/'work/graphics-review/title-redo-request/00-melonds-screenshot.png').convert('RGB')
 ui=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',14)
 recs=[];sections=[]
 for i,k in enumerate(KEYS):
  row=next(r for r in manifest['graphics'] if r['edition']=='jp' and r['key']==k);stem=k.replace('/','-')
  ref=Image.open(ROOT/row['path']).convert('RGBA');old=Image.open(ROOT/'work/graphics-approved/full-test-v01'/(stem+'.png')).convert('RGBA')
  pl=palette((ROOT/'work/extracted/jp'/inv[k.split('/')[0]+'.NCLR']['disk_file']).read_bytes());available=set(c[:3] for c in pl[1:]);used={p[:3] for p in ref.get_flattened_data() if p[3]}&available
  pa,pb=[badge(ref,i,f,used) for f in (FONT_A[i],FONT_B[i])]
  checks={}
  for name,im in [('original',ref),('approved',old),('A',pa),('B',pb)]:
   im.save(OUT/f'{stem}-{name}.png')
   if name not in ['A','B']:continue
   pix=list(im.get_flattened_data());assert im.size==ref.size and all(p[3] in (0,255) and (p[3]==0 or p[:3] in used) for p in pix)
   if i:assert all(p[3]==255 for p in pix)
   a=np.array(im);sil=(np.any(a[:,:,:3]!=255,2) if i else a[:,:,3]>0)
   checks[name]={'size':im.size,'bbox':box(sil),'opaque_colors':len({p[:3] for p in pix if p[3]}),'outside_palette':0,'opaque_white_background':bool(i)}
  # Exact samples; sample from the source image, not inferred from the draft.
  ra=np.array(ref);measure=[]
  for x,y in POINTS[i]:
   sample=['#'+bytes(ra[yy,x,:3]).hex() for yy in range(y,y+5)];assert sample[0]=='#000000' and sample[3]=='#000000' and sample[4]=='#ffffff',sample
   measure.append({'x':x,'y':y,'direction':'down','pixels':sample,'outer_dark_px':1,'band_px':2,'inner_black_px':1})
  cx,cy=(18,28) if not i else (20,465);w,h=ref.size;bg=Image.fromarray(np.array(shot)[cy:cy+h*2:2,cx:cx+w*2:2].copy())
  # Source screenshot is displayed at 2x. Sample an actual blank rectangle, no old lettering.
  assert len(bg.getcolors(100000))==1,(k,bg.getcolors(100000)[:5])
  bg.save(OUT/f'{stem}-game-background.png')
  ims=[ref,old,pa,pb];names=['일본판 원본','현재 확정본',f'A · {FONT_A[i]}',f'B · {FONT_B[i]}']
  cw=max(180,w*4+16);sheet=Image.new('RGB',(cw*4+24,430),'#eef1eb');dr=ImageDraw.Draw(sheet)
  dr.text((12,5),k+'   '+CAP[i],font=ui,fill='#18251f')
  for j,(im,title) in enumerate(zip(ims,names)):
   x=12+j*cw;dr.text((x,39),title,font=small,fill='black')
   for top,baseimg,label in [(65,Image.new('RGB',ref.size,'white'),'흰 배경'),(244,bg,'게임 배경')]:
    dr.text((x,top),label+' · 1배 / 4배',font=small,fill='#425047');flat=baseimg.copy();flat.paste(im,mask=im.getchannel('A'));sheet.paste(flat,(x,top+24));sheet.paste(flat.resize((w*4,h*4),Image.Resampling.NEAREST),(x,top+54))
  sheet.save(OUT/f'{stem}-sheet.png')
  recs.append(dict(key=k,text=CAP[i],measurements=measure,checks=checks,fonts=[FONT_A[i],FONT_B[i]],game_background_xy=[cx,cy]))
  block=f'<section><h2>{CAP[i]}</h2><p>{k} · {w}×{h}px · <a href="{stem}-sheet.png">두 후보 전체 시트</a></p><div class="row">'
  for suffix,title in zip(['original','approved','A','B'],names):
   block+=f'<div class="cell {suffix}"><b>{title}</b>'
   for z in (1,4):
    block+=f'<div class="pane"><img class="sprite" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}" style="--scene:url({stem}-game-background.png);--dims:{w*z}px {h*z}px" alt="{title} {z}배"><small>{z}배</small></div>'
   block+='</div>'
  sections.append(block+'</div></section>')
 info="""<section><h2>원본에서 잰 단면</h2><p>좌표는 원본 PNG의 왼쪽 위가 (0,0). 아래 표는 위에서 아래로 읽은 연속 픽셀이며, 가로 방향에서는 글자 모양에 따라 띠가 달라집니다.</p><table><tr><th>원본 글자</th><th>단면 시작 (x,y)</th><th>바깥 어두운 선</th><th>색 띠</th><th>안쪽 검정</th><th>안쪽·바깥쪽 AA 표본</th></tr><tr><td>タ / し / ス</td><td>(8,3) / (48,4) / (80,4)</td><td>1px</td><td>2px</td><td>1px</td><td>タ: 안쪽 #dedede (8,9), 바깥 #626262 (8,19)</td></tr><tr><td>コ / コ</td><td>(12,5) / (22,5)</td><td>1px</td><td>2px</td><td>1px</td><td>안쪽 #9c9c9c (12,16), 바깥 #626262 (12,20)</td></tr><tr><td>タ / ！</td><td>(8,4) / (40,4)</td><td>1px</td><td>2px</td><td>1px</td><td>！: 안쪽 #8b8b8b (40,14), 바깥 #626262 (40,21)</td></tr></table><p>가로 단면 예: ‘コ’ y=12, x=3에서 바깥 #414141 → #b4ac29 → 노랑 #f6ee41 5px → #d5cd39 → #202020 → 흰 획. ‘タ’ y=12, x=1에서 바깥 #414141 → #b47b29 → 주황 #f6a441 1px → #413110 → 안쪽 회색.</p><p><a href="measurements.json">측정 좌표·시안별 팔레트/크기 검사</a></p></section>"""
 head="""<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>타이틀 글씨 · 1차 비교</title><style>body{font:16px/1.5 system-ui;background:#f1f2eb;color:#18251f;margin:20px}section{background:white;padding:16px;margin:14px 0;border:1px solid #d7dacc;border-radius:10px}h1,h2,p{margin:0 0 8px}.row,nav{display:flex;flex-wrap:wrap;gap:16px}nav{position:sticky;top:0;padding:10px;background:#e4e9dc;z-index:1}.pane{margin:8px 0}.pane small{display:block;color:#53624f}.sprite{image-rendering:pixelated;background:white;vertical-align:top;outline:1px solid #ddded7}body.scene .sprite{background-image:var(--scene);background-size:var(--dims)}body:not(.both) .B{display:none}body.alt:not(.both) .A{display:none}body.alt:not(.both) .B{display:block}select{font:inherit}table{border-collapse:collapse}td,th{padding:5px;border:1px solid #cccebd;text-align:left}</style><h1>타이틀 글씨 · 1차</h1><p>원본과 현재 확정본을 기준으로 새 글씨를 1배·4배에서 비교하세요.</p><nav><label>시안 <select onchange="document.body.classList.toggle('alt',this.value=='B');document.body.classList.toggle('both',this.value=='both')"><option>A</option><option>B</option><option value="both">A와 B 함께</option></select></label><label>배경 <select onchange="document.body.classList.toggle('scene',this.value=='game')"><option>흰색</option><option value="game">실제 게임 화면에서 채취</option></select></label></nav>"""
 write(OUT/'index.html',head+''.join(sections)+info+'</html>')
 write(OUT/'measurements.json',json.dumps(recs,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
