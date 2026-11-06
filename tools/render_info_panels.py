"""Complete information panels with native fonts and pixel-masked background restoration."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/panels-v2'
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)

def glyph(text,small,style):
    if small:core,metrics=render_line(text,256)
    else:
        core=Image.new('L',(256,24));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),text,font=F9,fill=255);core=core.crop(core.getbbox());metrics={'native_glyph_shapes_preserved':True,'spacing_pixels_removed':0}
    padding=2 if style=='double' else 1
    ink=Image.new('L',(core.width+2*padding,core.height+2*padding));ink.paste(core,(padding,padding));layer=Image.new('RGBA',ink.size)
    if style=='double':layer.paste((255,255,255,255),(0,0),ink.filter(ImageFilter.MaxFilter(5)))
    border=(0,0,0,255) if style=='double' else (16,49,123,255) if style=='blue' else (65,65,65,255)
    layer.paste(border,(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((255,255,255,255),(0,0),ink)
    return layer,metrics

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets'];rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='panels' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==10
    checks=[];updates={}
    for r in rows:
        loc=r['localization'];src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);stem=r['key'].replace('/','-');new=loc['approval']!='approved';rec={'key':r['key'],'size':list(src.size),'text':loc['korean_proposal'],'new':new}
        if not new:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA');assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256'];rec['approved_pixels_unchanged']=True
        else:
            clean=a.copy();old=np.zeros(a.shape[:2],bool);overlay=Image.new('RGBA',src.size);placements=[];family=r['key'].split('/')[0];n=int(r['key'].split('/')[-1])
            def restore(rect,mode):
                x0,y0,x1,y1=rect;region=np.zeros(a.shape[:2],bool);region[y0:y1,x0:x1]=True
                if mode=='gold':
                    black=np.all(a==[0,0,0,255],axis=2)&region
                    near=np.array(Image.fromarray(black.astype('uint8')*255).filter(ImageFilter.MaxFilter(3)))>0
                    mask=region&near&(np.all(a==[0,0,0,255],axis=2)|np.all(a==[255,255,255,255],axis=2))
                    sample=48 if src.width<100 else 65
                    for yy in range(y0,y1):clean[yy,mask[yy]]=a[yy,sample]
                else:
                    mask=np.zeros(a.shape[:2],bool)
                    for yy in range(y0,y1):
                        color=np.array([205,205,205,255]) if mode=='gray' else a[yy,40 if family=='NPCSB3Pen' else 6]
                        if mode=='blue':assert tuple(color) in [(24,90,255,255),(74,123,255,255)]
                        row=region[yy]&np.any(a[yy]!=color,axis=1);mask[yy]=row;clean[yy,row]=color
                    allowed={(255,255,255,255),(49,49,49,255),(65,65,65,255)} if mode=='gray' else {(255,255,255,255),(16,49,123,255),(16,49,131,255)}
                    assert all(tuple(p) in allowed for p in a[mask]),(r['key'],mode,set(map(tuple,a[mask]))-allowed)
                old[:]|=mask;yy,xx=np.where(mask);assert len(xx)
                return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
            def place(text,box,small,style,align='start',limit=None):
                layer,metrics=glyph(text,small,style);x=(box[0]+box[2]-layer.width)//2 if align=='center' else box[2]-layer.width if align=='right' else box[0];y=(box[1]+box[3]-layer.height)//2
                assert 0<=x and 0<=y and x+layer.width<=src.width and y+layer.height<=src.height,(r['key'],text,layer.size)
                if limit:assert x>=limit[0] and y>=limit[1] and x+layer.width<=limit[2] and y+layer.height<=limit[3]
                overlay.alpha_composite(layer,(x,y));placements.append({'text':text,'font':'GalmuriMono7' if small else 'Galmuri9','font_px':8 if small else 10,'style':style,'original_bbox':box,'text_bbox':[x,y,x+layer.width,y+layer.height],'metrics':metrics})
            if family=='NewPCStaticB3':
                header=restore((8,8,src.width-8,21),'gray');title={35:'장난감',36:'할 일',37:'와츠'}[n]
                place(title,header,False,'gray','center',(8,8,src.width-8,21))
                if n==36:
                    box=restore((38,36,63,48),'blue');place('앞으로',box,True,'blue',limit=(8,23,src.width-8,src.height-8))
                elif n==37:
                    for y,text in [(31,'공사중 와츠'),(52,'하우스 와츠')]:
                        box=restore((7,y,80,y+10),'blue');place(text,box,True,'blue',limit=(7,y,90,y+10))
                        unit=restore((100,y,121,y+17),'blue');place('와츠',unit,True,'blue','right',(96,y,123,y+17))
            elif family=='NPCSB3Pen':
                box=restore((56,24,87,35),'blue');place('절교중',box,True,'blue','center',(40,24,92,35))
            elif family=='StatusMenuA':
                box=restore((4 if n==56 else 7,7,61,20),'gold');place(loc['korean_proposal'],box,False,'double',limit=(4 if n==56 else 7,6,61,21))
            else:raise ValueError(r['key'])
            erased=Image.fromarray(clean);result=Image.alpha_composite(erased,overlay);b=np.array(result);fresh=np.array(overlay)[:,:,3]>0;mask=old|fresh
            assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:,:,3],b[:,:,3])
            if family=='NPCSB3Pen':assert np.array_equal(a[35:],b[35:])
            if family=='StatusMenuA':assert np.array_equal(a[21:],b[21:])
            Image.fromarray(mask.astype('uint8')*255).save(OUT/f'{stem}-mask.png')
            rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
            text='와츠／공사중 와츠／하우스 와츠／와츠' if family=='NewPCStaticB3' and n==37 else '절교중' if family=='NPCSB3Pen' else loc['korean_proposal']
            updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'panels-v2','editing_method':'galmuri','font':'Galmuri9 / GalmuriMono7' if len({p['font'] for p in placements})>1 else placements[0]['font'],'font_px':None if len({p['font_px'] for p in placements})>1 else placements[0]['font_px'],'korean_proposal':text,'lines':text.split('／'),'method_reason':'기존 패널과 같은 갈무리9 큰 제목·갈무리7 작은 안내, 원본 색상·외곽선 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'문자·테두리 마스크만 제거, 줄무늬 및 제목 띠의 행별 색 복원. 캐릭터·패널 프레임 보존. 숫자와 문구 조합·팔레트 재삽입·게임실행 미확인.'}
            rec.update(text=text,placements=placements,outside_mask_changed_pixels=0,character_or_panel_body_changed_pixels=0,resized=False,runtime_verified=False)
        for suffix,im in [('original',src),('erased',erased),('korean',result)]:im.save(OUT/f'{stem}-{suffix}.png')
        rec['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(rec)
        sheet=Image.new('RGB',(1200,900),'#dae0d6');ImageDraw.Draw(sheet).text((5,5),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            bx=5+j*600;sheet.paste(im,(bx,25),im);z=min(3,580//im.width,560//im.height);big=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST);sheet.paste(big,(bx,310),big)
        sheet.save(OUT/f'{stem}-overview.png')
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'category_total':10,'new_drafts':len(updates),'changed_references':refs,'approved_unchanged':2,'items':checks};(ROOT/'metadata/graphics_panels_v2_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>정보 패널·화면 배경10개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>정보 패널·화면 배경10개</h1><p>신규8개 · 기존 확정2개 유지 · 원본 크기·무늬 보존</p><a href="../../graphics-review/dashboard.html?category=panels&revision=panels-v2">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,3]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'}))

if __name__=='__main__':main()
