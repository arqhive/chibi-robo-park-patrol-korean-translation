"""Render 14 menu text fragments while preserving arrows and small icons."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageFont,ImageDraw,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch16-v2'
IDS=[11,12,25,26,67,68,69,70,76,83,84,85,86]
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    keys={f'NewPCStaticA/cell/{n}' for n in IDS}|{'NewPCShopMInfo/cell/14'}
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in keys];assert len(rows)==14
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);shop=r['key'].startswith('NewPCShopMInfo/');stem=r['key'].replace('/','-');loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);region=np.ones(a.shape[:2],bool);limit=(0,0,src.width,src.height)
        if shop:region[:,:14]=False;limit=(14,0,src.width,src.height)
        elif n==26:region[:,:15]=False;limit=(15,0,src.width,src.height)
        elif n==11:region[15:]=False;limit=(0,0,24,15)
        elif n in [12,25]:region[:,25:]=False;limit=(0,0,25,16)
        elif n in [83,84]:region[:,37:]=False;limit=(0,0,37,16)
        old=(a[:,:,3]>0)&region;ys,xs=np.where(old);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        clean=a.copy();clean[old]=0;erased=Image.fromarray(clean)
        mono=shop or n in [70,86];padding=1 if shop else 2
        if mono:
            core,metrics=render_line(loc['korean_proposal'],limit[2]-limit[0]-2*padding)
        else:
            core=Image.new('L',(256,30));draw=ImageDraw.Draw(core);draw.fontmode='1';draw.text((3,3),loc['korean_proposal'],font=F9,fill=255);core=core.crop(core.getbbox());metrics={'spacing_pixels_removed':0,'native_glyph_shapes_preserved':True}
        ink=Image.new('L',(core.width+2*padding,core.height+2*padding));ink.paste(core,(padding,padding));edge=ink.filter(ImageFilter.MaxFilter(3));layer=Image.new('RGBA',ink.size)
        if shop:
            layer.paste((65,65,65,255),(0,0),edge);layer.paste((255,255,255,255),(0,0),ink)
        else:
            outer=edge.filter(ImageFilter.MaxFilter(3));layer.paste((255,255,255,255),(0,0),outer);layer.paste((0,0,0,255),(0,0),edge)
            layer.paste((255,230,0,255) if n in [11,12,25] else (255,255,255,255),(0,0),ink)
        x=max(limit[0],min(box[0],limit[2]-layer.width));y=max(limit[1],min((box[1]+box[3]-layer.height)//2,limit[3]-layer.height))
        assert x>=limit[0] and y>=limit[1] and x+layer.width<=limit[2] and y+layer.height<=limit[3],(r['key'],layer.size,limit)
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|(np.array(overlay)[:,:,3]>0)
        assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[~region],b[~region])
        if not shop:
            previous=Image.open(ROOT/'work/graphics-draft/batch16-v1'/f'{stem}-korean.png').convert('RGBA')
            assert previous.tobytes()==result.tobytes()
        else:
            assert not np.any(clean[:,14:,3]),'All original text must be erased'
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();family,size=('GalmuriMono7',8) if mono else ('Galmuri9',10)
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'font':family,'font_px':size,'metrics':metrics,'text_bbox':[x,y,x+layer.width,y+layer.height],'editable_region':limit,'resized':False,'outside_mask_changed_pixels':0,'protected_icon_pixels_changed':0,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch16-v2','editing_method':'galmuri','font':family,'font_px':size,'method_reason':'원본 도트 UI와 기존 갈무리 선택에 맞춘 기본크기 렌더링. 화살표·아이콘 개별 보호.','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'원본 크기·화살표·아이콘 보존. 글자 획 변형 없이 배치. 팔레트변환·게임실행 미확인.'}
        if i%8==0:sheets.append(Image.new('RGB',(1100,640),'#d5d9cf'))
        sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%8;cx=j%2*550;cy=j//2*160;d.text((cx+3,cy+2),r['key'],fill='black')
        for k,im in enumerate([src,result]):
            sheet.paste(im,(cx+3+k*270,cy+23),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+3+k*270,cy+60),big)
    for i,s in enumerate(sheets):s.save(OUT/f'overview-{i+1}.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch16_v2_checks.json').write_text(json.dumps({'references':14,'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>메뉴 표시14개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>메뉴 표시14개</h1><p>갈무리9 기본10px · 도구사요 / 놀이기구: / 남은 양은 갈무리Mono7 기본8px · 원본 아이콘·화살표 보존</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('14 labels; original arrows and icons preserved')

if __name__=='__main__':main()
