"""User-requested one-line captions and fixed-cell tool-label alignment."""
from pathlib import Path
import hashlib, json, html
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from preview_neicon_mono7 import render_line, FONT

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/icon-alignment-v1'
SINGLE={'cassette':{'강 내기','길 내기','큰 바위','큰 봉긋'},'park':{'강 내기','길 내기'}}

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    categories=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    checks=[];updates={};seen=set();sheets=[]
    for row in m['graphics']:
        if row['edition']!='jp' or row['pixel_sha256'] not in categories:continue
        loc=row['localization'];category=categories[row['pixel_sha256']]['category'];text=loc['korean_proposal']
        one_line=text in SINGLE.get(category,set())
        if not one_line and category!='tools':continue
        digest=row['pixel_sha256']
        if digest in seen:continue
        seen.add(digest)
        stem=row['key'].replace('/','-')
        previous_path=loc.get('alignment_previous_output',loc['output'])
        previous=Image.open(ROOT/previous_path).convert('RGBA');a=np.array(previous)
        lines=[text] if one_line else loc['lines']
        y0=36 if one_line else 33
        # The one-line sold-out label and the lettering inside its icon are already aligned.
        unchanged_sold_out=category=='tools' and len(lines)==1
        cleaned=a.copy();cleaned[32:]=0
        ink=Image.new('L',previous.size);placements=[]
        for i,line in enumerate(lines):
            glyph,metrics=render_line(line,previous.width-2)
            advance=int(FONT.getlength(line))
            fixed=category=='tools' and advance<=previous.width-2
            x=(previous.width-advance)//2 if fixed else (previous.width-glyph.width)//2
            yy=y0+i*10+1
            assert x>=1 and x+glyph.width+1<=previous.width
            assert yy+8<=previous.height
            ink.paste(glyph,(x,yy))
            placements.append(dict(metrics,ink_origin=[x,yy],advance=advance,alignment='native_fixed_cells' if fixed else 'center_ink',native_glyph_shapes_preserved=True))
        edge=ink.filter(ImageFilter.MaxFilter(3));overlay=Image.new('RGBA',previous.size)
        overlay.paste((16,49,123,255),(0,0),edge);overlay.paste((255,255,255,255),(0,0),ink)
        erased=Image.fromarray(cleaned);result=Image.alpha_composite(erased,overlay)
        if unchanged_sold_out:result=previous.copy()
        b=np.array(result);changed=np.any(a!=b,axis=2)
        assert np.array_equal(a[:32],b[:32])
        assert previous.size==result.size
        if unchanged_sold_out:assert not changed.any()
        if category=='tools' and not unchanged_sold_out:
            assert result.crop((0,32,32,33)).getbbox() is None
            assert result.crop((0,33,32,34)).getbbox() is not None
        for suffix,im in [('previous',previous),('korean',result),('erased',erased),('mask',Image.fromarray(changed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        src=Image.open(ROOT/row['path']).convert('RGBA');src.save(OUT/f'{stem}-original.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        record={'key':row['key'],'category':category,'text':text,'lines':lines,'size':list(result.size),'placements':placements,'changed_pixels':int(changed.sum()),'icon_changed_pixels':0,'outside_caption_changed_pixels':0,'resized':False,'font':'GalmuriMono7','font_px':8,'previous_output':previous_path,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False}
        checks.append(record)
        if changed.any():
            updates[digest]={'alignment_previous_output':previous_path,'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'lines':lines,'draft_version':'icon-alignment-v1','approval':'pending','work_status':'review','font':'GalmuriMono7','font_px':8,'note':'요청한 이름 한 줄 처리 및 도구 이름 고정 글자칸 정렬. 두 줄 이름은 그림 아래1px 여백. 원본 그림·규격·폰트 획 유지. 팔레트변환·게임실행 미확인.'}
        j=len(checks)-1
        if j%8==0:sheets.append(Image.new('RGB',(1120,1080),'#d6dacf'))
        sheet=sheets[-1];draw=ImageDraw.Draw(sheet);x=j%2*560;y=(j%8)//2*270
        draw.text((x+5,y+3),row['key']+'   BEFORE / AFTER',fill='black')
        for col,im in enumerate([previous,result]):
            sheet.paste(im,(x+10+col*270,y+24),im)
            zoom=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(zoom,(x+85+col*270,y+55),zoom)
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    count=0
    for row in m['graphics']:
        if row['edition']=='jp' and row['pixel_sha256'] in updates:
            loc=row['localization']
            if loc.get('approval')=='approved':
                loc['previous_visual_approval']={k:loc[k] for k in ['output','approved_backup','approved_sha256','approval_scope'] if k in loc}
            for k in ['approved_backup','approved_sha256','approval_scope']:loc.pop(k,None)
            loc.update(updates[row['pixel_sha256']]);count+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'changed_references':count,'changed_unique_images':len(updates),'inspected_unique_images':len(checks),'items':checks}
    (ROOT/'metadata/graphics_icon_alignment_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>이름표 줄바꿈·정렬 수정</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:40px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>이름표 줄바꿈·정렬 수정</h1><a href="../../graphics-review/dashboard.html?revision=icon-alignment-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{html.escape(" / ".join(c["lines"]))} · '+('수정' if c['changed_pixels'] else '기존 정렬 유지')+'</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('previous','이전 확정'),('korean','수정 결과')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(f'{count} references / {len(updates)} unique changed; {len(checks)} inspected; icon pixels unchanged')

if __name__=='__main__':main()
