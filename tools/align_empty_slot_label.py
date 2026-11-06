"""Move the restored empty-slot label down exactly one native pixel."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/empty-slot-align-v1'


def main():
    OUT.mkdir(exist_ok=True)
    before=Image.open(ROOT/'work/graphics-draft/batch01-v1/TitleSave-cell-26-korean.png').convert('RGBA')
    source=Image.open(ROOT/'work/graphics-draft/batch01-v1/TitleSave-cell-26-original.png').convert('RGBA')
    a=np.array(before);assert not np.any(a[-1,:,3])
    b=np.zeros_like(a);b[1:]=a[:-1]
    after=Image.fromarray(b);assert after.getbbox()==source.getbbox()==(0,4,32,13)
    after.save(OUT/'TitleSave-cell-26-korean.png')
    mask=np.maximum(np.array(source)[:,:,3],b[:,:,3]);Image.fromarray(mask).save(OUT/'TitleSave-cell-26-mask.png')
    preview=Image.new('RGBA',(104,16),(204,204,204,255))
    for x,im in [(0,source),(36,before),(72,after)]:preview.alpha_composite(im,(x,0))
    preview.resize((832,128),Image.Resampling.NEAREST).save(OUT/'comparison-8x.png')
    report={'offset_xy':[0,1],'previous_bbox':list(before.getbbox()),'new_bbox':list(after.getbbox()),'original_bbox':list(source.getbbox()),'size':list(after.size),'pixels_clipped':0,'glyph_pixels_unchanged':True,'output_sha256':hashlib.sha256((OUT/'TitleSave-cell-26-korean.png').read_bytes()).hexdigest()}
    (ROOT/'metadata/empty_slot_alignment_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
