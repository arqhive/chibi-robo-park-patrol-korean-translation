"""Native Galmuri9 10px preview, never compress or clip letter shapes."""
import hashlib
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/titlesave-galmuri9-10px-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),10)
ICON_END={27:13,29:14,31:14,33:13,35:16,37:16,47:17}


def glyphs(text):
    parts=[];x=0
    for char in text:
        if char==' ':x+=2;continue
        g=Image.new('L',(32,32));draw=ImageDraw.Draw(g);draw.fontmode='1'
        draw.text((4,4),char,font=FONT,fill=255)
        box=g.getbbox();parts.append((g.crop(box),x,box[1]));x+=box[2]-box[0]+1
    top=min(y for _,_,y in parts);bottom=max(y+g.height for g,_,y in parts)
    mask=Image.new('L',(x-1,bottom-top))
    for g,x,y in parts:mask.paste(g,(x,y-top))
    assert set(np.unique(np.array(mask)))<={0,255}
    return mask


def place(base,text,box,left=False,top=None):
    g=glyphs(text);x0,y0,x1,y1=box
    assert g.width+2<=x1-x0 and g.height+2<=y1-y0,(text,g.size,box)
    x=x0+1 if left else x0+(x1-x0-g.width)//2
    y=top+1 if top is not None else y0+(y1-y0-g.height)//2
    mask=Image.new('L',base.size);mask.paste(g,(x,y));outline=mask.filter(ImageFilter.MaxFilter(3))
    bounds=outline.getbbox()
    assert bounds[0]>=x0 and bounds[2]<=x1 and bounds[1]>=y0 and bounds[3]<=y1
    result=base.copy();result.paste((0,0,0,255),(0,0,*base.size),outline);result.paste((255,255,255,255),(0,0,*base.size),mask)
    return result,np.array(outline)>0,{'text':text,'glyph_size':list(g.size),'ink_bbox':list(bounds),'resized':False}


def main():
    OUT.mkdir(exist_ok=True)
    f=ROOT/'metadata/extraction_manifest.json';manifest=json.loads(f.read_text(encoding='utf-8'))
    rows={r['key']:r for r in manifest['graphics'] if r['edition']=='jp'}
    records=[];updates={}
    for key in ['TitleSave/cell/26']+[f'TitleSave/cell/{i}' for i in ICON_END]+['TitleSaveBG/screen']:
        r=rows[key];loc=r['localization'];stem=key.replace('/','-')
        source=Image.open(ROOT/r['path']).convert('RGBA')
        erased=Image.open(ROOT/'work/graphics-draft/titlesave-font9-v1'/f'{stem}-erased.png').convert('RGBA')
        previous=Image.open(ROOT/'work/graphics-draft/titlesave-font9-v1'/f'{stem}-korean.png').convert('RGBA')
        before=np.array(source);requires_expansion=key=='TitleSave/cell/26'
        if requires_expansion:
            text='비어 있음';bbox=source.getbbox();needed=glyphs(text).width+2
            trial=Image.new('RGBA',(needed,source.height))
            result,new,info=place(trial,text,(0,0,needed,source.height),left=True,top=bbox[1]);details=[info]
            assert result.getbbox()[:2]==bbox[:2]
            allowed=new.copy()
        elif key=='TitleSaveBG/screen':
            result=erased.copy();new=np.zeros(before.shape[:2],bool);details=[]
            for n,shift in enumerate([0,84,168],1):
                result,mask,info=place(result,f'데이터 {n}',(25+shift,27,63+shift,38));new|=mask;details.append(info)
        else:
            idx=int(key.split('/')[-1]);end=ICON_END[idx];right=max(x for x in range(source.width) if before[0,x,3])
            result,new,info=place(erased,loc['korean_proposal'],(end+1,2,right,13));details=[info]
            assert np.array_equal(before[:,:end],np.array(result)[:,:end])
            assert np.array_equal(before[:,right:],np.array(result)[:,right:])
            assert np.array_equal(before[[0,1,13,14,15]],np.array(result)[[0,1,13,14,15]])
        if not requires_expansion:
            allowed=np.any(before!=np.array(erased),axis=2)|new
            assert not np.any(np.any(before!=np.array(result),axis=2)&~allowed)
        for suffix,im in [('original',source),('previous',previous),('erased',erased),('korean',result),('mask',Image.fromarray(allowed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rec={'key':key,'font':'Galmuri9','font_size':10,'details':details,'resized':False,'original_size':list(source.size),'preview_size':list(result.size),'requires_resource_width_expansion':requires_expansion,'outside_mask_changed_pixels':None if requires_expansion else 0,'icon_and_frame_preserved':key.startswith('TitleSave/cell/') and not requires_expansion,'runtime_verified':False,'output_sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest()};records.append(rec)
        relative=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        updates[r['pixel_sha256']]={'output':None if requires_expansion else relative,'preview':relative,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'draft_version':'titlesave-galmuri9-10px-v1','method_reason':'Galmuri9 정규 10px, 이진 도트 그대로 렌더링, 가로·세로 리사이즈 없음','work_status':'review','approval':'pending','requires_resource_width_expansion':requires_expansion,'note':'비어 있음: 원본 시작점 (0,4), 자연 폭 41px. 원본 32px를 넘어 미리보기만 제공. 리소스 폭 확장 미구현, 주입용 output 없음.' if requires_expansion else '갈무리9 정규 10px. 글자 크기 변형 없이 원래 캔버스에 배치, 아이콘·테두리 보존.'}
    for r in manifest['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    f.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/titlesave_galmuri9_10px_checks.json').write_text(json.dumps({'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>TitleSave 갈무리9 10px 비교</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{padding:20px;background:white;margin:20px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:22px;flex-wrap:wrap}.note{color:#864511}</style><h1>TitleSave · 갈무리9 정규 10px</h1><p>가로 압축·크기 재조정 없이 그렸습니다. 비어 있음만 41px가 필요해 폭 확장 미리보기로 표시했습니다. 게임 주입은 아직 하지 않았습니다.</p>'
    for rec in records:
        stem=rec['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{rec["key"]}</h2>'
        if rec['requires_resource_width_expansion']:page+='<p class="note">원본 폭 32px → 필요 폭 41px. 시작 위치 (0,4) 유지. 리소스 폭 확장 필요, 현재는 미리보기입니다.</p>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배</p><div class="row">'
            for suffix,label in [('original','원본'),('previous','이전 갈무리7 9px'),('korean','갈무리9 10px')]:
                w,h=Image.open(OUT/f'{stem}-{suffix}.png').size
                page+=f'<div>{label}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False))


if __name__=='__main__':main()
