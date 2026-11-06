"""Raise both checkpoint labels one pixel from batch02-v4."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from preview_titlesave_galmuri9 import glyphs, FONT_PATH
from edit_graphics_batch02 import TEXTS, START
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch02-v5'


def main():
    OUT.mkdir(exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'};updates={};checks=[]
    sheet=Image.new('RGB',(850,7*120),'#d3d5cc');label=ImageDraw.Draw(sheet)
    for i,(index,text) in enumerate(TEXTS.items()):
        key=f'MiniMap/cell/{index}';r=rows[key];stem=key.replace('/','-')
        assert r['localization'].get('approval')!='approved'
        source=Image.open(ROOT/r['path']).convert('RGBA');before=np.array(source)
        previous=Image.open(ROOT/'work/graphics-draft/batch02-v4'/f'{stem}-korean.png').convert('RGBA')
        xstart=START.get(index,0);old=(before[:,:,3]>0);old[:,:xstart]=False
        erased=before.copy();erased[old]=0;erased=Image.fromarray(erased)
        g=glyphs(text);width,height=g.width+2,g.height+2
        x=xstart if index in START else max(0,(source.width-width)//2)
        source_rows=np.where(old)[0]
        source_top,source_bottom=int(source_rows.min()),int(source_rows.max()+1)
        offset=1 if index in (136,145) else 0
        y=(source_top+source_bottom-height)//2+offset
        assert y>=0 and y+height<=source.height
        canvas=(max(source.width,x+width),source.height);expanded=canvas!=source.size
        ink=Image.new('L',canvas);ink.paste(g,(x+1,y+1));outline=ink.filter(ImageFilter.MaxFilter(3))
        result=Image.new('RGBA',canvas);result.paste(erased,(0,0));result.paste((255,255,255,255),(0,0,*canvas),outline);result.paste((0,0,0,255),(0,0,*canvas),ink)
        new=np.array(outline)>0;allowed=new.copy();allowed[:,:source.width]|=old
        padded=np.zeros((canvas[1],canvas[0],4),dtype='uint8');padded[:,:source.width]=before
        after=np.array(result)
        assert not np.any(np.any(padded!=after,axis=2)&~allowed)
        assert np.array_equal(before[:,:xstart],after[:,:xstart])
        bounds=outline.getbbox();assert bounds[1]+bounds[3]==source_top+source_bottom+2*offset
        assert bounds==(x,y,x+width,y+height)
        for suffix,im in [('original',source),('previous',previous),('erased',erased),('korean',result),('mask',Image.fromarray(allowed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rec={'key':key,'text':text,'font':'Galmuri9','font_px':10,'glyph_size':list(g.size),'ink_bbox':list(bounds),'original_size':list(source.size),'preview_size':list(canvas),'vertical_margins':[y,source.height-y-height],'original_text_y':[source_top,source_bottom],'original_center_y':(source_top+source_bottom)/2,'result_center_y':(bounds[1]+bounds[3])/2,'offset_from_v3_y':offset,'no_resizing':True,'requires_resource_width_expansion':expanded,'protected_left_columns':xstart,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'output_sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False};checks.append(rec)
        label.text((10,i*120+2),key+' / original -> Galmuri9 10px'+(' (width expansion)' if expanded else ''),fill='black')
        for j,im in enumerate([source,result]):
            q=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(q,(10+j*400,i*120+30),q)
        path=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        updates[r['pixel_sha256']]={'output':None if expanded else path,'preview':path,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch02-v5','editing_method':'galmuri','method_reason':f'Galmuri9 정규 10px, 원본 글자 중심 기준 아래 {offset}px 배치. 리사이즈 없음','work_status':'review','approval':'pending','requires_resource_width_expansion':expanded,'note':f'갈무리9 10px, 원본 글자 중심 기준 아래 {offset}px 배치. 아이콘·글자 마스크 밖 픽셀 보존. '+(f'원본 폭 {source.width}px 대비 필요 폭 {canvas[0]}px: 폭 확장 미구현, 미리보기만 제공.' if expanded else '원래 캔버스 크기 유지.')}
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch02_v5_checks.json').write_text(json.dumps({'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>미니맵 · 갈무리9 10px 중앙 정렬</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{padding:20px;background:white;margin:20px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:28px;flex-wrap:wrap}.note{color:#8a4911}</style><h1>미니맵 · 갈무리9 정규 10px / 체크포인트 위치 수정</h1><p>체크포인트 두 종류의 글자만 이전 결과(v4)보다 1px 올렸습니다. 다른 다섯 항목은 그대로입니다. 아이콘은 원본 그대로 유지했습니다. 글자를 압축하거나 자르지 않았습니다.</p><a href="../../graphics-review/dashboard.html">작업 현황판</a>'
    for rec in checks:
        stem=rec['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{rec["key"]} · {rec["text"]}</h2><p>원본 글자 중심 {rec["original_center_y"]}px / 한글 중심 {rec["result_center_y"]}px</p>'
        if rec['requires_resource_width_expansion']:page+=f'<p class="note">원본 폭 {rec["original_size"][0]}px → 필요 폭 {rec["preview_size"][0]}px. 폭 확장이 필요한 미리보기이며 실제 리소스 확장·주입은 아직 하지 않았습니다.</p>'
        else:page+='<p>원래 이미지 크기 안에 들어갑니다.</p>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배 비교</p><div class="row">'
            for suffix,name in [('original','원본'),('previous','이전 위치'),('korean','최신 수정 결과')]:
                with Image.open(OUT/f'{stem}-{suffix}.png') as im:w,h=im.size
                page+=f'<div>{name}<br><img src="{stem}-{suffix}.png" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(checks,ensure_ascii=False))


if __name__=='__main__':main()
