"""Freeze the approved button category revisions (24 references, 19 unique images)."""
from pathlib import Path
import json, hashlib, shutil
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r.get('localization',{}).get('draft_version')=='buttons-v5']
    assert len(rows)==24
    out=ROOT/'work/graphics-approved/buttons-final';backup=ROOT/'backups/graphics-approved/buttons-final'
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
    report={'user_reply':'공사 중 표시 다음 묶음 가시죠','date':'2026-10-15','version':'buttons-v5','scope':'Visual design','references':24,'unique_images':len(updates),'items':records}
    (ROOT/'metadata/graphics_buttons_category_approval.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Frozen24 references / '+str(len(updates))+' unique images; backup hashes verified')

if __name__=='__main__':main()
