"""Remove downsampling residue below the reference-derived bi stem."""
import json
import hashlib
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-reference-v2'
PIXELS=[(78,76),(79,76),(80,76),(82,75)]


def main():
    OUT.mkdir(exist_ok=True)
    before=Image.open(ROOT/'work/graphics-draft/title-reference-v1/title-korean.png').convert('RGBA')
    background=Image.open(ROOT/'work/graphics-draft/title-cleanup-v8/title-panels-clean.png').convert('RGBA')
    after=before.copy()
    for xy in PIXELS:after.putpixel(xy,background.getpixel(xy))
    changed=np.any(np.array(before)!=np.array(after),axis=2)
    assert set(map(tuple,np.argwhere(changed)))=={(y,x) for x,y in PIXELS}
    before.save(OUT/'before.png');after.save(OUT/'title-korean.png')
    mask=Image.open(ROOT/'work/graphics-draft/title-reference-v1/letter-mask.png').convert('L')
    for xy in PIXELS:mask.putpixel(xy,0)
    mask.save(OUT/'letter-mask.png')
    sheet=Image.new('RGB',(480,300),'#cccccc');draw=ImageDraw.Draw(sheet)
    for i,(src,label) in enumerate([(before,'Before'),(after,'After')]):
        crop=src.crop((75,69,87,82)).resize((240,260),Image.Resampling.NEAREST)
        sheet.paste(crop,(240*i,25),crop);draw.text((240*i,5),label,fill='black')
    sheet.save(OUT/'stem-comparison.png')
    after.resize((768,416),Image.Resampling.NEAREST).save(OUT/'preview-4x.png')
    report={'changed_pixels':int(changed.sum()),'restored_background_xy':PIXELS,'all_other_pixels_identical_to_v1':True,'output_sha256':hashlib.sha256((OUT/'title-korean.png').read_bytes()).hexdigest(),'rom_injection_tested':False}
    (ROOT/'metadata/title_reference_v2_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>비 세로획 아래 잔상 정리</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>비 · ㅣ획 아래 잔상 정리</h1><p>획 끝 아래의 흐린 픽셀을 정리해 판 테두리와 분리했습니다. 수정한 4픽셀 외에는 이전 결과 그대로입니다.</p><img src="stem-comparison.png">'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('수정','title-korean.png')]:
            page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
