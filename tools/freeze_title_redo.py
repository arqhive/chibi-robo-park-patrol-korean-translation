"""Freeze the four user-approved title graphics; no game build or injection."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
ITEMS={
 'TitleLogo/cell/0':('work/graphics-draft/piweora-outer-round-v1/after.png','기존 피워라의 회색 띠 바깥 검은 선 연결 및 계단 모서리 정리. 글씨·색 띠·아랫판·캐릭터·꽃 보존.'),
 'TitleLogo/cell/1':('work/graphics-draft/title-touch-top-ghost-cleanup-v1/title-touch.png','새 이미지젠 생성본 형태를 유지해 축소·원본 팔레트 변환, 윗선 잔상15픽셀 제거.'),
 'TitleSave/cell/50':('work/graphics-draft/title-save-imagegen-fit-v1/TitleSave-cell-50.png','새 이미지젠 여기를 생성·축소, 윗선 잔상14픽셀 제거. 불투명 흰 배경 유지.'),
 'TitleSave/cell/51':('work/graphics-draft/title-save-imagegen-fit-v1/TitleSave-cell-51.png','새 이미지젠 터치! 생성·축소, 윗선 잔상15픽셀 제거. 불투명 흰 배경 유지.')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def main():
 out=ROOT/'work/graphics-approved/title-redo-v1';backup=ROOT/'backups/graphics-approved/title-redo-v1';out.mkdir(exist_ok=True);backup.mkdir(exist_ok=True)
 mp=ROOT/'metadata/extraction_manifest.json';m=json.loads(mp.read_text('utf8'));before=json.loads(mp.read_text('utf8'));updates={};records=[];page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>타이틀 4종 · 최신 확정본</title><style>body{font:16px system-ui;margin:22px;background:#f1f3ed;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>타이틀 4종 · 최신 확정본</h1>'
 for key,(rel,note) in ITEMS.items():
  r=next(r for r in m['graphics'] if r['edition']=='jp' and r['key']==key);loc=r['localization'];stem=key.replace('/','-');src=ROOT/rel;im=Image.open(src).convert('RGBA');assert im.size==(r['width'],r['height'])
  old=Image.open(ROOT/loc['output']).convert('RGBA')
  if key=='TitleLogo/cell/0':assert np.array_equal(np.array(old)[40:],np.array(im)[40:])
  if key.startswith('TitleSave/'):assert im.getchannel('A').getextrema()==(255,255)
  digest=sha(src)
  for d in (out,backup):
   dst=d/(stem+'.png')
   if dst.exists():assert sha(dst)==digest,'Frozen file differs; never overwrite'
   else:shutil.copy2(src,dst)
   assert sha(dst)==digest
  original=np.array(Image.open(ROOT/r['path']).convert('RGBA'));mask=np.any(original!=np.array(im),axis=2);Image.fromarray(mask.astype('uint8')*255).save(out/(stem+'-mask.png'))
  dst=(out/(stem+'.png')).relative_to(ROOT).as_posix();back=(backup/(stem+'.png')).relative_to(ROOT).as_posix()
  update={'output':dst,'preview':dst,'approved_backup':back,'approved_sha256':digest,'approval':'approved','work_status':'approved','approval_scope':'User-approved artwork 2026-11-06; ROM insertion and runtime not performed','draft_version':'title-redo-v1','comparison':'work/graphics-approved/title-redo-v1/index.html#'+stem,'edit_mask':(out/(stem+'-mask.png')).relative_to(ROOT).as_posix(),'note':note+' 사용자 확정. 게임 반영은 별도 요청 전까지 하지 않음.','previous_output':loc['output']}
  if key=='TitleLogo/cell/1':update['korean_proposal']='터치 해서 시작!'
  updates[r['pixel_sha256']]=update
  records.append({'key':key,'source':rel,'previous_output':loc['output'],'frozen':dst,'backup':back,'sha256':digest,'size':list(im.size)})
  w,h=im.size;page+=f'<section id="{stem}"><h2>{key}</h2>'
  for z in (1,4):
   page+=f'<p>{z}배</p><div class="row">'
   # The older full-test snapshot is kept intact for comparison.
   for path,title in [('../full-test-v01/'+stem+'.png','이전 확정본'),(stem+'.png','새 확정본')]:page+=f'<div>{title}<br><img src="{path}" width="{w*z}" height="{h*z}"></div>'
   page+='</div>'
  page+='</section>'
 refs=[]
 for r in m['graphics']:
  if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']]);refs.append(r['key'])
 for a,b in zip(before['graphics'],m['graphics']):
  if a['key'] not in refs or a['edition']!='jp':assert a==b
 save(mp,m);(out/'index.html').write_text(page,encoding='utf8')
 report={'date':'2026-11-06','user_reply':'ㅇㅋ 확정','scope':'latest four title artwork revisions','items':records,'references_updated':refs,'unrelated_manifest_rows_unchanged':True,'logo_lower_40_rows_onward_identical':True,'rom_built':False,'runtime_verified':False}
 save(ROOT/'metadata/title_redo_approval_v1.json',report)
 rp=ROOT/'metadata/title_redo_current_review.json';review=json.loads(rp.read_text('utf8'));review.update(save_prompt_visual_approval='approved',all_four_visual_approval='approved',manifest_updated=True,frozen='work/graphics-approved/title-redo-v1',backup='backups/graphics-approved/title-redo-v1',review='work/graphics-approved/title-redo-v1/index.html',rom_built=False);save(rp,review)
 pp=ROOT/'project.json';p=json.loads(pp.read_text('utf8'));p['checks']['title_redo_approval']='metadata/title_redo_approval_v1.json';p['checks']['title_redo_current_review']='metadata/title_redo_current_review.json';p['graphics_confirmation']['title_redo']={'date':'2026-11-06','approval':'approved','references':len(refs),'unique_artworks':len(records),'review':'work/graphics-approved/title-redo-v1/index.html','rom_built':False,'user_constraint':'게임엔 넣지말고 결과만 보여라'};save(pp,p)
 print(json.dumps({'frozen_artworks':len(records),'updated_references':len(refs),'rom_built':False}))
if __name__=='__main__':main()
