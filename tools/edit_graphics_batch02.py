"""MiniMap batch: native Galmuri7, unchanged icons and transparent backgrounds."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch02-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri7.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),8)
TEXTS={115:'몽키버거',116:'꽃집',117:'공원 입구',135:'뒷골목',136:'체크포인트',144:'출발/도착',145:'체크포인트'}
START={136:10,144:16,145:15}


def glyphs(text):
    parts=[];x=0
    for char in text:
        if char==' ':x+=2;continue
        im=Image.new('L',(32,32));draw=ImageDraw.Draw(im);draw.fontmode='1';draw.text((4,4),char,font=FONT,fill=255)
        box=im.getbbox();parts.append((im.crop(box),x,box[1]));x+=box[2]-box[0]+1
    top=min(y for _,_,y in parts);bottom=max(y+g.height for g,_,y in parts)
    mask=Image.new('L',(x-1,bottom-top))
    for g,x,y in parts:mask.paste(g,(x,y-top))
    assert set(np.unique(np.array(mask)))<={0,255}
    return mask


def main():
    OUT.mkdir(exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'};updates={};checks=[]
    sheet=Image.new('RGB',(820,7*115),'#d3d5cc');label=ImageDraw.Draw(sheet)
    for i,(index,text) in enumerate(TEXTS.items()):
        key=f'MiniMap/cell/{index}';r=rows[key];stem=key.replace('/','-')
        assert r['localization'].get('approval')!='approved'
        source=Image.open(ROOT/r['path']).convert('RGBA');before=np.array(source)
        xstart=START.get(index,0)
        old=(before[:,:,3]>0);old[:,:xstart]=False
        erased=before.copy();erased[old]=0;erased=Image.fromarray(erased)
        ys,xs=np.where(old);oldbox=(int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1))
        g=glyphs(text);width=g.width+2;height=g.height+2
        x=xstart if index in START else oldbox[0]+(oldbox[2]-oldbox[0]-width)//2
        y=oldbox[1]
        assert x>=0 and x+width<=source.width and y+height<=source.height,(key,(width,height),(x,y))
        ink=Image.new('L',source.size);ink.paste(g,(x+1,y+1));outline=ink.filter(ImageFilter.MaxFilter(3))
        result=erased.copy();result.paste((255,255,255,255),(0,0,*source.size),outline);result.paste((0,0,0,255),(0,0,*source.size),ink)
        new=np.array(outline)>0;allowed=old|new;after=np.array(result)
        assert not np.any(np.any(before!=after,axis=2)&~allowed)
        assert np.array_equal(before[:,:xstart],after[:,:xstart])
        assert source.size==result.size
        for suffix,im in [('original',source),('erased',erased),('korean',result),('mask',Image.fromarray(allowed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rec={'key':key,'text':text,'font':'Galmuri7','font_px':8,'glyph_size':list(g.size),'ink_bbox':list(outline.getbbox()),'size':list(source.size),'no_resizing':True,'protected_left_columns':xstart,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'output_sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False};checks.append(rec)
        label.text((10,i*115+2),key+' / original -> Korean',fill='black')
        for j,im in enumerate([source,result]):
            q=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(q,(10+j*370,i*115+28),q)
        updates[r['pixel_sha256']]={'korean_proposal':text,'output':(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix(),'preview':(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix(),'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch02-v1','editing_method':'galmuri','method_reason':'미니맵 원본이 명확한 7px 도트 글자: Galmuri7 정규 8px, 검정 획·흰 외곽선 1px, 리사이즈 없음','work_status':'review','approval':'pending','note':'아이콘 및 글자 마스크 밖 원본 픽셀 보존. 출발/도착은 전각 슬래시 대신 반각 슬래시로 동일한 구분 의미 유지.' if index==144 else '원본 글자 높이·흰 외곽선에 맞춘 정규 도트 렌더링. 아이콘과 글자 마스크 밖 픽셀 보존.'}
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch02_checks.json').write_text(json.dumps({'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>두 번째 묶음 · 미니맵 7종</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{padding:20px;background:white;margin:20px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:28px;flex-wrap:wrap}</style><h1>두 번째 묶음 · 미니맵 지명·안내 7종</h1><p>갈무리7 정규 8px · 검정 글자와 흰 외곽선 · 크기 변형 없음. 점·출입문·깃발 아이콘은 원본 그대로입니다. 게임 삽입·실행은 아직 확인하지 않았습니다.</p><a href="../../graphics-review/dashboard.html">작업 현황판</a>'
    for rec in checks:
        stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}"><h2>{rec["key"]} · {rec["text"]}</h2>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배 비교</p><div class="row">'
            for suffix,name in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{name}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':main()
