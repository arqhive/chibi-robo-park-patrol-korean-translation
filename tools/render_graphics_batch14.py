"""Native font toy selection labels with original color bands and panels."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch14-v2'
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)
F7=ImageFont.truetype(str(ROOT/'work/fonts/galmuri-mono7/GalmuriMono7.ttf'),8)
BANDS={0:((238,0,255),(106,0,123)),1:((255,246,0),(65,197,246)),2:((0,246,0),(255,197,0)),3:((255,156,0),(8,180,0)),5:((255,98,197),(255,0,0)),10:((255,255,255),(255,0,0)),14:((255,0,8),(0,164,255))}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NewPCSelectToy/') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==13
    checks=[];updates={};sheet=Image.new('RGB',(1300,1500),'#d5d9cf');d=ImageDraw.Draw(sheet)
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);stem=r['key'].replace('/','-');loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);clean=a.copy();panel=None
        if n==6:
            panel=(4,9,92,26)
            for y in range(9,26):
                color=(255,74,74,255) if y%2 else (255,123,123,255)
                assert np.array_equal(a[y,4],color) and np.array_equal(a[y,91],color)
                clean[y,4:92]=color
        elif n in [7,11,12,13]:
            panel=(11,24,101,39)
            assert np.all(a[24,11:101]==[255,213,0,255]) and np.all(a[38,11:101]==[255,213,0,255])
            clean[24:39,11:101]=(255,213,0,255)
        else:clean[a[:,:,3]>0]=0
        old=np.any(a!=clean,axis=2);yy,xx=np.where(old);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        erased=Image.fromarray(clean);font=F7 if n==6 else F9
        ink=Image.new('L',(256,32));draw=ImageDraw.Draw(ink);draw.fontmode='1';draw.text((3,3),loc['korean_proposal'],font=font,fill=255)
        ink=ink.crop(ink.getbbox());w,h=ink.size
        glyph=Image.new('L',(w+4,h+4));glyph.paste(ink,(2,2));black=glyph.filter(ImageFilter.MaxFilter(3));white=black.filter(ImageFilter.MaxFilter(3))
        layer=Image.new('RGBA',glyph.size);layer.paste((255,255,255,255),(0,0),white);layer.paste((0,0,0,255),(0,0),black)
        fill=np.zeros((h+4,w+4,4),dtype=np.uint8);fill[:]=(255,255,255,255)
        if n in BANDS:
            top,bottom=BANDS[n];fill[:2+h//2,:,:3]=top;fill[2+h//2:,:,:3]=bottom
        elif n==4:
            fill[:2+h//2,:2+w//2,:3]=(255,0,8);fill[:2+h//2,2+w//2:,:3]=(255,246,0);fill[2+h//2:,:,:3]=(0,164,255)
        layer.paste(Image.fromarray(fill),(0,0),glyph)
        if panel:
            x=(panel[0]+panel[2]-layer.width)//2;y=(panel[1]+panel[3]-layer.height)//2
            assert x>=panel[0] and y>=panel[1] and x+layer.width<=panel[2] and y+layer.height<=panel[3]
        else:
            x=box[0];y=max(0,min((box[1]+box[3]-layer.height)//2,src.height-layer.height))
        if n==5:y+=1  # User requested a one-pixel downward translation.
        assert x>=0 and y>=0 and x+layer.width<=src.width and y+layer.height<=src.height,(r['key'],layer.size,box)
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result)
        previous=Image.open(ROOT/'work/graphics-draft/batch14-v1'/f'{stem}-korean.png').convert('RGBA')
        if n==5:
            assert previous.getbbox()[3] < previous.height
            shifted=Image.new('RGBA',previous.size);shifted.paste(previous,(0,1))
            assert shifted.tobytes()==result.tobytes()
        else:assert previous.tobytes()==result.tobytes()
        mask=old|(np.array(overlay)[:,:,3]>0);assert np.array_equal(a[~mask],b[~mask])
        if panel:
            protected=np.ones(a.shape[:2],bool);protected[panel[1]:panel[3],panel[0]:panel[2]]=False
            assert np.array_equal(a[protected],b[protected]) and np.array_equal(a[:,:,3],b[:,:,3])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();family,size=('GalmuriMono7',8) if n==6 else ('Galmuri9',10)
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'font':family,'font_px':size,'text_bbox':[x,y,x+layer.width,y+layer.height],'panel':panel,'resized':False,'native_glyphs_and_advances_preserved':True,'outside_mask_changed_pixels':0,'panel_frame_changed_pixels':0 if panel else None,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch14-v2','editing_method':'galmuri','font':family,'font_px':size,'method_reason':'명확한 도트 글씨. 원본 색상 밴드·검정 외곽선·흰 바깥 테두리를 유지하고 갈무리 기본 크기 사용.','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'원본 규격 및 간판·프레임 보존. 글자 축소·가로압축 없음. 팔레트변환·게임실행 미확인.'}
        cx=(i%3)*430;cy=(i//3)*300;d.text((cx+4,cy+3),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            sheet.paste(im,(cx+4+j*210,cy+22),im);big=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST);sheet.paste(big,(cx+4,cy+80+j*110),big)
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch14_v2_checks.json').write_text(json.dumps({'references':13,'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>장난감 선택 화면13개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>장난감 선택 화면13개</h1><p>갈무리9 기본10px · 누구에게 부탁할까?는 갈무리Mono7 기본8px · 원본 규격과 색상·간판 보존</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('13 labels; original panels and native glyphs preserved')

if __name__=='__main__':main()
