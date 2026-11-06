"""Render red warning windows in native Galmuri9, preserving each frame and icon."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/warnings-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),10)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets'];rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='warnings' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==9
    checks=[];updates={};sheet=Image.new('RGB',(1250,1100),'#dae0d6')
    for i,r in enumerate(rows):
        loc=r['localization'];assert loc['approval']!='approved';src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);stem=r['key'].replace('/','-');assert src.size==(149,32)
        region=np.zeros(a.shape[:2],bool);region[7:23,24:145]=True
        old=region&np.any(a!=[255,0,0,255],axis=2)
        assert all(tuple(v) in [(65,65,65,255),(255,255,255,255)] for v in a[old])
        clean=a.copy();clean[old]=(255,0,0,255)
        assert np.all(clean[region]==[255,0,0,255])
        white=region&np.all(a==[255,255,255,255],axis=2);yy,xx=np.where(white);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        core=Image.new('L',(256,24));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),loc['korean_proposal'],font=FONT,fill=255);core=core.crop(core.getbbox())
        ink=Image.new('L',(core.width+2,core.height+2));ink.paste(core,(1,1));layer=Image.new('RGBA',ink.size);layer.paste((65,65,65,255),(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((255,255,255,255),(0,0),ink)
        x=box[0]-1;y=(box[1]+box[3]-core.height)//2-1
        assert x>=24 and y>=7 and x+layer.width<=145 and y+layer.height<=23
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));erased=Image.fromarray(clean);result=Image.alpha_composite(erased,overlay);b=np.array(result);fresh=np.array(overlay)[:,:,3]>0;mask=old|fresh
        assert np.all(region[fresh]) and np.array_equal(a[~mask],b[~mask])
        assert np.array_equal(a[~region],b[~region]) and np.array_equal(a[:,:,3],b[:,:,3])
        assert np.array_equal(a[:,:24],b[:,:24]) and np.array_equal(a[:,145:],b[:,145:])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'warnings-v1','editing_method':'galmuri','font':'Galmuri9','font_px':10,'lines':[loc['korean_proposal']],'method_reason':'검은 안내창과 동일한 갈무리9 기본10px, 흰 획·회색65 외곽선1px. 원본 글자 시작x와 세로 중심 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'문구 생략 없음. 원본 빨간 바탕·경고 아이콘·창 프레임·상단색상점 보존. 팔레트 재삽입·게임실행 미확인.'}
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'font':'Galmuri9','font_px':10,'original_ink_bbox':box,'text_bbox':[x,y,x+layer.width,y+layer.height],'native_glyph_changed_pixels':0,'outside_mask_changed_pixels':0,'frame_and_icon_changed_pixels':0,'text_shortened':False,'resized':False,'requires_resource_width_expansion':False,'runtime_verified':False,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest()})
        cx=i%2*625;cy=i//2*220;ImageDraw.Draw(sheet).text((cx+5,cy+5),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            bx=cx+5+j*310;sheet.paste(im,(bx,cy+25),im);big=im.resize((298,64),Image.Resampling.NEAREST);sheet.paste(big,(bx,cy+90),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');sheet.save(OUT/'overview.png')
    report={'category_total':9,'references':refs,'unique_messages':3,'font':'Galmuri9','font_px':10,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks}
    (ROOT/'metadata/graphics_warning_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>빨간 경고창9종</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>빨간 경고창9종</h1><p>갈무리9 기본10px · 원본149×32 · 문구 전체 유지 · 18참조 반영</p><a href="../../graphics-review/dashboard.html?category=warnings&revision=warnings-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,3]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{149*z}" height="{32*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'{len(checks)} images, {refs} references')

if __name__=='__main__':main()
