"""Apply requested two-line labels, with explicitly requested narrow long lines."""
from pathlib import Path
import json, shutil, hashlib, html
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from edit_neicon_galmuri7 import glyphs

ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'work/graphics-draft/neicon-v7'
OUT=ROOT/'work/graphics-draft/neicon-v8'
SPLITS={
 'NEIconOBJCheckP':['체크','포인트'],
 'NEIconOBJSandG':['치비','출발도착점'],
 'NEIconPlayCbHang':['치비','매달리기봉'],
 'NEIconPlayPBar':['치비','철봉'],
 'NEIconPlayWAMole':['치비','두더지잡기'],
}

def line_image(text):
    regular=glyphs(text,1)
    if regular.width+2<=32:
        return regular, {'text':text,'gap':1,'source_ink_width':regular.width,'ink_width':regular.width,'condensed':False}
    regular=glyphs(text,0)
    parts=[];x=0
    for char in text:
        width=glyphs(char,0).width
        part=regular.crop((x,0,x+width,regular.height))
        if width>6:
            part=part.resize((6,part.height),Image.Resampling.NEAREST)
        parts.append(part);x+=width
    result=Image.new('L',(sum(p.width for p in parts),regular.height));x=0
    for part in parts:
        result.paste(part,(x,0));x+=part.width
    assert result.width+2<=32
    return result, {'text':text,'gap':0,'source_ink_width':regular.width,'ink_width':result.width,'condensed':True,'max_glyph_width':6,'height_preserved':True}

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NEIcon*.png'):
        shutil.copy2(p,OUT/p.name)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==139
    checks=[];proof=Image.new('RGB',(960,750),'#d3d5cc');draw=ImageDraw.Draw(proof)
    for r in rows:
        key=r['key'];family=key.split('/')[0];stem=key.replace('/','-');loc=r['localization']
        for f in ('output','preview','erased','edit_mask','comparison'):
            if isinstance(loc.get(f),str):loc[f]=loc[f].replace('neicon-v7/','neicon-v8/')
        loc['draft_version']='neicon-v8'
        if family not in SPLITS:
            assert (OLD/f'{stem}-korean.png').read_bytes()==(OUT/f'{stem}-korean.png').read_bytes()
            continue
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);old=a[:,:,3]>0;old[:32]=False
        ys,xs=np.where(old);bbox=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
        erased=a.copy();erased[old]=0;erased=Image.fromarray(erased)
        lines=SPLITS[family];rendered=[line_image(t) for t in lines];total=sum(g.height+2 for g,_ in rendered)+1
        y=max(32,min((bbox[1]+bbox[3]-total)//2,src.height-total));ink=Image.new('L',src.size);placements=[]
        for g,rec in rendered:
            x=(src.width-g.width-2)//2;h=g.height+2
            assert 0<=x and y+h<=src.height
            ink.paste(g,(x+1,y+1));placements.append(dict(rec,bbox=[x,y,x+g.width+2,y+h]));y+=h+1
        border=ink.filter(ImageFilter.MaxFilter(3));result=erased.copy();result.paste((16,49,123,255),(0,0,*src.size),border);result.paste((255,255,255,255),(0,0,*src.size),ink)
        b=np.array(result);mask=old|(np.array(border)>0)
        assert np.array_equal(a[:32],b[:32]) and np.array_equal(a[~mask],b[~mask])
        for suffix,im in [('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        previous=Image.open(OLD/f'{stem}-korean.png').convert('RGBA');previous.save(OUT/f'{stem}-previous.png')
        loc.update(korean_proposal=' '.join(lines),lines=lines,letter_gap_px=None,line_letter_gaps=[v['gap'] for v in placements],line_ink_widths=[v['ink_width'] for v in placements],horizontal_condensation=any(v['condensed'] for v in placements),method_reason='사용자 지정2줄 배치. 긴 둘째 줄은 사용자 요청으로 자간0px·글자당 최대6px 가로축소, 높이 유지.',note=' / '.join(lines)+' · 원본32×56와 아이콘 보존. 긴 둘째 줄만 가로폭 축소. 게임실행 미확인.')
        checks.append({'key':key,'lines':lines,'size':list(src.size),'placements':placements,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False})
        i=len(checks)-1;cx=(i%2)*480;cy=(i//2)*150;draw.text((cx+5,cy+3),key,fill='black')
        for j,im in enumerate([src,previous,result]):
            draw.text((cx+5+j*155,cy+18),['Original','Previous','Revised'][j],fill='black')
            proof.paste(im,(cx+5+j*155,cy+37),im)
            big=im.resize((64,112),Image.Resampling.NEAREST);proof.paste(big,(cx+45+j*155,cy+37),big)
    assert len(checks)==10
    proof.save(OUT/'changed-proof.png')
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    oldpage=(OLD/'index.html').read_text(encoding='utf-8');page=oldpage[:oldpage.index('<p>전체 139개')]
    page+='<p>NEIcon 전체139개 사용처. 지정5명칭의 컬러·회색10도안을 수정했습니다. 체크 / 포인트, 치비 / 출발도착점, 치비 / 매달리기봉, 치비 / 철봉, 치비 / 두더지잡기. 긴 둘째 줄3종만 자간0px·글자당 최대6px로 폭을 줄였습니다. 원본크기·아이콘 보존, 게임실행 미확인.</p>'
    for r in rows:
        loc=r['localization'];key=r['key'];stem=key.replace('/','-');w,h=Image.open(OUT/f'{stem}-korean.png').size
        method='이미지젠·정밀보수' if loc['editing_method']=='imagegen' else '갈무리7'
        if key.split('/')[0] in SPLITS and loc['horizontal_condensation']:method+=' · 둘째 줄 가로폭 축소'
        page+=f'<section id="{stem}" data-find="{html.escape(key+" "+loc["korean_proposal"],quote=True)}"><h2>{key} · {html.escape(loc["korean_proposal"])}</h2><p>{html.escape(" / ".join(loc["lines"]))} · {method}</p>'
        for z in (1,4):
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','최신 결과')]:page+=f'<div>{title}<br><img loading="lazy" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    page+=oldpage[oldpage.index('<script>'):];(OUT/'index.html').write_text(page,encoding='utf-8')
    report={'references':139,'changed_references':10,'unchanged_references':129,'items':checks}
    (ROOT/'metadata/neicon_v8_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='items'}))

if __name__=='__main__':main()
