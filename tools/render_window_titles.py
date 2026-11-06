"""Complete Chibi-PC titles using the approved small window-title style."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/window-title-v1'

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets'];rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='window-title' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==6
    checks=[];updates={};sheet=Image.new('RGB',(1250,900),'#dae0d6')
    for i,r in enumerate(rows):
        loc=r['localization'];src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);stem=r['key'].replace('/','-');new=loc['approval']!='approved';rec={'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'new':new}
        if new:
            assert r['key'].startswith('PCMP')
            old=a[:,:,3]>0;old[:,:11]=False
            assert all(tuple(v) in [(65,65,65,255),(255,255,255,255)] for v in a[old])
            yy,xx=np.where(old);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
            clean=a.copy();clean[old]=0;erased=Image.fromarray(clean)
            core,metrics=render_line(loc['korean_proposal'],src.width-box[0]-2)
            assert metrics['spacing_pixels_removed']==0
            ink=Image.new('L',(core.width+2,9));ink.paste(core,(1,1));layer=Image.new('RGBA',ink.size);layer.paste((65,65,65,255),(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((255,255,255,255),(0,0),ink)
            x=box[0];y=(box[1]+box[3]-layer.height)//2
            assert x>=11 and y>=0 and x+layer.width<=src.width and y+layer.height<=src.height
            overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|(np.array(overlay)[:,:,3]>0)
            assert np.array_equal(a[:,:11],b[:,:11]) and np.array_equal(a[~mask],b[~mask])
            Image.fromarray(mask.astype('uint8')*255).save(OUT/f'{stem}-mask.png')
            rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
            updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'window-title-v1','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'lines':[loc['korean_proposal']],'method_reason':'기존 도구사요·예보 창 제목과 같은 Mono7 기본8px, 흰 획·회색65 외곽선1px. 원본 시작x 및 세로 중심 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 창 아이콘과 고유 하늘색 보존. 원본 크기 유지. 팔레트 재삽입·게임실행 미확인.'}
            rec.update(font='GalmuriMono7',font_px=8,style_reference='NewPCShopMInfo/cell/14',metrics=metrics,original_text_bbox=box,text_bbox=[x,y,x+layer.width,y+layer.height],icon_changed_pixels=0,outside_mask_changed_pixels=0,resized=False,runtime_verified=False)
        else:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA');assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256'];rec.update(approved_pixels_unchanged=True,approved_output=loc['output'])
        for suffix,im in [('original',src),('erased',erased),('korean',result)]:im.save(OUT/f'{stem}-{suffix}.png')
        rec['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(rec)
        cx=i%2*625;cy=i//2*300;ImageDraw.Draw(sheet).text((cx+5,cy+5),r['key']+(' new' if new else ' approved'),fill='black')
        for j,im in enumerate([src,result]):
            bx=cx+5+j*310;sheet.paste(im,(bx,cy+30),im);big=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST);sheet.paste(big,(bx,cy+80),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');sheet.save(OUT/'overview.png')
    report={'category_total':6,'new_drafts':len(updates),'changed_references':refs,'approved_unchanged':4,'items':checks}
    (ROOT/'metadata/graphics_window_title_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>창 제목6개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>창 제목6개</h1><p>치비컴2개 신규 · 확정4개 유지 · 갈무리7 창 제목 스타일</p><a href="../../graphics-review/dashboard.html?category=window-title&revision=window-title-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'}))

if __name__=='__main__':main()
