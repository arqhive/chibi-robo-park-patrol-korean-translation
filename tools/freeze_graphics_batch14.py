"""Freeze forecast decorative labels explicitly approved with 다음."""
from pathlib import Path
import json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in {c['key'] for c in json.loads((ROOT/'metadata/graphics_batch14_v2_checks.json').read_text(encoding='utf-8'))['items']} and r.get('localization',{}).get('action')=='translate_proposed']
    assert len(rows)==13
    out=ROOT/'work/graphics-approved/batch14-final';backup=ROOT/'backups/graphics-approved/batch14-final'
    out.mkdir(parents=True,exist_ok=True);backup.mkdir(parents=True,exist_ok=True)
    records=[];updates={}
    for r in rows:
        loc=r['localization'];src=ROOT/loc['output'];name=r['key'].replace('/','-')+'.png';digest=hashlib.sha256(src.read_bytes()).hexdigest()
        for directory in [out,backup]:
            dst=directory/name
            if dst.exists():assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest,'Do not overwrite frozen asset'
            else:shutil.copy2(src,dst)
            assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
        rec={'key':r['key'],'path':(out/name).relative_to(ROOT).as_posix(),'backup':(backup/name).relative_to(ROOT).as_posix(),'sha256':digest}
        records.append(rec)
        updates.setdefault(r['pixel_sha256'],{'output':rec['path'],'preview':rec['path'],'approved_backup':rec['backup'],'approved_sha256':digest,'approval':'approved','work_status':'approved','approval_scope':'Visual design approved; palette conversion and runtime verification pending'})
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'user_reply':'다음','date':'2026-10-15','version':'batch14-v2','scope':'Visual design','references':13,'unique_images':len(updates),'items':records}
    (ROOT/'metadata/graphics_batch14_approval.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Frozen13 references / '+str(len(updates))+' unique images; backup hashes verified')

if __name__=='__main__':main()
