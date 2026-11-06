"""Align 많이 and 꽤 to the original lettering's leftmost pixel."""
from pathlib import Path
import json,shutil,hashlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OLD=ROOT/'work/graphics-draft/batch08-v1'
OUT=ROOT/'work/graphics-draft/batch08-v2'

def main():
    OUT.mkdir(exist_ok=True)
    for p in OLD.glob('NewPCKForecast-*.png'):shutil.copy2(p,OUT/p.name)
    records=json.loads((ROOT/'metadata/graphics_batch08_checks.json').read_text(encoding='utf-8'))['items']
    proof=Image.new('RGB',(1200,480),'#d3d5cc');draw=ImageDraw.Draw(proof)
    for rec in records:
        stem=rec['key'].replace('/','-');n=int(rec['key'].split('/')[-1])
        rec['output']=rec['output'].replace('batch08-v1/','batch08-v2/')
        rec['changed_this_revision']=n in [15,16]
        if n not in [15,16]:
            assert (OLD/f'{stem}-korean.png').read_bytes()==(OUT/f'{stem}-korean.png').read_bytes()
            continue
        src=Image.open(OLD/f'{stem}-original.png').convert('RGBA')
        bg=Image.open(OLD/f'{stem}-erased.png').convert('RGBA')
        layer=Image.open(OLD/f'{stem}-lettering.png').convert('RGBA')
        box=layer.getbbox();left=rec['original_text_bbox'][0];dx=left-box[0]
        moved=Image.new('RGBA',src.size);moved.paste(layer.crop(box),(left,box[1]))
        assert moved.crop(moved.getbbox()).tobytes()==layer.crop(box).tobytes()
        result=Image.alpha_composite(bg,moved)
        a,b=np.array(src),np.array(result)
        mask=np.any(a!=np.array(bg),axis=2)|(np.array(moved)[:,:,3]>0)
        assert np.array_equal(a[~mask],b[~mask]) and np.array_equal(a[:,:,3],b[:,:,3])
        assert moved.getbbox()[0]==left and moved.getbbox()[1]==box[1]
        for suffix,im in [('korean',result),('lettering',moved),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        rec.update(result_text_bbox=list(moved.getbbox()),horizontal_shift=dx,lettering_pixels_identical=True,sha256=hashlib.sha256((OUT/f'{stem}-korean.png').read_bytes()).hexdigest())
        y=5+(n-15)*235;draw.text((5,y),rec['key']+' / original - previous - aligned',fill='black')
        for j,im in enumerate([src,Image.open(OLD/f'{stem}-korean.png').convert('RGBA'),result]):
            proof.paste(im,(5+j*400,y+20),im)
            big=im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST);proof.paste(big,(5+j*400,y+65),big)
    proof.save(OUT/'alignment-proof.png')
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    keys={r['key'] for r in records}
    for r in m['graphics']:
        if r['edition']!='jp' or r['key'] not in keys:continue
        loc=r['localization'];assert loc['approval']!='approved'
        for field in ['output','preview','erased','edit_mask','comparison']:loc[field]=loc[field].replace('batch08-v1/','batch08-v2/')
        loc['draft_version']='batch08-v2'
        if r['key'].endswith('/15') or r['key'].endswith('/16'):loc['note']='사용자 요청으로 원본 글자 왼쪽 시작점에 맞춤. 글자 모양·크기·세로위치 그대로. 원본 줄무늬·투명영역 보존. 게임실행 미확인.'
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch08_v2_checks.json').write_text(json.dumps({'items':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page=(OLD/'index.html').read_text(encoding='utf-8').replace('<h1>쿠로 예보 · 장식 글씨5개</h1>','<h1>쿠로 예보 · 장식 글씨5개</h1><p>많이·꽤는 원본 글자의 왼쪽 시작 위치로 이동했습니다. 글자 모양·크기·세로 위치는 유지했습니다.</p>')
    (OUT/'index.html').write_text(page,encoding='utf-8')
    print([(r['text'],r.get('horizontal_shift'),r['result_text_bbox']) for r in records if r['changed_this_revision']])

if __name__=='__main__':main()
