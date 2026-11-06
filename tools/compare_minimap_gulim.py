"""Compare native Gulim renders without compressing or overwriting approved graphics."""
import json
import hashlib
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTCollection
from PIL import Image,ImageDraw,ImageFont,ImageFilter
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/minimap-font-comparison'
FONT_PATH=Path('C:/Windows/Fonts/gulim.ttc')
TEXTS={115:'몽키버거',116:'꽃집',117:'공원 입구',135:'뒷골목',136:'체크포인트',144:'출발/도착',145:'체크포인트'}
START={136:10,144:16,145:15}
SIZES=[9,11,12]


def glyphs(text,size):
    font=ImageFont.truetype(str(FONT_PATH),size,index=0)
    canvas=Image.new('L',(400,48));draw=ImageDraw.Draw(canvas);draw.fontmode='1'
    draw.text((4,4),text,font=font,fill=255)
    return canvas.crop(canvas.getbbox())


def main():
    OUT.mkdir(exist_ok=True)
    m=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
    rows={r['key']:r for r in m['graphics'] if r['edition']=='jp'};report=[]
    page='<meta charset="utf-8"><title>미니맵 · 굴림 글꼴 비교</title><style>body{font:16px/1.7 sans-serif;background:#eef1e8;padding:24px}section{background:white;padding:20px;margin:24px 0}.row{display:flex;gap:26px;flex-wrap:wrap}img{image-rendering:pixelated;background:repeating-conic-gradient(#ccc 0% 25%,#eee 0% 50%) 0/12px 12px}.bad{color:#944b12}small{display:block}</style><h1>미니맵 · 갈무리와 굴림 비교</h1><p>모든 글자는 해당 크기에서 직접 렌더링했습니다. 가로 압축이나 확대·축소는 없습니다. 칸을 넘는 후보는 잘리지 않도록 미리보기 캔버스만 늘렸고, 필요한 크기를 표시했습니다. 실제 게임 리소스는 바꾸지 않았습니다.</p>'
    # Put the user-reported flower-shop label first.
    for idx in [116,115,117,135,136,144,145]:
        key=f'MiniMap/cell/{idx}';r=rows[key];stem=key.replace('/','-');text=TEXTS[idx]
        original=Image.open(ROOT/r['path']).convert('RGBA')
        current=Image.open(ROOT/'work/graphics-draft/batch02-v1'/f'{stem}-korean.png').convert('RGBA')
        erased=Image.open(ROOT/'work/graphics-draft/batch02-v1'/f'{stem}-erased.png').convert('RGBA')
        original.save(OUT/f'{stem}-original.png');current.save(OUT/f'{stem}-current.png')
        alpha=np.array(original)[:,:,3]>0;xstart=START.get(idx,0);alpha[:,:xstart]=False
        ys,xs=np.where(alpha);left,right,top=int(xs.min()),int(xs.max()+1),int(ys.min())
        variants=[('original','원본',original,None),('current','현재 갈무리7 8px',current,None)]
        for size in SIZES:
            ink=glyphs(text,size);w,h=ink.width+2,ink.height+2
            x=xstart if idx in START else max(0,left+(right-left-w)//2)
            target=(max(original.width,x+w),max(original.height,top+h))
            result=Image.new('RGBA',target);result.paste(erased,(0,0))
            mask=Image.new('L',target);mask.paste(ink,(x+1,top+1));outer=mask.filter(ImageFilter.MaxFilter(3))
            result.paste((255,255,255,255),(0,0,*target),outer);result.paste((0,0,0,255),(0,0,*target),mask)
            assert np.array_equal(np.array(original)[:,:xstart],np.array(result)[:original.height,:xstart])
            assert set(np.unique(np.array(mask)))<={0,255}
            suffix=f'gulim-{size}';result.save(OUT/f'{stem}-{suffix}.png')
            rec={'key':key,'text':text,'font':'Gulim','size_px':size,'ink_size':list(ink.size),'original_canvas':list(original.size),'preview_canvas':list(target),'fits_original_canvas':target==original.size,'resized':False,'icon_changed_pixels':0};report.append(rec)
            variants.append((suffix,f'굴림 {size}px',result,rec))
        page+=f'<section id="{stem}"><h2>{text} · {key}</h2>'
        for zoom in [1,4]:
            page+=f'<p>{zoom}배 비교</p><div class="row">'
            for suffix,label,im,rec in variants:
                note='' if rec is None else ('원래 칸에 들어감' if rec['fits_original_canvas'] else f'폭/높이 확장 필요: {im.width}×{im.height} (원본 {original.width}×{original.height})')
                page+=f'<div>{label}<small class="{("bad" if rec and not rec["fits_original_canvas"] else "")}">{note}</small><img src="{stem}-{suffix}.png" width="{im.width*zoom}" height="{im.height*zoom}"></div>'
            page+='</div>'
        page+='</section>'
    (OUT/'index.html').write_text(page,encoding='utf-8')
    font=TTCollection(str(FONT_PATH)).fonts[0]
    strikes=[s.bitmapSizeTable.ppemY for s in font['EBLC'].strikes]
    (ROOT/'metadata/minimap_gulim_comparison.json').write_text(json.dumps({'font_sha256':hashlib.sha256(FONT_PATH.read_bytes()).hexdigest(),'embedded_bitmap_sizes':strikes,'candidates_only':True,'items':report},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([r for r in report if r['size_px']==11],ensure_ascii=False))


if __name__=='__main__':main()
