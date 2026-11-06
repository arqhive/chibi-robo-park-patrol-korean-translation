"""Repair ten outline pixels in the mood heading's syllable 늘."""
from pathlib import Path
import json, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'work/graphics-draft/neicon-v3'
OUT = ROOT / 'work/graphics-draft/neicon-v4'
STEM = 'NEIconFeelMSG-cell-0'

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NEIcon*.png'):
        shutil.copy2(p, OUT / p.name)
    before = Image.open(OLD / f'{STEM}-korean.png').convert('RGBA')
    after = before.copy()
    fixes = [(x, 5) for x in range(36, 45)] + [(44, 12)]
    for x, y in fixes:
        assert before.getpixel((x, y)) == (255, 255, 255, 255)
        after.putpixel((x, y), (0, 0, 0, 255))
    a, b = np.array(before), np.array(after)
    changed = np.any(a != b, axis=2)
    assert int(changed.sum()) == 10
    assert np.array_equal(a[:,:,3], b[:,:,3])
    after.save(OUT / f'{STEM}-korean.png')
    before.save(OUT / f'{STEM}-previous.png')
    Image.fromarray(changed.astype('uint8') * 255).save(OUT / 'outline-repair-mask.png')
    proof = Image.new('RGB', (600, 220), '#c9c9c9')
    draw = ImageDraw.Draw(proof)
    for y, label, im in [(10, 'Before', before), (110, 'After', after)]:
        draw.text((5, y), label, fill='black')
        proof.paste(im, (100, y), im)
        enlarged = im.resize((512, 64), Image.Resampling.NEAREST)
        proof.paste(enlarged, (5, y+25), enlarged)
    proof.save(OUT / 'feel-proof.png')
    p = ROOT / 'metadata/extraction_manifest.json'
    manifest = json.loads(p.read_text(encoding='utf-8'))
    rows = [r for r in manifest['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows) == 139
    for r in rows:
        loc = r['localization']
        for f in ('output', 'preview', 'erased', 'edit_mask', 'comparison'):
            if isinstance(loc.get(f), str):
                loc[f] = loc[f].replace('neicon-v3/', 'neicon-v4/')
        loc['draft_version'] = 'neicon-v4'
        if r['key'] == 'NEIconFeelMSG/cell/0':
            loc['note'] = '이미지젠 글씨의 늘: ㄴ·ㅡ 사이 검은 외곽선9px, ㄹ 내부 외곽선 끊김1px 보수. 나머지 픽셀·투명도 동일. 게임실행 미확인.'
        else:
            name = r['key'].replace('/', '-') + '-korean.png'
            assert (OLD/name).read_bytes() == (OUT/name).read_bytes()
    p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page = (OLD/'index.html').read_text(encoding='utf-8')
    start = page.index('<p>전체 139개'); end = page.index('<section ', start)
    page = page[:start] + '<p>전체 139개 사용처를 표시합니다. 오늘 기분은 ?의 늘에서 ㄴ과 ㅡ 사이 검은 외곽선과 ㄹ 내부의 끊긴 외곽선을 보수했습니다. 총10픽셀만 변경했으며 나머지138개 도안은 동일합니다.</p><p>원본128×16 크기·투명도 유지 · 게임실행 미확인 · <a href="feel-proof.png">수정 전후 비교</a> · <a href="../../../metadata/neicon_v3_prompt.json">기존 이미지젠 프롬프트</a></p>' + page[end:]
    assert page.count('<section id=') == 139
    (OUT/'index.html').write_text(page,encoding='utf-8')
    report = {'references':139,'changed_references':1,'unchanged_references':138,'changed_pixels':10,'black_outline_pixels_added':[list(v) for v in fixes],'size':list(after.size),'alpha_identical':True,'outside_repair_mask_changed_pixels':0,'output':str((OUT/f'{STEM}-korean.png').relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256((OUT/f'{STEM}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False}
    (ROOT/'metadata/neicon_v4_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__':
    main()
