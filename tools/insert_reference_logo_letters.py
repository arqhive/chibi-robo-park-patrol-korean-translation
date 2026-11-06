"""Composite the user's exact reference glyphs into the approved title panels."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-reference-v1'
REF=ROOT/'graphics/references/title-lettering-user.png'
BASE=ROOT/'work/graphics-draft/title-cleanup-v8/title-panels-clean.png'
# Labels refer to connected dark ink components in the hash-locked reference.
SPECS=[('치',[8,11],20,24,55,30,39),('비',[6,12],456,58,55,29,72.5),('로',[9],894,91,55,29,105.5),('보',[7],1334,124,55,29,138.5)]


def main():
    assert hashlib.sha256(REF.read_bytes()).hexdigest()=='ce8255a6b1813df53efd7e5a91e33d77c694c023700ba42c828ac439289d2ded'
    OUT.mkdir(exist_ok=True)
    rgb=np.array(Image.open(REF).convert('RGB'))
    labels,_=ndimage.label(rgb.max(2)<100)
    base=Image.open(BASE).convert('RGBA');background=np.array(base).astype(int)
    result=base.copy();allowed=np.zeros(background.shape[:2],bool);checks=[]
    face=(background[:,:,:3].max(2)-background[:,:,:3].min(2)>80)&(background[:,:,3]>0)
    contact=Image.new('RGBA',(960,360),(0,0,0,0))
    for i,(char,ids,sx,dx,dy,dw,cx) in enumerate(SPECS):
        black=np.isin(labels,ids)
        domain=ndimage.binary_fill_holes(black)|ndimage.binary_dilation(black,iterations=2)
        mask=domain&(rgb.max(2).astype(int)-rgb.min(2)<60)
        rgba=np.dstack([rgb,mask.astype('uint8')*255]);rgba[~mask]=0
        glyph=Image.fromarray(rgba);cut=glyph.crop(glyph.getbbox());cut.save(OUT/f'reference-glyph-{i}.png')
        thumb=cut.copy();thumb.thumbnail((220,340),Image.Resampling.LANCZOS)
        contact.alpha_composite(thumb,(i*240+(240-thumb.width)//2,(360-thumb.height)//2))
        ax=dw/380;by=33/390;cy=by*(165/380)-13/380*dw/30
        tx=dx-ax*sx;ty=dy-by*205-cy*sx
        # Common inset keeps reference shapes clear of the robot and panel rims.
        fit=.90
        ax*=fit;by*=fit;cy*=fit;tx=fit*tx+(1-fit)*cx;ty=fit*ty+(1-fit)*65
        inv=(1/ax,0,-tx/ax,-cy/(ax*by),1/by,(cy*tx/ax-ty)/by)
        ss=4
        coeff=(inv[0]/ss,0,inv[2],inv[3]/ss,inv[4]/ss,inv[5])
        layer=glyph.transform((192*ss,104*ss),Image.Transform.AFFINE,coeff,Image.Resampling.BICUBIC).resize((192,104),Image.Resampling.LANCZOS)
        a=np.array(layer);a[a[:,:,3]<8]=0
        active=a[:,:,3]>0
        assert not np.any(active&~face),char
        layer=Image.fromarray(a);layer.save(OUT/f'layer-{i}.png');result.alpha_composite(layer);allowed|=active
        ys,xs=np.where(active)
        checks.append({'character':char,'source_components':ids,'source_cutout_size':list(cut.size),'destination_bbox':[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)],'outside_panel_face_pixels':0})
    contact.save(OUT/'extracted-letters.png')
    base.save(OUT/'before.png');result.save(OUT/'title-korean.png')
    result.resize((1152,624),Image.Resampling.NEAREST).save(OUT/'preview-6x.png')
    Image.fromarray(allowed.astype('uint8')*255).save(OUT/'letter-mask.png')
    changed=np.any(np.array(base)!=np.array(result),axis=2)
    assert not np.any(changed&~allowed)
    assert np.array_equal(np.array(base)[:,:,3],np.array(result)[:,:,3])
    report={'method':'Exact source glyph extraction and affine downsampling; no regenerated lettering','reference_sha256':hashlib.sha256(REF.read_bytes()).hexdigest(),'background_sha256':hashlib.sha256(BASE.read_bytes()).hexdigest(),'size':list(result.size),'glyphs':checks,'changed_pixels':int(changed.sum()),'outside_letter_mask_changes':0,'original_alpha_preserved':True,'output_sha256':hashlib.sha256((OUT/'title-korean.png').read_bytes()).hexdigest(),'rom_injection_tested':False}
    (ROOT/'metadata/title_reference_v1_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>레퍼런스 글자 직접 삽입</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}.reference{max-width:100%;image-rendering:auto}</style><h1>치비로보 · 레퍼런스 글자 직접 삽입</h1><p>주신 이미지의 검은 획과 흰 하이라이트를 직접 추출하여 네 판에 맞췄습니다. 정리한 바탕·테두리·로봇·느낌표는 보존했습니다. 이번 수정은 치비로보 네 글자이며, 피워라는 아직 넣지 않았습니다.</p>'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('정리한 바탕','before.png'),('글자 삽입','title-korean.png')]:
            page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    page+='<h2>원본에서 추출한 글자</h2><img src="extracted-letters.png" class="reference"><h2>사용자 제공 원본</h2><img src="../../../graphics/references/title-lettering-user.png" class="reference"><p>PNG 검토안이며 게임 주입·실행은 아직 하지 않았습니다.</p>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
