"""Imagegen review sprites at source dimensions, with native palette antialiasing."""
from pathlib import Path
import json,hashlib
import numpy as np
from scipy import ndimage as nd
from PIL import Image
from extract_graphics import palette
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'work/graphics-draft/title-save-imagegen-fit-v1'
ITEMS=[('TitleSave-cell-50','여기를','title-here-imagegen-v1',(40,24)),('TitleSave-cell-51','터치!','title-tap-imagegen-v1',(48,24))]
def main():
 OUT.mkdir(exist_ok=False);inv=json.loads((ROOT/'metadata/inventory_jp.json').read_text('utf8'))['files'];r=next(r for r in inv if r['path']=='TitleSave.NCLR');pal=palette((ROOT/'work/extracted/jp'/r['disk_file']).read_bytes());sw=np.array(sorted({c[:3] for c in pal[1:]}),int);recs=[]
 for stem,text,folder,size in ITEMS:
  source=ROOT/'work/graphics-draft'/folder/'generated-original.png';a=np.array(Image.open(source).convert('RGBA'));labels,n=nd.label(a[:,:,3]>=128);sizes=np.bincount(labels.ravel());sizes[0]=0;main=labels==sizes.argmax();y,x=np.where(main);rect=[int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)];crop=Image.fromarray(a).crop(rect)
  factor=min((size[0]-2)/crop.width,20/crop.height);w=round(crop.width*factor);h=round(crop.height*factor);small=crop.resize((w,h),Image.Resampling.LANCZOS)
  q=np.array(small);alpha=q[:,:,3].astype(float)/255;rgb=np.rint(q[:,:,:3]*alpha[:,:,None]+255*(1-alpha[:,:,None])).astype('uint8')
  distance=((rgb[:,:,None,:].astype(int)-sw[None,None,:,:])**2).sum(3);rgb=sw[distance.argmin(2)].astype('uint8')
  canvas=Image.new('RGBA',size,'white');xy=((size[0]-w)//2,(size[1]-h)//2);canvas.paste(Image.fromarray(rgb).convert('RGBA'),xy);canvas.save(OUT/(stem+'-reduced.png'))
  assert np.all(np.array(canvas)[:,:,3]==255);assert all(tuple(p[:3]) in set(map(tuple,sw)) for p in canvas.get_flattened_data())
  recs.append({'key':stem.replace('-cell-','/cell/'),'text':text,'generated_source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'crop':rect,'sprite_size':list(size),'artwork_size':[w,h],'placement':list(xy),'opaque_white_background':True,'palette_unmatched_pixels':0})
  print(text,w,h,xy)
 (OUT/'checks.json').write_text(json.dumps(recs,ensure_ascii=False,indent=2),encoding='utf8')
 sheet=Image.new('RGB',(1000,420),'white')
 for i,(stem,text,folder,size) in enumerate(ITEMS):
  a=Image.open(OUT/(stem+'-reduced.png'));sheet.paste(a,(10,i*210+5));sheet.paste(a.resize((size[0]*8,size[1]*8),Image.Resampling.NEAREST),(10,i*210+35))
 sheet.save(OUT/'inspection.png')
if __name__=='__main__':main()
