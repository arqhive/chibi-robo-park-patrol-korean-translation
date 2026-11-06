"""Authorized Galmuri rendering and precision composition, first review batch.

Writes versioned drafts only, never edits source PNGs or game resources.
"""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch01-v1'
FONTS=Path.home()/'AppData/Local/Microsoft/Windows/Fonts'
FONT=ImageFont.truetype(str(FONTS/'Galmuri7.ttf'),8)


def glyphs(text):
    # Native pixels, tight but non-overlapping advances; no resampling.
    im=Image.new('L',(600,16));x=0
    for ch in text:
        if ch==' ':x+=2;continue
        g=Image.new('L',(20,16));ImageDraw.Draw(g).text((0,-1),ch,font=FONT,fill=255)
        box=g.getbbox();g=g.crop(box);im.paste(g,(x,0));x+=g.width+1
    return im.crop(im.getbbox())


def place(base,text,box,outline=True):
    g=glyphs(text);x0,y0,x1,y1=box;pad=int(outline)
    assert g.width+pad*2<=x1-x0 and g.height+pad*2<=y1-y0,(text,g.size,box)
    x=x0+(x1-x0-g.width)//2;y=y0+(y1-y0-g.height)//2
    mask=Image.new('L',base.size);mask.paste(g,(x,y))
    outer=mask.filter(ImageFilter.MaxFilter(3)) if outline else mask
    result=base.copy()
    if outline:result.paste((0,0,0,255),(0,0,*base.size),outer)
    result.paste((255,255,255,255),(0,0,*base.size),mask)
    return result,outer


def fitted_generated(name,size,box):
    im=Image.open(OUT/(name+'-imagegen.png')).convert('RGBA')
    # Ignore isolated nearly transparent generation fringe for cropping only.
    bbox=im.getchannel('A').point(lambda v:255 if v>=96 else 0).getbbox()
    im=im.crop(bbox);w=box[2]-box[0];h=box[3]-box[1]
    ratio=min(w/im.width,h/im.height)
    im=im.resize((round(im.width*ratio),round(im.height*ratio)),Image.Resampling.LANCZOS)
    # DS source is binary alpha. Quantize onto the source palette later below.
    im.putalpha(im.getchannel('A').point(lambda a:255 if a>=96 else 0))
    result=Image.new('RGBA',size);result.alpha_composite(im,(box[0]+(w-im.width)//2,box[1]+(h-im.height)//2))
    return result


def source_palette(im,source,crisp_text=False):
    colors=sorted({c[:3] for c in source.getdata() if c[3]})
    if crisp_text:
        colors=[c for c in colors if max(c)-min(c)>50 or max(c)<60 or min(c)>220]
    arr=np.array(im);rgb=arr[:,:,:3].astype(np.int32);pal=np.array(colors,dtype=np.int32)
    dist=((rgb[:,:,None,:]-pal[None,None,:,:])**2).sum(axis=3)
    arr[:,:,:3]=pal[dist.argmin(axis=2)].astype(np.uint8)
    arr[arr[:,:,3]==0]=0
    return Image.fromarray(arr)


def main():
    path=ROOT/'metadata/extraction_manifest.json';m=json.loads(path.read_text(encoding='utf-8'))
    targets={}
    for r in m['graphics']:
        if r['edition']=='jp' and r['key'].split('/')[0] in ['TitleLogo','TitleSave','TitleSaveBG','EditIconStaticA'] and r.get('localization',{}).get('action')=='translate_proposed':
            targets.setdefault(r['pixel_sha256'],r)
    checks=[];records={}
    for digest,r in targets.items():
        assert r['localization'].get('draft_version') in (None,'batch01-v1'),'A newer revision exists; do not reset it with the v1 builder'
        assert r['localization'].get('approval')!='approved','Create a new version instead of overwriting an approved draft'
        key=r['key'];source=Image.open(ROOT/r['path']).convert('RGBA');before=np.array(source)
        base=source.copy();allowed=Image.new('L',source.size);name=key.replace('/','-')
        is_gen=key in ['TitleLogo/cell/0','TitleLogo/cell/1','TitleSave/cell/50','TitleSave/cell/51']
        if key=='TitleLogo/cell/0':
            gen=Image.open(OUT/'title-imagegen.png').convert('RGBA').resize(source.size,Image.Resampling.LANCZOS)
            gen.putalpha(gen.getchannel('A').point(lambda a:255 if a>=96 else 0))
            # Lock original robot, cord/clouds, flower/exclamation and trademark.
            preserve=Image.new('L',source.size);d=ImageDraw.Draw(preserve)
            d.polygon([(0,68),(30,68),(29,79),(35,84),(40,80),(49,85),(60,79),(73,86),(90,87),(95,99),(95,104),(0,104)],fill=255)
            d.rectangle((156,0,191,103),fill=255)
            a=np.array(preserve)>0
            b=np.array(source);b[~a]=0;base=Image.fromarray(b)
            g=np.array(gen);g[a]=before[a];result=Image.fromarray(g)
            allowed=Image.fromarray((~a).astype('uint8')*255)
        elif is_gen:
            tag={'TitleLogo/cell/1':'touch','TitleSave/cell/50':'here','TitleSave/cell/51':'tap'}[key]
            base=Image.new('RGBA',source.size)
            # Source is text-only on transparency; original contour is removal mask.
            oldbox=source.getchannel('A').getbbox();margin=1
            box=(margin,oldbox[1],source.width-margin,oldbox[3])
            result=fitted_generated(tag,source.size,box)
            allowed=Image.fromarray(np.maximum(np.array(source.getchannel('A')),np.array(result.getchannel('A'))))
        elif key=='TitleSaveBG/screen':
            b=np.array(base);mask=np.zeros((source.height,source.width),dtype=bool)
            for shift in [0,84,168]:
                for y in range(28,37):
                    for x in range(25+shift,63+shift):
                        if tuple(b[y,x,:3]) in [(0,0,0),(255,255,255)]:
                            mask[y,x]=True;b[y,x]=(24,24,24,255)
            base=Image.fromarray(b);result=base.copy();allowed=Image.fromarray(mask.astype('uint8')*255)
            for n,shift in enumerate([0,84,168],1):
                result,new=place(result,f'데이터 {n}',(25+shift,28,63+shift,37))
                allowed=Image.fromarray(np.maximum(np.array(allowed),np.array(new)))
        elif key.startswith('TitleSave/') and key!='TitleSave/cell/26':
            # Interior backdrop is flat white above y8 and gray below, verified
            # from the original. Remove only pixels differing from that backdrop.
            b=np.array(base);mask=np.zeros((source.height,source.width),dtype=bool)
            frame_right=max(x for x in range(source.width) if before[0,x,3])
            for y in range(2,13):
                bg=(255,255,255,255) if y<8 else (180,180,180,255)
                for x in range(13,frame_right):
                    if tuple(b[y,x])!=bg:mask[y,x]=True;b[y,x]=bg
            base=Image.fromarray(b);result,new=place(base,r['localization']['korean_proposal'],(13,2,frame_right,13))
            allowed=Image.fromarray(np.maximum(mask.astype('uint8')*255,np.array(new)))
        else:
            base=Image.new('RGBA',source.size)
            result,new=place(base,r['localization']['korean_proposal'],(0,0,source.width,source.height))
            allowed=Image.fromarray(np.maximum(np.array(source.getchannel('A')),np.array(new)))
        if is_gen or key=='TitleSaveBG/screen':
            quantized=source_palette(result,source,crisp_text=is_gen and key!='TitleLogo/cell/0')
            # Keep exact protected source pixels, including transparent RGB.
            q=np.array(quantized);a=np.array(allowed)>0;q[~a]=before[~a];result=Image.fromarray(q)
        after=np.array(result);a=np.array(allowed)>0
        outside=int(np.any(before!=after,axis=2)[~a].sum())
        assert outside==0,(key,outside)
        assert result.size==source.size
        if key.startswith('TitleSave/') and not is_gen and key!='TitleSave/cell/26':
            assert np.array_equal(before[:,:13],after[:,:13]),'Button icon changed'
            assert np.array_equal(before[:,frame_right:],after[:,frame_right:]),'Button right edge changed'
        existing=set(source.getdata());newcolors=set(result.getdata())
        # Transparent RGBA is normalized only within the editable area.
        assert {c for c in newcolors if c[3]} <= {c for c in existing if c[3]},key
        for suffix,im in [('original',source),('erased',base),('korean',result),('mask',allowed)]:im.save(OUT/f'{name}-{suffix}.png')
        comparison=f'work/graphics-draft/batch01-v1/index.html#{name}'
        records[digest]={'output':(OUT/f'{name}-korean.png').relative_to(ROOT).as_posix(),'comparison':comparison,'erased':(OUT/f'{name}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{name}-mask.png').relative_to(ROOT).as_posix(),'editing_method':'imagegen' if is_gen else 'galmuri','method_reason':'둥근 장식 글자·로고: 이미지젠 생성 후 원본 규격에 정밀 합성' if is_gen else '원본에서 명확한 도트 글자로 확인: Galmuri7 8px, 픽셀 재축소 없음','work_status':'review','approval':'pending','draft_version':'batch01-v1'}
        checks.append({'key':key,'method':records[digest]['editing_method'],'size':list(source.size),'outside_mask_changed_pixels':outside,'source_opaque_palette_preserved':True,'output_sha256':hashlib.sha256((OUT/f'{name}-korean.png').read_bytes()).hexdigest(),'source_file_sha256':hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest(),'runtime_verified':False})
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in records:r['localization'].update(records[r['pixel_sha256']])
    path.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch01_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    import html
    page='<meta charset="utf-8"><title>첫 그래픽 비교</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{padding:20px;background:white;margin:20px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px} .row{display:flex;gap:22px;flex-wrap:wrap}h2{font-size:20px}</style><h1>타이틀·저장 화면 · 첫 비교</h1><p>장식 4도안: 이미지젠 / 도트 11도안: 갈무리7. 모두 사용자 확정 전이며 게임 삽입·실행은 미확인입니다.</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for check in checks:
        name=check['key'].replace('/','-');w,h=check['size'];page+=f'<section id="{name}"><h2>{html.escape(check["key"])}</h2><p>{check["method"]} · {w}×{h}px · 변경 마스크 밖 변경 0픽셀</p>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배</p><div class="row">'
            for suffix,label in [('original','원본'),('erased','지운 뒤'),('korean','한글')]:page+=f'<div>{label}<br><img src="{name}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print('Prepared',len(checks),'drafts; outside-mask changes: 0')


if __name__=='__main__':main()
