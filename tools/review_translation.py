"""Validate translation structure and render a source/Korean review; no ROM writes."""
import collections
import hashlib
import html
import json
import re
import unicodedata
from pathlib import Path

from translate_batch import FORMAT

ROOT=Path(__file__).resolve().parents[1]

def read(name):return json.loads((ROOT/name).read_text(encoding='utf-8'))
def save(name,data):
    p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def text(parts):return ''.join(p for p in parts if isinstance(p,str))
def controls(parts):return [p for p in parts if isinstance(p,dict)]

def main():
    source=read('translations/jp-source.json');rows=read('translations/ko.json')
    extra_source=read('translations/extra-source.json');extra=read('translations/extra-ko.json')
    glossary=read('translations/glossary.json')
    assert glossary['status']=='approved_for_translation'
    assert hashlib.sha256((ROOT/'translations/jp-source.json').read_bytes()).hexdigest()==glossary['source_sha256']
    assert hashlib.sha256((ROOT/'translations/extra-source.json').read_bytes()).hexdigest()==glossary['extra_source_sha256']
    assert len(rows)==len(source)==2349 and len(extra)==len(extra_source)==19
    failures=[];number_review=[];term_review=[];variable_rows=[];empty_segments=[]
    keys=[];allrows=[]
    for sources,translations in [(source,rows),(extra_source,extra)]:
        for src,row in zip(sources,translations):
            loc=dict(file=row['file'],index=row.get('index',f'0x{row.get("offset",0):x}'))
            key=(loc['file'],loc['index']);keys.append(key)
            if any(src[k]!=row[k] for k in src if k not in ('translation_parts','status')):
                failures.append(dict(**loc,error='source_metadata_changed'))
            target=row['translation_parts']
            if target is None:
                failures.append(dict(**loc,error='translation_missing'));continue
            if controls(src['source_parts'])!=controls(target):failures.append(dict(**loc,error='control_tokens_changed'))
            if [type(p).__name__ for p in src['source_parts']]!=[type(p).__name__ for p in target]:
                failures.append(dict(**loc,error='segment_structure_changed'))
            jp,ko=text(src['source_parts']),text(target)
            if FORMAT.findall(jp)!=FORMAT.findall(ko):failures.append(dict(**loc,error='format_tokens_changed'))
            if jp.count('\n')!=ko.count('\n'):failures.append(dict(**loc,error='line_count_changed'))
            retained=row['status'].startswith('retained_')
            if retained and target!=src['source_parts']:failures.append(dict(**loc,error='retained_row_changed'))
            if not retained and re.search('[\u3040-\u30ff\u4e00-\u9fff]',ko):failures.append(dict(**loc,error='untranslated_japanese'))
            if not retained and re.findall(r'\d+',unicodedata.normalize('NFKC',jp))!=re.findall(r'\d+',ko):
                number_review.append(dict(**loc,source=jp,korean=ko))
            if not retained:
                for entry in glossary['entries']:
                    j,k=entry['japanese'],entry['korean_proposal']
                    # Long compound names mask their shorter component terms.
                    longer=any(j in e['japanese'] and j!=e['japanese'] and e['japanese'] in jp for e in glossary['entries'])
                    if j in jp and k not in ko and not longer:
                        term_review.append(dict(**loc,japanese_term=j,korean_term=k,source=jp,korean=ko))
            if '%s' in ko:variable_rows.append(loc)
            if any(isinstance(p,str) and not p for p in target):empty_segments.append(loc)
            allrows.append(dict(**loc,source=jp,korean=ko,status=row['status']))
    assert len(set(keys))==len(keys)
    report=dict(schema=1,bmg_rows=len(rows),extra_rows=len(extra),
        bmg_status_counts=dict(collections.Counter(r['status'] for r in rows)),
        extra_status_counts=dict(collections.Counter(r['status'] for r in extra)),
        hard_failures=failures,number_wording_review=number_review,
        glossary_context_review=term_review,string_variable_rows=variable_rows,
        empty_string_segment_rows=empty_segments,
        unique_hangul_syllables=len({c for r in allrows for c in r['korean'] if '\uac00'<=c<='\ud7a3'}),
        limitations=['Structural checks do not establish semantic equivalence.',
            'Pixel widths and full Korean font expansion are not validated.',
            'Dynamic string particles, speaker bindings and timing/color effects require follow-up.',
            'ARM9 translations are separate candidates; relocation/injection not performed.'],
        source_hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['translations/jp-source.json','translations/us-source.json','translations/extra-source.json']})
    save('metadata/translation_checks.json',report)
    e=lambda s:html.escape(str(s))
    labels={'translated_draft':'번역 초안','translated_draft_runtime_use_unverified':'추가 문자열 초안 · 실행 미확인',
        'retained_empty_or_control':'빈 항목·제어 전용 보존','retained_original_english':'영문 크레디트 보존','retained_technical_test':'기술 시험 문자열 보존'}
    trs=''.join(f'<tr data-file="{e(r["file"])}" data-status="{e(r["status"])}"><td>{e(r["file"])}<br>#{e(r["index"])}</td><td>{e(r["source"])}</td><td>{e(r["korean"])}</td><td>{labels[r["status"]]}</td></tr>' for r in allrows)
    notes=read('translations/context-notes.json')
    notehtml=''.join(f'<li><b>{e(n["topic"])}</b> — {e(n["decision"])} <small>{e(n["references"])}</small></li>' for n in notes['items'])
    options=''.join(f'<option>{e(f)}</option>' for f in sorted({r['file'] for r in allrows}))
    body='''<!doctype html><html lang="ko"><meta charset="utf-8"><title>피워라 치비로보! · 본문 번역 대조</title>
<style>body{font:16px/1.6 sans-serif;margin:32px auto;max-width:1400px;padding:0 24px;background:#f7f7f3;color:#222}table{width:100%;border-collapse:collapse;background:white}td,th{border:1px solid #ccc;padding:10px;vertical-align:top;text-align:left}td:nth-child(2),td:nth-child(3){white-space:pre-wrap;width:35%}td:first-child{font-size:13px}th{position:sticky;top:66px;background:#eee}.filters{position:sticky;top:0;background:#f7f7f3;padding:12px 0;z-index:2}input,select{font:inherit;padding:7px;max-width:95%}.notice{background:#fff0c4;padding:16px}li{margin:12px 0}small{display:block;color:#555}</style>
<h1>피워라 치비로보! · 본문 번역 대조</h1>
<p class="notice">용어·말투안은 사용자 확정본을 적용했습니다. 본문은 첫 번역 초안이며, 전체 실행·화면 폭 검증 완료본이 아닙니다. 태그는 데이터에 그대로 보존했고 이 표에는 글자만 표시합니다. 이 대조표는 번역 원본 JSON에서 재생성합니다.</p>'''
    body+=f'<p>BMG {len(rows):,}항목: 번역 초안 2,290 / 빈 항목·제어 전용 32 / 영문 크레디트 19 / 기술 시험 8. ARM9 후보 19개는 별도 번역. 구조 검사 오류 {len(failures)}개.</p>'
    body+='<details><summary>문맥 판단과 후속 확인 사항</summary><ul>'+notehtml+'</ul></details>'
    body+='<div class="filters"><input id="query" placeholder="원문·번역·번호 검색"> <select id="file"><option value="">모든 파일</option>'+options+'</select> <label><input type="checkbox" id="retained">보존 항목도 표시</label> <span id="count"></span></div>'
    body+='<table><thead><tr><th>위치</th><th>일본어 원문</th><th>한국어 초안</th><th>구분</th></tr></thead><tbody>'+trs+'</tbody></table>'
    body+='''<script>const rows=[...document.querySelectorAll('tbody tr')], q=document.querySelector('#query'),f=document.querySelector('#file'),r=document.querySelector('#retained');function filter(){let count=0;for(const x of rows){const show=(!f.value||x.dataset.file===f.value)&&(!q.value||x.textContent.toLowerCase().includes(q.value.toLowerCase()))&&(r.checked||!x.dataset.status.startsWith('retained_'));x.hidden=!show;if(show)count++;}document.querySelector('#count').textContent=count+'항목';}for(const x of [q,f,r])x.addEventListener('input',filter);filter();</script></html>'''
    p=ROOT/'work/translation-review/index.html';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body,encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['bmg_rows','extra_rows','bmg_status_counts','unique_hangul_syllables']},ensure_ascii=False))
    print(f'Structural failures: {len(failures)}; number wording flags: {len(number_review)}; glossary context flags: {len(term_review)}; string-variable rows: {len(variable_rows)}; empty string segments: {len(empty_segments)}')
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
