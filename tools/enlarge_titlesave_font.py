"""Prepare a one-pixel taller Galmuri trial for the TitleSave pixel-text family."""
import hashlib
import html
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/titlesave-font9-v1'
FONT=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri7.ttf'),9)
ICON_END={27:13,29:14,31:14,33:13,35:16,37:16,47:17}


def glyphs(text):
    canvas=Image.new('L',(600,24));x=0
    for char in text:
        if char==' ':x+=2;continue
        g=Image.new('L',(24,24));draw=ImageDraw.Draw(g);draw.fontmode='1';draw.text((0,-1),char,font=FONT,fill=255)
        g=g.crop(g.getbbox());canvas.paste(g,(x,0));x+=g.width+1
    return canvas.crop(canvas.getbbox())


def place(base,text,box,left=False,top=None):
    g=glyphs(text);natural=list(g.size);x0,y0,x1,y1=box
    if g.width+2>x1-x0:
        g=g.resize((x1-x0-2,g.height),Image.Resampling.NEAREST)
    assert g.height+2<=y1-y0,(text,g.size,box)
    x=x0+1 if left else x0+(x1-x0-g.width)//2
    y=top+1 if top is not None else y0+(y1-y0-g.height)//2
    mask=Image.new('L',base.size);mask.paste(g,(x,y));outline=mask.filter(ImageFilter.MaxFilter(3))
    assert outline.getbbox()[0]>=x0 and outline.getbbox()[2]<=x1
    assert outline.getbbox()[1]>=y0 and outline.getbbox()[3]<=y1
    result=base.copy();result.paste((0,0,0,255),(0,0,*base.size),outline);result.paste((255,255,255,255),(0,0,*base.size),mask)
    return result,np.array(outline)>0,{'text':text,'natural_glyph_size':natural,'placed_glyph_size':list(g.size),'ink_bbox':list(outline.getbbox())}


def main():
    OUT.mkdir(exist_ok=True)
    f=ROOT/'metadata/extraction_manifest.json';manifest=json.loads(f.read_text(encoding='utf-8'))
    selected=['TitleSave/cell/26']+[f'TitleSave/cell/{i}' for i in ICON_END]+['TitleSaveBG/screen']
    rows={r['key']:r for r in manifest['graphics'] if r['edition']=='jp'};records=[];updates={}
    for key in selected:
        r=rows[key];loc=r['localization'];stem=key.replace('/','-')
        source=Image.open(ROOT/r['path']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA')
        previous_path=OUT/f'{stem}-previous.png' if loc.get('draft_version')=='titlesave-font9-v1' else ROOT/loc['output']
        previous=Image.open(previous_path).convert('RGBA');before=np.array(source)
        if key=='TitleSave/cell/26':
            text='비어 있음';bbox=source.getchannel('A').getbbox()
            result,new,info=place(erased,text,(bbox[0],0,source.width,source.height),left=True,top=bbox[1]);details=[info]
            assert result.getbbox()[:2]==bbox[:2]
        elif key=='TitleSaveBG/screen':
            result=erased.copy();new=np.zeros((source.height,source.width),bool);details=[]
            for n,shift in enumerate([0,84,168],1):
                result,mask,info=place(result,f'데이터 {n}',(25+shift,27,63+shift,38));new|=mask;details.append(info)
        else:
            idx=int(key.split('/')[-1]);end=ICON_END[idx];right=max(x for x in range(source.width) if before[0,x,3])
            result,new,info=place(erased,loc['korean_proposal'],(end+1,2,right,13));details=[info]
            assert np.array_equal(before[:,:end],np.array(result)[:,:end])
            assert np.array_equal(before[:,right:],np.array(result)[:,right:])
            assert np.array_equal(before[[0,1,13,14,15]],np.array(result)[[0,1,13,14,15]])
        allowed=np.any(before!=np.array(erased),axis=2)|new
        assert not np.any(np.any(before!=np.array(result),axis=2)&~allowed)
        for suffix,im in [('original',source),('previous',previous),('erased',erased),('korean',result),('mask',Image.fromarray(allowed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rec={'key':key,'font_size':9,'previous_font_size':8,'glyph_height':8,'previous_glyph_height':7,'details':details,'outside_mask_changed_pixels':0,'icon_and_frame_preserved':key not in ['TitleSave/cell/26','TitleSaveBG/screen'],'size':list(source.size),'output_sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False};records.append(rec)
        updates[r['pixel_sha256']]={'output':(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix(),'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'draft_version':'titlesave-font9-v1','method_reason':'Galmuri7 9px 시험안: 글자 높이 7→8px, 비어 있음은 32px 칸에 가로폭 조정','work_status':'review','approval':'pending'}
    for r in manifest['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:
            r['localization'].update(updates[r['pixel_sha256']])
            if r['key']=='TitleSave/cell/26':r['localization']['korean_proposal']='비어 있음';r['localization']['note']='사용자 최신 지시: 띄어쓰기 복원, 원본 잉크 시작 (0,4)에 배치. 높이 +1px, 가로폭만 칸에 맞춤.'
    f.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/titlesave_font9_checks.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>TitleSave 글자 1px 확대</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{padding:20px;background:white;margin:20px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:22px;flex-wrap:wrap}</style><h1>TitleSave · 글자 1px 확대 시험안</h1><p>갈무리 설정 8→9px, 실제 글자 높이 7→8px. 비어 있음은 원본 시작점 (0,4)에 맞추고 띄어쓰기를 복원했습니다. 이 항목만 32px 폭에 맞춰 가로폭을 조정했습니다. 장식 그림인 여기를·터치!는 폰트 확대 대상에서 제외했습니다.</p>'
    for rec in records:
        stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}"><h2>{rec["key"]}</h2>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배</p><div class="row">'
            for suffix,label in [('original','원본'),('previous','이전'),('korean','1px 확대')]:page+=f'<div>{label}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(records,ensure_ascii=False))


if __name__=='__main__':main()
