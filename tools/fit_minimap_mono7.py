"""Fit four approved overflow previews to source canvases, preserving native glyphs."""
from pathlib import Path
import json, hashlib, html, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from preview_neicon_mono7 import render_line

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/minimap-mono7-v1'
START={117:0,136:10,144:16,145:15}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    updates={};checks=[]
    page='<meta charset="utf-8"><title>미니맵 4개 · 갈무리7</title><style>body{font:16px/1.7 sans-serif;background:#edf1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:32px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px;outline:1px solid #aaa}</style><h1>미니맵 4개 · 고정폭 갈무리7</h1><p>원본 크기 유지 · 글자 획 변형 없음 · 체크포인트는 기존 요청대로 원본 중심보다 1px 아래</p>'
    sheet=Image.new('RGB',(900,520),'#dbe1d5');draw=ImageDraw.Draw(sheet)
    for i,(n,start) in enumerate(START.items()):
        key=f'MiniMap/cell/{n}';r=next(r for r in m['graphics'] if r['edition']=='jp' and r['key']==key)
        loc=r['localization'];text=loc['korean_proposal'];stem=key.replace('/','-')
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        previous=Image.open(ROOT/'work/graphics-approved/batch02-final'/f'{stem}.png').convert('RGBA')
        old=a[:,:,3]>0;old[:,:start]=False;yy,xx=np.where(old)
        clean=a.copy();clean[old]=0;erased=Image.fromarray(clean)
        g,metrics=render_line(text,src.width-start-2)
        w,h=g.width+2,g.height+2
        x=start if start else (src.width-w)//2
        y=(int(yy.min())+int(yy.max())+1-h)//2+(1 if n in (136,145) else 0)
        assert 0<=x and x+w<=src.width and 0<=y and y+h<=src.height
        ink=Image.new('L',src.size);ink.paste(g,(x+1,y+1));border=ink.filter(ImageFilter.MaxFilter(3))
        result=erased.copy();result.paste((255,255,255,255),(0,0,*src.size),border);result.paste((0,0,0,255),(0,0,*src.size),ink)
        mask=old|(np.array(border)>0);b=np.array(result)
        assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:,:start],b[:,:start])
        for suffix,im in [('original',src),('previous',previous),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
        update={k:v for k,v in loc.items() if not k.startswith('approved_') and k!='approval_scope'}
        update.update(output=output,preview=output,erased=f'{rel}/{stem}-erased.png',edit_mask=f'{rel}/{stem}-mask.png',comparison=f'{rel}/index.html#{stem}',font='GalmuriMono7',font_px=8,lines=[text],draft_version='minimap-mono7-v1',approval='pending',work_status='review',requires_resource_width_expansion=False,method_reason='사용자 요청: 넘치는 4개만 고정폭 갈무리7 정규8px. 원래 획 보존, 원본 크기 유지.',note='아이콘·마스크 밖 픽셀 보존. 체크포인트는 원본 중심보다1px 아래 유지. 폭 확장 불필요. 게임실행 미확인.',revision_request='넘치는 미니맵4개를 갈무리7로 변경',previous_approved_preview=f'work/graphics-approved/batch02-final/{stem}.png')
        updates[r['pixel_sha256']]=update
        checks.append(dict(key=key,text=text,source_size=list(src.size),result_size=list(result.size),bbox=[x,y,x+w,y+h],metrics=metrics,icon_changed_pixels=0,outside_mask_changed_pixels=0,requires_resource_width_expansion=False,runtime_verified=False,sha256=hashlib.sha256((ROOT/output).read_bytes()).hexdigest()))
        draw.text((8,i*130+5),key,fill='black')
        for j,im in enumerate([src,previous,result]):
            im=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(im,(8+j*295,i*130+30),im)
        page+=f'<section id="{stem}"><h2>{key} · {html.escape(text)}</h2><p>원본과 결과 모두 {src.width}×{src.height}px</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('previous','이전 갈무리9'),('korean','갈무리7 수정본')]:
                im=Image.open(OUT/f'{stem}-{suffix}.png');page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{im.width*z}" height="{im.height*z}"></div>'
            page+='</div>'
        page+='</section>'
    cassette=next(r for r in m['graphics'] if r['edition']=='jp' and r['key']=='NewPCCassette/cell/25')
    path=Path(os.path.relpath(ROOT/cassette['path'],OUT)).as_posix()
    page+=f'<section><h2>보류 카세트 · NewPCCassette/cell/25</h2><p>원본 유지 — 사용자 요청에 따라 게임에서 발견되면 다시 검토합니다. 북미판에도 동일한 일본어 그림이 남아 있습니다. 미사용 여부는 미확인입니다.</p><img src="{path}" width="32" height="56">　<img src="{path}" width="128" height="224"></section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization']=updates[r['pixel_sha256']].copy()
    cassette['localization'].update(japanese_reading='ウエアルケール (기능 미확인)',note='사용자 판독: 우에아루 케-루. JP/US 동일 그림. 上を歩ける를 비튼 다리 이름일 가능성은 있으나 미확인. 사용자 요청으로 원본 유지, 실제 게임에서 발견되면 재검토. 미사용 여부 미확인.',defer_until='user_observes_in_game',user_reply='그럼 안쓰는걸수도 있겠네요 그냥 두고 제가 만약에 게임에서 확인하면 그때 고치죠')
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'changed_artworks':4,'all_original_dimensions':True,'items':checks,'cassette':{'key':cassette['key'],'jp_us_same_pixel_sha256':cassette['pixel_sha256'],'disposition':'preserve_until_observed_in_game','unused_confirmed':False}}
    (ROOT/'metadata/minimap_mono7_fit_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
