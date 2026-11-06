"""Render button captions without touching the original button sprites."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from preview_neicon_mono7 import render_line,FONT_PATH
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch17-v2'
IDS=[19,20,30,31,32,33,34,35,89,90,91,92,93,94]

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in {f'NewPCStaticA/cell/{n}' for n in IDS}];assert len(rows)==14
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);loc=r['localization'];assert loc['approval']!='approved';stem=r['key'].replace('/','-')
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        gray=np.all(a==[65,65,65,255],axis=2);gy,gx=np.where(gray);button=[int(gx.min()),int(gy.min()),int(gx.max()+1),int(gy.max()+1)]
        left,right=(29,62) if n in [19,20] else (0,button[0])
        region=np.zeros(a.shape[:2],bool);region[:,left:right]=True;old=(a[:,:,3]>0)&region;ys,xs=np.where(old);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
        clean=a.copy();clean[old]=0
        repair=np.zeros(a.shape[:2],bool)
        if n==19:
            # Original Japanese outline overlaps the frame: restore its two columns
            # from the identical unobstructed edge immediately above, pixel by pixel.
            for yy in range(12,21):
                for xx in (27,28):
                    if not np.array_equal(a[yy,xx],a[10,xx]):
                        repair[yy,xx]=True;clean[yy,xx]=a[10,xx]
            assert int(repair.sum())==14
        erased=Image.fromarray(clean)
        core,metrics=render_line(loc['korean_proposal'],right-left-4);ink=Image.new('L',(core.width+4,11));ink.paste(core,(2,2));black=ink.filter(ImageFilter.MaxFilter(3));white=black.filter(ImageFilter.MaxFilter(3));layer=Image.new('RGBA',ink.size)
        color=(74,213,255,255) if loc['korean_proposal']=='끝내기' else (255,205,0,255) if loc['korean_proposal']=='뒤로' else (255,74,74,255)
        assert np.any(np.all(a[old]==color,axis=1)),r['key']
        layer.paste((255,255,255,255),(0,0),white);layer.paste((0,0,0,255),(0,0),black);layer.paste(color,(0,0),ink)
        x=max(left,min((box[0]+box[2]-layer.width)//2,right-layer.width));y=(box[1]+box[3]-layer.height)//2
        assert x>=left and x+layer.width<=right and y>=0 and y+layer.height<=src.height
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|repair|(np.array(overlay)[:,:,3]>0)
        assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[~(region|repair)],b[~(region|repair)])
        assert not np.any(clean[:,left:right,3])
        previous=np.array(Image.open(ROOT/'work/graphics-draft/batch17-v1'/f'{stem}-korean.png').convert('RGBA'))
        assert np.array_equal(previous[~repair],b[~repair])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'text_bbox':[x,y,x+layer.width,y+layer.height],'original_text_bbox':box,'protected_button_bbox':button,'font':'GalmuriMono7','font_px':8,'metrics':metrics,'resized':False,'outside_mask_changed_pixels':0,'button_pixels_changed':int(repair.sum()),'frame_outline_restored_pixels':int(repair.sum()),'unchanged_outside_repair_vs_v1':True,'source_extra_fragment_preserved':n in [19,20],'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch17-v2','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'method_reason':'명확한 도트 버튼 글씨. Mono7 기본8px 원본 획과 빨강/하늘색/노랑 및 검정/흰 테두리 유지.','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'셀19 버튼 오른쪽 테두리에 남았던 일본어 외곽선14픽셀 복원. 그 외 v1 픽셀 동일. 셀19·20 우측 끝 원본 조각은 보호영역으로 그대로 유지. 팔레트변환·게임실행 미확인.'}
        if i%8==0:sheets.append(Image.new('RGB',(1120,880),'#d5d9cf'))
        sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%8;cx=j%2*560;cy=j//2*220;d.text((cx+3,cy+2),r['key'],fill='black')
        for k,im in enumerate([src,result]):
            sheet.paste(im,(cx+3+k*275,cy+23),im);big=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);sheet.paste(big,(cx+3+k*275,cy+65),big)
    for i,s in enumerate(sheets):s.save(OUT/f'overview-{i+1}.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch17_v2_checks.json').write_text(json.dumps({'references':14,'items':checks,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>메뉴 버튼14개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>메뉴 버튼14개</h1><p>갈무리Mono7 기본8px · 취소 왼쪽 버튼 테두리 잔상 정리 · 나머지13개 동일 · 전체14개</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        if c['source_extra_fragment_preserved']:page+='<p>우측 끝에 보이는 조각은 원본에도 있으며 그대로 유지했습니다.</p>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('14 button labels; cell19 frame restored14 pixels; all other pixels identical to v1')

if __name__=='__main__':main()
