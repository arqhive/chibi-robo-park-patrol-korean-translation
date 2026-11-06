"""Match the orange upper-right rim to the yellow panel corner."""
import hashlib
import json
import shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/graphics-draft/title-cleanup-v7'
REFERENCE = ROOT / 'graphics/references/title-lettering-user.png'


def main():
    OUT.mkdir(exist_ok=True)
    before = Image.open(ROOT / 'work/graphics-draft/title-cleanup-v6/title-panels-clean.png').convert('RGBA')
    after = before.copy()
    after.putpixel((54, 40), (0, 0, 0, 0))
    for y in [41, 42]:
        for x in [52, 53, 54]:
            after.putpixel((x, y), before.getpixel((x + 65, y)))
    changes = np.argwhere(np.any(np.array(before) != np.array(after), axis=2))
    expected = {(40, 54)} | {(y, x) for y in [41, 42] for x in [52, 53, 54]}
    assert set(map(tuple, changes)) == expected
    before.save(OUT / 'before.png')
    after.save(OUT / 'title-panels-clean.png')
    sheet = Image.new('RGB', (720, 300), '#cccccc')
    draw = ImageDraw.Draw(sheet)
    for i, (src, x, y, label) in enumerate([(before,55,41,'Orange before'), (after,55,41,'Orange after'), (after,120,41,'Yellow reference')]):
        crop = src.crop((x-7,y-4,x+3,y+9)).resize((200,260),Image.Resampling.NEAREST)
        sheet.paste(crop,(i*240,30),crop)
        draw.text((i*240,5),label,fill='black')
    sheet.save(OUT / 'corner-comparison.png')
    report = {'changed_pixels': len(changes), 'changed_xy': [[int(x),int(y)] for y,x in changes], 'all_other_pixels_identical_to_v6': True, 'reference_corner': 'yellow panel x117..119, y41..42', 'new_text_added': False, 'output_sha256': hashlib.sha256((OUT/'title-panels-clean.png').read_bytes()).hexdigest(), 'lettering_reference': str(REFERENCE.relative_to(ROOT)).replace(chr(92),'/'), 'lettering_reference_sha256': hashlib.sha256(REFERENCE.read_bytes()).hexdigest()}
    (ROOT/'metadata/title_cleanup_v7_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page = '<meta charset="utf-8"><title>주황 판 오른쪽 위 모서리 수정</title><style>body{font:16px/1.6 sans-serif;background:#eef1e9;margin:30px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.row{display:flex;gap:24px;flex-wrap:wrap}</style><h1>주황 판 오른쪽 위 모서리 수정</h1><p>위로 솟은 픽셀과 그 아래 윤곽을 노란 판 끝 패턴에 맞췄습니다. 수정한 7픽셀 외에는 v6와 동일합니다.</p><img src="corner-comparison.png">'
    for zoom in [1,4]:
        page += f'<h2>{zoom}배 비교</h2><div class="row">'
        for label,file in [('이전','before.png'),('수정','title-panels-clean.png')]:
            page += f'<div>{label}<br><img src="{file}" width="{192*zoom}" height="{104*zoom}"></div>'
        page += '</div>'
    page += '<h2>보관한 글자 레퍼런스</h2><p>검은 획과 흰 하이라이트를 참고할 사용자 제공 이미지입니다. 글자 작업은 아직 적용하지 않았습니다.</p><img src="../../../graphics/references/title-lettering-user.png" style="max-width:100%;image-rendering:auto">'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    main()
