"""Complete menu information using approved font and outline styles."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/menu-info-v1'
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)
PHRASES={32:'제작가능',33:'수리가능',34:'삭제가능'}

def main():
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    policy=json.loads((ROOT/'metadata/graphics_caption_overrides.json').read_text(encoding='utf-8'))
    sand_choice=policy.get('sand_label_edge_policy')
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets'];rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='menu-text' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==21
    OUT.mkdir(parents=True,exist_ok=True);checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        if r['key']=='NewPCStaticA/cell/73' and not sand_choice:
            continue  # Render the other labels while the user's answer is pending.
        loc=r['localization'];src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);stem=r['key'].replace('/','-');family=r['key'].split('/')[0];n=int(r['key'].split('/')[-1]);new=loc['approval']!='approved';text=loc['korean_proposal']
        rec={'key':r['key'],'text':text,'size':list(src.size),'new':new}
        if not new:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA')
            assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256']
            rec.update(approved_pixels_unchanged=True,approved_output=loc['output'])
        else:
            panel=family=='NewPCStaticB2' and n in [23,24];bracket=family=='NewPCStaticB3';sand=family=='NewPCStaticA' and n==73
            region=np.ones(a.shape[:2],bool);clean=a.copy();preserve=0
            if panel:
                region[:]=False;region[7:20,5:75]=True
                for y in range(7,20):
                    color=a[y,5];assert np.array_equal(color,a[y,74]) and tuple(color) in [(255,74,74,255),(255,123,123,255)]
                    mask=region[y]&np.any(a[y]!=color,axis=1);clean[y,mask]=color
                ref='NewPCSelectToy/cell/6';font='GalmuriMono7';px=8;padding=2
            else:
                if bracket:
                    # The bracket shifts between cells: retain its full component.
                    first=int(np.flatnonzero(np.any(a[:,:,3]>0,axis=0))[0]);preserve=first+5
                    region[:,:preserve]=False;text='］'+PHRASES[n]
                clean[region&(a[:,:,3]>0)]=0
                ref='NEIconOBJCheckP/cell/0' if bracket else 'NewPCStaticA/cell/67';font='GalmuriMono7' if bracket or sand else 'Galmuri9';px=8 if bracket or sand else 10;padding=1 if bracket else 2
            old=np.any(a!=clean,axis=2);yy,xx=np.where(old);box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
            render_text=PHRASES[n] if bracket else text
            if font=='GalmuriMono7':core,metrics=render_line(render_text,256)
            else:
                core=Image.new('L',(256,24));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),render_text,font=F9,fill=255);core=core.crop(core.getbbox());metrics={'native_glyph_shapes_preserved':True,'spacing_pixels_removed':0}
            ink=Image.new('L',(core.width+2*padding,core.height+2*padding));ink.paste(core,(padding,padding));layer=Image.new('RGBA',ink.size)
            if padding==2:layer.paste((255,255,255,255),(0,0),ink.filter(ImageFilter.MaxFilter(5)))
            border=(16,49,123,255) if bracket else (0,0,0,255);layer.paste(border,(0,0),ink.filter(ImageFilter.MaxFilter(3)))
            color={71:(0,255,41,255),72:(189,82,0,255),73:(255,205,0,255)}.get(n,(255,255,255,255)) if family=='NewPCStaticA' else (255,255,255,255)
            layer.paste(color,(0,0),ink)
            if sand:
                # Authorized exception: preserve all 15 ink columns, trimming only
                # the outermost horizontal outline columns to the 16px resource.
                assert sand_choice['approved'] and sand_choice['mode']=='omit_horizontal_edge_outline'
                layer=layer.crop((2,0,18,layer.height))
                assert np.all(np.array(layer)[padding:padding+core.height,:core.width][np.array(core)>0]==color)
                rec['edge_outline_columns_omitted']=[2,1];rec['native_core_preserved']=True
            if panel:x=(5+75-layer.width)//2;y=(7+20-layer.height)//2
            else:x=max(preserve,min(box[0],src.width-layer.width));y=(box[1]+box[3]-layer.height)//2
            assert 0<=x and 0<=y and x+layer.width<=src.width and y+layer.height<=src.height,(r['key'],layer.size)
            if panel:assert x>=5 and y>=7 and x+layer.width<=75 and y+layer.height<=20
            overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));erased=Image.fromarray(clean);result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|(np.array(overlay)[:,:,3]>0)
            assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[~region],b[~region])
            if bracket:
                assert np.array_equal(a[:,:preserve],b[:,:preserve])
                rec['preserved_bracket_columns']=[first,preserve]
            rec.update(text=text,font=font,font_px=px,style_reference=ref,metrics=metrics,text_bbox=[x,y,x+layer.width,y+layer.height],original_text_bbox=box,outside_mask_changed_pixels=0,protected_pixels_changed=0,resized=False,runtime_verified=False)
            rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
            updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'menu-info-v1','editing_method':'galmuri','font':font,'font_px':px,'korean_proposal':text,'lines':[text],'method_reason':f'기존 승인 도안 {ref}의 갈무리 크기·외곽선 스타일에 맞춤.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 크기 유지. 글자 획 축소 없음. 창 줄무늬·프레임·문장 괄호 보존. 팔레트 재삽입·게임실행 미확인.'}
            Image.fromarray(mask.astype('uint8')*255).save(OUT/f'{stem}-mask.png')
        for suffix,im in [('original',src),('erased',erased),('korean',result)]:im.save(OUT/f'{stem}-{suffix}.png')
        rec['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(rec)
        if i%8==0:sheets.append(Image.new('RGB',(1250,1000),'#dae0d6'))
        sheet=sheets[-1];cx=i%2*625;cy=(i%8)//2*250;ImageDraw.Draw(sheet).text((cx+5,cy+5),r['key']+(' new' if new else ' approved'),fill='black')
        for j,im in enumerate([src,result]):
            bx=cx+5+j*310;sheet.paste(im,(bx,cy+28),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(bx,cy+90),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    report={'category_total':21,'new_drafts':len(updates),'changed_references':refs,'approved_unchanged':sum(not c['new'] for c in checks),'items':checks}
    (ROOT/'metadata/graphics_menu_info_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>메뉴 항목·정보 글씨21개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>메뉴 항목·정보 글씨21개</h1><p>기존 확정 스타일에 맞춤 · 신규10개 · 확정11개 유지 · 원본 크기</p><a href="../../graphics-review/dashboard.html?category=menu-text&revision=menu-info-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>'+('신규 · '+c['font'] if c['new'] else '기존 확정 유지')+'</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps({k:v for k,v in report.items() if k!='items'}))

if __name__=='__main__':main()
