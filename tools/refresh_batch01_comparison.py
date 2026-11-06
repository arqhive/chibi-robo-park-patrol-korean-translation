"""Refresh the existing side-by-side board from the canonical asset manifest."""
import html
import json
import os
import re
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
PAGE=ROOT/'work/graphics-draft/batch01-v2/index.html'


def main():
    manifest=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
    rows={g['key'].replace('/','-'):g for g in manifest['graphics'] if g['edition']=='jp'}
    page=PAGE.read_text(encoding='utf-8')
    def section(match):
        block=match.group(0);row=rows.get(match.group(1))
        if not row:return block
        loc=row.get('localization',{})
        for labels,field,label in [('수정 결과|최신 수정 결과','output','최신 수정 결과'),('글자 지운 뒤','erased','글자 지운 뒤')]:
            selected=loc.get('preview') or loc.get('output') if field=='output' else loc.get(field)
            if not selected:continue
            target=ROOT/selected;assert target.is_file(),target
            link=html.escape(os.path.relpath(target,PAGE.parent).replace(chr(92),'/'),quote=True)
            def replace_image(m):
                old=PAGE.parent/html.unescape(m[3])
                with Image.open(old) as im:old_width=im.width
                with Image.open(target) as im:w,h=im.size
                attrs=m[4]
                width=re.search(r'width="(\d+)"',attrs)
                zoom=int(width[1])/old_width if width else 1
                attrs=re.sub(r'width="\d+"',f'width="{round(w*zoom)}"',attrs)
                attrs=re.sub(r'height="\d+"',f'height="{round(h*zoom)}"',attrs)
                return m[1]+label+m[2]+link+attrs
            block=re.sub(r'(<div>)(?:'+labels+r')(<br><img src=")([^"]+)("[^>]*>)',replace_image,block)
        block=re.sub(r'<p data-preview-note="true">.*?</p>','',block)
        if loc.get('requires_resource_width_expansion'):
            note='<p data-preview-note="true">갈무리9 10px · 비어 있음: 원본 32px → 필요 폭 41px. 원본 시작점 유지, 압축 없는 미리보기이며 리소스 폭 확장이 필요합니다.</p>'
            block=block.replace('</h2>','</h2>'+note,1)
        return block
    page=re.sub(r'<section id="([^"]+)">.*?</section>',section,page,flags=re.S)
    page=re.sub(r'<title>.*?</title>','<title>첫 묶음 최신 수정 비교</title>',page,count=1)
    page=re.sub(r'<h1>.*?</h1>','<h1>첫 묶음 · 최신 수정 비교</h1>',page,count=1)
    for src in re.findall(r'<img[^>]+src="([^"]+)"',page):
        assert (PAGE.parent/html.unescape(src)).is_file(),src
    PAGE.write_text(page,encoding='utf-8')
    print('Updated current output and erased-background links; all images exist.')


if __name__=='__main__':main()
