"""Build the explicitly authorized AJBJ flower-icon text probe, preserving ROM layout."""
import argparse
import json
import struct
from pathlib import Path

import ndspy.rom

from inspect_roms import ROOT, INPUTS, sha, save
from prepare_output_probe import prepare

OUTPUT_NAME = 'ChibiRobo_AJBJ_KO_font-test_v02.nds'


def write_verified(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f'Refusing to overwrite different content: {path}')
    else:
        with path.open('xb') as stream:
            stream.write(data)
    assert path.read_bytes() == data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--copy-to', type=Path, help='Optional delivery directory')
    args = parser.parse_args()
    state = json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
    assert state['decisions']['build_requested'] is True, 'Explicit build authorization required'
    resources, probe, _ = prepare()
    assert set(resources) == {635, 637, 638, 639, 908}
    source = ROOT/INPUTS['jp']
    original = source.read_bytes()
    assert sha(original) == probe['original_sha256']
    inventory = json.loads((ROOT/'metadata/inventory_jp.json').read_text(encoding='utf-8'))
    rows = {r['id']: r for r in inventory['files']}
    fat_offset, fat_size = struct.unpack_from('<II', original, 0x48)
    assert fat_size == len(rows)*8
    built = bytearray(original)
    allowed = []
    changes = []
    for fid, payload in sorted(resources.items()):
        start, end = struct.unpack_from('<II', original, fat_offset+fid*8)
        row = rows[fid]
        assert (start, end) == (row['offset'], row['end'])
        assert sha(original[start:end]) == row['sha256']
        assert 0 < len(payload) <= end-start, 'Probe must not grow or relocate resources'
        # Check no other FAT entry shares or overlaps this resource.
        assert all(other['end'] <= start or other['offset'] >= end for other in rows.values() if other['id'] != fid and other['size'])
        built[start:start+len(payload)] = payload
        allowed.append((start, start+len(payload)))
        if len(payload) != end-start:
            struct.pack_into('<I', built, fat_offset+fid*8+4, start+len(payload))
            allowed.append((fat_offset+fid*8+4, fat_offset+fid*8+8))
        changes.append({'id': fid, 'path': row['path'], 'start': start, 'original_bytes': end-start, 'built_bytes': len(payload), 'original_sha256': row['sha256'], 'built_sha256': sha(payload)})
    built = bytes(built)
    assert len(built) == len(original) and built[:0x200] == original[:0x200]
    cursor = 0
    changed_bytes = 0
    for start, end in sorted(allowed):
        assert start >= cursor
        assert original[cursor:start] == built[cursor:start], 'Unexpected change outside selected regions'
        changed_bytes += sum(a != b for a, b in zip(original[start:end], built[start:end]))
        cursor = end
    assert original[cursor:] == built[cursor:]

    output = ROOT/'build'/OUTPUT_NAME
    write_verified(output, built)
    # Parse the file read back from disk independently, including updated FAT.
    parsed = ndspy.rom.NintendoDSRom(output.read_bytes())
    assert len(parsed.files) == len(rows)
    for fid, row in rows.items():
        assert parsed.filenames.filenameOf(fid) == row['path']
        if fid in resources:
            assert parsed.files[fid] == resources[fid]
        else:
            assert parsed.files[fid] == original[row['offset']:row['end']]
    assert sha(source.read_bytes()) == probe['original_sha256']
    deliveries = [str(output)]
    if args.copy_to:
        destination = args.copy_to.resolve()/OUTPUT_NAME
        assert destination.resolve() != source.resolve()
        write_verified(destination, built)
        deliveries.append(str(destination))
    report = {
        'build': 'font-test-v02', 'source_sha256': probe['original_sha256'],
        'output_sha256': sha(built), 'bytes': len(built), 'outputs': deliveries,
        'changes': changes, 'changed_bytes_including_fat': changed_bytes,
        'unmodified_files_verified': len(rows)-len(resources),
        'all_files_reextracted_and_verified': True, 'outside_allowed_ranges_identical': True,
        'header_identical': True, 'original_rehashed_unchanged': True,
        'rom_layout_preserved': True, 'runtime_verified': False,
        'note': 'Eleven temporary glyph slots only. Full font expansion and hardware remain unverified.',
    }
    save(ROOT/'metadata/output_probe_build.json', report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
