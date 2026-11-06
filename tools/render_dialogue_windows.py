"""Render all black guidance windows with native Galmuri9 and masked text replacement."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/dialogue-v1'
FONT_PATH=Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'
FONT=ImageFont.truetype(str(FONT_PATH),10)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets'];rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='dialogue' and r['pixel_sha256'] not in seen:rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==30
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];assert loc['approval']!='approved';src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);stem=r['key'].replace('/','-')
        assert src.size==(152,40)
        # All variants have the same solid-black interior. Preserve its frame,
        # control lights and the original prompt arrow, including its halo.
        region=np.zeros(a.shape[:2],bool);region[7:21,4:145]=True;region[21:36,17:145]=True
        old=region&np.any(a[:,:,:3]!=0,axis=2);clean=a.copy();clean[old]=(0,0,0,255)
        assert np.all(clean[region]==[0,0,0,255])
        erased=Image.fromarray(clean);overlay=Image.new('RGBA',src.size)
        header,body=loc['korean_proposal'].split('＞');header=header.strip();body=body.strip();placements=[]
        for text,box in [(header,(4,7,145,21)),(body,(17,21,145,36))]:
            left,top,right,bottom=box;white=np.all(a[top:bottom,left:right]==[255,255,255,255],axis=2);yy,xx=np.where(white)
            original=[left+int(xx.min()),top+int(yy.min()),left+int(xx.max()+1),top+int(yy.max()+1)]
            core=Image.new('L',(256,24));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),text,font=FONT,fill=255);core=core.crop(core.getbbox())
            ink=Image.new('L',(core.width+2,core.height+2));ink.paste(core,(1,1));layer=Image.new('RGBA',ink.size);layer.paste((65,65,65,255),(0,0),ink.filter(ImageFilter.MaxFilter(3)));layer.paste((255,255,255,255),(0,0),ink)
            x=original[0]-1;y=(original[1]+original[3]-core.height)//2-1
            assert left<=x and top<=y and x+layer.width<=right and y+layer.height<=bottom,(r['key'],text,layer.size,(x,y))
            overlay.alpha_composite(layer,(x,y));placements.append({'text':text,'original_ink_bbox':original,'text_bbox':[x,y,x+layer.width,y+layer.height],'ink_size':list(core.size),'native_glyph_shapes_preserved':True})
        result=Image.alpha_composite(erased,overlay);b=np.array(result);fresh=np.array(overlay)[:,:,3]>0;mask=old|fresh
        assert np.all(region[fresh]) and np.array_equal(a[~mask],b[~mask])
        assert np.array_equal(a[~region],b[~region]) and np.array_equal(a[:,:,3],b[:,:,3])
        assert np.array_equal(a[:,145:],b[:,145:]) and np.array_equal(a[:7],b[:7]) and np.array_equal(a[36:],b[36:])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rel=OUT.relative_to(ROOT).as_posix();output=f'{rel}/{stem}-korean.png'
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':f'{rel}/{stem}-erased.png','edit_mask':f'{rel}/{stem}-mask.png','comparison':f'{rel}/index.html#{stem}','draft_version':'dialogue-v1','editing_method':'galmuri','font':'Galmuri9','font_px':10,'lines':[header,'＞'+body],'method_reason':'사용자 지정 갈무리9 기본10px. 원본 흰 획·회색 외곽선, 두 줄 배치 및 각 줄 시작위치 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'문구 생략 없음. 글자·잔상만 마스크 제거. 검은 바탕·창 테두리·상단색상점·질문 화살표 보존. 팔레트 재삽입·게임실행 미확인.'}
        checks.append({'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'font':'Galmuri9','font_px':10,'placements':placements,'outside_mask_changed_pixels':0,'frame_and_arrow_changed_pixels':0,'native_glyph_changed_pixels':0,'text_shortened':False,'resized':False,'requires_resource_width_expansion':False,'runtime_verified':False,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest()})
        if i%10==0:sheets.append(Image.new('RGB',(1250,1100),'#dae0d6'))
        sheet=sheets[-1];cx=i%2*625;cy=(i%10)//2*220;ImageDraw.Draw(sheet).text((cx+5,cy+5),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            bx=cx+5+j*310;sheet.paste(im,(bx,cy+25),im);big=im.resize((304,80),Image.Resampling.NEAREST);sheet.paste(big,(bx,cy+90),big)
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    report={'category_total':30,'references':refs,'unique_questions':5,'font':'Galmuri9','font_px':10,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks}
    (ROOT/'metadata/graphics_dialogue_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>검은 안내창30개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>검은 안내창30개</h1><p>갈무리9 기본10px · 원본152×40 · 문구 전체 유지</p><a href="../../graphics-review/dashboard.html?category=dialogue&revision=dialogue-v1">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2>'
        for z in [1,3]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{152*z}" height="{40*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'{len(checks)} images, {refs} references')

if __name__=='__main__':main()
