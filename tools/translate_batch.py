"""Import authored Korean string segments without changing BMG control tokens."""
import argparse
import copy
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORMAT=re.compile(r'%(?:[-+ #0]*\d*(?:\.\d+)?[diuoxXfFeEgGcs]|%)')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('file')
    ap.add_argument('batch')
    args=ap.parse_args()
    source=json.loads((ROOT/'translations/jp-source.json').read_text(encoding='utf-8'))
    dest=ROOT/'translations/ko.json'
    rows=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else copy.deepcopy(source)
    bykey={(r['file'],r['index']):r for r in rows}
    count=0
    for line in Path(args.batch).read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):continue
        index,text=line.split('\t',1)
        row=bykey[args.file,int(index)]
        segments=[s.replace('\\n','\n') for s in text.split('¦')]
        originals=[p for p in row['source_parts'] if isinstance(p,str)]
        assert len(segments)==len(originals),(index,len(segments),originals)
        assert FORMAT.findall(''.join(originals))==FORMAT.findall(''.join(segments)),index
        assert ''.join(originals).count('\n')==''.join(segments).count('\n'),('line count',index)
        it=iter(segments)
        row['translation_parts']=[next(it) if isinstance(p,str) else copy.deepcopy(p) for p in row['source_parts']]
        row['status']='translated_draft'
        count+=1
    for src,row in zip(source,rows):
        assert all(src[k]==row[k] for k in src if k not in ('translation_parts','status'))
    dest.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Imported {count} rows; {sum(r["translation_parts"] is not None for r in rows)}/{len(rows)} populated.')

if __name__=='__main__':main()
