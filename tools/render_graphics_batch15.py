"""Shop labels reuse approved captions and preserve all non-letter artwork."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from preview_neicon_mono7 import render_line,FONT_PATH
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch15-v1'
NEW={0:['치비','자전거'],1:['치비','버기'],2:['치비','카누'],8:['방수','스프레이'],9:['치비','전지'],10:['비탈','미끄럼 칩'],11:['터보','칩'],12:['서서 페달','밟기 칩'],13:['헬리콥터','칩'],14:['치빅','핸드'],42:['몽키','스푼'],47:['품절']}

def caption(lines,width,height,y):
    ink=Image.new('L',(width,height));placements=[]
    for line in lines:
        g,rec=render_line(line,width-2);x=(width-g.width-2)//2;ink.paste(g,(x+1,y+1));placements.append(dict(rec,bbox=[x,y,x+g.width+2,y+9]));y+=10
    border=ink.filter(ImageFilter.MaxFilter(3));layer=Image.new('RGBA',ink.size);layer.paste((16,49,123,255),(0,0),border);layer.paste((255,255,255,255),(0,0),ink)
    return layer,placements

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    approved=[r for r in m['graphics'] if r['edition']=='jp' and r.get('localization',{}).get('approval')=='approved' and r['localization'].get('lines')]
    rules={e['japanese_reading']:e for e in json.loads((ROOT/'metadata/graphics_caption_overrides.json').read_text(encoding='utf-8'))['entries']}
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NewPCShopIcon/') and r.get('localization',{}).get('action')=='translate_proposed'];assert len(rows)==44
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);loc=r['localization'];assert loc['approval']!='approved';stem=r['key'].replace('/','-');reading=loc['japanese_reading']
        donors=[a for a in approved if a['localization'].get('japanese_reading')==reading]
        donor=next((a for a in donors if a['key'].startswith('NEIcon')),donors[0] if donors else None)
        if donor:lines=donor['localization']['lines'];text=donor['localization']['korean_proposal']
        else:lines=NEW[n];text=loc['korean_proposal']
        if reading in rules:
            assert lines==rules[reading]['lines'] and text==rules[reading]['korean_proposal']
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);old=a[:,:,3]>0;old[:32]=False
        ys,xs=np.where(old);total=len(lines)*10-1;y=max(32,min((int(ys.min())+int(ys.max())+1-total)//2,src.height-total));assert total<=src.height-32
        clean=a.copy();clean[old]=0
        if n==47:
            # A second sold-out caption is embedded inside the blank yellow icon.
            # Its untouched rows above/below establish the exact frame/background.
            assert np.array_equal(a[11],a[21])
            for yy in range(12,21):clean[yy]=a[11]
            old|=np.any(a!=clean,axis=2)
        erased=Image.fromarray(clean);layer,placements=caption(lines,src.width,src.height,y)
        if donor:
            dimage=Image.open(ROOT/donor['localization']['output']).convert('RGBA');dc=dimage.crop((0,32,dimage.width,dimage.height));dc=dc.crop(dc.getbbox());lc=layer.crop(layer.getbbox())
            assert dc.size==lc.size and dc.tobytes()==lc.tobytes(),(r['key'],donor['key'])
        if n==47:
            inside,extra=caption(lines,src.width,src.height,12);layer.alpha_composite(inside);placements+=extra
        result=Image.alpha_composite(erased,layer);b=np.array(result);mask=old|(np.array(layer)[:,:,3]>0)
        assert np.array_equal(a[~mask],b[~mask])
        if n!=47:assert np.array_equal(a[:32],b[:32])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        checks.append({'key':r['key'],'text':text,'lines':lines,'size':list(src.size),'placements':placements,'font':'GalmuriMono7','font_px':8,'resized':False,'approved_caption_source':donor['key'] if donor else None,'approved_caption_pixels_identical':True if donor else None,'outside_mask_changed_pixels':0,'icon_changed_pixels':int(np.any(a[:32]!=b[:32],axis=2).sum()),'sold_out_icon_text_edited':n==47,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'korean_proposal':text,'lines':lines,'draft_version':'batch15-v1','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'method_reason':'기존 승인 이름표는 동일 문구·줄바꿈·글자 픽셀 재사용. 신규 이름은 Mono7 기본8px 원본 획 유지.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 규격 유지. 품절 셀은 그림 안/아래 글씨 모두 번역하고 원래 노란 배경 복원. 팔레트변환·게임실행 미확인.'}
        if i%12==0:sheets.append(Image.new('RGB',(1200,850),'#d6dacf'))
        sheet=sheets[-1];d=ImageDraw.Draw(sheet);j=i%12;cx=(j%4)*300;cy=(j//4)*280;d.text((cx+3,cy+3),r['key'],fill='black')
        for k,im in enumerate([src,result]):
            sheet.paste(im,(cx+5+k*145,cy+20),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+5+k*145,cy+85),big)
    for i,s in enumerate(sheets):s.save(OUT/f'overview-{i+1}.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'references':len(rows),'approved_caption_reuse_count':sum(c['approved_caption_source'] is not None for c in checks),'items':checks,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()}
    (ROOT/'metadata/graphics_batch15_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>상점 아이콘44개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>상점 아이콘44개</h1><p>갈무리Mono7 기본8px · 승인된 이름과 줄바꿈 재사용 · 원본 규격 유지 · 전체44개 표시</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{html.escape(" / ".join(c["lines"]))}</p>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'44 labels; {report["approved_caption_reuse_count"]} approved captions pixel-identical')

if __name__=='__main__':main()
