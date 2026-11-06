"""Freeze the user's saved 16x16 Myeong PNG without altering its pixels."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 source=Path.home()/'Downloads/DayResultPark-cell-22-edited.png';im=Image.open(source).convert('RGBA');assert im.size==(16,16)
 a=np.array(im);assert set(map(tuple,a.reshape(-1,4)))<={(0,0,0,0),(0,0,0,255),(255,255,255,255)}
 original=Image.open(ROOT/'work/graphics-draft/dayresult-myeong-white-v1/after.png').convert('RGBA');edited=int(np.any(np.array(original)!=a,axis=2).sum())
 out=ROOT/'work/graphics-approved/dayresult-myeong-user-v1';backup=ROOT/'backups/graphics-approved/dayresult-myeong-user-v1';out.mkdir(exist_ok=True);backup.mkdir(exist_ok=True);name='DayResultPark-cell-22.png';digest=sha(source)
 for d in [out,backup]:
  dst=d/name
  if dst.exists():assert sha(dst)==digest,'Never overwrite a different frozen asset'
  else:shutil.copy2(source,dst)
  assert sha(dst)==digest
 mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text('utf8'));before=json.loads(mp.read_text('utf8'));row=next(r for r in m['graphics'] if r['edition']=='jp' and r['key']=='DayResultPark/cell/22');digest_src=row['pixel_sha256'];previous=row['localization']['output'];path=(out/name).relative_to(ROOT).as_posix();back=(backup/name).relative_to(ROOT).as_posix()
 src=np.array(Image.open(ROOT/row['path']).convert('RGBA'));Image.fromarray(np.any(src!=a,axis=2).astype('uint8')*255).save(out/'edit-mask.png')
 refs=[]
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256']==digest_src:
   refs.append(r['key']);r['localization'].update(output=path,preview=path,approved_backup=back,approved_sha256=digest,approval='approved',work_status='approved',approval_scope='User directly edited pixels in the local editor and approved the saved PNG, 2026-11-06; ROM not rebuilt',previous_output=previous,draft_version='dayresult-myeong-user-v1',final_editing_method='user_pixel_editor',method_reason='이미지젠 기반 명 글자를 검정·흰색으로 정리한 뒤 사용자가16x16 픽셀 수정기에서 직접 수정하여 저장·확정.',note='사용자가 저장한 PNG를 픽셀 변경 없이 복사해 동결. 검정·흰색·투명3종, 원본16x16 유지. 게임 반영은 별도 요청 전까지 하지 않음.',edit_mask=(out/'edit-mask.png').relative_to(ROOT).as_posix(),comparison='work/graphics-approved/dayresult-myeong-user-v1/index.html')
 for r0,r1 in zip(before['graphics'],m['graphics']):
  if r0['edition']!='jp' or r0['pixel_sha256']!=digest_src:assert r0==r1
 save(mp,m)
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>명 · 사용자 수정 확정본</title><style>body{font:16px system-ui;background:#eef1e8;margin:22px;color:#19271d}section{background:white;padding:18px;margin:16px 0;border-radius:10px}.row{display:flex;flex-wrap:wrap;gap:32px}img{image-rendering:pixelated;background:repeating-conic-gradient(#ddd 0% 25%,#f4f4f4 0% 50%) 0/12px 12px}h1,h2{margin:0 0 12px}</style><h1>명 · 사용자 직접 수정 확정본</h1>'
 for z in [1,4,8,16]:
  page+=f'<section><h2>{z}배</h2><div class="row">'
  for file,title in [('../full-test-v01/DayResultPark-cell-22.png','이전 확정본'),(name,'사용자 수정 확정본')]:page+=f'<div>{title}<br><img src="{file}" width="{16*z}" height="{16*z}"></div>'
  page+='</div></section>'
 (out/'index.html').write_text(page,encoding='utf8')
 report={'date':'2026-11-06','user_reply':'오케이 저장했어 이걸로 확정해줘','source':str(source),'source_sha256':digest,'frozen':path,'backup':back,'references':refs,'size':[16,16],'source_pixels_changed_during_freeze':0,'changed_from_editor_start':edited,'rom_built':False,'runtime_verified':False,'unrelated_manifest_rows_unchanged':True}
 save(ROOT/'metadata/dayresult_myeong_user_approval_v1.json',report)
 pp=ROOT/'project.json';p=json.loads(pp.read_text('utf8'));p['checks']['dayresult_myeong_user_approval']='metadata/dayresult_myeong_user_approval_v1.json';p['graphics_confirmation']['dayresult_myeong']={'approval':'approved','date':'2026-11-06','user_edited':True,'output':path,'backup':back,'sha256':digest,'review':'work/graphics-approved/dayresult-myeong-user-v1/index.html','rom_built':False};save(pp,p)
 print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
