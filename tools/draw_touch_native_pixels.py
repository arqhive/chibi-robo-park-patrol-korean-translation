"""An explicitly authored native pixel drawing. No input image resampling or font rendering."""
from pathlib import Path
import json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/title-touch-hand-pixels-v1'
TER=[
 '.WWWWWW....WW.',
 'WWWWWWW...WWW.',
 'WWW.......WWW.',
 'WWW.......WWW.',
 'WWWWWW..WWWWW.',
 'WWWWWWW.WWWWW.',
 'WWW.......WWW.',
 'WWW.......WWW.',
 'WWW.......WWW.',
 'WWWWWWW...WWW.',
 'WWWWWWW...WWW.',
 '.WWWWWW....WW.']
CHI=[
 '..WW......WW.',
 '..WWW....WWW.',
 'WWWWWWW..WWW.',
 'WWWWWWWW.WWW.',
 '...W.....WWW.',
 '..WWW....WWW.',
 '.WWWWW...WWW.',
 'WWW.WWW..WWW.',
 'WWW..WWW.WWW.',
 'WW....WW.WWW.',
 '.W....W..WWW.',
 '..........WW.']
TER_EDGE=[[(2,8),(12,14)],[(1,9),(11,15)],[(0,9),(10,15)],[(0,9),(10,15)],[(0,5),(10,15)],[(0,8),(9,15)],[(0,9),(8,15)],[(0,9),(9,15)],[(0,5),(10,15)],[(0,5),(10,15)],[(0,9),(10,15)],[(0,9),(10,15)],[(1,9),(11,15)],[(2,8),(12,14)]]
CHI_EDGE=[[(3,5),(11,13)],[(2,7),(10,14)],[(1,9),(9,14)],[(0,9),(9,14)],[(0,10),(9,14)],[(2,7),(9,14)],[(2,7),(9,14)],[(1,8),(9,14)],[(0,9),(9,14)],[(0,4),(5,10),(9,14)],[(0,4),(6,10),(9,14)],[(0,3),(6,10),(9,14)],[(1,3),(7,9),(10,14)],[(11,13)]]
def main():
 OUT.mkdir(exist_ok=False)
 # Every drawing primitive is a literal native row/span or letter-pixel row.
 # Output enlargement is for inspection only.
 im=Image.new('RGBA',(38,24));black=(0,0,0,255);orange=(246,156,57,255);white=(255,255,255,255)
 outer=[(6,32),(4,34),(2,36),(1,37),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(0,38),(1,37),(2,36),(4,34),(6,32)]
 inner=[(7,31),(5,33),(3,35),(2,36),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(1,37),(2,36),(3,35),(5,33),(7,31)]
 for y,((l,r),(il,ir)) in enumerate(zip(outer,inner),2):
  for x in range(l,r):im.putpixel((x,y),black)
  for x in range(il,ir):im.putpixel((x,y),orange)
 # Explicit top and bottom black contour rows cap the orange field.
 for x in range(6,32):im.putpixel((x,2),black);im.putpixel((x,21),black)
 for ox,rows,edge in [(3,TER,TER_EDGE),(20,CHI,CHI_EDGE)]:
  for y,spans in enumerate(edge,5):
   for l,r in spans:
    for x in range(l,r):im.putpixel((ox+x,y),black)
  for y,row in enumerate(rows,6):
   for x,c in enumerate(row):
    if c=='W':im.putpixel((ox+1+x,y),white)
 im.save(OUT/'touch-native.png');im.resize((456,288),Image.Resampling.NEAREST).save(OUT/'touch-12x.png')
 # A literal colour-code grid is the editable master, not a generated font mask.
 code={(0,0,0,0):'.',black:'#',orange:'O',white:'W'}
 grid='\n'.join(''.join(code[im.getpixel((x,y))] for x in range(38)) for y in range(24))
 (OUT/'pixels.txt').write_text(grid+'\n',encoding='utf8')
 ref=Image.open(ROOT/'work/graphics-draft/title-touch-imagegen-v1/generated-original.png');ref.crop((15,180,620,550)).save(OUT/'generation-reference.png')
 page='<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>터치 · 픽셀 직접 배치</title><style>body{font:16px system-ui;margin:22px;background:#f1f3ed;color:#19251e}section{padding:16px;background:white;margin:16px 0}img{image-rendering:pixelated;background:white}h1,h2{margin:0 0 12px}</style><h1>터치 · 픽셀 직접 배치 1차</h1><p>38×24px 격자에 획과 테두리를 직접 지정한 초안입니다.</p>'
 for z in (1,4,12):page+=f'<section><h2>{z}배</h2><img src="touch-native.png" width="{38*z}" height="{24*z}"></section>'
 page+='<section><h2>옮겨 그리는 생성 원본</h2><img src="generation-reference.png" style="max-width:100%;height:auto;image-rendering:auto"></section><p><a href="pixels.txt">직접 지정한 픽셀 격자</a></p>'
 (OUT/'index.html').write_text(page,encoding='utf8');(OUT/'checks.json').write_text(json.dumps({'method':'hand-authored native pixel rows and coordinate spans','size':[38,24],'font_rendering':False,'source_resampling':False,'auto_contour_filter':False,'rom_built':False,'manifest_changed':False},indent=2),encoding='utf8')
if __name__=='__main__':main()
