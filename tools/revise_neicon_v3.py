from pathlib import Path
import json, shutil, hashlib
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import label, binary_dilation

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'work/graphics-draft/neicon-v2'
OUT = ROOT / 'work/graphics-draft/neicon-v3'
KEY = 'NEIconFeelMSG/cell/0'
STEM = KEY.replace('/', '-')

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NEIcon*.png'):
        shutil.copy2(p, OUT / p.name)
    a = np.array(Image.open(OUT / 'feel-imagegen.png').convert('RGBA'))
    labs, _ = label(a[:, :, 3] >= 128)
    counts = np.bincount(labs.ravel())
    keep = counts >= 1000
    keep[0] = False
    support = binary_dilation(keep[labs], iterations=2)
    a[~support] = 0
    master = Image.fromarray(a)
    crop = master.crop(master.getbbox())
    scale = min(126 / crop.width, 14 / crop.height)
    small = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
    a = np.array(small)
    opaque = a[:, :, 3] >= 128
    white = a[:, :, :3].mean(axis=2) >= 128
    a[:] = 0
    a[opaque, 3] = 255
    a[opaque & white, :3] = 255
    small = Image.fromarray(a)
    result = Image.new('RGBA', (128, 16))
    result.paste(small, ((128-small.width)//2, (16-small.height)//2))
    result.save(OUT / f'{STEM}-korean.png')
    shutil.copy2(OLD / f'{STEM}-korean.png', OUT / f'{STEM}-previous.png')
    original = Image.open(OUT / f'{STEM}-original.png').convert('RGBA')
    mask = (np.array(original)[:, :, 3] > 0) | (np.array(result)[:, :, 3] > 0)
    Image.fromarray(mask.astype('uint8')*255).save(OUT / f'{STEM}-mask.png')
    proof = Image.new('RGB', (600, 220), '#c9c9c9')
    draw = ImageDraw.Draw(proof)
    for y, name, im in [(10, 'Original', original), (110, 'Revised', result)]:
        draw.text((5,y), name, fill='black')
        proof.paste(im, (100,y), im)
        big = im.resize((512,64), Image.Resampling.NEAREST)
        proof.paste(big, (5,y+25), big)
    proof.save(OUT / 'feel-proof.png')
    p = ROOT / 'metadata/extraction_manifest.json'
    m = json.loads(p.read_text(encoding='utf-8'))
    rows = [r for r in m['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==139
    unchanged = 0
    for r in rows:
        loc = r['localization']
        for field in ('output', 'preview', 'erased', 'edit_mask', 'comparison'):
            if isinstance(loc.get(field), str):
                loc[field] = loc[field].replace('neicon-v2/', 'neicon-v3/')
        loc['draft_version'] = 'neicon-v3'
        if r['key']==KEY:
            loc.update(korean_proposal='오늘 기분은 ?', lines=['오늘 기분은 ?'], method_reason='사용자 수정: 기울기 없이 갈무리를 크게 그린 듯한 이미지젠 도트 글씨. 오늘 / 기분은 ? 두 어절 간격과 물음표 앞 공백.', note='이미지젠 생성 후 원본128×16 안에 배치. 흰 글씨·검은 외곽선, 수평 배치. 게임실행 미확인.')
        else:
            name=r['key'].replace('/','-')+'-korean.png'
            assert (OLD/name).read_bytes()==(OUT/name).read_bytes()
            unchanged += 1
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    page=(OLD/'index.html').read_text(encoding='utf-8')
    start=page.index('<p>전체139개'); end=page.index('<section ',start)
    page=page[:start]+'<p>전체 139개 사용처를 표시합니다. 오늘 기분은 ?은 기울기 없이 갈무리를 크게 그린 듯한 이미지젠 글씨로 교체했습니다. 나머지 138개는 직전 결과를 유지했습니다.</p><p>원본 크기 유지 · 게임실행 미확인 · <a href="../../../metadata/neicon_v3_prompt.json">이미지젠 프롬프트</a></p>'+page[end:]
    page=page.replace('오늘 기분은?', '오늘 기분은 ?')
    (OUT/'index.html').write_text(page,encoding='utf-8')
    report={'references':139,'changed_references':1,'unchanged_references':unchanged,'text':'오늘 기분은 ?','size':list(result.size),'ink_bbox':result.getbbox(),'imagegen_master':'work/graphics-draft/neicon-v3/feel-imagegen.png','output':'work/graphics-draft/neicon-v3/'+STEM+'-korean.png','sha256':hashlib.sha256((OUT/f'{STEM}-korean.png').read_bytes()).hexdigest(),'runtime_verified':False}
    (ROOT/'metadata/neicon_v3_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    main()
