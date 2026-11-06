"""Render NEIcon captions with native Galmuri metrics and intact glyph masks."""
from pathlib import Path
from functools import lru_cache
import json, hashlib, html, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'work/graphics-draft/neicon-v8'
OUT=ROOT/'work/graphics-draft/neicon-v9'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri7.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),8)
OVERRIDES={'NEIconOBJSandG':['출발','도착점'],'NEIconPlayWAMole':['두더지','잡기'],'NEIconPlayCbHang':['매달리기','봉']}

@lru_cache(None)
def native(char):
    canvas=Image.new('L',(16,16));d=ImageDraw.Draw(canvas);d.fontmode='1'
    d.text((0,0),char,font=FONT,fill=255)
    bbox=canvas.getbbox()
    assert bbox and 1<=bbox[1]<bbox[3]<=8
    # Preserve the common y=1..7 band, including blank rows in short glyphs.
    return canvas.crop((bbox[0],1,bbox[2],8)),bbox[0],int(FONT.getlength(char))

def render_line(text,limit):
    parts=[];cursor=0
    for char in text:
        if char==' ':
            cursor+=int(FONT.getlength(char));continue
        g,bearing,advance=native(char)
        parts.append([char,g,cursor+bearing]);cursor+=advance
    origin=parts[0][2]
    for part in parts:part[2]-=origin
    natural=parts[-1][2]+parts[-1][1].width
    removed=0
    while parts[-1][2]+parts[-1][1].width>limit:
        gaps=[parts[i+1][2]-parts[i][2]-parts[i][1].width for i in range(len(parts)-1)]
        if not gaps or max(gaps)<=1:raise ValueError((text,natural,limit,'requires rewriting, never shrink'))
        i=max(range(len(gaps)),key=lambda i:gaps[i])
        for part in parts[i+1:]:part[2]-=1
        removed+=1
    width=parts[-1][2]+parts[-1][1].width
    result=Image.new('L',(width,7))
    for char,g,x in parts:result.paste(g,(x,0))
    for char,g,x in parts:
        assert result.crop((x,0,x+g.width,7)).tobytes()==g.tobytes()
    return result,{'text':text,'native_ink_width':natural,'ink_width':width,'spacing_pixels_removed':removed,'minimum_ink_gap':min((parts[i+1][2]-parts[i][2]-parts[i][1].width for i in range(len(parts)-1)),default=None),'native_glyph_shapes_preserved':True}

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NEIcon*.png'):shutil.copy2(p,OUT/p.name)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==139
    checks=[];sheets=[];updates={}
    for i,r in enumerate(rows):
        key=r['key'];stem=key.replace('/','-');loc=r['localization'];family=key.split('/')[0]
        for f in ('output','preview','erased','edit_mask','comparison'):
            if isinstance(loc.get(f),str):loc[f]=loc[f].replace('neicon-v8/','neicon-v9/')
        loc['draft_version']='neicon-v9'
        src=Image.open(ROOT/r['path']).convert('RGBA');prev=Image.open(OLD/f'{stem}-korean.png').convert('RGBA')
        if loc['editing_method']=='imagegen':
            result=prev.copy();prev.save(OUT/f'{stem}-previous.png');checks.append({'key':key,'method':'imagegen','unchanged':True})
        else:
            lines=OVERRIDES.get(family,loc['lines']);a=np.array(src)
            old=a[:,:,3]>0;old[:32]=False;ys,xs=np.where(old)
            total=len(lines)*9+len(lines)-1
            assert total<=src.height-32,(key,lines,src.size)
            y=max(32,min((int(ys.min())+int(ys.max())+1-total)//2,src.height-total))
            clean=a.copy();clean[old]=0;erased=Image.fromarray(clean);ink=Image.new('L',src.size);placements=[]
            for line in lines:
                g,rec=render_line(line,src.width-2);x=(src.width-g.width-2)//2
                ink.paste(g,(x+1,y+1));placements.append(dict(rec,bbox=[x,y,x+g.width+2,y+9]));y+=10
            border=ink.filter(ImageFilter.MaxFilter(3));result=erased.copy()
            result.paste((16,49,123,255),(0,0,*src.size),border);result.paste((255,255,255,255),(0,0,*src.size),ink)
            b=np.array(result);mask=old|(np.array(border)>0)
            assert np.array_equal(a[:32],b[:32]) and np.array_equal(a[~mask],b[~mask])
            assert set(np.unique(np.array(ink)))<={0,255}
            for suffix,im in [('erased',erased),('korean',result),('previous',prev),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
            for obsolete in ('line_letter_gaps','line_ink_widths'):loc.pop(obsolete,None)
            loc.update(lines=lines,korean_proposal=' '.join(lines),horizontal_condensation=False,letter_gap_px=None,font='Galmuri7',font_px=8,line_height_px=9,line_gap_px=1,method_reason='갈무리7 정규8px·원래 글자 획 보존. 폰트 기본 간격 우선, 넘칠 때 빈 자간만 줄여 흰 획 사이 최소1px 유지. 공통7px 글자 영역·9px 외곽선 포함 줄 높이.',note=' / '.join(lines)+' · 가로축소0·원본 획 변형0·아이콘 변경0. 게임실행 미확인.')
            checks.append({'key':key,'method':'galmuri','size':list(src.size),'lines':lines,'placements':placements,'font_px':8,'ink_band_height':7,'outlined_line_height':9,'line_gap':1,'resized':False,'native_glyph_changed_pixels':0,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'changed_from_v8':not np.array_equal(np.array(prev),b),'sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False})
        if r['pixel_sha256'] in updates:
            other=updates[r['pixel_sha256']]
            assert (ROOT/loc['output']).read_bytes()==(ROOT/other['output']).read_bytes()
            loc.update(other)
        else:updates[r['pixel_sha256']]=loc.copy()
        if i%24==0:sheets.append(Image.new('RGB',(1280,1080),'#d3d5cc'))
        sheet=sheets[-1];draw=ImageDraw.Draw(sheet);j=i%24;cx=(j%4)*320;cy=(j//4)*180
        draw.text((cx+4,cy+3),key,fill='black')
        for k,im in enumerate([prev,result]):
            z=min(2,140//im.width);big=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST)
            sheet.paste(big,(cx+5+k*155,cy+25),big)
    for i,s in enumerate(sheets):s.save(OUT/f'overview-{i+1}.png')
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'references':139,'font_rebuilt_references':138,'imagegen_preserved':1,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'font_size_reference':'https://github.com/quiple/galmuri','all_native_glyphs_preserved':True,'horizontal_resizing':False,'items':checks}
    (ROOT/'metadata/neicon_v9_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    oldpage=(OLD/'index.html').read_text(encoding='utf-8');page=oldpage[:oldpage.index('<p>NEIcon 전체139개')]
    page+='<p>전체139개. 갈무리7 138개 사용처를 정규8px·원본 글자 획 그대로 다시 렌더링했습니다. 가로축소 없음. 글자 영역7px·외곽선 포함 줄 높이9px·줄 사이1px 통일. 기본 자간을 우선하고 폭이 부족할 때 빈 자간만 줄였습니다.</p><p>출발 / 도착점 · 두더지 / 잡기 · 매달리기 / 봉으로 변경. 오늘 / 기분은 ?은 직전 이미지젠 결과 유지. 원본 크기·아이콘 보존, 게임실행 미확인. <a href="font-audit.html">원본 폰트·외곽선 비교와 원인 설명</a></p>'
    for r in rows:
        loc=r['localization'];key=r['key'];stem=key.replace('/','-');w,h=Image.open(OUT/f'{stem}-korean.png').size
        page+=f'<section id="{stem}" data-find="{html.escape(key+" "+loc["korean_proposal"],quote=True)}"><h2>{key} · {html.escape(loc["korean_proposal"])}</h2><p>{html.escape(" / ".join(loc["lines"]))}</p>'
        for z in (1,4):
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('previous','이전 결과'),('erased','글자 지운 뒤'),('korean','최신 결과')]:page+=f'<div>{title}<br><img loading="lazy" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    page+=oldpage[oldpage.index('<script>'):];(OUT/'index.html').write_text(page,encoding='utf-8')
    audit='<meta charset="utf-8"><style>body{font:16px sans-serif;padding:24px}img{image-rendering:pixelated;margin-right:32px}section{padding:20px;background:#e6e6df;margin:16px 0}</style><h1>갈무리7 렌더링 확인</h1><p>기존 정규8px 크기는 맞았습니다. v8의 긴3명칭6도안은 가로축소로 획이 손상됐습니다. 나머지는 원래 획이었지만 글자별 여백 제거와 줄별 높이 계산으로 간격·기준선이 달랐습니다. v9는 획을 보존하고 기본 간격·고정 줄 높이로 통일했습니다. 흰 글씨에1px 남색 외곽선은 기존처럼 유지하므로 외곽선이 붙어 보이는 특성은 남습니다.</p><p><a href="index.html">전체139개 비교판</a> · <a href="https://github.com/quiple/galmuri">공식 크기 안내: Galmuri7 8px</a></p>'
    for i,t in enumerate(['치비','출발','도착점','두더지','잡기','매달리기','봉','무성무성']):
        g,rec=render_line(t,30);ink=Image.new('L',(g.width+2,9));ink.paste(g,(1,1))
        plain=Image.new('RGB',ink.size,'white');plain.paste('black',(0,0,*ink.size),ink)
        outline=Image.new('RGBA',ink.size);outline.paste((16,49,123,255),(0,0,*ink.size),ink.filter(ImageFilter.MaxFilter(3)));outline.paste((255,255,255,255),(0,0,*ink.size),ink)
        plain.save(OUT/f'font-{i}-plain.png');outline.save(OUT/f'font-{i}-outline.png')
        audit+=f'<section><h2>{t}</h2><p>원본 획 / 기존 색상의 외곽선 적용 · 원래 크기와6배 확대</p>'
        for z in (1,6):
            audit+='<p>'+''.join(f'<img src="font-{i}-{suffix}.png" width="{ink.width*z}" height="{ink.height*z}">' for suffix in ['plain','outline'])+'</p>'
        audit+='</section>'
    (OUT/'font-audit.html').write_text(audit,encoding='utf-8')
    print(json.dumps({'font_rebuilt':138,'pixel_changed':sum(c.get('changed_from_v8',False) for c in checks),'condensed':0,'glyph_shape_changes':0}))

if __name__=='__main__':main()
