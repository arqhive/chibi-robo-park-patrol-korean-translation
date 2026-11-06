"""Prepare review-only native-size artwork from the selected imagegen design."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from scipy import ndimage as nd
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/title-touch-imagegen-fit-v1'
def main():
 OUT.mkdir(exist_ok=False)
 src=ROOT/'work/graphics-draft/title-touch-imagegen-v1/generated-original.png';a=np.array(Image.open(src).convert('RGBA'))
 labels,n=nd.label(a[:,:,3]>=128);sizes=np.bincount(labels.ravel());ids=np.argsort(sizes[1:])[-4:]+1;active=np.isin(labels,ids)
 yy,xx=np.where(active);rect=(int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1));x0,y0,x1,y1=rect
 a=a[y0:y1,x0:x1];active=active[y0:y1,x0:x1];rgb=a[:,:,:3].astype(int)
 colors=np.array([(0,0,0),(255,255,255),(246,156,57),(255,238,90),(189,213,65)],dtype=np.uint8)
 classes=np.zeros(active.shape,dtype=np.uint8)
 bright=rgb.max(axis=2);sat=np.ptp(rgb,axis=2)
 whites=(bright>=180)&(sat<55);classes[whites]=1
 chromatic=(sat>=55)&(bright>=115)
 dist=((rgb[:,:,None,:]-colors[None,None,2:,:].astype(int))**2).sum(3)
 classes[chromatic]=2+np.argmin(dist,axis=2)[chromatic]
 w=132;h=round(active.shape[0]*w/active.shape[1]);assert h<=22
 # Area voting transfers solid shapes, rather than generating gray/olive mixtures.
 coverage=np.array(Image.fromarray(active.astype('uint8')*255).resize((w,h),Image.Resampling.BOX))/255
 scores=np.stack([np.array(Image.fromarray(((classes==i)&active).astype('uint8')*255).resize((w,h),Image.Resampling.BOX)) for i in range(5)],axis=2)
 winner=scores.argmax(2);mask=coverage>=.5
 # Keep one continuous outer black pixel contour, with no extra thick gray rim.
 envelope=nd.binary_fill_holes(mask)
 outer=envelope&~nd.binary_erosion(envelope,structure=nd.generate_binary_structure(2,1))
 winner[outer]=0
 native=np.zeros((h,w,4),dtype=np.uint8);native[:,:,:3]=colors[winner];native[:,:,3]=mask.astype('uint8')*255;native[~mask]=0
 result=Image.new('RGBA',(136,24));xy=((136-w)//2,(24-h)//2);result.paste(Image.fromarray(native),xy)
 arr=np.array(result);lab,n=nd.label(arr[:,:,3]>0);parts=nd.find_objects(lab);mark=max(parts,key=lambda q:q[1].stop);left,right=mark[1].start,mark[1].stop;half=(right-left)//2
 assert (right-left)%2==0
 arr[:,left+half:right]=arr[:,left:left+half][:,::-1]
 assert np.array_equal(arr[:,left:right],arr[:,left:right][:,::-1])
 result=Image.fromarray(arr)
 result.save(OUT/'title-touch.png');result.resize((816,144),Image.Resampling.NEAREST).save(OUT/'title-touch-6x.png')
 # Palettes are read-only: validate against the actual target family.
 from extract_graphics import palette
 inv=json.loads((ROOT/'metadata/inventory_jp.json').read_text('utf8'))['files'];r=next(r for r in inv if r['path']=='TitleLogo.NCLR');pal=palette((ROOT/'work/extracted/jp'/r['disk_file']).read_bytes());allowed={c[:3] for c in pal[1:]}
 assert all(tuple(c) in allowed for c in colors)
 assert result.size==(136,24)
 previous=ROOT/'work/graphics-draft/title-touch-letter-contours-v1/after.png'
 sheet=Image.new('RGB',(840,320),'white')
 for j,im in enumerate([Image.open(previous).convert('RGBA'),result]):
  im=im.resize((816,144),Image.Resampling.NEAREST);sheet.paste(im,(10,8+j*160),im)
 sheet.save(OUT/'compare-white.png')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>画像生成 · 実寸確認</title><style>body{font:16px system-ui;background:#f1f3ed;margin:22px;color:#18251e}.row{display:flex;flex-wrap:wrap;gap:24px}section{background:white;padding:16px;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>이미지젠 새 글씨 · 실제 크기</h1><p>136×24px · 결과 확인용</p>'
 for z in [1,4,6]:
  page+=f'<section><h2>{z}배 비교</h2><div class="row">'
  for file,t in [('../title-touch-letter-contours-v1/after.png','이전 픽셀 시안'),('title-touch.png','이미지젠 새 시안')]:page+=f'<div>{t}<br><img src="{file}" width="{136*z}" height="{24*z}"></div>'
  page+='</div></section>'
 page+='<section><h2>이미지젠 생성 원본</h2><img src="../title-touch-imagegen-v1/generated-original.png" style="width:min(100%,1200px);height:auto;image-rendering:auto"></section>'
 (OUT/'index.html').write_text(page,encoding='utf8')
 report={'source':str(src.relative_to(ROOT)),'source_crop':list(rect),'size':[136,24],'placement':list(xy),'artwork_size':[w,h],'opaque_colours':colors.tolist(),'palette_unmatched_pixels':0,'rom_built':False,'manifest_changed':False,'exclamation_exact_symmetry':True,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
 (OUT/'checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');print(report)
if __name__=='__main__':main()
