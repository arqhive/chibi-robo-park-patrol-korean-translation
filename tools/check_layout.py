"""Conservative pixel checks. Unknown windows, effects and variables never pass.

Input JSON: list of {file, index, parts}, where parts contain strings or
{type: integer, data: hex-string} BMG escapes. No ROM writes.
"""
import argparse
from collections import Counter
import json
import re
import struct

from analyze_resources import nftr, message_repr
from inspect_roms import ROOT, save
from prepare_output_probe import SLOTS
import ndspy.bmg

FONT_IDS = {0: 639, 1: 638, 2: 637, 3: 635, 4: 636}
FORMAT = re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGcs]|%)')


def load_fonts(probe=False):
    fonts = {}
    if probe:
        import ndspy.rom
        rom = ndspy.rom.NintendoDSRom((ROOT/'build/ChibiRobo_AJBJ_KO_font-test_v02.nds').read_bytes())
    for enum, fid in FONT_IDS.items():
        b = (ROOT/f'work/extracted/jp/files/{fid:04}.bin').read_bytes()
        if probe:
            b = rom.files[fid]
        r, mapping, widths, tiles = nftr(b)
        finf = next(x['offset'] for x in r['blocks'] if x['magic'] == 'FNIF')
        fonts[enum] = {'file_id': fid, 'cell': r['cell'], 'mapping': mapping, 'widths': widths,
                       'line_feed': b[finf+9], 'probe': probe}
    return fonts


def measure(parts, fonts, initial_font=2, spacing=2):
    """Widths under explicit font/spacing assumptions, not inferred window limits."""
    enum = initial_font
    lines = [{'advance': 0, 'characters': 0, 'height': 0}]
    issues = set()
    variables = []
    for part in parts:
        if isinstance(part, dict):
            typ, data = part['type'], bytes.fromhex(part['data'])
            if len(data) < 3 or data[1] != 0:
                issues.add('unknown_tag'); continue
            group, value = data[0], data[2]
            if (typ, group) in [(128, 1), (255, 3)] and len(data) == 3:
                enum = value
                if enum not in fonts:
                    issues.add('unknown_font')
            elif (typ, group) in [(128, 0), (128, 3), (128, 4), (255, 0)]:
                pass  # timing / palette operations; no normal character advance
            else:
                issues.add('unresolved_effect_or_tag')
            continue
        at = 0
        while at < len(part):
            match = FORMAT.match(part, at)
            if match and match[0] != '%%':
                variables.append(match[0]); issues.add('unbounded_variable')
                at = match.end(); continue
            ch = '%' if match else part[at]
            at = match.end() if match else at+1
            if ch == '\n':
                lines.append({'advance': 0, 'characters': 0, 'height': 0}); continue
            if ch == '\r' or ord(ch) < 32:
                issues.add('unknown_control'); continue
            if ch == '%' and not match:
                issues.add('unparsed_percent')
            if enum not in fonts:
                issues.add('unknown_font'); continue
            font = fonts[enum]
            lookup = SLOTS.get(ch, ch) if font['probe'] else ch
            try:
                code = int.from_bytes(lookup.encode('cp932'), 'big')
            except UnicodeEncodeError:
                issues.add('missing_glyph'); continue
            index = font['mapping'].get(code)
            if index is None:
                issues.add('missing_glyph'); continue
            # The game has a second width mode (left+ink width); in these
            # four general fonts it equals CWDH advance for all mapped glyphs.
            left, width, advance = font['widths'][index]
            if left+width != advance:
                issues.add('width_mode_ambiguous')
            line = lines[-1]
            line['advance'] += advance+spacing
            line['characters'] += 1
            line['height'] = max(line['height'], font['line_feed'])
    for line in lines:
        # Both game functions exist: tag-aware allocation keeps final spacing;
        # the plain line-width function removes it. Keep both values explicit.
        line['allocation_width'] = line['advance']
        line['content_width'] = line['advance']-spacing if line['characters'] else 0
        del line['advance']
    return {'lines': lines, 'raw_line_count': len(lines), 'variables': variables,
            'issues': sorted(issues), 'assumptions': {'initial_font': initial_font, 'spacing': spacing},
            'known_content_width_max': max(x['content_width'] for x in lines)}


def tokens(parts):
    return [p for p in parts if isinstance(p, dict)]


def formats(parts):
    return [m[0] for p in parts if isinstance(p, str) for m in FORMAT.finditer(p)]


def assess(source, translated, fonts, profile=None):
    errors, pending = [], []
    if tokens(source) != tokens(translated): errors.append('tags_changed')
    if formats(source) != formats(translated): errors.append('format_placeholders_changed')
    measured = measure(translated, fonts, initial_font=(profile or {}).get('font', 2), spacing=(profile or {}).get('spacing', 2))
    pending.extend(measured['issues'])
    if profile is None:
        pending.append('window_unlinked')
    else:
        if measured['known_content_width_max'] > profile['conservative_content_width_px']:
            errors.append('width_over_budget')
        if measured['raw_line_count'] > profile['conservative_lines']:
            errors.append('lines_over_budget')
    return {'status': 'fail' if errors else 'unresolved' if pending else 'pass_conservative_profile',
            'errors': errors, 'pending': sorted(set(pending)), 'measurement': measured}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('translations', help='JSON list of {file,index,parts}')
    parser.add_argument('--output', default='work/layout-analysis/translation-check.json')
    args = parser.parse_args()
    profiles = json.loads((ROOT/'metadata/window_profiles.json').read_text(encoding='utf-8'))['profiles']
    lookup = {(p['file'], p['index']): p for p in profiles if p.get('conservative_content_width_px') is not None}
    names = {r['path']: r['id'] for r in json.loads((ROOT/'metadata/inventory_jp.json').read_text(encoding='utf-8'))['files']}
    fonts = load_fonts(probe=True)
    rows = []
    for row in json.loads((ROOT/args.translations).read_text(encoding='utf-8')):
        fid = names[row['file']]
        bmg = ndspy.bmg.BMG((ROOT/f'work/extracted/jp/files/{fid:04}.bin').read_bytes())
        source = message_repr(bmg.messages[row['index']])['parts']
        result = assess(source, row['parts'], fonts, lookup.get((row['file'], row['index'])))
        rows.append({'file': row['file'], 'index': row['index'], **result})
    save(ROOT/args.output, {'summary': dict(Counter(r['status'] for r in rows)), 'results': rows})
    print(json.dumps(dict(Counter(r['status'] for r in rows)), ensure_ascii=False))
    raise SystemExit(1 if any(r['status'] != 'pass_conservative_profile' for r in rows) else 0)


if __name__ == '__main__': main()
