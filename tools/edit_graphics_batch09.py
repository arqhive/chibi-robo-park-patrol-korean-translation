"""Render native Mono7 forecast UI while preserving all non-letter pixels."""
from pathlib import Path
import hashlib, html, json, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/graphics-draft/batch09-v1'
FONT_PATH = ROOT / 'work/fonts/galmuri-mono7/GalmuriMono7.ttf'
FONT = ImageFont.truetype(str(FONT_PATH), 8)
IDS = list(range(12)) + [16, 17, 18, 19]
ICONS = [7, 8, 9, 10, 11, 19]


def lettering(text, color, font=FONT):
    # Render once at the font's native size: no resizing, condensation or kerning.
    ink = Image.new('L', (256, 20))
    draw = ImageDraw.Draw(ink)
    draw.fontmode = '1'
    draw.text((2, 2), text, font=font, fill=255)
    box = ink.getbbox()
    ink = ink.crop((box[0]-1, box[1]-1, box[2]+1, box[3]+1))
    outer = ink.filter(ImageFilter.MaxFilter(3))
    layer = Image.new('RGBA', ink.size)
    layer.paste((*color, 255), (0, 0), outer)
    layer.paste((255, 255, 255, 255), (0, 0), ink)
    return layer


def main():
    global OUT
    revised = '--galmuri9-headings' in sys.argv
    version = 'batch09-v2' if revised else 'batch09-v1'
    OUT = ROOT / 'work/graphics-draft' / version
    large_path = Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri9.ttf'
    large_font = ImageFont.truetype(str(large_path), 10) if revised else None
    OUT.mkdir(parents=True, exist_ok=True)
    p = ROOT / 'metadata/extraction_manifest.json'
    manifest = json.loads(p.read_text(encoding='utf-8'))
    rows = [r for r in manifest['graphics'] if r['edition'] == 'jp' and
            r['key'] in {f'NewPCKForecast2/cell/{n}' for n in IDS}]
    assert len(rows) == 16
    checks, updates = [], {}
    for r in rows:
        key = r['key']; n = int(key.split('/')[-1]); stem = key.replace('/', '-')
        loc = r['localization']; assert loc['approval'] != 'approved'
        text = loc['korean_proposal']
        src = Image.open(ROOT/r['path']).convert('RGBA'); a = np.array(src)
        old = a[:, :, 3] > 0
        if n == 0:
            old[:] = False
            old[8:21, 60:150] = np.any(a[8:21, 60:150, :3] != 205, axis=2)
        elif n in ICONS:
            old[:32] = False
        elif n in [16, 17]:
            old[:, :15 if n == 16 else 16] = False
        yy, xx = np.where(old)
        box = [int(xx.min()), int(yy.min()), int(xx.max()+1), int(yy.max()+1)]
        clean = a.copy(); clean[old] = (205,205,205,255) if n == 0 else (0,0,0,0)
        erased = Image.fromarray(clean)
        large = revised and n in [0,18]
        font_name, font_px = ('Galmuri9',10) if large else ('GalmuriMono7',8)
        layer = lettering(text, (65,65,65) if n in [0,16,17] else (16,49,123), large_font if large else FONT)
        x = (src.width-layer.width)//2 if n == 0 or n in ICONS else box[0]
        y = (box[1]+box[3]-layer.height)//2 if n == 0 or n in ICONS else box[1]
        assert x >= 0 and y >= 0 and x+layer.width <= src.width and y+layer.height <= src.height, key
        new = Image.new('RGBA', src.size); new.alpha_composite(layer, (x,y))
        result = Image.alpha_composite(erased, new); b = np.array(result)
        mask = old | (np.array(new)[:,:,3] > 0)
        assert np.array_equal(a[~mask], b[~mask])
        if n in ICONS: assert np.array_equal(a[:32], b[:32])
        if n in [16,17]: assert np.array_equal(a[:,:box[0]], b[:,:box[0]])
        if n == 0: assert np.array_equal(a[23:], b[23:])
        if revised and not large:
            previous = Image.open(ROOT/'work/graphics-draft/batch09-v1'/f'{stem}-korean.png').convert('RGBA')
            assert previous.tobytes() == result.tobytes(), key
        for suffix, im in [('original',src),('erased',erased),('korean',result),
                           ('mask',Image.fromarray(mask.astype('uint8')*255))]:
            im.save(OUT/f'{stem}-{suffix}.png')
        output = (OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        checks.append({'key':key,'text':text,'size':list(src.size),'original_text_bbox':box,
                       'text_bbox':[x,y,x+layer.width,y+layer.height],
                       'font':font_name,'font_px':font_px,'native_advance_preserved':True,
                       'resized':False,'outside_mask_changed_pixels':0,'protected_artwork_changed_pixels':0,
                       'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),
                       'runtime_verified':False})
        updates[r['pixel_sha256']] = {'output':output,'preview':output,
            'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),
            'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),
            'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,
            'draft_version':version,'editing_method':'galmuri','font':font_name,'font_px':font_px,
            'method_reason':f'명확한 도트 UI 글씨. {font_name}의 기본 픽셀 크기와 글자 간격 유지.',
            'work_status':'review','approval':'pending','requires_resource_width_expansion':False,
            'note':'원본 규격·아이콘·창 테두리·배경 보존. 글자 축소 및 가로 압축 없음. 팔레트변환·게임실행 미확인.'}
    for r in manifest['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:
            r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report = {'references':16,'unique_images':len(updates),
              'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'items':checks}
    if revised:
        report.update({'galmuri9_sha256':hashlib.sha256(large_path.read_bytes()).hexdigest(),
                       'changed_ids':[0,18],'other_14_pixel_identical_to_v1':True})
    report_name = 'graphics_batch09_v2_checks.json' if revised else 'graphics_batch09_checks.json'
    (ROOT/'metadata'/report_name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page = '''<meta charset="utf-8"><title>예보 화면 · 작은 글씨 16개</title>
<style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:18px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style>
<h1>다음 묶음 · 예보 화면의 작은 글씨와 이름표 16개</h1>
<p>갈무리Mono7 · 원래 픽셀 크기와 간격 유지 · 원본 규격과 아이콘 보존<br>문장 조각은 원본 시작 위치, 이름표는 원본 세로 중심에 맞췄습니다. 전체 16개를 표시합니다.</p>
<a href="../../graphics-review/dashboard.html">현황판</a>'''
    if revised:
        page = page.replace('갈무리Mono7 · 원래', '셀0·18: 갈무리9 10px / 나머지14개: 갈무리Mono7 · 원래')
    for c in checks:
        stem = c['key'].replace('/','-'); w,h = c['size']
        page += f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{c["font"]} {c["font_px"]}px</p>'
        for z in [1,4]:
            page += f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:
                page += f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page += '</div>'
        page += '</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    # Compact QA sheet; the full window gets a separate native/zoom comparison.
    sheet = Image.new('RGB',(900,800),'#dadcd5'); d = ImageDraw.Draw(sheet)
    for i,c in enumerate(checks[1:]):
        ox=(i%3)*300; oy=(i//3)*160; stem=c['key'].replace('/','-')
        d.text((ox+4,oy+3),c['key'],fill='black')
        for j,suffix in enumerate(['original','korean']):
            im=Image.open(OUT/f'{stem}-{suffix}.png').convert('RGBA')
            z=2 if im.width>56 else 3
            im=im.resize((im.width*z,im.height*z),Image.Resampling.NEAREST)
            sheet.paste(im,(ox+4+(j*145 if im.height>48 else 0),oy+20+(j*45 if im.height<=48 else 0)),im)
    sheet.save(OUT/'overview.png')
    print('16 assets rendered; original sizes, native font advances and protected artwork verified')


if __name__ == '__main__':
    main()
