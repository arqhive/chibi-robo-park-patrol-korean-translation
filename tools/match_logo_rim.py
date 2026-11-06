"""Match the intact exclamation panel's five-column rim pattern."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-cleanup-v4'
SOURCE=ROOT/'work/stage4/png/cb6c5f5541e90b241c5593cd00628394bc70a7c9a52699b39381aa7a822a55db.png'
PREVIOUS=ROOT/'work/graphics-draft/title-cleanup-v3/title-panels-clean.png'
# Original exclamation-panel samples, upper antialias/core/inner blend.
SAMPLES=[(158,52),(159,51),(160,51),(161,50),(162,50)]
# Front-face span, starting dark-line row, face color, right side column.
PANELS=[(25,54,53,(246,164,65),56),(58,86,52,(197,222,74),88),
        (91,119,53,(255,246,98),121),(123,152,52,(197,222,74),154)]


def main():
    OUT.mkdir(exist_ok=True)
    source=np.array(Image.open(SOURCE).convert('RGBA'))
    old=np.array(Image.open(PREVIOUS).convert('RGBA'));new=old.copy()
    allowed=np.zeros(old.shape[:2],bool)
    palette=np.unique(source[source[:,:,3]>0,:3],axis=0).astype(float)
    samples=np.array([[source[y+d,x] for d in [-1,0,1]] for x,y in SAMPLES])
    def tint(pixel,face):
        if tuple(face)==(246,164,65):return pixel
        # Match the same shadow coverage against each existing flat face.
        fraction=np.clip(np.dot(pixel[:3].astype(float)-41,np.array([246,164,65])-41)/np.sum((np.array([246,164,65])-41)**2),0,1)
        rgb=41+(np.array(face)-41)*fraction
        chosen=palette[np.argmin(((palette-rgb)**2).sum(1))].astype('uint8')
        return np.r_[chosen,255].astype('uint8')
    rows=[]
    for left,right,start,face,side in PANELS:
        core=[]
        for x in range(left,right+1):
            i=x-left;y=start-(2*i+4)//5;phase=i%5
            new[:y-1,x]=0;allowed[:y+3,x]=True
            new[y-1,x]=samples[phase,0]
            new[y,x]=samples[phase,1]
            new[y+1,x]=tint(samples[phase,2],face)
            new[y+2,x]=(*face,255)
            core.append(y)
        # Join the last tread to the untouched vertical side without a spike.
        end=core[-1]
        for x in range(right+1,side+1):
            new[:end,x]=0;allowed[:end+2,x]=True
            new[end,x]=source[42,186] if x==side else source[41,185]
            new[end+1,x]=old[end+1,x] if old[end+1,x,3] else source[43,186]
        rows.append({'x_range':[left,right],'core_y':core})
    assert np.array_equal(new[~allowed],old[~allowed])
    assert np.array_equal(new[:,156:],old[:,156:])
    for panel in rows:
        for i,y in enumerate(panel['core_y']):
            x=panel['x_range'][0]+i
            assert np.array_equal(new[y-1:y+1,x],samples[i%5,:2])
    im=Image.fromarray(new);im.save(OUT/'title-panels-clean.png')
    Image.fromarray(old).save(OUT/'before.png')
    Image.fromarray(allowed.astype('uint8')*255).save(OUT/'edit-mask.png')
    im.resize((768,416),Image.Resampling.NEAREST).save(OUT/'title-panels-clean-4x.png')
    # Show the borrowed pattern at high magnification on a neutral backdrop.
    preview=Image.new('RGBA',(192*5,104*5),(210,210,210,255))
    preview.alpha_composite(im.resize(preview.size,Image.Resampling.NEAREST))
    preview.convert('RGB').save(OUT/'inspection.png')
    report={'reference_samples':SAMPLES,'pattern_rgba':samples.tolist(),'panels':rows,'new_text_added':False,
        'outside_mask_changed_pixels':0,'exclamation_panel_changed_pixels':0,'outer_and_dark_rim_sample_match':True,
        'output_sha256':hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v4_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>느낌표 판 기준 윗선 정리</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>느낌표 판의 도트 패턴을 적용한 윗선</h1><p>원본 느낌표 판에서 가져온 검은 선·안쪽 음영·바깥 가장자리 패턴으로 정리했습니다. 새 글자는 아직 넣지 않았습니다.</p>'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('패턴 적용','title-panels-clean.png')]:page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print('Four panel rims matched; outside-mask changes 0; no new text.')


if __name__=='__main__':main()
