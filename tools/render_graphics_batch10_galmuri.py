"""Render native Galmuri14 lettering in the four forecast quantity labels."""
from pathlib import Path
import json, hashlib, html
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch10-v2'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri14.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),15)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in {f'NewPCKForecast2/cell/{n}' for n in [12,13,14,15]}]
    checks=[];updates={};sheet=Image.new('RGB',(1000,660),'#d8dcd4');d=ImageDraw.Draw(sheet)
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);stem=r['key'].replace('/','-');loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);old=a[:,:,3]>0
        # Native 15px font rasterization; preserve all original glyphs and advances.
        core=Image.new('L',(256,32));draw=ImageDraw.Draw(core);draw.fontmode='1'
        draw.text((3,3),loc['korean_proposal'],font=FONT,fill=255)
        core=core.crop(core.getbbox());w,h=core.size
        ink=Image.new('L',(w+4,h+4));ink.paste(core,(2,2))
        white=ink.filter(ImageFilter.MaxFilter(3));navy=white.filter(ImageFilter.MaxFilter(3))
        layer=Image.new('RGBA',ink.size);layer.paste((16,49,123,255),(0,0),navy);layer.paste((255,255,255,255),(0,0),white);layer.paste((255,0,0,255),(0,0),ink)
        yy,xx=np.where(old);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        x=box[0];y=box[1];assert x+layer.width<=src.width and y+layer.height<=src.height
        clean=a.copy();clean[old]=0;erased=Image.fromarray(clean);result=erased.copy();result.alpha_composite(layer,(x,y))
        mask=old|(np.array(result)[:,:,3]>0)
        assert np.array_equal(a[~mask],np.array(result)[~mask])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        core.save(OUT/f'core-{n}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'original_bbox':box,'text_bbox':list(result.getbbox()),'original_start_preserved':True,'outside_mask_changed_pixels':0,'palette':[[255,0,0,255],[255,255,255,255],[16,49,123,255],[0,0,0,0]],'font':'Galmuri14','font_px':15,'native_glyphs_and_advances_preserved':True,'resized':False,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch10-v2','editing_method':'galmuri','font':'Galmuri14','font_px':15,'method_reason':'사용자 지정 갈무리 큰 사이즈: Galmuri14 기본15px. 원본 빨강 획/흰 테두리/남색 외곽선 유지','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 시작 위치와 규격 유지. Galmuri14 기본15px 원본 획과 간격, 흰색/남색 각1px 테두리. 크기 변형 없음. 팔레트변환·게임실행 미확인.'}
        d.text((5,i*165+2),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            sheet.paste(im,(10+j*490,i*165+20),im);big=im.resize((im.width*5,im.height*5),Image.Resampling.NEAREST);sheet.paste(big,(10+j*490,i*165+45),big)
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch10_v2_checks.json').write_text(json.dumps({'items':checks,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'imagegen_used':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>예보 수량 글씨4개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>예보 수량 장식 글씨4개</h1><p>갈무리14 기본15px · 빨간 획 / 흰 테두리 / 남색 외곽선 · 원본 시작 위치와 규격 유지</p><p><a href="../../graphics-review/dashboard.html">현황판</a></p>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':main()
