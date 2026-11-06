"""Native Galmuri ability labels within the original resource dimensions."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/abilities-v1'
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)
SHORT={'立ちこぎ':'서서밟기','坂すべり':'미끄럼','ヘリ':'헬기'}

def nine(text,space_reduction=0):
    im=Image.new('L',(256,24));d=ImageDraw.Draw(im);d.fontmode='1';x=0
    for ch in text:
        d.text((x,0),ch,font=F9,fill=255)
        x+=int(F9.getlength(ch))-(space_reduction if ch==' ' else 0)
    return im.crop(im.getbbox())

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='abilities' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==30
    updates={};checks=[];sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);small=r['key'].startswith('PlayIcon/');old=a[:,:,3]>0
        if not small:old[:,:16]=False
        assert all(tuple(p) in [(0,0,0,255),(255,255,255,255)] for p in a[old])
        yy,xx=np.where(old);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)];x=box[0]
        clean=a.copy();clean[old]=0;erased=Image.fromarray(clean)
        text=SHORT.get(loc['japanese_reading'],loc['korean_proposal']);padding=1 if small else 2;limit=src.width-x-2*padding;space_reduction=0
        if small:
            core,metrics=render_line(text,limit);font='GalmuriMono7';px=8
        else:
            core=nine(text);font='Galmuri9';px=10
            while core.width>limit and ' ' in text and space_reduction<3:
                space_reduction+=1;core=nine(text,space_reduction)
            metrics={'native_glyph_shapes_preserved':True,'space_width_reduced_px':space_reduction}
            if core.width>limit:
                core,metrics=render_line(text,limit);font='GalmuriMono7';px=8;space_reduction=0
                metrics['font_selection_reason']='Original 40px label area cannot fit Galmuri9 without changing glyph shapes; use native Mono7'
        assert core.width<=limit
        ink=Image.new('L',(core.width+2*padding,core.height+2*padding));ink.paste(core,(padding,padding));layer=Image.new('RGBA',ink.size)
        if small:
            layer.paste((255,255,255,255),(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((0,0,0,255),(0,0),ink)
        else:
            layer.paste((255,255,255,255),(0,0),ink.filter(ImageFilter.MaxFilter(5)));layer.paste((0,0,0,255),(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((255,255,255,255),(0,0),ink)
        y=(box[1]+box[3]-layer.height)//2
        assert 0<=y and y+layer.height<=src.height and x+layer.width<=src.width
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|(np.array(overlay)[:,:,3]>0)
        assert np.array_equal(a[~mask],b[~mask])
        if not small:assert np.array_equal(a[:,:16],b[:,:16])
        assert set(np.unique(np.array(core)))<={0,255}
        stem=r['key'].replace('/','-')
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
        updates[r['pixel_sha256']]={'korean_proposal':text,'lines':[text],'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'abilities-v1','editing_method':'galmuri','font':font,'font_px':px,'method_reason':'사용자 지정: 작은 기술 이름 갈무리7, 큰 이름 갈무리9. 원본 이름칸 폭에 따라 선택, 글자 획 리사이즈 없음.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 시작x와 세로 중심 유지. 아이콘16열 보존. 원본 크기 안에 배치. 팔레트변환·게임실행 미확인.'}
        checks.append({'key':r['key'],'text':text,'font':font,'font_px':px,'size':list(src.size),'original_text_bbox':box,'text_bbox':[x,y,x+layer.width,y+layer.height],'metrics':metrics,'native_glyph_changed_pixels':0,'outside_mask_changed_pixels':0,'icon_changed_pixels':0,'resized':False,'requires_resource_width_expansion':False,'runtime_verified':False,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest()})
        if i%10==0:sheets.append(Image.new('RGB',(1100,1000),'#dae0d6'))
        sheet=sheets[-1];cx=i%2*550;cy=(i%10)//2*200;d=ImageDraw.Draw(sheet);d.text((cx+5,cy+4),r['key']+' / '+font,fill='black')
        for j,im in enumerate([src,result]):
            bx=cx+5+j*275;sheet.paste(im,(bx,cy+28),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(bx,cy+65),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    report={'category_total':30,'references':refs,'font7_count':sum(c['font_px']==8 for c in checks),'font9_count':sum(c['font_px']==10 for c in checks),'items':checks}
    (ROOT/'metadata/graphics_abilities_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>기술·댄스 이름30개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>기술·댄스 이름30개</h1><p>작은 이름 갈무리7 · 큰 이름 갈무리9 · 원본 크기 유지</p><a href="../../graphics-review/dashboard.html?category=abilities&revision=abilities-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{c["font"]} {c["font_px"]}px</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'}))

if __name__=='__main__':main()
