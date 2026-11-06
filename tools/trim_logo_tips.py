"""Trim only the overhanging caps at the four upper-right corners."""
import json,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-cleanup-v6'
TIPS=[(55,41),(87,40),(120,41),(153,40)]


def main():
    OUT.mkdir(exist_ok=True)
    before=np.array(Image.open(ROOT/'work/graphics-draft/title-cleanup-v5/title-panels-clean.png').convert('RGBA'))
    after=before.copy();coords=[]
    for x,y in TIPS:
        for yy in [y,y+1]:
            coords.append([x+1,yy]);after[yy,x+1]=0
    changed=np.any(before!=after,axis=2)
    assert int(changed.sum())==8
    assert set(map(tuple,np.argwhere(changed)))=={(y,x) for x,y in coords}
    Image.fromarray(before).save(OUT/'before.png')
    result=Image.fromarray(after);result.save(OUT/'title-panels-clean.png')
    result.resize((768,416),Image.Resampling.NEAREST).save(OUT/'title-panels-clean-4x.png')
    sheet=Image.new('RGB',(800,420),'#ccc');d=ImageDraw.Draw(sheet)
    for row,a in enumerate([before,after]):
        for col,(x,y) in enumerate(TIPS):
            q=Image.fromarray(a).crop((x-6,y-4,x+5,y+8)).resize((165,180),Image.Resampling.NEAREST)
            sheet.paste(q,(col*200,row*210+20),q)
            d.text((col*200,row*210),f'{col+1} '+('before' if row==0 else 'after'),fill='black')
    sheet.save(OUT/'tips-comparison.png')
    report={'removed_pixel_coordinates':coords,'changed_pixels':8,'all_other_pixels_identical_to_v5':True,'new_text_added':False,'output_sha256':hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v6_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>오른쪽 위 끝 돌출 제거</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>오른쪽 위 끝 돌출 제거</h1><p>네 모서리에서 바깥으로 나온 픽셀만 제거했습니다. 왼쪽 모서리와 나머지 픽셀은 v5 그대로입니다. 새 글자는 넣지 않았습니다.</p>'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('끝 정리','title-panels-clean.png')]:page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    page+='<h2>오른쪽 끝 확대 · 위: 이전 / 아래: 수정</h2><img src="tips-comparison.png" width="800" height="420">'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
