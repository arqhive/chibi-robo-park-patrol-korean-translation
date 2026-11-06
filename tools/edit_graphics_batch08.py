"""Composite imagegen forecast lettering over exact source scanline patterns."""
from pathlib import Path
import json,hashlib,html
import numpy as np
from PIL import Image,ImageDraw
from scipy.ndimage import label,binary_dilation
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch08-v1'
IDS=[0,15,16,17,18]
BLUES=np.array([[74,123,255,255],[24,90,255,255]],dtype=np.uint8)

def restore(a):
    stripes=(a==BLUES[0]).all(2)|(a==BLUES[1]).all(2)
    yy,xx=np.where(stripes);box=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
    x0,y0,x1,y1=box
    bg=np.zeros_like(a)
    for y in range(y0,y1):
        vals=a[y][stripes[y]];assert len(vals)>0
        unique,counts=np.unique(vals,axis=0,return_counts=True);color=unique[counts.argmax()]
        # Text antialiasing can coincidentally equal the other stripe color.
        # Both untouched outer edges confirm the actual background for this row.
        assert np.array_equal(a[y,x0],color) and np.array_equal(a[y,x1-1],color),('unconfirmed stripe row',y)
        bg[y,x0:x1]=color
    assert np.array_equal(a[:,:,3],bg[:,:,3]),'Source alpha must match the original stripe rectangle'
    mask=np.any(a!=bg,axis=2)
    assert not np.any(mask[:,[x0,x1-1]])
    return Image.fromarray(bg),mask,box

def main():
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'));rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'}
    checks=[];updates={};proof=Image.new('RGB',(1320,900),'#d3d5cc');draw=ImageDraw.Draw(proof)
    for i,n in enumerate(IDS):
        key=f'NewPCKForecast/cell/{n}';stem=key.replace('/','-');r=rows[key];loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);erased,old,bgbox=restore(a)
        yy,xx=np.where(old);oldbox=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1))
        master=np.array(Image.open(OUT/f'master-{n}.png').convert('RGBA'))
        labs,num=label(master[:,:,3]>=128);sizes=np.bincount(labs.ravel());keep=sizes>=1000;keep[0]=False
        support=binary_dilation(keep[labs],iterations=2);master[~support]=0
        cleaned=Image.fromarray(master);cleaned=cleaned.crop(cleaned.getbbox());cleaned.save(OUT/f'master-{n}-clean.png')
        height=38 if n==0 else 32
        scale=min(height/cleaned.height,(bgbox[2]-bgbox[0]-4)/cleaned.width)
        w,h=round(cleaned.width*scale),round(cleaned.height*scale)
        small=cleaned.resize((w,h),Image.Resampling.LANCZOS);arr=np.array(small);arr[arr[:,:,3]<8]=0;small=Image.fromarray(arr)
        x=max(bgbox[0]+2,min((oldbox[0]+oldbox[2]-w)//2,bgbox[2]-w-2));y=max(bgbox[1],min((oldbox[1]+oldbox[3]-h)//2,bgbox[3]-h))
        overlay=Image.new('RGBA',src.size);overlay.alpha_composite(small,(x,y));result=Image.alpha_composite(erased,overlay)
        mask=old|(np.array(overlay)[:,:,3]>0);b=np.array(result)
        assert src.size==result.size and np.array_equal(a[~mask],b[~mask])
        assert np.array_equal(a[:,:,3],b[:,:,3])
        assert np.array_equal(np.array(erased)[~old],a[~old])
        for suffix,im in [('original',src),('erased',erased),('lettering',overlay),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix();digest=hashlib.sha256((ROOT/output).read_bytes()).hexdigest()
        rec={'key':key,'text':loc['korean_proposal'],'size':list(src.size),'original_text_bbox':list(oldbox),'result_text_bbox':[x,y,x+w,y+h],'stripe_rectangle':list(bgbox),'background_restoration':'Exact original row colors within existing alpha rectangle; glyph/AA/shadow difference mask only','outside_mask_changed_pixels':0,'original_alpha_preserved':True,'master':(OUT/f'master-{n}.png').relative_to(ROOT).as_posix(),'output':output,'sha256':digest,'runtime_verified':False};checks.append(rec)
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'draft_version':'batch08-v1','editing_method':'imagegen','method_reason':'원본 장식 글자 색 구조를 이미지젠으로 재생성. 원본 행별 줄무늬 색상으로 기존 글자·AA·그림자 마스크만 복원 후 비율 유지 합성','work_status':'review','approval':'pending','requires_resource_width_expansion':False,'note':'원본크기·투명영역·마스크 밖 픽셀 보존. 제목 초록/검정/주황, 수량 빨강/흰외곽선/남색그림자. 팔레트변환·게임실행 미확인.'}
        draw.text((8,i*180+3),key,fill='black')
        for col,im in enumerate([src,erased,result]):
            z=2 if n==0 else 3;big=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST);proof.paste(big,(8+col*440,i*180+25),big)
    proof.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch08_checks.json').write_text(json.dumps({'items':checks},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>쿠로 예보 · 장식 글씨5개</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:24px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>쿠로 예보 · 장식 글씨5개</h1><p>이미지젠으로 원본 색 구조를 맞춘 시안입니다. 파란 배경은 기존 글자·안티앨리어싱·그림자 부분만 원래 행별 색으로 복원했습니다. 원본 크기와 투명영역 유지. 팔레트변환·게임실행 미확인.</p><p><a href="../../graphics-review/dashboard.html">전체 현황판</a> · <a href="../../../metadata/graphics_batch08_prompts.json">이미지젠 프롬프트</a></p>'
    for rec in checks:
        stem=rec['key'].replace('/','-');w,h=rec['size'];page+=f'<section id="{stem}"><h2>{rec["key"]} · {html.escape(rec["text"])}</h2>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(checks,ensure_ascii=False))

if __name__=='__main__':main()
