"""Translate launcher captions using precise glyph masks on their orange strips."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from preview_neicon_mono7 import render_line,FONT,FONT_PATH
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/menu-icons-v1'

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='launchers' and r['pixel_sha256'] not in seen:
            rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==26
    # Short source text leaves the rounded label ends visible. Recover the
    # common blank strip, keeping every edge color and only removing glyph pixels.
    donors={}
    for n in [21,22]:
        r=next(r for r in rows if r['key']==f'PCMPGeoSelect/cell/{n}')
        a=np.array(Image.open(ROOT/r['path']).convert('RGBA'));inactive=n==22
        fg=(98,98,98,255) if inactive else (255,255,255,255)
        bg=(98,65,0,255) if inactive else (255,164,0,255)
        strip=a[50:59,4:60].copy();strip[np.all(strip==fg,axis=2)]=bg
        donors[inactive]=strip
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];stem=r['key'].replace('/','-');src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        new=not r['key'].startswith('NewPCLogIn/')
        text='공 미끄럼틀' if loc['japanese_reading']=='流し玉すべり台' else loc['korean_proposal']
        if new:
            assert loc['approval']!='approved'
            inactive=tuple(a[54,6])==(98,65,0,255)
            fg=(98,98,98,255) if inactive else (255,255,255,255)
            strip=a[50:59,4:60];letters=np.all(strip==fg,axis=2);assert letters.any()
            background=donors[inactive]
            assert np.array_equal(strip[~letters],background[~letters]),r['key']
            old=np.zeros(a.shape[:2],bool);old[50:59,4:60]=letters
            clean=a.copy();part=clean[50:59,4:60];part[letters]=background[letters]
            assert np.array_equal(clean[50:59,4:60],background)
            erased=Image.fromarray(clean)
            core,metrics=render_line(text,52);advance=int(FONT.getlength(text));assert advance<=52
            x=(64-advance)//2;y=51
            ink=Image.new('L',src.size);ink.paste(core,(x,y));inkmask=np.array(ink)>0
            assert x>=6 and x+core.width<=58
            result=erased.copy();result.paste(fg,(0,0),ink);b=np.array(result);mask=old|inkmask
            assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:50],b[:50]) and np.array_equal(a[59:],b[59:])
            assert np.array_equal(b[51:58,x:x+core.width][np.array(core)>0],np.tile(fg,(int((np.array(core)>0).sum()),1)))
            for suffix,im in [('erased',erased),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
            output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
            updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'korean_proposal':text,'lines':[text],'draft_version':'menu-icons-v1','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'method_reason':'원본의 한 줄 픽셀 이름표. Mono7 기본8px, 고정 글자칸 중심 정렬.','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'이름표 획 마스크만 제거해 주황 바탕·둥근 모서리 복원. 그림·창 테두리·일반/비활성 상태색 유지. 팔레트변환·게임실행 미확인.'}
            record={'key':r['key'],'new':True,'text':text,'size':list(src.size),'font':'GalmuriMono7','font_px':8,'metrics':metrics,'text_bbox':[x,y,x+core.width,y+7],'inactive':inactive,'foreground':fg,'resized':False,'outside_mask_changed_pixels':0,'icon_changed_pixels':0,'blank_strip_verified':True,'runtime_verified':False}
        else:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA');erased.save(OUT/f'{stem}-erased.png')
            assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256']
            record={'key':r['key'],'new':False,'text':text,'size':list(src.size),'approved_output':loc['output'],'approved_pixels_unchanged':True}
        src.save(OUT/f'{stem}-original.png');result.save(OUT/f'{stem}-korean.png');record['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(record)
        if i%6==0:sheets.append(Image.new('RGB',(1120,870),'#d5d9cf'))
        j=i%6;cx=j%2*560;cy=j//2*290;sheet=sheets[-1];d=ImageDraw.Draw(sheet);d.text((cx+4,cy+3),r['key'],fill='black')
        for k,im in enumerate([src,result]):
            sheet.paste(im,(cx+4+k*275,cy+22),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+4+k*275,cy+90),big)
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'category_total':26,'new_drafts':20,'new_references':refs,'approved_unchanged':6,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks}
    (ROOT/'metadata/graphics_menu_icons_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>메뉴 선택 아이콘26개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>메뉴 선택 아이콘26개</h1><p>신규20개 · 기존 확정6개 유지 · 공 미끄럼틀로 표기</p><a href="../../graphics-review/dashboard.html?category=launchers&revision=menu-icons-v1">카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>'+('신규 · 갈무리Mono7 기본8px' if c['new'] else '기존 확정 유지')+'</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'20 new menu icons / {refs} references; 6 approved images unchanged')

if __name__=='__main__':main()
