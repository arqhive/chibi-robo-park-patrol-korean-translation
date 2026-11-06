"""Native Mono7 login captions, with protected icon pixels."""
from pathlib import Path
import json,hashlib,html,argparse
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from preview_neicon_mono7 import render_line,FONT_PATH
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/batch12-v1'
LINES={0:['공원','만들기'],1:['도구','사요'],2:['쿠로','예보'],3:['공원','만들기'],4:['도구','사요'],5:['쿠로','예보'],6:['예보'],7:['예보'],8:['카세트','컬렉션'],9:['카세트','컬렉션']}
# Explicit user choice: shorten both sticker icons to 스티커 / 컬렉션.
LINES.update({10:['스티커','컬렉션'],11:['스티커','컬렉션']})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--sticker-lines',nargs=2);args=ap.parse_args()
    lines=dict(LINES)
    if args.sticker_lines:lines[10]=lines[11]=args.sticker_lines
    OUT.mkdir(parents=True,exist_ok=True)
    p=ROOT/'metadata/extraction_manifest.json';m=json.loads(p.read_text(encoding='utf-8'))
    rows=[r for r in m['graphics'] if r['edition']=='jp' and r['key'] in {f'NewPCLogIn/cell/{n}' for n in lines}]
    checks=[];updates={};sheet=Image.new('RGB',(1100,840),'#d6dacf');d=ImageDraw.Draw(sheet)
    for i,r in enumerate(rows):
        n=int(r['key'].split('/')[-1]);stem=r['key'].replace('/','-');loc=r['localization'];assert loc['approval']!='approved'
        src=Image.open(ROOT/r['path']).convert('RGBA');a=np.array(src);old=a[:,:,3]>0;old[:32]=False
        ys,xs=np.where(old);total=len(lines[n])*9+len(lines[n])-1
        y=max(32,min((int(ys.min())+int(ys.max())+1-total)//2,src.height-total));clean=a.copy();clean[old]=0
        erased=Image.fromarray(clean);ink=Image.new('L',src.size);placements=[]
        for line in lines[n]:
            g,rec=render_line(line,src.width-2);x=(src.width-g.width-2)//2;ink.paste(g,(x+1,y+1));placements.append(dict(rec,bbox=[x,y,x+g.width+2,y+9]));y+=10
        border=ink.filter(ImageFilter.MaxFilter(3));result=erased.copy();result.paste((16,49,123,255),(0,0),border);result.paste((255,255,255,255),(0,0),ink)
        mask=old|(np.array(border)>0);b=np.array(result)
        assert np.array_equal(a[:32],b[:32]) and np.array_equal(a[~mask],b[~mask])
        for suffix,im in [('original',src),('erased',erased),('korean',result),('mask',Image.fromarray(mask.astype('uint8')*255))]:im.save(OUT/f'{stem}-{suffix}.png')
        text=''.join(lines[n]) if n in [0,1,3,4] else ' '.join(lines[n]);output=(OUT/f'{stem}-korean.png').relative_to(ROOT).as_posix()
        updates[r['pixel_sha256']]={'output':output,'preview':output,'erased':(OUT/f'{stem}-erased.png').relative_to(ROOT).as_posix(),'edit_mask':(OUT/f'{stem}-mask.png').relative_to(ROOT).as_posix(),'comparison':OUT.relative_to(ROOT).as_posix()+'/index.html#'+stem,'korean_proposal':text,'lines':lines[n],'draft_version':'batch12-v1','editing_method':'galmuri','font':'GalmuriMono7','font_px':8,'method_reason':'명확한 도트 이름표. 확정 NEIcon 계열과 동일한 Mono7 기본8px 원본 획 사용.','approval':'pending','work_status':'review','requires_resource_width_expansion':False,'note':'원본 그림32행과 규격 보존. 글자 원본 획 변형 없음, 원본 세로 중심 정렬. 팔레트변환·게임실행 미확인.'}
        if n in [1,4]:updates[r['pixel_sha256']].update(japanese_reading='ドーグカエール',reading_correction='Source inspection corrects erroneous パークツクール; established Korean term 도구사요')
        checks.append({'key':r['key'],'text':text,'lines':lines[n],'size':list(src.size),'placements':placements,'font':'GalmuriMono7','font_px':8,'resized':False,'icon_changed_pixels':0,'outside_mask_changed_pixels':0,'sha256':hashlib.sha256((ROOT/output).read_bytes()).hexdigest(),'runtime_verified':False})
        cx=(i%4)*275;cy=(i//4)*280;d.text((cx+3,cy+3),r['key'],fill='black')
        for j,im in enumerate([src,result]):
            sheet.paste(im,(cx+5+j*135,cy+22),im);big=im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST);sheet.paste(big,(cx+5+j*135,cy+85),big)
    sheet.save(OUT/'overview.png')
    for r in m['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in updates:r['localization'].update(updates[r['pixel_sha256']])
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'metadata/graphics_batch12_checks.json').write_text(json.dumps({'references':len(rows),'items':checks,'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    page='<meta charset="utf-8"><title>로그인 아이콘 이름표</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:20px 0}.row{display:flex;gap:28px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}</style><h1>로그인 아이콘 이름표</h1><p>갈무리Mono7 기본8px · 원본 아이콘과 규격 보존 · 전체 '+str(len(rows))+'개</p><a href="../../graphics-review/dashboard.html">현황판</a>'
    for c in checks:
        stem=c['key'].replace('/','-');w,h=c['size'];page+=f'<section id="{stem}"><h2>{c["key"]} · {html.escape(c["text"])}</h2><p>{html.escape(" / ".join(c["lines"]))}</p>'
        for z in [1,4]:
            page+=f'<p>{z}배 비교</p><div class="row">'
            for suffix,title in [('original','원본'),('erased','글자 지운 뒤'),('korean','한글')]:page+=f'<div>{title}<br><img src="{stem}-{suffix}.png" width="{w*z}" height="{h*z}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8');print(f'{len(rows)} labels; icons unchanged; native glyph masks preserved')

if __name__=='__main__':main()
