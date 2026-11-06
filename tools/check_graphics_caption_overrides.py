"""Check repeated graphic names against user-approved caption overrides."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
policy=json.loads((ROOT/'metadata/graphics_caption_overrides.json').read_text(encoding='utf-8'))
rules=policy['entries']
categories=json.loads((ROOT/'metadata/graphics_visual_categories.json').read_text(encoding='utf-8'))['assets']
manifest=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
count=0
for row in manifest['graphics']:
    if row['edition']!='jp':continue
    loc=row.get('localization',{})
    for rule in rules:
        if loc.get('japanese_reading')!=rule['japanese_reading']:continue
        assert loc.get('korean_proposal')==rule['korean_proposal'],row['key']
        assert loc.get('lines')==rule['lines'],row['key']
        count+=1
    for rule in policy.get('visual_category_line_overrides',[]):
        category=categories.get(row['pixel_sha256'],{}).get('category')
        if category not in rule['categories'] or loc.get('korean_proposal')!=rule['korean_proposal']:continue
        assert loc.get('lines')==rule['lines'],row['key']
        count+=1
print(f'{count} repeated captions match approved names and line breaks')
