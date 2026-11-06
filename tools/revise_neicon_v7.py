"""Insert the literal slash in 오늘 / 기분은 ? while preserving glyph shapes."""
from pathlib import Path
import json, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'work/graphics-draft/neicon-v6'
OUT = ROOT / 'work/graphics-draft/neicon-v7'
STEM = 'NEIconFeelMSG-cell-0'

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NEIcon*.png'):
        shutil.copy2(p, OUT / p.name)
    before = Image.open(OLD / f'{STEM}-korean.png').convert('RGBA')
    after = Image.new('RGBA', before.size)
    after.paste(before.crop((2,0,48,16)), (0,0))
    after.paste(before.crop((53,0,126,16)), (55,0))
    ink = Image.new('L', before.size)
    for y in range(3,13):
        x = 51 - (y-3)//3
        ink.putpixel((x,y),255)
        ink.putpixel((x+1,y),255)
    border = ink.filter(ImageFilter.MaxFilter(3))
    after.paste((0,0,0,255),(0,0,128,16),border)
    after.paste((255,255,255,255),(0,0,128,16),ink)
    a, b = np.array(before), np.array(after)
    changed = np.any(a != b, axis=2)
    assert np.array_equal(a[:,2:48], b[:,:46])
    assert np.array_equal(a[:,53:126], b[:,55:128])
    source = np.array(Image.open(OLD / f'{STEM}-original.png').convert('RGBA'))
    mask = (source[:,:,3]>0) | (b[:,:,3]>0)
    Image.fromarray(mask.astype('uint8')*255).save(OUT / f'{STEM}-mask.png')
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
                loc[f] = loc[f].replace('neicon-v6/', 'neicon-v7/')
        loc['draft_version'] = 'neicon-v7'
        if r['key'] == 'NEIconFeelMSG/cell/0':
            loc['korean_proposal'] = '오늘 / 기분은 ?'
            loc['lines'] = ['오늘 / 기분은 ?']
            loc['note'] = '오늘 뒤 실제 슬래시 추가. 기존 오늘은 왼쪽2px, 기분은 ?은 오른쪽2px 이동해 간격 확보. 글자 형태 그대로 보존, 원본128×16 유지. 게임실행 미확인.'
        else:
            name = r['key'].replace('/', '-') + '-korean.png'
            assert (OLD/name).read_bytes() == (OUT/name).read_bytes()
    p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page = (OLD/'index.html').read_text(encoding='utf-8')
    start = page.index('<p>전체 139개'); end = page.index('<section ', start)
    page = page[:start] + '<p>전체 139개 사용처를 표시합니다. 오늘 / 기분은 ?에 실제 슬래시를 추가했습니다. 기존 글자 형태와 나머지138개 도안은 유지했습니다.</p><p>원본128×16 크기 유지 · 게임실행 미확인 · <a href="feel-proof.png">수정 전후 비교</a></p>' + page[end:]
    page = page.replace('오늘 기분은 ?', '오늘 / 기분은 ?')
    assert page.count('<section id=') == 139
    (OUT/'index.html').write_text(page,encoding='utf-8')
    report = {'references':139,'changed_references':1,'unchanged_references':138,'text':'오늘 / 기분은 ?','original_glyph_pixels_preserved_under_translation':True,'left_group_offset_x':-2,'right_group_offset_x':2,'changed_pixels':int(changed.sum()),'size':list(after.size),'output':str((OUT/f'{STEM}-korean.png').relative_to(ROOT)).replace('\\','/'),'sha256':hashlib.sha256((OUT/f'{STEM}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False}
    (ROOT/'metadata/neicon_v7_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__ == '__main__':
    main()
