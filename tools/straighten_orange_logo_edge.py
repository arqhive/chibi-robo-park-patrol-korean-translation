"""Remove the sideways bulge by continuing the existing vertical edge."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/graphics-draft/title-cleanup-v8'


def main():
    OUT.mkdir(exist_ok=True)
    before = Image.open(ROOT/'work/graphics-draft/title-cleanup-v7/title-panels-clean.png').convert('RGBA')
    after = before.copy()
    # Continue the actual straight edge below the bump, not the top-rim cap.
    after.putpixel((55,41),(0,0,0,0))
    after.putpixel((54,43),before.getpixel((54,47)))
    for y in [42,43,44]:
        after.putpixel((55,y),before.getpixel((55,47)))
    for y in [43,44]:
        after.putpixel((56,y),(0,0,0,0))
    changes=np.argwhere(np.any(np.array(before)!=np.array(after),axis=2))
    expected={(41,55),(43,54),(42,55),(43,55),(44,55),(43,56),(44,56)}
    assert set(map(tuple,changes))==expected
    assert all(after.getpixel((56,y))[3]==0 for y in range(39,52))
    assert all(after.getpixel((54,y))==before.getpixel((54,47)) for y in range(42,52))
    before.save(OUT/'before.png');after.save(OUT/'title-panels-clean.png')
    sheet=Image.new('RGB',(600,430),'#cccccc');draw=ImageDraw.Draw(sheet)
    for i,(src,label) in enumerate([(before,'Before'),(after,'After')]):
        crop=src.crop((47,37,61,56)).resize((280,380),Image.Resampling.NEAREST)
        sheet.paste(crop,(i*300,30),crop);draw.text((i*300,5),label,fill='black')
    sheet.save(OUT/'edge-comparison.png')
    report={'changed_pixels':len(changes),'changed_xy':[[int(x),int(y)] for y,x in changes],'all_other_pixels_identical_to_v7':True,'rightmost_column_56_clear_y39_to51':True,'dark_vertical_edge_column_54_continuous_y42_to51':True,'new_text_added':False,'output_sha256':hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v8_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>주황 판 오른쪽 돌출 수정</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>주황 판 오른쪽 돌출 수정</h1><p>오른쪽 세로선 아래의 곧은 윤곽을 기준으로, 바깥으로 나온 검은 선과 밝은 잔상까지 정리했습니다.</p><img src="edge-comparison.png">'
    for zoom in [1,4]:
        page+=f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('수정','title-panels-clean.png')]:
            page+=f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page+='</div>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    main()
