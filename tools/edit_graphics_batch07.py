"""Reuse approved NEIcon lettering on the matching cassette labels."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch07-v1'

def main():
    OUT.mkdir(exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    ne=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('approval')=='approved']
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NewPCCassette/') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==48
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];assert loc['approval']!='approved';key=r['key'];stem=key.replace('/','-')
        matches=[s for s in ne if s['localization']['japanese_reading']==loc['japanese_reading']]
        assert matches,key
        donor=matches[0];dl=donor['localization'];approved=Image.open(ROOT/dl['output']).convert('RGBA')
        caption=approved.crop((0,32,approved.width,approved.height));caption=caption.crop(caption.getbbox())
        for other in matches[1:]:
            q=Image.open(ROOT/other['localization']['output']).convert('RGBA');q=q.crop((0,32,q.width,q.height));q=q.crop(q.getbbox())
            assert q.size==caption.size and q.tobytes()==caption.tobytes()
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        old=a[:,:,3]>0;old[:32]=False;ys,xs=np.where(old)
        x=(src.width-caption.width)//2;y=max(32,min((int(ys.min())+int(ys.max())+1-caption.height)//2,src.height-caption.height))
        assert 0<=x and x+caption.width<=src.width and y+caption.height<=src.height
        clean=a.copy();clean[old]=0;erased=Image.fromarray(clean);result=erased.copy();result.alpha_composite(caption,(x,y));b=np.array(result)
        new=b[:,:,3]>0;new[:32]=False;mask=old|new
        assert np.array_equal(a[:32],b[:32]) and np.array_equal(a[~mask],b[~mask])
        assert result.crop((x,y,x+caption.width,y+caption.height)).tobytes()==caption.tobytes()
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/output).read_bytes()).hexdigest()
        checks.append({'key':key,'text':dl['korean_proposal'],'lines':dl['lines'],'size':list(src.size),'donor_key':donor['key'],'donor_approved_sha256':dl['approved_sha256'],'approved_caption_pixels_identical':True,'text_bbox':[x,y,x+caption.width,y+caption.height],'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'resized':False,'sha256':digest,'runtime_verified':False})
        updates[r['pixel_sha256']]={'korean_proposal':dl['korean_proposal'],'lines':dl['lines'],'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch07-v1','editing_method':'galmuri','method_reason':'원본은 NEIcon과 동일 계열의 명확한 도트 이름표. 사용자 확정 GalmuriMono7 문구·줄바꿈·글자 픽셀을 그대로 재사용','font':'GalmuriMono7','font_px':8,'work_status':'review','approval':'pending','requires_resource_width_expansion':False,'reused_approved_caption':donor['key'],'note':'카세트 그림 원본 픽셀 보존. 확정 NEIcon 글자 픽셀 동일. 원본 규격 유지. 팔레트변환·게임실행 미확인.'}
        if i%16==0:sheets.append(Image.new('RGB',(1200,800),'#d3d5cc'))
        sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%16;cx=j%4*300;cy=j//4*200;d.text((cx+5,cy+4),key,fill='black')
        for k,im in enumerate([src,result]):
            big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+5+k*150,cy+25),big)
    for i,s in enumerate(sheets):s.save(OUT/f'overview-{i+1}.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch07_checks.json').write_text(json.dumps({'references':48,'unique_images':len(updates),'approved_caption_reuse':True,'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>카세트 이름표48개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:18px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}header{position:sticky;top:0;background:#eef1e8;padding:10px;z-index:1}input{font:inherit;padding:6px;width:300px}</style><header><b>다음 묶음 · 카세트 이름표48개</b> · <a href="../../graphics-review/dashboard.html">현황판</a><br><input id="search" placeholder="이름 또는 자원 검색"><span id="count"></span></header><p>확정한 NEIcon의 문구·줄바꿈·갈무리Mono7 글자 픽셀을 그대로 사용했습니다. 카세트 그림과 원본 크기를 보존했습니다. 전체48개를 한 번에 표시합니다. 팔레트변환·게임실행 미확인.</p>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}" data-find="{html.escape(c["key"]+" "+c["text"],quote=True)}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{html.escape(" / ".join(c["lines"]))} · 확정 글자: {c["donor_key"]}</p>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img loading="lazy" src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    page+='<script>const sections=[...document.querySelectorAll("section")];function filter(){let n=0;const q=document.querySelector("#search").value.toLowerCase();for(const s of sections){s.hidden=!s.dataset.find.toLowerCase().includes(q);if(!s.hidden)n++;}document.querySelector("#count").textContent=` ${n}개 전체 표시`;}document.querySelector("#search").addEventListener("input",filter);filter();</script>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('48 cassette labels; protected icons unchanged; approved lettering pixels identical')

if __name__=='__main__':main()
