"""Read-only JP code/resource follow-up. Does not build or run a game ROM."""
import hashlib
import html
import json
import re
import struct
from collections import defaultdict

from inspect_roms import ROOT, INPUTS, save
from trace_stage4_code import Audit, BASE

OUT = ROOT / 'work/stage4-code'


def load(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


def immediate_argument(a, call, register):
    """Conservative local candidate: stop at control transfer or first write.

    This is not CFG reachability. Only a literal movs in the straight-line
    suffix qualifies, and all other cases remain unresolved.
    """
    for p in range(call - 2, max(0, call - 64), -2):
        w = int.from_bytes(a.b[p:p+2], 'little')
        if w & 0xf800 == 0xf800:
            break
        ins = next(a.md.disasm(a.b[p:p+2], BASE+p), None)
        if ins is None or ins.mnemonic.startswith('b') or ins.mnemonic in ['pop', 'push']:
            break
        if ins.op_str.startswith(register+',') and ins.mnemonic not in ['str', 'strb', 'strh', 'cmp', 'tst']:
            if ins.mnemonic == 'movs' and ins.op_str.startswith(register+', #'):
                return int(ins.op_str.split('#')[1], 0)
            break
    return None


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = Audit()
    inv = {r['path']: r for r in load('metadata/inventory_jp.json')['files']}
    source = load('work/stage4-followup/technical-findings.json')
    materials = defaultdict(list)
    for row in source['materials']:
        if row['edition'] == 'jp':
            materials[row['file']].append(row)
    external = {name for name, rows in materials.items()
                if any(r['texture_binding']['status'].startswith('external') for r in rows)}
    assert len(external) == 158

    # FieldDataPark vtable: load method, then per-cell model selector.
    assert a.word(0x1386e4+8) == BASE+0xdaa61
    assert a.word(0x1386e4+12) == BASE+0xdaaed
    assert a.word(0xdac94) == BASE+0x138734
    assert 0xdabc0 in a.calls[0xda874]
    assert 0xda8b0 in a.calls[0xe996c]
    assert a.text(a.word(0xda91c)) == '.nsbmd'
    catalog = [a.text(a.word(0x138734+i*4))+'.nsbmd' for i in range(153)]
    assert len(set(catalog)) == 153 and set(catalog) <= set(inv)
    bindings = {}
    for i, name in enumerate(catalog):
        if name in external:
            bindings[name] = dict(file=name, bank='FldTexBank.nsbtx',
                                  route='FieldDataPark indexed lazy loader',
                                  table_entry=0x138734+i*4,
                                  caller=0xdabc0, binding_call=0xda8b0)
    assert len(bindings) == 152
    # Common loader consumes table slots 1/2 and 5/6; both loops use this+0xc.
    for table, bank in [(0x114d5c, 'FldTexBank.nsbtx'), (0x114d8c, 'FldTexEditBank.nsbtx')]:
        assert a.text(a.word(table)) == bank
        for slot in [1, 2, 5, 6]:
            name = a.text(a.word(table+slot*4))
            if name:
                assert name in external and name not in bindings
                bindings[name] = dict(file=name, bank=bank, route='common resource-table loader',
                                      table_entry=table+slot*4,
                                      binding_call=0x8fc86 if slot < 3 else 0x8fd28)
    assert set(external)-set(bindings) == {'Fld3x3.nsbmd'}
    checked_pairs = 0
    for name, binding in bindings.items():
        for row in materials[name]:
            for kind in ['texture', 'palette']:
                if row[kind] is not None:
                    assert any(c['file'] == binding['bank'] for c in row[kind+'_binding']['candidates']), (name, kind, row[kind])
                    checked_pairs += 1
        binding['status'] = 'conditional_code_path_and_material_names_verified'
        binding['runtime_verified'] = False

    event_sites = []
    for target, register in [(0xa4288, 'r1'), (0x75f40, 'r0')]:
        for call in a.calls[target]:
            event_sites.append(dict(call=call, target=target, register=register,
                                    immediate_event_candidate=immediate_argument(a, call, register)))
    known = [r for r in event_sites if r['immediate_event_candidate'] is not None]
    assert len(event_sites) == 73 and len(known) == 60
    assert not {117, 118, 140} & {r['immediate_event_candidate'] for r in known}
    # A previous 0x76 numeric match belongs to a model/effect routine, not this queue.
    assert 0x5064a in a.calls[0x77c50] and 0x5064a not in a.calls[0x75f40]
    event_evidence = []
    for row in event_sites:
        p = row['call']-24
        if int.from_bytes(a.b[p:p+2], 'little') & 0xf800 == 0xf800:
            p += 2
        event_evidence.append(a.disasm(p, row['call']+4))
    (OUT/'event-setter-sites.txt').write_text('\n\n'.join(event_evidence), encoding='utf-8')

    # Resolve every direct caller of the dynamic single-background wrappers.
    assert a.calls[0x6bd04] == [0x6a90c]
    intro = [a.text(a.word(0x10b578+i*4)) for i in range(4)]
    assert intro == ['Blue_White', 'BGWhite', 'LogoBandai', 'LogoSkip']
    assert a.calls[0x6f1a0] == [0xb710, 0x69dc0, 0x6ff36, 0x73bf0]
    for call in [0xb710, 0x69dc0, 0x73bf0]:
        assert immediate_argument(a, call, 'r0') == 0
    assert a.text(a.word(0x6f234)) == 'NewPCEditBGA'
    assert a.text(a.word(0x6ff74)) == 'StatusMenuBG'
    assert a.calls[0xb9b84] == [0xb9a04, 0xb9a18, 0xb9a2c]
    logos = [a.text(a.word(p)) for p in [0xb9a94, 0xb9a98, 0xb9a9c]]
    assert logos == ['Blue_White', 'LogoBandai', 'LogoSkip']
    background_routes = [
        dict(wrapper=0x6bd04, call=0x6a90c, source_table=0x10b578, names=intro,
             note='Two pairs; caller loop runs twice.'),
        dict(wrapper=0x6f1a0, calls=[0xb710, 0x69dc0, 0x73bf0], names=['NewPCEditBGA'],
             note='Null argument selects the default name.'),
        dict(wrapper=0x6f1a0, call=0x6ff36, names=['StatusMenuBG']),
        dict(wrapper=0xb9b84, calls=[0xb9a04, 0xb9a18, 0xb9a2c], names=logos),
    ]

    # Full-ROM literal scan: file-name-table matches are not code references.
    rom = (ROOT/INPUTS['jp']).read_bytes()
    original = next(r for r in load('metadata/originals.json') if r['edition'] == 'jp')
    assert hashlib.sha256(rom).hexdigest() == original['sha256']
    fnt, fnt_size = struct.unpack_from('<2I', rom, 0x40)
    overlay_fields = struct.unpack_from('<4I', rom, 0x50)
    assert overlay_fields == (0, 0, 0, 0)
    names = ['BGBalloon', 'BGDesktop', 'BGMPWindow', 'EditBGA', 'EditBGB', 'PCBG', 'Red_White', 'Fld3x3']
    literal_scans = []
    for name in names:
        # Either full extension or bare basename, but never a longer identifier.
        pattern = rb'(?<![A-Za-z0-9_])'+name.encode()+rb'(?![A-Za-z0-9_])(?:\.[A-Za-z0-9]+)?'
        hits = [dict(rom_offset=m.start(), text=m.group().decode('ascii'),
                     in_filename_table=fnt <= m.start() < fnt+fnt_size)
                for m in re.finditer(pattern, rom)]
        assert hits and all(r['in_filename_table'] for r in hits), (name, hits)
        literal_scans.append(dict(name=name, hits=hits, non_fnt_literal_hits=0,
                                  status='no_literal_reference_found_not_proof_of_unused'))

    snippets = [(0xdaa60,0xdaab2), (0xdabb0,0xdabc4), (0xda874,0xda91a),
                (0x8fc58,0x8fc8a), (0x8fcf8,0x8fd2c), (0x6a900,0x6a932),
                (0x6f1a0,0x6f1de), (0x6ff2e,0x6ff3a), (0xa4288,0xa4298)]
    for start, end in snippets:
        (OUT/f'route-{start:06x}.txt').write_text(a.disasm(start,end), encoding='utf-8')

    result = dict(
        source_edition='JP AJBJ Rev 0', source_sha256=original['sha256'],
        offset_basis='ARM9 file offsets unless explicitly marked rom_offset',
        external_model_count=158, code_linked_models=len(bindings),
        material_texture_palette_pairs_checked=checked_pairs,
        individual_model_table=dict(offset=0x138734, entries=153, external_entries=152,
                                    other_entry='FldTest.nsbmd'),
        model_bindings=list(bindings.values()), unresolved_model_files=['Fld3x3.nsbmd'],
        event_call_sites=event_sites, event_constant_sites=len(known),
        event_dynamic_or_unresolved_sites=len(event_sites)-len(known),
        event_ids_without_immediate_requests_in_examined_sites=[117,118,140],
        rejected_numeric_match=dict(call=0x5064a, target=0x77c50,
                                    reason='Same numeric constant is not an event-queue call.'),
        dynamic_background_routes=background_routes, name_literal_scans=literal_scans,
        overlay_table_fields=list(overlay_fields), runtime_verified=False,
        limits=['Bank bindings are conditional code paths, not proof that every catalog entry is used.',
                'Dynamic event IDs, indirect calls, arithmetic names and compressed content can escape literal searches.',
                'No game play or full control-flow reachability was performed.'],
    )
    save(ROOT/'metadata/stage4_deep_connections.json', result)
    master = load('metadata/extraction_manifest.json')
    master['code_connections'] = {
        'evidence': 'metadata/stage4_deep_connections.json',
        'jp_external_models': 158, 'jp_conditional_code_linked_models': 157,
        'jp_unresolved_models': ['Fld3x3.nsbmd'], 'runtime_verified': False}
    for issue in master['failures_and_unresolved']:
        if issue.get('edition') == 'jp' and issue.get('stage') == 'model_texture_binding' and issue['file'] in bindings:
            issue['followup_status'] = 'conditional_code_bank_binding_verified_runtime_unverified'
            issue['code_bank_binding'] = bindings[issue['file']]
    save(ROOT/'metadata/extraction_manifest.json', master)
    model_rows = ''.join(f'<tr><td>{html.escape(r["file"])}</td><td>{r["bank"]}</td><td>{html.escape(r["route"])}</td></tr>' for r in bindings.values())
    body = '''<!doctype html><html lang="ko"><meta charset="utf-8"><title>피워라 치비로보! · 코드 연결 추가 조사</title>
<style>body{font:17px/1.65 sans-serif;max-width:1100px;margin:40px auto;padding:0 24px;background:#f7f7f3;color:#222}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #ccc;padding:9px;text-align:left}h1{font-size:28px}code{background:#eee}a{color:#195bab}</style>
<h1>피워라 치비로보! · 코드·자원 연결 추가 조사</h1>
<p>일본판 AJBJ Rev 0의 정적 조사입니다. 게임을 실행해 확인한 결과와 구분합니다. 4단계 범위는 아직 승인 전입니다.</p>
<table><tr><th>항목</th><th>확인 결과</th><th>남은 제한</th></tr>
<tr><td>외부 텍스처 모델 158개</td><td>152개는 일반 필드의 이름표→개별 로더→일반 뱅크 연결. 5개는 일반·편집 자원표→공통 로더 연결. 총 157개.</td><td>Fld3x3 1개는 호출 경로 미확인. 확인한 모델도 실제 등장 시점과 모든 상태를 검증한 것은 아님.</td></tr>
<tr><td>추가 문자열의 이벤트 진입</td><td>이벤트 등록 함수와 래퍼의 직접 호출 73곳을 조사. 60곳은 즉시값 ID, 13곳은 동적 값 또는 미해결. 상품 없음 안내는 ID 101 요청을 확인.</td><td>저장 117·불러오기 118·여섯 화면 선택 140은 이 60곳에서 즉시값 요청을 찾지 못함. 동적 경로가 있으므로 개발용·미사용 확정 불가.</td></tr>
<tr><td>동적 배경 로더</td><td>직접 호출 인자를 추적해 부팅 로고(Blue_White·LogoBandai·LogoSkip), BGWhite, NewPCEditBGA, StatusMenuBG 확인.</td><td>미연결 배경 이름의 호출 근거로 대체하지 않음.</td></tr>
<tr><td>미연결 배경 7개</td><td>전체 원본에서 완전한 이름을 검색하니 파일명 목록에서만 발견. ARM9·ARM7 오버레이 테이블은 비어 있음.</td><td>이름 조립·파일 번호·압축 등은 이 검색으로 배제할 수 없음. BGBalloon, BGDesktop, BGMPWindow, EditBGA/B, PCBG, Red_White 보류.</td></tr>
<tr><td>작은 그림 22개</td><td>기존 판독 보류 유지.</td><td>임의로 문구를 만들지 않음.</td></tr></table>
<p>원본 해시와 모델 재질의 텍스처·팔레트 이름을 확인했습니다. 번역 주입과 ROM 빌드는 하지 않았습니다.</p>
<details><summary>157개 모델별 연결 근거</summary><table><tr><th>모델</th><th>뱅크</th><th>경로</th></tr>'''+model_rows+'''</table></details>
<p><a href="../stage4-followup/index.html">그림·문자열 추가 조사</a> · <a href="../../docs/stage4-code-connections.md">상세 코드 근거</a></p></html>'''
    (OUT/'index.html').write_text(body, encoding='utf-8')
    page = ROOT/'work/stage4-followup/index.html'
    content = page.read_text(encoding='utf-8')
    marker = '<!-- deep-connections -->'
    if marker not in content:
        content = content.replace('<h1>', marker+'<p><a href="../stage4-code/index.html">최신 코드·자원 연결 조사 보기</a> — 외부 모델 158개 중 157개의 조건부 뱅크 연결을 확인했습니다. 아래 표는 앞선 조사 시점의 결과입니다.</p><h1>', 1)
        page.write_text(content, encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['code_linked_models','material_texture_palette_pairs_checked','event_constant_sites','event_dynamic_or_unresolved_sites','runtime_verified']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
