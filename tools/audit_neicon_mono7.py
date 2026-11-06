"""Compare actual font files, including unmodified native font spacing."""
from pathlib import Path
import json, hashlib
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/graphics-draft/neicon-mono7-v1'
PATHS=[Path.home()/'AppData/Local/Microsoft/Windows/Fonts/Galmuri7.ttf',ROOT/'work/fonts/galmuri-mono7/GalmuriMono7.ttf']
FONTS=[ImageFont.truetype(str(p),8) for p in PATHS]

def draw_text(text,font):
    im=Image.new('L',(max(1,round(font.getlength(text))),9));d=ImageDraw.Draw(im);d.fontmode='1';d.text((0,0),text,font=font,fill=255)
    return im

def main():
    manifest=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
    chars=sorted(set(''.join(r['localization']['korean_proposal'] for r in manifest['graphics'] if r['edition']=='jp' and r['key'].startswith('NEIcon') and r.get('localization',{}).get('editing_method')=='galmuri')))
    records=[]
    for c in chars:
        a,b=[draw_text(c,f) for f in FONTS]
        records.append({'char':c,'old_advance':FONTS[0].getlength(c),'mono_advance':FONTS[1].getlength(c),'old_ink_bbox':a.getbbox(),'mono_ink_bbox':b.getbbox(),'same_mask_and_advance':a.size==b.size and a.tobytes()==b.tobytes()})
    report={'source_page':'https://typedia.kr/font/galmurimono7/','official_page':'https://quiple.dev/font/galmuri','download':'https://raw.githubusercontent.com/quiple/galmuri/main/dist/GalmuriMono7.ttf','font_sha256':hashlib.sha256(PATHS[1].read_bytes()).hexdigest(),'license':'work/fonts/galmuri-mono7/ofl.md','compared_characters':len(records),'different_characters':[r['char'] for r in records if not r['same_mask_and_advance']],'all_139_output_files_identical_to_v9':True,'characters':records}
    for p in (ROOT/'work/graphics-draft/neicon-v9').glob('NEIcon*-korean.png'):
        assert p.read_bytes()==(OUT/p.name).read_bytes()
    (ROOT/'metadata/neicon_mono7_font_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet=Image.new('RGB',(680,380),'#eeeeea');d=ImageDraw.Draw(sheet)
    for row,text in enumerate(['벤치','치비 출발 도착점','iIlMW 0123']):
        for col,font in enumerate(FONTS):
            x=15+col*335;y=10+row*125
            d.text((x,y),['Galmuri7 (8px)','GalmuriMono7 (8px)'][col],fill='black')
            mask=draw_text(text,font);sample=Image.new('RGB',mask.size,'white');sample.paste('black',(0,0,*mask.size),mask)
            sheet.paste(sample,(x,y+20));big=sample.resize((sample.width*4,sample.height*4),Image.Resampling.NEAREST);sheet.paste(big,(x,y+45))
    sheet.save(OUT/'mono-font-proof.png')
    page='<meta charset="utf-8"><style>body{font:17px/1.7 sans-serif;padding:24px;background:#eee}img{image-rendering:pixelated}</style><h1>Galmuri7 / GalmuriMono7 실제 파일 비교</h1><p>왼쪽은 기존 Galmuri7, 오른쪽은 공식 GalmuriMono7입니다. 양쪽 모두 정규8px, 폰트 기본 간격 그대로이며 자간 조정·가로축소를 하지 않았습니다.</p><img src="mono-font-proof.png"><p>벤은 흰 획7×7px, 치는6×7px로 두 폰트에서 같습니다. 한글 자리 폭은 모두8px입니다. Mono는 영문·숫자·공백을4px로 맞추지만 한글 자형 자체를7×7로 늘리는 기능은 아닙니다.</p><p>NEIcon 전체에 폰트만 교체한 결과139개 PNG 모두 v9와 동일했습니다. 기존 배치를 고정한 비교이므로 칸에 맞추기 위한 v9의 자간 조정은 유지되어 있습니다.</p><p><a href="index.html#NEIconOIBench-cell-0">전체 비교판 · 벤치</a> · <a href="https://typedia.kr/font/galmurimono7/">사용자 제공 소개</a> · <a href="https://quiple.dev/font/galmuri">제작자 배포처</a></p>'
    (OUT/'font-audit.html').write_text(page,encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='characters'},ensure_ascii=False))

if __name__=='__main__':main()
