"""Apply recorded contact-sheet observations, audit coverage, and present scope.

These classifications are human-readable analyst observations, not OCR or runtime
proof. Review IDs refer to this exact extraction's deduplicated JP PNG ordering.
The manifest remains the only authoritative per-asset status list.
"""
from collections import Counter, defaultdict
import html
import json
from pathlib import Path
import struct

import ndspy.soundArchive
from PIL import Image
from inspect_roms import ROOT, save, sha

OUT=ROOT/'work/stage4'


def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def span(spec):
    result=set()
    for part in spec.split():
        if '-' in part:
            a,b=map(int,part.split('-'));result.update(range(a,b+1))
        else:result.add(int(part))
    return result


JAPANESE_UI=span('''42 43 59 60 77 78 120 121 126 127 136
235-237 240-243 327 328 331-375 378-388 391-470
590-633 635-639 643-650 655-690 741 791-798 801-808 814-840 842-855
869 883 895 896 903 904 909 910 913-918 950-956 959 966-969 971-976
988-991 996-1001 1006 1007 1061 1062 1064 1065 1097-1102 1110 1129
1136-1186 1188-1196 1201-1205 1278-1280 1287 1299-1306 1309 1310 1312
1356-1359 1370-1373 1395-1401 1418-1421 1423-1426 1431 1432 1460-1467 1469-1471''')
JAPANESE_UI.update(range(743,790,2))
JAPANESE_UI.update(range(1017,1038,2))
UNCLEAR_UI=span('160-163 168 169 174 175 178-181 870-881 1130-1134 1269')
ENGLISH_UI=span('27 182 183 305 315 569 570 907 908 1012 1014 1038 1125 1126 1187 1297 1325 1428-1430')
UNCLEAR_MODELS=span('154 318 327 366 367 449 558-560 708 711 793-796 805 806 809')
ENGLISH_MODELS=span('171 172 177 185 186 238 253 256 330 550 553 673-678 807 808 875 876 879 1015 1016')
REVIEW_ORDER_DIGESTS={
    'ui':'83c006026bbf33d05ba0dd96e1e7138ff12151656513a16541ccf05aea16fbc7',
    'models':'17919e421b7cab20d89f35c8b9cf1269a25fb483a3e21698f5131b1eccbd9cee',
    'raw':'200fc4161f80fd76d6eb7c1ee5c0a0617899ae07364836c4ae71007dd299ff31',
}


def main():
    manifest=load('metadata/extraction_manifest.json')
    indices={c:load(f'work/stage4/{c}-review-index.json') for c in ['ui','models','raw']}
    assert {c:len(v) for c,v in indices.items()}=={'ui':1473,'models':1050,'raw':8},'Re-review changed extraction ordering'
    for category,rows in indices.items():
        assert sha('\n'.join(r['key']+' '+r['pixel_sha256'] for r in rows).encode())==REVIEW_ORDER_DIGESTS[category], 'Source images/order changed; visual re-review required'
    assert indices['ui'][1432]['key']=='TitleLogo/cell/1'
    assert 'dan_ball03' in indices['models'][154]['key']
    observations={}
    for category,rows in indices.items():
        for i,r in enumerate(rows):
            status='no_japanese_identified_in_contact_review'
            note='Native-size source PNG available. Contact-sheet review is not runtime or exhaustive OCR proof.'
            if category=='ui':
                if i in JAPANESE_UI:status='japanese_graphic_candidate'
                elif i in UNCLEAR_UI:status='text_legibility_pending'
                elif i in ENGLISH_UI:status='original_english_preserve'
            elif category=='models':
                if i in UNCLEAR_MODELS:status='text_legibility_pending'
                elif i in ENGLISH_MODELS:status='original_english_preserve'
                note+=' Model material/palette bindings are not all verified.'
            elif category=='raw':
                status='linear_layout_visually_coherent_no_japanese_seen' if i%2 else 'tiled_layout_visually_incoherent'
                note='256x128 is an inference from file size and visible scene; runtime binding unverified.'
            observations[r['pixel_sha256']]={'classification':status,'review_id':r['review_id'],'method':'contact_sheet_visual_review','note':note}
    for r in manifest['graphics']:
        if r['edition']=='jp':
            r['review']=observations[r['pixel_sha256']]
            r['status']=r['review']['classification']

    # Inventory every special resource, explicitly listing unpaired maps/palettes.
    coverage={};audio=[]
    for edition in ['jp','us']:
        inventory=load(f'metadata/inventory_{edition}.json')['files']
        files={r['path']:r for r in inventory}
        refs={p for r in manifest['graphics'] if r['edition']==edition for p in r['source_files']}
        coverage[edition]={
            'nitrofs_files':len(files),
            'extensions':dict(sorted(Counter(Path(n).suffix.lower() for n in files).items())),
            'screen_maps_without_confirmed_assembled_png':[n for n in files if n.endswith('.NSCR') and n not in refs],
            'raw_palettes_without_confirmed_texture_pair':[n for n in files if n.endswith('.ntfp') and n not in refs],
            'animation_scope':'All NCER cells and embedded TEX0 textures decoded; NANR/NSB animation timelines, palette swaps and final scene compositing not reconstructed.',
            'video_scope':'No standalone movie file extension identified in NitroFS. Embedded/custom animation or video absence is not proven.',
            'script_scope':'154 standalone HMB and all 421 NARC members scanned for NUL-terminated cp932/UTF16 Japanese candidates. HMB/F1x1 instruction semantics and text references not fully decoded.',
        }
        for name,r in files.items():
            if not name.endswith('.sdat'):continue
            s=ndspy.soundArchive.SDAT((ROOT/f'work/extracted/{edition}'/r['disk_file']).read_bytes())
            audio.append({'edition':edition,'file':name,
                          'sequences':len(s.sequences),'sequence_archives':len(s.sequenceArchives),
                          'banks':len(s.banks),'wave_archives':len(s.waveArchives),
                          'streams':[n for n,v in s.streams],
                          'status':'container_inventory_only_listening_and_lyrics_unverified'})
    manifest['coverage']=coverage;manifest['audio']=audio
    # All 47 scanner candidates inspected; 19 plausible ARM9 Japanese strings.
    extra=load('work/stage4/extra-string-candidates.json')
    assert len(extra)==47 and extra[7]['text']=='ながれぼしベンチ\nアソビカタ'
    arm9=(ROOT/'work/extracted/jp/arm9.bin').read_bytes()
    for i,r in enumerate(extra):
        plausible=7<=i<=25
        r['status']='japanese_string_runtime_or_debug_use_unresolved' if plausible else 'rejected_binary_or_encoding_false_positive'
        if plausible:
            r['original_byte_length']=len(r['text'].encode(r['encoding']))
            needle=struct.pack('<I',0x02000000+r['offset'])
            r['exact_address_literals_arm9']=[p for p in range(0,len(arm9)-3,4) if arm9[p:p+4]==needle]
            r['note']='Address literals are clues, not proof of visible runtime use. Do not inject without reference/capacity analysis.'
    manifest['extra_strings']=extra
    manifest['supplemental_audit_needs_refresh']=False

    # Validate each unique output PNG and source member, including claimed sizes/hashes.
    checked=set()
    for r in manifest['graphics']:
        if r['path'] in checked:continue
        im=Image.open(ROOT/r['path']).convert('RGBA')
        assert im.size==(r['width'],r['height'])
        assert sha(struct.pack('<II',*im.size)+im.tobytes())==r['pixel_sha256']
        checked.add(r['path'])
    for r in manifest['archives']:
        raw=(ROOT/r['path']).read_bytes()
        assert len(raw)==r['size'] and sha(raw)==r['sha256']
    # Every NCGR is represented, including a visibly unassembled fallback.
    for edition in ['jp','us']:
        inv=load(f'metadata/inventory_{edition}.json')['files']
        refs={p for r in manifest['graphics'] if r['edition']==edition for p in r['source_files']}
        assert all(r['path'] in refs for r in inv if r['path'].lower().endswith('.ncgr'))
    manifest['validation']={'png_hash_and_dimensions_verified':len(checked),'archive_member_hashes_verified':len(manifest['archives']),
                            'all_188_ncgr_per_edition_accounted_for':True,'visual_review_unique_jp':{c:len(v) for c,v in indices.items()},
                            'visual_review_limit':'All contact sheets reviewed; selected small labels enlarged. Unreadable labels are pending, not declared absent.'}
    save(ROOT/'metadata/extraction_manifest.json',manifest)
    make_report(manifest,indices)
    print(json.dumps(manifest['review_summary'],ensure_ascii=False,indent=2))
    # Preserve the completed follow-up when regenerating the initial review.
    if (ROOT/'metadata/stage4_followup.json').exists():
        from investigate_stage4 import main as investigate
        investigate()


STYLE='''<style>body{font:16px "Malgun Gothic",sans-serif;background:#f3f5f8;color:#172033;margin:32px auto;max-width:1150px;line-height:1.8;padding:0 24px}h1{font-size:30px}h2{margin-top:32px}table{border-collapse:collapse;width:100%;background:white}td,th{border:1px solid #ccd3dc;padding:10px;text-align:left;vertical-align:top}article,details,.note{background:white;border:1px solid #d3dae5;border-radius:8px;padding:16px;margin:12px 0}img{image-rendering:pixelated;max-width:100%;background:repeating-conic-gradient(#ddd 0% 25%,#aaa 0% 50%) 0/16px 16px;margin:8px;vertical-align:top}code{overflow-wrap:anywhere}a{color:#174faf}.pending{color:#9a4b00}pre{white-space:pre-wrap;font:inherit}input{width:95%;padding:12px;font:inherit}</style>'''


def page(title,body,name):
    (OUT/name).write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>'+html.escape(title)+'</title>'+STYLE+'<h1>'+html.escape(title)+'</h1>'+body+'</html>',encoding='utf-8')


def make_report(m,indices):
    jp=[r for r in m['graphics'] if r['edition']=='jp']
    groups=defaultdict(list)
    for r in jp:
        if r['status']=='japanese_graphic_candidate':groups[r['source_files'][0]].append(r)
    unique=len({r['pixel_sha256'] for rows in groups.values() for r in rows})
    pending=[r for cat in ['ui','models'] for r in indices[cat] if (cat=='ui' and int(r['review_id'].split('-')[1]) in UNCLEAR_UI) or (cat=='models' and int(r['review_id'].split('-')[1]) in UNCLEAR_MODELS)]
    summary={'japanese_graphic_families':len(groups),'japanese_graphic_unique_png':unique,
             'japanese_graphic_asset_references':sum(map(len,groups.values())),
             'small_or_unclear_label_unique_png':len(pending),'plausible_extra_japanese_strings':19,'scanner_false_positives':28}
    m['review_summary']=summary;save(ROOT/'metadata/extraction_manifest.json',m)
    cards=[]
    for name,rows in sorted(groups.items()):
        seen=set();pics=[]
        for r in rows:
            if r['pixel_sha256'] in seen:continue
            seen.add(r['pixel_sha256'])
            pics.append(f'<span title="{html.escape(r["key"])}"><img loading="lazy" src="png/{Path(r["path"]).name}" alt="{html.escape(r["key"])}"></span>')
        cards.append(f'<details><summary><b>{html.escape(name)}</b> · {len(seen)}개 도안 / {len(rows)}개 참조</summary>'+''.join(pics)+'</details>')
    page('일본어 그림 후보',f'<p><a href="index.html">조사 요약</a> · 원본 크기 PNG입니다. 후보 확정과 번역·디자인 승인은 별개입니다. 같은 그림의 복사본은 함께 관리합니다.</p>'+''.join(cards),'japanese-graphics.html')
    page('작은 글씨·그림 보류 목록','<p>일본어인지 확정하지 못한 작은 라벨, 포장지, 조각입니다. 원래 영어라면 유지합니다. 모델의 팔레트 연결도 일부 미확정입니다.</p>'+''.join(f'<article><b>{r["review_id"]}</b> {html.escape(r["key"])}<br><img src="png/{Path(r["path"]).name}"><img style="width:{r["width"]*3}px" src="png/{Path(r["path"]).name}"></article>' for r in pending),'pending.html')
    texts=load('translations/jp-source.json')
    page('일본판 원문 전체','<p>빈 항목·개발용 후보·원래 영문도 포함한 전체 BMG 목록입니다. 화자와 실제 표시 여부는 아직 일부 미확인입니다. 아래 표시에서 태그는 생략했지만 JSON에는 원형을 보존했습니다.</p><input id="q" placeholder="원문 또는 파일명 검색"><div id="entries">'+''.join(f'<article><b>{html.escape(r["file"])} #{r["index"]}</b><pre>{html.escape(r["source_text"])}</pre></article>' for r in texts)+'</div><script>q.oninput=()=>{for(const e of document.querySelectorAll("article"))e.hidden=!e.textContent.toLowerCase().includes(q.value.toLowerCase())}</script>','text.html')
    extras=[r for r in m['extra_strings'] if r['status'].startswith('japanese_string')]
    page('대사 파일 밖의 일본어候補'.replace('候補',' 후보'),'<p>ARM9에서 찾은 19개입니다. 개발 메뉴가 섞여 있으며 실제 노출·재배치 안전성은 확인하지 않았습니다. 본문 번역과 분리해 후속 조사합니다.</p><table><tr><th>ARM9 오프셋</th><th>원문</th><th>주소 상수 발견 수</th></tr>'+''.join(f'<tr><td>0x{r["offset"]:x}</td><td><pre>{html.escape(r["text"])}</pre></td><td>{len(r["exact_address_literals_arm9"])}</td></tr>' for r in extras)+'</table>','extra-text.html')
    maps=m['coverage']['jp']['screen_maps_without_confirmed_assembled_png']
    body=f'''<p>일본판 AJBJ Rev 0 기준 · 북미판 AJBE 대조 · 4단계 조사 범위 확인용</p>
<table><tr><th>분야</th><th>추출·확인 결과</th><th>남은 확인</th></tr>
<tr><td>본문</td><td><a href="text.html">BMG 5개 · 2,349항목</a> (비어 있지 않은 항목 2,317개)<br>북미판 2,387항목 · 총 10개 BMG를 JSON에서 재생성해 원본과 바이트 일치</td><td>화자·창 연결, 동적 변수, 개발용 여부</td></tr>
<tr><td>글자 그림</td><td><a href="japanese-graphics.html">일본어 후보 {len(groups)}묶음 · 중복 제외 {unique}개 도안</a><br>타이틀의 시작 안내는 TitleLogo 셀 1에서 확인</td><td>번역·규칙·각 장 승인 전. 원래 영어는 유지</td></tr>
<tr><td>작은 글씨</td><td><a href="pending.html">판독 보류 {len(pending)}개 도안</a></td><td>일본어인지 미확정. 포장지·모델 라벨·그림 조각 등</td></tr>
<tr><td>추가 문자열</td><td><a href="extra-text.html">ARM9 일본어 후보 19개</a><br>47개 탐지 결과 중 바이너리 오인 28개 제외</td><td>실제 표시인지 개발용인지 미확정</td></tr>
<tr><td>3D·효과</td><td>모델 604개와 텍스처 뱅크 2개 조사<br>지역별 TEX0 텍스처 1,490개를 PNG로 추출</td><td>지역별 모델 187개는 외부 텍스처 연결 필요. 일부 팔레트는 후보 전부 추출. 애니메이션·장면 합성 미재현</td></tr>
<tr><td>스크립트·컨테이너</td><td>지역별 NARC 24개 / 421멤버 추출·무변경 재조립 일치</td><td>HMB/F1x1 명령 의미, 짧은·길이 지정·압축 문자열 탐지 보장 안 됨</td></tr>
<tr><td>영상·음성</td><td>독립 영상 파일 확장자 미발견. SDAT 2개에서 오프닝·엔딩 스트림 3개 항목 확인(중복 포함)</td><td>내장·독자 영상 부재는 미증명. 음성·가사는 청취하지 않음</td></tr>
</table>
<h2>연결이 남은 자료</h2><p>배경 맵 7개: {html.escape(', '.join(maps))}. Red_White는 원본 맵의 타일 번호가 단독 타일 데이터 범위를 넘습니다. 나머지 6개는 같은 이름의 타일이 없어 연결을 보류했습니다. MasterSky01/02 팔레트도 연결 미확인입니다.</p>
<p class="pending">전체 한글 폰트 확장, 대부분 창의 실제 폭·줄 수, 실기는 아직 미확인입니다. 확인된 한글 출력은 꽃 아이콘 안내 한 장면입니다.</p>
<h2>다음 단계에서 정할 범위</h2><p>본문 2,349항목과 일본어 그림 후보 {len(groups)}묶음을 기본 조사·번역 대상으로 잡고, 추가 문자열 19개·작은 글씨 {len(pending)}개·미연결 자원은 후속 조사 목록으로 유지하는 안입니다. 개발용·원래 영문·빈 항목은 맥락을 확인해 구분합니다. 이 화면은 범위 검토안이며 번역이나 빌드를 실행한 결과가 아닙니다.</p>
<p><a href="ui.html">모든 UI 원본·북미판 대조</a> · <a href="models.html">모든 모델 텍스처</a> · <a href="raw.html">헤더 없는 텍스처 후보</a></p>
<p>목록의 단일 기준: metadata/extraction_manifest.json · 기술 근거: docs/stage4-extraction.md</p>'''
    page('피워라 치비로보! · 전수 추출 결과',body,'index.html')


if __name__=='__main__':main()
