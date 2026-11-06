"""Remove all remnants above each panel's dark upper rim; no lettering added."""
import json, hashlib
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-cleanup-v3'
SRC=ROOT/'work/graphics-draft/batch01-v2/TitleLogo-cell-0-erased.png'
# Manually inspected native-pixel intervals and endpoints of the dark panel rims.
RIMS=[(24,56,54,41),(57,88,53,41),(90,121,54,41),(122,154,53,41)]


def main():
    OUT.mkdir(exist_ok=True)
    im=Image.open(SRC).convert('RGBA');before=np.array(im);after=before.copy()
    boundary={};mask=np.zeros(before.shape[:2],bool)
    for left,right,y_left,y_right in RIMS:
        for x in range(left,right+1):
            predicted=round(y_left+(y_right-y_left)*(x-left)/(right-left))
            candidates=[y for y in range(predicted-2,predicted+3)
                        if before[y,x,3] and max(before[y,x,:3])<110]
            cut=max(candidates) if candidates else predicted
            # Preserve at most two contiguous dark pixels of the actual rim.
            if candidates and before[cut-1,x,3] and max(before[cut-1,x,:3])<110:cut-=1
            boundary[x]=cut;mask[:cut,x]=True
    # Gaps and left margin above the plates contain no protected artwork.
    for x in range(0,156):
        if x not in boundary:
            cut=38 if x==155 else 52
            boundary[x]=cut;mask[:cut,x]=True
    after[mask]=0
    assert not after[:,:,3][mask].any()
    assert np.array_equal(before[~mask],after[~mask])
    result=Image.fromarray(after)
    result.save(OUT/'title-panels-clean.png');im.save(OUT/'before.png')
    Image.fromarray(mask.astype('uint8')*255).save(OUT/'removal-mask.png')
    result.resize((768,416),Image.Resampling.NEAREST).save(OUT/'title-panels-clean-4x.png')
    report={'input':SRC.relative_to(ROOT).as_posix(),'output':(OUT/'title-panels-clean.png').relative_to(ROOT).as_posix(),
            'removed_visible_pixels':int(((before[:,:,3]>0)&mask).sum()),'remaining_visible_pixels_above_rims':0,
            'changed_pixels_outside_removal_mask':0,'size':list(im.size),'new_lettering_added':False,
            'column_cut_y':boundary,'output_sha256':hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v3_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='''<meta charset="utf-8"><title>색 판 윗선 잔여 픽셀 정리</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>검은 윗선 위 잔여 픽셀 제거</h1><p>글자를 넣기 전 바탕만 정리했습니다. 원래 색 판·검은 윗선·로봇·꽃은 유지했습니다.</p>'''
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배</h2><div class="row">'
        for label,file in [('이전','before.png'),('잔여 픽셀 제거','title-panels-clean.png')]:page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='column_cut_y'},ensure_ascii=False))


if __name__=='__main__':main()
