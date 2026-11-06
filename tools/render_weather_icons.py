"""Complete the four status time labels; show all fourteen weather icons."""
from pathlib import Path
import json, hashlib, html
import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/weather-icons-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),10)

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    rows=[r for r in m['graphics'] if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='weather-icons'];assert len(rows)==14
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];stem=r['key'].replace('/','-');src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        new=r['key'].startswith('StatusMenuA2/')
        if new:
            assert loc['approval']!='approved'
            region=np.zeros(a.shape[:2],bool);region[:,24:]=True
            old=(a[:,:,3]>0)&region;ys,xs=np.where(old);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
            clean=a.copy();clean[old]=0;erased=Image.fromarray(clean)
            core=Image.new('L',(160,32));d=ImageDraw.Draw(core);d.fontmode='1';d.text((3,3),loc['korean_proposal'],font=FONT,fill=255);core=core.crop(core.getbbox())
            ink=Image.new('L',(core.width+4,core.height+4));ink.paste(core,(2,2));black=ink.filter(ImageFilter.MaxFilter(3));white=black.filter(ImageFilter.MaxFilter(3))
            layer=Image.new('RGBA',ink.size);layer.paste((255,255,255,255),(0,0),white);layer.paste((0,0,0,255),(0,0),black);layer.paste((255,255,255,255),(0,0),ink)
            x=box[0];y=(box[1]+box[3]-layer.height)//2
            assert x>=24 and y>=0 and x+layer.width<=src.width and y+layer.height<=src.height
            overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result)
            mask=old|(np.array(overlay)[:,:,3]>0)
            assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:,:24],b[:,:24])
            assert not np.any(clean[:,24:,3])
            assert set(np.unique(np.array(ink)))<={0,255}
            for suffix,im in [('erased',erased),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
            output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
            updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'weather-icons-v1','editing_method':'galmuri','font':'Galmuri9','font_px':10,'method_reason':'원본13px 외곽선 포함 도트 글씨에 맞춰 Galmuri9 기본10px, 흰 획·검정1px·흰1px 외곽선 사용.','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'원본 글씨 시작 x와 세로 중심 유지. 해·달 그림24열 및 외부 픽셀 동일. 팔레트변환·게임실행 미확인.'}
            record={'key':r['key'],'new':True,'text':loc['korean_proposal'],'size':list(src.size),'font':'Galmuri9','font_px':10,'resized':False,'original_text_bbox':box,'text_bbox':[x,y,x+layer.width,y+layer.height],'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'erased_text_alpha_zero':True,'runtime_verified':False}
        else:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA')
            assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256']
            assert result.size==src.size
            record={'key':r['key'],'new':False,'text':loc['korean_proposal'],'size':list(src.size),'approved_output':loc['output'],'approved_pixels_unchanged':True}
            erased.save(OUT/f'{stem}-erased.png')
        src.save(OUT/f'{stem}-original.png');result.save(OUT/f'{stem}-korean.png')
        record['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(record)
        if i%8==0:sheets.append(Image.new('RGB',(1120,1000),'#d5d9cf'))
        j=i%8;cx=j%2*560;cy=j//2*250;sheet=sheets[-1];draw=ImageDraw.Draw(sheet);draw.text((cx+4,cy+3),r['key'],fill='black')
        for k,im in enumerate([src,result]):
            sheet.paste(im,(cx+4+k*275,cy+23),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+4+k*275,cy+90),big)
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_weather_icons_checks.json').write_text(json.dumps({'category_total':14,'new_drafts':4,'approved_unchanged':10,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>시간·날씨·쿠로 아이콘14개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>시간·날씨·쿠로 아이콘14개</h1><p>신규4개 · 기존 확정10개 유지</p><a href="../../graphics-review/dashboard.html?category=weather-icons&revision=weather-icons-v1">카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>'+('신규 · 갈무리9 기본10px' if c['new'] else '기존 확정 유지')+'</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('4 new time labels; 10 approved images unchanged; complete14-item comparison')

if __name__=='__main__':main()
