"""Restore four upper-left joins from source pixels, retaining v4 rim pattern."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-cleanup-v5'
ORIGINAL=ROOT/'work/stage4/png/cb6c5f5541e90b241c5593cd00628394bc70a7c9a52699b39381aa7a822a55db.png'
PREVIOUS=ROOT/'work/graphics-draft/title-cleanup-v4/title-panels-clean.png'
CORNERS=[(24,54),(57,53),(90,54),(122,53)]


def main():
    OUT.mkdir(exist_ok=True)
    original=np.array(Image.open(ORIGINAL).convert('RGBA'))
    before=np.array(Image.open(PREVIOUS).convert('RGBA'));after=before.copy()
    mask=Image.new('1',(192,104));draw=ImageDraw.Draw(mask);polygons=[]
    for x,y in CORNERS:
        polygon=[(x-1,y-2),(x+5,y-5),(x+5,y-1),(x+3,y+1),(x+3,y+5),(x-1,y+5)]
        draw.polygon(polygon,fill=1);polygons.append(polygon)
    selected=np.array(mask);after[selected]=original[selected]
    assert np.array_equal(after[selected],original[selected])
    assert np.array_equal(after[~selected],before[~selected])
    result=Image.fromarray(after);result.save(OUT/'title-panels-clean.png')
    Image.fromarray(before).save(OUT/'before.png')
    Image.fromarray(selected.astype('uint8')*255).save(OUT/'repair-mask.png')
    result.resize((768,416),Image.Resampling.NEAREST).save(OUT/'title-panels-clean-4x.png')
    sheet=Image.new('RGB',(720,720),'#bbbbbb');d=ImageDraw.Draw(sheet)
    for row,(x,y) in enumerate(CORNERS):
        for col,(label,a) in enumerate([('original',original),('v4',before),('v5',after)]):
            im=Image.fromarray(a).crop((x-3,y-5,x+9,y+7)).resize((168,168),Image.Resampling.NEAREST)
            sheet.paste(im,(col*240,row*180+12),im);d.text((col*240,row*180),f'{row+1} {label}',fill='black')
    sheet.save(OUT/'corners-comparison.png')
    report={'repair_polygons':polygons,'changed_pixels':int(np.any(before!=after,axis=2).sum()),
        'restored_corner_source_mismatch_pixels':0,'outside_corner_mask_changed_pixels':0,'new_text_added':False,
        'output_sha256':hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v5_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>왼쪽 위 모서리 복원</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>네 판의 왼쪽 위 모서리 복원</h1><p>꺾이는 모서리와 세로선 연결 부분을 원본 픽셀로 복원했습니다. 새 글자는 넣지 않았습니다.</p>'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('모서리 복원','title-panels-clean.png')]:page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    page+='<h2>모서리별 원본 · 이전 · 복원</h2><img src="corners-comparison.png" width="720" height="720">'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
