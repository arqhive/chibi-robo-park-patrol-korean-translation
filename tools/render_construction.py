"""Render twelve construction labels with native Mono7, preserving sprite backgrounds."""
from pathlib import Path
import json, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from preview_neicon_mono7 import render_line, FONT_PATH

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/construction-v2'

def diamond():
    a=np.zeros((32,32,4),dtype=np.uint8)
    for y in range(32):
        depth=min(y,31-y);left=15-depth;right=16+depth
        a[y,left:right+1]=(255,205,0,255)
        a[y,[left,right]]=(255,255,255,255)
        if depth>=1:a[y,[left+1,right-1]]=(0,0,0,255)
        if depth>=4:a[y,[left+4,right-4]]=(0,0,0,255)
    return a

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    jp={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
    rows=[];seen=set()
    for r in jp.values():
        if cats.get(r['pixel_sha256'],{}).get('category')=='construction' and r['pixel_sha256'] not in seen:
            rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==12
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        assert r['localization']['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);sign=r['key']=='NewPCStaticA/cell/27';stem=r['key'].replace('/','-')
        record={'key':r['key'],'size':list(src.size)}
        if sign:
            clean=diamond()
            assert np.array_equal(a[:9],clean[:9]) and np.array_equal(a[23:],clean[23:])
            old=np.any(a!=clean,axis=2)
            assert not old[:9].any() and not old[23:].any()
            record['background_restoration']='Symmetric diamond contours continued through original text mask; exposed top and bottom unchanged'
        else:
            donor_key='NewPCStaticB/cell/'+str(int(r['key'].split('/')[-1])-1)
            clean=np.array(Image.open(ROOT/jp[donor_key]['path']).convert('RGBA'))
            old=np.any(a!=clean,axis=2)
            yy,xx=np.where(old)
            assert (xx.min(),yy.min(),xx.max()+1,yy.max()+1)==(4,12,29,21)
            assert all(tuple(p) in [(0,0,0,255),(255,255,255,255)] for p in a[old])
            restored=a.copy();restored[old]=clean[old];assert np.array_equal(restored,clean)
            record.update(background_donor=donor_key,background_restoration='Exact corresponding text-free sprite, copied only at original text pixels')
        core,metrics=render_line('공사중',28 if sign else 30)
        assert metrics['spacing_pixels_removed']==0
        padding=2 if sign else 1
        ink=Image.new('L',(core.width+padding*2,7+padding*2));ink.paste(core,(padding,padding))
        border=ink.filter(ImageFilter.MaxFilter(3));layer=Image.new('RGBA',ink.size)
        if sign:layer.paste((255,255,255,255),(0,0),ink.filter(ImageFilter.MaxFilter(5)))
        layer.paste((0,0,0,255),(0,0),border)
        if sign:
            fill=Image.new('RGBA',ink.size,(255,0,0,255));ImageDraw.Draw(fill).rectangle((0,0,fill.width,padding+2),fill=(255,123,123,255));layer.paste(fill,(0,0),ink)
        else:layer.paste((255,255,255,255),(0,0),ink)
        x=(32-layer.width)//2;y=(32-layer.height)//2 if sign else 12
        assert x>=0 and y>=0 and x+layer.width<=32 and y+layer.height<=32
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));fresh=np.array(overlay)[:,:,3]>0
        erased=Image.fromarray(clean);result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|fresh
        assert np.array_equal(a[~mask],b[~mask])
        assert set(map(tuple,b.reshape(-1,4))) <= (set(map(tuple,a.reshape(-1,4))) | set(map(tuple,clean.reshape(-1,4))))
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rel=OUT.relative_to(ROOT).as_posix()
        updates[r['pixel_sha256']]={'output':f'{rel}/{stem}-korean.png','preview':f'{rel}/{stem}-korean.png','erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'construction-v2','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'lines':['공사중'],'korean_proposal':'공사중','method_reason':'사용자 선택: 마름모 표지 포함 전체 갈무리7 한 줄. 고정폭 Mono7 기본8px, 원래 획·간격 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'공사중 한 줄. 원본32×32, 기본 획·자간 보존. 팔레트 재삽입·게임실행 미확인.'}
        record.update(font='GalmuriMono7',font_px=8,metrics=metrics,text_bbox=[x,y,x+layer.width,y+layer.height],old_text_pixels=int(old.sum()),outside_mask_changed_pixels=0,native_glyph_changed_pixels=0,resized=False,source_colors_only=True,runtime_verified=False,sha256=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest())
        checks.append(record)
        if i%6==0:sheets.append(Image.new('RGB',(900,840),'#e2e6dd'))
        sheet=sheets[-1];cx=(i%2)*450;cy=(i%6)//2*280;d=ImageDraw.Draw(sheet);d.text((cx+8,cy+4),r['key'],fill='black')
        for j,im in enumerate([src,erased,result]):
            px=cx+8+j*145;d.text((px,cy+24),['original','erased','korean'][j],fill='black');sheet.paste(im,(px,cy+44),im);big=im.resize((128,128),Image.Resampling.NEAREST);sheet.paste(big,(px,cy+95),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for i,im in enumerate(sheets):im.save(OUT/f'overview-{i+1}.png')
    report={'category_total':12,'references':refs,'font':'GalmuriMono7','font_px':8,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'diamond_user_choice':'이 표지도 갈무리7 한 줄','items':checks}
    (ROOT/'metadata/graphics_construction_v2_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>공사중 표시12개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>공사중 표시12개</h1><p>갈무리Mono7 기본8px · 한 줄 · 원본32×32 유지</p><a href="../../graphics-review/dashboard.html?category=construction&revision=construction-v2">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{c["key"]} · 공사중</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{32*z}" height="{32*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'{len(checks)} images / {refs} references rendered')

if __name__=='__main__':main()
