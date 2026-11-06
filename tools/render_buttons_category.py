"""Finish button captions, preserving backgrounds, and remove two orphan fragments."""
from pathlib import Path
from collections import deque
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from preview_neicon_mono7 import render_line
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/buttons-v5'
F9=ImageFont.truetype(str(Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'),10)

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
    cats=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
    rows=[];seen=set()
    for r in m['graphics']:
        if r['edition']=='jp' and cats.get(r['pixel_sha256'],{}).get('category')=='buttons' and r['pixel_sha256'] not in seen:
            rows.append(r);seen.add(r['pixel_sha256'])
    assert len(rows)==38
    checks=[];updates={};sheets=[]
    for i,r in enumerate(rows):
        loc=r['localization'];stem=r['key'].replace('/','-');family=r['key'].split('/')[0];n=int(r['key'].split('/')[-1]);src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src)
        correction=family=='NewPCStaticA' and n in [19,20]
        new=family=='NewPCStaticB' or family.startswith('PC')
        record={'key':r['key'],'text':loc['korean_proposal'],'size':list(src.size),'new':new,'correction':correction}
        if correction:
            oldpath=loc.get('buttons_previous_output',loc['output']);previous=Image.open(ROOT/oldpath).convert('RGBA');a=np.array(previous);mask=np.zeros(a.shape[:2],bool);mask[:,62:]=a[:,62:,3]>0
            b=a.copy();b[mask]=0;result=Image.fromarray(b);erased=Image.open(ROOT/loc['erased']).convert('RGBA');e=np.array(erased);e[:,62:]=0;erased=Image.fromarray(e)
            previous.save(OUT/f'{stem}-previous.png')
            assert np.array_equal(a[~mask],b[~mask]) and not b[:,62:,3].any()
            record.update(removed_fragment_pixels=int(mask.sum()),previous_output=oldpath,outside_mask_changed_pixels=0)
            font,size=loc['font'],loc['font_px']
        elif new:
            assert loc['approval']!='approved'
            region=np.zeros(a.shape[:2],bool)
            if family=='NewPCStaticB':
                ending=n in [19,20,29,30];cancel=n in [13,14,23,24]
                color=(213,139,0,255) if ending else (255,0,0,255) if cancel else (32,106,255,255)
                if ending:region[12:29,38:81]=True
                elif cancel:region[12:29,3:43]=True
                else:region[18:32,5:39]=True
                old=region&np.all(a==color,axis=2);assert old.any()
                clean=a.copy();clean[old]=(255,255,255,255)
                core=Image.new('L',(128,30));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),loc['korean_proposal'],font=F9,fill=255);core=core.crop(core.getbbox());metrics={'native_glyph_shapes_preserved':True};font,size='Galmuri9',10
            else:
                ending=n==11;color=(65,65,65,255)
                if ending:region[1:12,25:55]=True
                else:region[8:19,16:44]=True
                old=region&(np.all(a==color,axis=2)|np.all(a==[255,255,255,255],axis=2));assert old.any()
                clean=a.copy()
                for yy in range(src.height):
                    bg=a[yy,13] if ending else np.array([49,205,255,255],dtype='uint8')
                    clean[yy,old[yy]]=bg
                core=Image.new('L',(128,30));d=ImageDraw.Draw(core);d.fontmode='1';d.text((0,0),loc['korean_proposal'],font=F9,fill=255);core=core.crop(core.getbbox());metrics={'native_glyph_shapes_preserved':True};font,size='Galmuri9',10
            erased=Image.fromarray(clean);ys,xs=np.where(old);box=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]
            ink=Image.new('L',(core.width+2,core.height+2));ink.paste(core,(1,1));border=ink.filter(ImageFilter.MaxFilter(3));layer=Image.new('RGBA',ink.size);layer.paste(color,(0,0),border);layer.paste((255,255,255,255),(0,0),ink)
            x=(box[0]+box[2]-layer.width)//2 if family=='NewPCStaticB' else box[0]
            y=(box[1]+box[3]-layer.height)//2
            if family.startswith('PC') and n==14:
                x=(box[0]+box[2]-layer.width)//2
                record['alignment']='original Japanese text bounding-box center'
                record['center_offset_px']=[(2*x+layer.width-box[0]-box[2])/2,(2*y+layer.height-box[1]-box[3])/2]
                assert all(abs(v)<=0.5 for v in record['center_offset_px'])
            if family=='NewPCStaticB':
                # Find the actual connected white label interior, independent of
                # the old Japanese text bounds or the adjacent button ring.
                white=np.all(clean==[255,255,255,255],axis=2)
                seed=((box[0]+box[2])//2,(box[1]+box[3])//2)
                assert white[seed[1],seed[0]]
                queue=deque([seed]);pixels={seed}
                while queue:
                    xx,yy=queue.popleft()
                    for nx,ny in [(xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)]:
                        if 0<=nx<src.width and 0<=ny<src.height and white[ny,nx] and (nx,ny) not in pixels:
                            pixels.add((nx,ny));queue.append((nx,ny))
                wx,wy=zip(*pixels);whitebox=[min(wx),min(wy),max(wx)+1,max(wy)+1]
                x=(whitebox[0]+whitebox[2]-layer.width)//2
                y=(whitebox[1]+whitebox[3]-layer.height)//2
                error=[(2*x+layer.width-whitebox[0]-whitebox[2])/2,(2*y+layer.height-whitebox[1]-whitebox[3])/2]
                assert all(abs(v)<=0.5 for v in error)
                y+=1
                record.update(white_interior_bbox=whitebox,center_offset_px=[error[0],error[1]+1],vertical_offset_from_center_px=1,alignment='white interior center plus user-requested 1px downward offset')
            assert x>=0 and y>=0 and x+layer.width<=src.width and y+layer.height<=src.height
            overlay=Image.new('RGBA',src.size);overlay.alpha_composite(layer,(x,y));fresh=np.array(overlay)[:,:,3]>0
            if family=='NewPCStaticB':assert np.all(clean[fresh]==[255,255,255,255]),r['key']
            else:assert np.all(region[fresh]),(r['key'],x,y,layer.size)
            result=Image.alpha_composite(erased,overlay);b=np.array(result);mask=old|fresh
            assert np.array_equal(a[~mask],b[~mask])
            record.update(font=font,font_px=size,metrics=metrics,text_bbox=[x,y,x+layer.width,y+layer.height],original_text_bbox=box,outside_mask_changed_pixels=0,resized=False,runtime_verified=False)
        else:
            result=Image.open(ROOT/loc['output']).convert('RGBA');erased=Image.open(ROOT/loc['erased']).convert('RGBA')
            assert hashlib.sha256((ROOT/loc['output']).read_bytes()).hexdigest()==loc['approved_sha256']
            record.update(approved_pixels_unchanged=True,approved_output=loc['output'])
        prior=Image.open(ROOT/'work/graphics-draft/buttons-v4'/f'{stem}-korean.png').convert('RGBA')
        targeted=family.startswith('PC') and n==14
        if not targeted:assert result.tobytes()==prior.tobytes(),r['key']
        else:
            pa=np.array(prior);oldletters=np.any(pa!=clean,axis=2)
            py,px=np.where(oldletters);expected=clean.copy()
            expected[py,px+3]=pa[py,px]
            assert np.array_equal(expected,np.array(result)),r['key']
            record['exact_3px_right_from_v4']=True
        record['back_button_center_updated']=targeted
        record['unchanged_from_v4']=result.tobytes()==prior.tobytes()
        for suffix,im in [('original',src),('erased',erased),('korean',result),('previous',prior)]:im.save(OUT/f'{stem}-{suffix}.png')
        if new or correction:
            Image.fromarray(mask.astype('uint8')*255).save(OUT/f'{stem}-mask.png')
            output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
            update={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'buttons-v5','editing_method':'galmuri','font':font,'font_px':size,'method_reason':'원본의 픽셀 글씨와 크기에 맞춰 갈무리 기본크기로 렌더링. 원본 버튼·아이콘과 배경 보존.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 글자 획·테두리만 마스크 제거, 버튼과 배경색 보존. 취소·끝내기 뒤의 고립 조각 제거. 팔레트변환·게임실행 미확인.'}
            if correction:update['buttons_previous_output']=oldpath
            updates[r['pixel_sha256']]=update
        record['sha256']=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest();checks.append(record)
        if new or correction:
            j=sum(c['new'] or c['correction'] for c in checks)-1
            if j%6==0:sheets.append(Image.new('RGB',(1200,790),'#d5d9cf'))
            sheet=sheets[-1];cx=j%2*600;cy=(j%6)//2*260;d=ImageDraw.Draw(sheet);d.text((cx+4,cy+3),r['key'],fill='black')
            for k,im in enumerate([prior,result]):
                sheet.paste(im,(cx+4+k*300,cy+24),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+4+k*300,cy+90),big)
    for i,sheet in enumerate(sheets):sheet.save(OUT/f'overview-{i+1}.png')
    refs=0
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:
            loc=r['localization']
            if loc['approval']=='approved':loc['previous_visual_approval']={k:loc[k] for k in ['output','approved_backup','approved_sha256','approval_scope'] if k in loc}
            for k in ['approved_backup','approved_sha256','approval_scope']:loc.pop(k,None)
            loc.update(updates[r['pixel_sha256']]);refs+=1
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_buttons_category_v5_checks.json').write_text(json.dumps({'category_total':38,'new_drafts':17,'corrections':2,'changed_references':refs,'approved_unchanged':19,'back_center_updates':3,'unchanged_from_v4':35,'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>버튼38개</title><style>body{font:16px/1.6 sans-serif;background:#eef1e8;padding:24px}section{background:white;margin:20px 0;padding:20px}.row{display:flex;gap:35px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>버튼·결정·취소·뒤로38개</h1><p>창형 뒤로3개 원본 글씨 중심 정렬 · 나머지35개 v4와 동일</p><a href="../../graphics-review/dashboard.html?category=buttons&revision=buttons-v5">전체 카테고리 현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>'+('조각 제거' if c['correction'] else '신규' if c['new'] else '기존 확정 유지')+'</p>'
        for z in [1,4]:
            page+=f'<p>{z}배</p><div class="row">'
            for suffix,title in [('original','원본'),('previous','이전 결과'),('korean','수정 결과')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'17 new,2 corrected,19 unchanged; {refs} references updated')

if __name__=='__main__':main()
