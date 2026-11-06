"""Reuse the first imagegen word, straighten individual characters, preserve current logo."""
import hashlib
import json
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-top-original-v1'
SRC=ROOT/'work/graphics-draft/batch01-v1/title-imagegen.png'
BASE=ROOT/'work/graphics-draft/title-reference-v2/title-korean.png'


def main():
    OUT.mkdir(exist_ok=True)
    a=np.array(Image.open(SRC).convert('RGBA'))
    r,g,b=a[:,:,:3].transpose(2,0,1).astype(int);yy,xx=np.indices(r.shape)
    selections=[(r>180)&(g>75)&(g<200)&(b<80)&(xx<570),(g>170)&(r>140)&(b<100)&(xx>530)&(xx<880),(r>200)&(g>195)&(b<90)&(xx>850)&(xx<1270)]
    chars=[]
    for i,selection in enumerate(selections):
        selection&=(yy>80)&(yy<450)&(a[:,:,3]>100)
        labels,_=ndimage.label(selection);sizes=np.bincount(labels.ravel());sizes[0]=0
        core=ndimage.binary_fill_holes(labels==sizes.argmax())
        distance=ndimage.distance_transform_edt(~core)
        # Rejoin the outline at former overlaps without carrying adjacent panel fragments.
        rgba=np.zeros_like(a);rgba[distance<=24]=(5,5,5,255)
        rgba[(distance>=12)&(distance<=17)]=(250,250,250,255)
        rgba[core]=a[core]
        cut=Image.fromarray(rgba);cut=cut.crop(cut.getbbox());cut.save(OUT/f'extracted-{i}.png')
        cut=cut.rotate(-10,resample=Image.Resampling.BICUBIC,expand=True)
        cut=cut.crop(cut.getchannel('A').point(lambda v:255 if v>80 else 0).getbbox())
        cut.save(OUT/f'clean-upright-{i}.png');chars.append(cut)
    scale=33/max(q.height for q in chars);widths=[round(q.width*scale) for q in chars]
    x=(170-sum(widths)+4)//2;layer=Image.new('RGBA',(192,104));placements=[]
    for i,(q,w) in enumerate(zip(chars,widths)):
        q=q.resize((w,round(q.height*scale)),Image.Resampling.LANCZOS)
        q.putalpha(q.getchannel('A').point(lambda v:255 if v>=96 else 0))
        layer.alpha_composite(q,(x,40-q.height))
        placements.append({'character':'피워라'[i],'xy':[x,40-q.height],'size':list(q.size),'bottom_y':40});x+=w-2
    base=Image.open(BASE).convert('RGBA');result=base.copy();result.alpha_composite(layer)
    active=np.array(layer)[:,:,3]>0;changed=np.any(np.array(base)!=np.array(result),axis=2)
    assert not np.any(active&(np.array(base)[:,:,3]>0))
    assert not np.any(changed&~active)
    assert np.array_equal(np.array(base)[40:],np.array(result)[40:])
    layer.save(OUT/'top-layer.png');base.save(OUT/'before.png');result.save(OUT/'title-korean.png')
    for zoom in [4,6]:result.resize((192*zoom,104*zoom),Image.Resampling.NEAREST).save(OUT/f'preview-{zoom}x.png')
    oldmask=np.array(Image.open(ROOT/'work/graphics-draft/title-reference-v2/letter-mask.png').convert('L'))>0
    Image.fromarray((oldmask|active).astype('uint8')*255).save(OUT/'letter-mask.png')
    report={'source':str(SRC.relative_to(ROOT)).replace(chr(92),'/'),'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'method':'First-generation colored character interiors retained; overlap outlines repaired; each character rotated clockwise 10 degrees; bottoms aligned','placements':placements,'overlap_with_existing_logo_pixels':0,'outside_top_layer_changes':0,'rows_40_to103_identical':True,'new_imagegen_call':False,'output_sha256':hashlib.sha256((OUT/'title-korean.png').read_bytes()).hexdigest(),'rom_injection_tested':False}
    (ROOT/'metadata/title_top_original_v1_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>첫 피워라 글자 수평 배치</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>처음 만든 피워라 · 기울기 보정</h1><p>첫 생성본의 세 글자를 추출해 각각 10° 돌려 바로 세우고 밑선을 맞췄습니다. 분리 경계의 외곽선을 복원했으며 흰 글씨와 주황·연두·노랑 면은 첫 생성본을 사용했습니다.</p>'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 결과</h2><img src="title-korean.png" width="{192*zoom}" height="{104*zoom}">'
    page+='<h2>기울기 보정한 글자 원본</h2><div class="row">'
    for i in range(3):page+=f'<img src="clean-upright-{i}.png" style="width:240px;height:auto;object-fit:contain;image-rendering:auto">'
    page+='</div><p>아래 치비로보·판 테두리·로봇·꽃·느낌표는 이전 결과와 픽셀 동일합니다. PNG 검토안이며 게임 주입은 아직 하지 않았습니다.</p>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
