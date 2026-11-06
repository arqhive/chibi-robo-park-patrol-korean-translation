"""Stage 3 inventory and calibrated conservative window profile. No ROM writes."""
from collections import Counter
import html
import json
from pathlib import Path

import ndspy.bmg
import numpy as np
from PIL import Image

from analyze_resources import message_repr
from check_layout import load_fonts, measure, FORMAT
from inspect_roms import ROOT, save, sha
from prepare_output_probe import TRANSLATION, SOURCE


def main():
    rows = {r['id']: r for r in json.loads((ROOT/'metadata/inventory_jp.json').read_text(encoding='utf-8'))['files']}
    fonts = load_fonts()
    metrics = {}
    for enum, f in fonts.items():
        metrics[enum] = {'file_id': f['file_id'], 'cell': f['cell'], 'line_feed': f['line_feed'],
                        'glyph_metrics': {str(code): {'index': idx, 'left': f['widths'][idx][0], 'ink_width': f['widths'][idx][1], 'advance': f['widths'][idx][2]} for code, idx in f['mapping'].items()}}
    save(ROOT/'metadata/font_metrics.json', metrics)
    records, file_summary, tagcounts = [], [], Counter()
    for fid in range(905, 910):
        data = (ROOT/f'work/extracted/jp/files/{fid:04}.bin').read_bytes()
        assert sha(data) == rows[fid]['sha256']
        bmg = ndspy.bmg.BMG(data)
        group = []
        for i, message in enumerate(bmg.messages):
            parts = message_repr(message)['parts']
            for p in parts:
                if isinstance(p, dict): tagcounts[f"{p['type']}:{p['data']}"] += 1
            scenarios = {str(e): measure(parts, fonts, e) for e in [0, 1, 2, 3]}
            record = {'file': rows[fid]['path'], 'index': i, 'parts': parts,
                      'nonempty': bool(parts), 'scenarios': scenarios,
                      'window_linked': fid == 908 and i == 2}
            records.append(record); group.append(record)
        scenario2 = [r['scenarios']['2'] for r in group]
        file_summary.append({'file': rows[fid]['path'], 'messages': len(group),
                             'nonempty': sum(r['nonempty'] for r in group),
                             'raw_line_count_max': max(m['raw_line_count'] for m in scenario2),
                             'messages_with_variables': sum(bool(m['variables']) for m in scenario2),
                             'messages_with_measurement_issues': sum(bool(m['issues']) for m in scenario2),
                             'width_max_default_normal_scenario': max(m['known_content_width_max'] for m in scenario2),
                             'width_is_window_limit': False})
    source = measure([SOURCE], fonts)
    translated = measure([TRANSLATION], load_fonts(True))
    calibration = []
    for name in ['user-flower-icon-target.png', 'v02-flower-icon-korean-confirmed.png']:
        path = ROOT/'work/output-probe/evidence'/name
        raw = np.array(Image.open(path).convert('RGB')).astype(int)
        r, g, b = (raw[:, :, i] for i in range(3))
        mask = (b > 200) & (b > r+45) & (b > g+45)
        mask[:95] = False; mask[180:] = False
        y, x = np.where(mask)
        calibration.append({'file': str(path.relative_to(ROOT)), 'sha256': sha(path.read_bytes()),
                            'blue_mask_bbox_exclusive': [int(x.min()), int(y.min()), int(x.max()+1), int(y.max()+1)],
                            'width_screenshot_px': int(x.max()+1-x.min()), 'height_screenshot_px': int(y.max()+1-y.min()),
                            'threshold': 'B>200, B>R+45, B>G+45, 95<=y<180',
                            'measurement_note': 'Color-mask bounds only, screenshot scale inferred as 2x; not engine window bounds'})
    profile = {'id': 'flower_icon_prompt', 'file': 'MsgResSystem.bmg', 'index': 2,
               'font': 2, 'font_name': 'Font_normal.NFTR', 'spacing': 2,
               'conservative_content_width_px': source['known_content_width_max'], 'conservative_lines': 1,
               'actual_window_max_width_px': None, 'actual_window_max_lines': None,
               'evidence': 'Both source and Korean user screenshots; default renderer font/spacing; source-fitted width is a conservative budget, not measured maximum',
               'korean_content_width_px': translated['known_content_width_max'],
               'source_allocation_width_px': source['lines'][0]['allocation_width'],
               'korean_allocation_width_px': translated['lines'][0]['allocation_width']}
    pending = [
        {'kind': '대사창', 'candidate_files': ['MsgResFull.bmg'], 'width_px': None, 'lines': None},
        {'kind': '도움말·설명', 'candidate_files': ['MsgResOther.bmg', 'MsgStatic.bmg'], 'width_px': None, 'lines': None},
        {'kind': '선택지·메뉴·이름', 'candidate_files': ['MsgResFull.bmg', 'MsgStatic.bmg'], 'width_px': None, 'lines': None},
        {'kind': '알림·아이템 획득', 'candidate_files': ['MsgResFull.bmg'], 'width_px': None, 'lines': None},
        {'kind': '저장·오류 안내의 다른 문구', 'candidate_files': ['MsgResSystem.bmg'], 'width_px': None, 'lines': None},
        {'kind': '스태프 표시', 'candidate_files': ['MsgResStaff.bmg'], 'width_px': None, 'lines': None},
    ]
    save(ROOT/'metadata/window_profiles.json', {'schema': 1, 'profiles': [profile], 'unresolved_categories': pending,
                                               'note': 'File associations outside index 2 are candidates, not established window mappings.'})
    save(ROOT/'work/layout-analysis/messages.json', records)
    report = {'messages': len(records), 'nonempty': sum(r['nonempty'] for r in records), 'linked_messages': 1,
              'unlinked_messages': len(records)-1, 'file_summary': file_summary, 'tag_counts': dict(tagcounts),
              'source_flower': source, 'probe_flower': translated, 'screenshot_calibration': calibration,
              'actual_window_maxima_fully_measured': False, 'rom_built': False}
    save(ROOT/'metadata/layout_analysis.json', report)
    sample = next(r for r in records if r['file'] == 'MsgResSystem.bmg' and r['index'] == 2)
    parts = [TRANSLATION if isinstance(p, str) else p for p in sample['parts']]
    save(ROOT/'work/layout-analysis/probe-translation.json', [{'file': sample['file'], 'index': 2, 'parts': parts}])
    table = ''.join(f"<tr><td>{html.escape(s['file'])}</td><td>{s['messages']}</td><td>{s['raw_line_count_max']}</td><td>{s['messages_with_variables']}</td><td>{s['width_max_default_normal_scenario']}</td></tr>" for s in file_summary)
    doc = f'''<!doctype html><meta charset="utf-8"><title>치비로보 글 창 조사</title>
<style>body{{font:17px sans-serif;background:#f5f6f8;color:#182536;margin:36px;line-height:1.7;max-width:1100px}}table{{border-collapse:collapse;background:white;width:100%}}th,td{{padding:10px 16px;border:1px solid #d6dce4}}.note{{background:#fff2cd;padding:16px}}</style>
<h1>3단계 · 글 창과 픽셀 폭 조사</h1><p>2,349항목의 글자 폭·줄바꿈·태그·변수를 조사했습니다. 실제 화면과 연결한 것은 꽃 아이콘 선택 안내 1항목입니다.</p>
<h2>확인한 화면</h2><p>원문 「{SOURCE}」: 173px / 한글 「{TRANSLATION}」: 161px. 기본 11px 폰트와 자간 2px 기준입니다. 마지막 자간을 포함하는 할당 폭은 각각 175px / 163px입니다.</p>
<p>사용자 스크린샷의 파란 글자 영역은 각각 348×26 / 324×26px입니다. 2배 표시와 외곽 효과를 고려한 예상 크기와 일치하여, 이 화면의 폭 계산 근거로 사용합니다.</p>
<p class="note">검사 예산은 원문이 실제 들어간 173px·1줄로 잡았습니다. 창이 허용하는 최대치라는 뜻은 아닙니다. 대사·도움말·선택지·알림 등 나머지 창의 최대 폭과 줄 수는 미확정입니다.</p>
<h2>전체 메시지 조사</h2><table><tr><th>파일</th><th>항목</th><th>원시 최대 줄 수</th><th>변수 포함 항목</th><th>기본 normal 시나리오 최대 폭</th></tr>{table}</table>
<p>파일별 수치는 번역 한도나 실제 창 크기가 아닙니다. 페이지 전환·호출 시 폰트 설정·동적 변수·흔들림 효과 때문에 표시값이 달라질 수 있습니다.</p>
<h2>자동 검사</h2><p>태그·변수 보존, 지원 글리프, 픽셀 폭과 줄 수를 검사합니다. 연결된 창은 보수적 예산 안인지 판정하고, 창·변수·효과가 미확정이면 ‘미확인’으로 남깁니다. 현재 한글 글리프 검사는 v02에 실린 11음절만 지원합니다.</p>'''
    (ROOT/'work/layout-analysis/index.html').write_text(doc, encoding='utf-8')
    print(json.dumps({'messages': len(records), 'linked': 1, 'file_summary': file_summary}, ensure_ascii=False))


if __name__ == '__main__': main()
