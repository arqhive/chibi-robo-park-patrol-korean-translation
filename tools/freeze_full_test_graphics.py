"""Snapshot all current graphics authorized for the full test ROM."""
import json,hashlib,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    assert (ROOT/'metadata/full_test_verification_v01.json').is_file()
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    out=ROOT/'work/graphics-approved/full-test-v01';backup=ROOT/'backups/graphics-approved/full-test-v01'
    out.mkdir(parents=True,exist_ok=True);backup.mkdir(parents=True,exist_ok=True);updates={};records=[]
    for r in m['graphics']:
        loc=r.get('localization',{})
        if r['edition']!='jp' or loc.get('action')!='translate_proposed':continue
        src=ROOT/loc['output'];digest=hashlib.sha256(src.read_bytes()).hexdigest();name=r['key'].replace('/','-')+'.png'
        for folder in (out,backup):
            dst=folder/name
            if dst.exists():assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
            else:shutil.copy2(src,dst)
            assert hashlib.sha256(dst.read_bytes()).hexdigest()==digest
        rec={'key':r['key'],'source':loc['output'],'frozen':(out/name).relative_to(ROOT).as_posix(),'backup':(backup/name).relative_to(ROOT).as_posix(),'sha256':digest};records.append(rec)
        updates.setdefault(r['pixel_sha256'],{'output':rec['frozen'],'preview':rec['frozen'],'approval':'approved','work_status':'approved','approved_sha256':digest,'approved_backup':rec['backup'],'approval_scope':'User approved current artwork for full test ROM; runtime not yet verified'})
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    assert len(updates)==509 and len(records)==552
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    report={'user_reply':'좋습니다 이제 다 떄려넣고 롬한번 만들어보죠','date':'2026-10-15','unique_artworks':len(updates),'references':len(records),'scope':'Current artwork accepted for full test build, not runtime approval','items':records}
    (ROOT/'metadata/graphics_full_test_approval_v01.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Frozen and backup-verified 509 unique images / 552 references')

if __name__=='__main__':main()
