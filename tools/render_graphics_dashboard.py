"""Render the work-only dashboard from the canonical extraction manifest."""
import collections
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render():
    manifest = json.loads((ROOT / 'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
    classification = json.loads((ROOT / 'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))
    categories = classification['categories']
    out = ROOT / 'work/graphics-review'
    out.mkdir(parents=True, exist_ok=True)
    localized = [r for r in manifest['graphics'] if r['edition'] == 'jp' and 'localization' in r]
    families = sorted({r['key'].split('/')[0] for r in localized})
    group_ids = {name: f'G{n:04}' for n, name in enumerate(families, 1)}
    targets = [r for r in localized if r['localization']['action'] == 'translate_proposed']
    unique = {}

    def link(path):
        if not path:
            return None
        filename, _, fragment = path.partition('#')
        p = ROOT / filename
        if not p.is_file():
            raise FileNotFoundError(p)
        return Path(os.path.relpath(p, out)).as_posix() + ('#' + fragment if fragment else '')

    for r in targets:
        p = r['localization']
        digest = r['pixel_sha256']
        family = r['key'].split('/')[0]
        if digest not in unique:
            visual = classification['assets'][digest]
            unique[digest] = {
                'category': visual['category'], 'variant': visual['variant'],
                'id': digest, 'source': link(r['path']), 'width': r['width'], 'height': r['height'],
                'japanese': p['japanese_reading'], 'korean': p['korean_proposal'],
                'method': p.get('editing_method', 'imagegen'),
                'status': p.get('work_status', 'queued'), 'approval': p.get('approval', 'pending'),
                'note': p.get('note', ''), 'output': link(p.get('output')),
                'comparison': link(p.get('comparison')), 'erased': link(p.get('erased')), 'preview': link(p.get('preview')), 'references': [], 'groups': [],
            }
        entry = unique[digest]
        assert entry['method'] == p.get('editing_method', 'imagegen'), 'Shared art has conflicting methods'
        assert entry['status'] == p.get('work_status', 'queued'), 'Shared art has conflicting statuses'
        entry['references'].append(r['key'])
        group = {'id': group_ids[family], 'name': family}
        if group not in entry['groups']:
            entry['groups'].append(group)
    priority = {'TitleLogo': 0, 'TitleSave': 1, 'TitleSaveBG': 2}
    items = sorted(unique.values(), key=lambda x: (
        min(priority.get(g['name'], 3) for g in x['groups']), x['references'][0]))
    assert set(unique) == set(classification['assets']), 'Visual classification must cover every current target'
    assert all(x['category'] in {c['id'] for c in categories} for x in items)
    payload = {'items': items, 'categories': categories, 'groups': [
        {'id': group_ids[name], 'name': name}
        for name in families if any(r['key'].split('/')[0] == name for r in targets)
    ], 'references': len(targets)}
    template = (ROOT / 'tools/templates/graphics_dashboard.html').read_text(encoding='utf-8')
    data = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c')
    (out / 'dashboard.html').write_text(template.replace('__GRAPHICS_DATA__', data), encoding='utf-8')
    checks = {
        'unique_targets': len(items), 'target_families': len(payload['groups']),
        'source_references': len(targets),
        'visual_categories': len(categories),
        'category_counts': dict(collections.Counter(x['category'] for x in items)),
        'all_targets_categorized_once': True,
        'methods': dict(collections.Counter(x['method'] for x in items)),
        'statuses': dict(collections.Counter(x['status'] for x in items)),
        'excluded_preserve_or_reading_pending': len({r['pixel_sha256'] for r in localized}) - len(items),
        'all_referenced_local_files_exist': True,
        'manifest_sha256': hashlib.sha256((ROOT / 'metadata/extraction_manifest.json').read_bytes()).hexdigest(),
    }
    (ROOT / 'metadata/graphics_dashboard_checks.json').write_text(
        json.dumps(checks, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(checks, ensure_ascii=False))


if __name__ == '__main__':
    render()
