"""User-requested v2 corrections; v1 and all source images are kept."""
import json, hashlib, html
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from collections import Counter
from edit_graphics_batch01 import ROOT, place, source_palette

OUT=ROOT/'work/graphics-draft/batch01-v2'
V1=ROOT/'work/graphics-draft/batch01-v1'
PANELS=[[(27,55),(51,45),(51,74),(27,82)],[(59,55),(85,44),(85,74),(59,84)],[(93,55),(117,45),(117,74),(93,84)],[(125,55),(150,44),(150,74),(125,84)]]
ICON_END={27:13,29:14,31:14,33:13,35:16,37:16,47:17}


def crop_visible(im):
    a=np.array(im.getchannel('A'))>=128
    ys=np.where(a.sum(axis=1)>8)[0];xs=np.where(a.sum(axis=0)>8)[0]
    return im.crop((int(xs[0]),int(ys[0]),int(xs[-1])+1,int(ys[-1])+1))


def resize_rgba(im,size):
    im=im.resize(size,Image.Resampling.LANCZOS)
    im.putalpha(im.getchannel('A').point(lambda a:255 if a>=120 else 0))
    return im


def logo(source):
    original=np.array(source);base=original.copy();oldmask=np.zeros(original.shape[:2],bool)
    # Letter interior masks: preserve the colored panel faces and all perimeter pixels.
    interiors=[]
    for poly in PANELS:
        mask=Image.new('1',source.size);ImageDraw.Draw(mask).polygon(poly,fill=1)
        inside=np.array(mask);interiors.append(inside)
        # Each original face is a flat palette color; remaining shades here
        # belong to the old glyph and its antialiasing, not a background texture.
        face=Counter(tuple(p) for p in original[inside] if p[3] and int(max(p[:3]))-int(min(p[:3]))>95).most_common(1)[0][0]
        glyph=inside & np.any(original!=face,axis=2) & (original[:,:,3]>0)
        base[glyph]=face
        oldmask|=glyph
    # Upper text is a freestanding outlined word. Stop above original panel rims.
    upper=np.zeros(original.shape[:2],bool)
    for x in range(17,157):
        ceiling=46
        for left,right in [(23,56),(57,89),(90,121),(122,155)]:
            if left<=x<=right:ceiling=min(ceiling,int(54-(x-left)*0.42)-2)
        upper[:max(0,ceiling),x]=original[:max(0,ceiling),x,3]>0
    base[upper]=0;oldmask|=upper
    erased=Image.fromarray(base);result=erased.copy()
    top=crop_visible(Image.open(OUT/'top-imagegen.png').convert('RGBA'))
    top=resize_rgba(top,(102,34));result.alpha_composite(top,(37,10))
    newmask=np.zeros(original.shape[:2],bool);newmask[10:44,37:139]=np.array(top.getchannel('A'))>0
    black=Image.open(OUT/'bottom-refined-imagegen.png').convert('RGBA')
    # Each generated black glyph is fitted to the original face slope. The panel
    # itself is never moved, cleared, resized or regenerated.
    for i,poly in enumerate(PANELS):
        left=round(i*black.width/4);right=round((i+1)*black.width/4)
        ch=crop_visible(black.crop((left,0,right,black.height)))
        alpha=ch.getchannel('A').resize((18,24),Image.Resampling.LANCZOS)
        alpha=alpha.point(lambda v:255 if v>120 else 0)
        a=np.array(alpha)>120
        x0=poly[0][0]+3;y0=poly[0][1]+3
        arr=np.array(result)
        for y,x in np.argwhere(a):
            px=x0+x+1;py=y0+y-round(x*0.40)
            if interiors[i][py,px]:arr[py,px]=(255,255,255,255);newmask[py,px]=True
        for y,x in np.argwhere(a):
            px=x0+x;py=y0+y-round(x*0.40)
            if interiors[i][py,px]:
                arr[py,px]=(24,24,24,255);newmask[py,px]=True
        result=Image.fromarray(arr)
    result=source_palette(result,source)
    allowed=oldmask|newmask
    arr=np.array(result);arr[~allowed]=original[~allowed];result=Image.fromarray(arr)
    return erased,result,allowed,{'panel_face_preservation':'Only original glyph/AA pixels filled; no full panel clearing','upper_baseline':'horizontal; generated top word placed without rotation','black_glyph_fill':True}


def touch(source):
    im=Image.open(OUT/'touch-imagegen.png').convert('RGBA');im=crop_visible(im)
    # Generation has four separate islands. Fit complete grouped composition.
    im=resize_rgba(im,(132,20));result=Image.new('RGBA',source.size);result.alpha_composite(im,(2,2))
    result=source_palette(result,source,crisp_text=True)
    allowed=(np.array(source.getchannel('A'))>0)|(np.array(result.getchannel('A'))>0)
    arr=np.array(result);arr[~allowed]=np.array(source)[~allowed]
    return Image.new('RGBA',source.size),Image.fromarray(arr),allowed,{'word_groups':['터치','해서','시작','!']}


def button(source,text,end):
    before=np.array(source);arr=before.copy();allowed=np.zeros(before.shape[:2],bool)
    right=max(x for x in range(source.width) if before[0,x,3])
    for y in range(2,13):
        bg=(255,255,255,255) if y<8 else (180,180,180,255)
        for x in range(end,right):
            if tuple(arr[y,x])!=bg:allowed[y,x]=True;arr[y,x]=bg
    erased=Image.fromarray(arr);result,new=place(erased,text,(end+1,2,right,13));allowed|=np.array(new)>0
    after=np.array(result)
    assert np.array_equal(before[:,:end],after[:,:end])
    return erased,result,allowed,{'protected_icon_columns':[0,end-1],'icon_changed_pixels':0}


def main():
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    selected=['TitleLogo/cell/0','TitleLogo/cell/1','TitleSave/cell/26']+[f'TitleSave/cell/{i}' for i in ICON_END]
    rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
    checks=[];changes={}
    for key in selected:
        r=rows[key];loc=r['localization'];source=Image.open(ROOT/r['path']).convert('RGBA');stem=key.replace('/','-')
        if key=='TitleLogo/cell/0':erased,result,allowed,extra=logo(source)
        elif key=='TitleLogo/cell/1':erased,result,allowed,extra=touch(source)
        elif key=='TitleSave/cell/26':
            erased=Image.new('RGBA',source.size);result,new=place(erased,'비어있음',(0,0,*source.size));allowed=(np.array(source.getchannel('A'))>0)|(np.array(new)>0);extra={'text':'비어있음','user_approved_ui_spacing':True}
        else:erased,result,allowed,extra=button(source,loc['korean_proposal'],ICON_END[int(key.split('/')[-1])])
        changed=np.any(np.array(source)!=np.array(result),axis=2)
        assert int(changed[~allowed].sum())==0,key
        for suffix,im in [('original',source),('erased',erased),('korean',result),('mask',Image.fromarray(allowed.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        if 'protected_icon_columns' in extra:
            previous=np.array(Image.open(V1/f'{stem}-korean.png').convert('RGBA'))
            end=extra['protected_icon_columns'][1]+1
            extra['previous_icon_changed_pixels']=int(np.any(np.array(source)[:,:end]!=previous[:,:end],axis=2).sum())
        record={'key':key,'size':list(source.size),'outside_mask_changed_pixels':0,'output_sha256':hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest(),**extra}
        checks.append(record)
        changes[r['pixel_sha256']]={'output':f'work/graphics-draft/batch01-v2/{stem}-korean.png','erased':f'work/graphics-draft/batch01-v2/{stem}-erased.png','edit_mask':f'work/graphics-draft/batch01-v2/{stem}-mask.png','comparison':f'work/graphics-draft/batch01-v2/index.html#{stem}','draft_version':'batch01-v2','work_status':'review','approval':'pending'}
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in changes:
            r['localization'].update(changes[r['pixel_sha256']])
            if r['key']=='TitleSave/cell/26':r['localization']['korean_proposal']='비어있음'
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch01_v2_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>그래픽 수정 비교 v2</title><style>body{font:16px/1.7 sans-serif;background:#edf1e8;padding:24px}section{background:white;padding:20px;margin:24px 0}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:20px;flex-wrap:wrap}</style><h1>첫 묶음 수정 비교 · v2</h1><p>원본 색 판과 검은 글자 / 수평 피워라 / 터치 안내 단어 간격 / 비어있음 / 버튼 아이콘 복원</p><a href="../../graphics-review/dashboard.html?status=review">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{html.escape(c["key"])}</h2>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배 비교</p><div class="row">'
            for label,file in [('원본',f'{stem}-original.png'),('이전 결과',f'../batch01-v1/{stem}-korean.png'),('글자 지운 뒤',f'{stem}-erased.png'),('수정 결과',f'{stem}-korean.png')]:page+=f'<div>{label}<br><img src="{file}" width="{w*zoom}" height="{h*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print('Revised',len(checks),'assets')


if __name__=='__main__':main()
