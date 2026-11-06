"""Render ordinary forecast sentence fragments over exact original scanlines."""
from pathlib import Path
import json, hashlib, html
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch11-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri14.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),15)
BLUES=np.array([[74,123,255,255],[24,90,255,255]],dtype=np.uint8)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in {f'NewPCKForecast/cell/{n}' for n in range(1,7)}]
    assert len(rows)==6
    checks=[];updates={};sheet=Image.new('RGB',(1250,780),'#d8dcd4');d=ImageDraw.Draw(sheet)
    for i,r in enumerate(rows):
        stem=r['key'].replace('/','-');loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);bg=np.empty_like(a)
        row_evidence=[]
        for y in range(src.height):
            counts=[int(np.all(a[y]==color,axis=1).sum()) for color in BLUES]
            chosen=int(np.argmax(counts));assert chosen==y%2 and counts[chosen]>counts[1-chosen]
            bg[y]=BLUES[chosen];row_evidence.append(counts)
        old=np.any(a!=bg,axis=2);yy,xx=np.where(old)
        box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        # Only original glyph/AA pixels change during erasure.
        clean=a.copy();clean[old]=bg[old];assert np.array_equal(clean,bg)
        erased=Image.fromarray(clean)
        ink=Image.new('L',(256,32));draw=ImageDraw.Draw(ink);draw.fontmode='1'
        draw.text((3,3),loc['korean_proposal'],font=FONT,fill=255)
        ink=ink.crop(ink.getbbox());w,h=ink.size
        x=box[0];y=(box[1]+box[3]-h)//2
        assert 0<=x and 0<=y and x+w<=src.width and y+h<=src.height
        overlay=Image.new('L',src.size);overlay.paste(ink,(x,y))
        result=erased.copy();result.paste((255,255,255,255),(0,0),overlay)
        mask=old|(np.array(overlay)>0);b=np.array(result)
        assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:,:,3],b[:,:,3])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'original_text_bbox':box,'text_bbox':[x,y,x+w,y+h],'font':'Galmuri14','font_px':15,'native_glyphs_and_advances_preserved':True,'resized':False,'outside_mask_changed_pixels':0,'original_alpha_preserved':True,'scanline_evidence_blue_counts':row_evidence,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch11-v1','editing_method':'galmuri','font':'Galmuri14','font_px':15,'method_reason':'예보 화면 일반 문장 조각. 직전 큰 갈무리 선택에 맞춰 Galmuri14 기본15px 적용. 원본 흰 글자, 파란 행별 줄무늬 보존.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 시작 x와 글자 세로 중심 유지. 원본 크기·마스크 밖 픽셀 보존. 조사·어순의 최종 화면 조합과 팔레트변환·게임실행 미확인.'}
        d.text((5,i*130+2),r['key'],fill='black')
        for j,im in enumerate([src,erased,result]):
            sheet.paste(im,(5+j*415,i*130+20));big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(5+j*415,i*130+50))
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch11_checks.json').write_text(json.dumps({'items':checks,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>예보 문장6개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated}</style><h1>예보 문장 조각6개</h1><p>갈무리14 기본15px · 원본 흰 글씨와 파란 줄무늬 배경 · 원본 시작 x와 글자 세로 중심 유지</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print('Six native Galmuri14 labels; scanline patterns and outside-mask pixels verified')

if __name__=='__main__':main()
