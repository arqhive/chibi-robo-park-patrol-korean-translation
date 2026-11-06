"""Create a standalone local editor seeded with the latest 16x16 label draft."""
from pathlib import Path
import hashlib,json
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]

def main():
    source=ROOT/'work/graphics-draft/dayresult-myeong-white-v1/after.png'
    im=Image.open(source).convert('RGBA');assert im.size==(16,16)
    pixels=list(im.tobytes());digest=hashlib.sha256(source.read_bytes()).hexdigest()[:16]
    template=(ROOT/'tools/templates/myeong_pixel_editor.html').read_text(encoding='utf8')
    out=ROOT/'work/graphics-review/myeong-pixel-editor';out.mkdir(parents=True,exist_ok=True)
    (out/'index.html').write_text(template.replace('__SEED__',json.dumps(pixels,separators=(',',':'))).replace('__HASH__',digest),encoding='utf8')
    print(out/'index.html')

if __name__=='__main__':main()
