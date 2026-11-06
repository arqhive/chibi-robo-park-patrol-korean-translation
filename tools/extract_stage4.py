"""Read-only text/container/graphics inventory for both source ROM editions."""
import copy
from collections import Counter
import html
import json
import re
import struct
from pathlib import Path

import ndspy.bmg
import ndspy.narc
import ndspy.texture
import ndspy.color
from PIL import Image,ImageDraw,ImageFont

from inspect_roms import ROOT,INPUTS,save,sha
from analyze_resources import message_repr
from extract_graphics import characters,palette,cells,background,tile_sheet,texture_blocks,colors

OUT=ROOT/'work/stage4'


def scan_strings(data, location):
    """Conservative NUL-terminated candidates, never certified display text."""
    result=[]
    jp=re.compile(r'[ぁ-ヺ一-鿿]')
    kana=re.compile(r'[ぁ-ヺ]')
    for match in re.finditer(rb'[^\x00]{4,512}\x00',data):
        raw=match[0][:-1]
        try:text=raw.decode('cp932')
        except UnicodeDecodeError:continue
        if len(jp.findall(text))<2 or not kana.search(text):continue
        if not all(c.isprintable() or c in '\n\t\r' for c in text):continue
        result.append({'location':location,'offset':match.start(),'encoding':'cp932','text':text,'status':'heuristic_candidate_unverified'})
    for alignment in [0,1]:
        usable=data[alignment:len(data)-(len(data)-alignment)%2]
        decoded=usable.decode('utf-16le',errors='replace')
        for m in re.finditer(r'[\x20-\x7e\u3000-\u30ff\u4e00-\u9fff\uff01-\uffef\n\r]{4,256}\x00',decoded):
            text=m[0][:-1]
            if len(jp.findall(text))<2 or not kana.search(text):continue
            result.append({'location':location,'offset':alignment+m.start()*2,'encoding':'utf-16le','text':text,'status':'heuristic_candidate_unverified'})
    return result


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    previous_path=ROOT/'metadata/extraction_manifest.json'
    previous=json.loads(previous_path.read_text(encoding='utf-8')) if previous_path.exists() else {}
    old_assets={(r['edition'],r['key']):r for r in previous.get('graphics',[])}
    originals=json.loads((ROOT/'metadata/originals.json').read_text(encoding='utf-8'))
    inventories={e:{r['path']:r for r in json.loads((ROOT/f'metadata/inventory_{e}.json').read_text(encoding='utf-8'))['files']} for e in ['jp','us']}
    assets=[];failures=[];archive_rows=[];scan_rows=[];text_rows=[];text_checks=[];texture_counts={};banner_rows=[]

    def emit(edition,key,kind,im,refs,**extra):
        im=im.convert('RGBA');digest=sha(struct.pack('<II',*im.size)+im.tobytes())
        dest=OUT/'png'/f'{digest}.png';dest.parent.mkdir(exist_ok=True)
        if not dest.exists():im.save(dest)
        row={'edition':edition,'key':key,'kind':kind,'path':str(dest.relative_to(ROOT)),
             'width':im.width,'height':im.height,'pixel_sha256':digest,'source_files':refs,
             'status':'extracted_pending_text_review',**extra}
        old=old_assets.get((edition,key),{})
        if old.get('pixel_sha256')==digest and 'review' in old:
            row['review']=old['review'];row['status']=old['status']
        assets.append(row)

    for ed in ['jp','us']:
        inventory=inventories[ed];rom=(ROOT/INPUTS[ed]).read_bytes()
        assert sha(rom)==next(r['sha256'] for r in originals if r['edition']==ed)
        def read(name):
            r=inventory[name];b=rom[r['offset']:r['end']];assert sha(b)==r['sha256'];return b
        for name,row in inventory.items():
            ext=Path(name).suffix.lower()
            data=read(name)
            if ext=='.bmg':
                bmg=ndspy.bmg.BMG(data);records=[]
                for idx,m in enumerate(bmg.messages):
                    rep=message_repr(m)
                    record={'edition':ed,'file':name,'index':idx,'source_text':''.join(p for p in rep['parts'] if isinstance(p,str)),
                            'source_parts':rep['parts'],'translation_parts':None,'speaker':None,'speaker_status':'unresolved',
                            'attributes':rep['attributes'],'is_null':rep['is_null'],'status':'untranslated' if rep['parts'] else 'empty'}
                    records.append(record);text_rows.append(record)
                # Read the exported representation, not the old message objects.
                loaded=json.loads(json.dumps(records,ensure_ascii=False))
                reconstructed=copy.deepcopy(bmg)
                for m,r in zip(reconstructed.messages,loaded):
                    m.stringParts=[p if isinstance(p,str) else ndspy.bmg.Message.Escape(p['type'],bytes.fromhex(p['data'])) for p in r['source_parts']]
                    m.info=bytes.fromhex(r['attributes']);m.isNull=r['is_null']
                assert reconstructed.save()==data
                text_checks.append({'edition':ed,'file':name,'messages':len(records),'json_to_bmg_byte_identical':True})
            elif ext=='.arc':
                arc=ndspy.narc.NARC(data)
                assert arc.save()==data
                for i,member in enumerate(arc.files):
                    out=OUT/'archives'/ed/Path(name).stem/f'{i:04}.bin';out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(member)
                    location=f'{name}#{i}'
                    archive_rows.append({'edition':ed,'container':name,'member':i,'size':len(member),'sha256':sha(member),'magic':member[:4].hex(),'path':str(out.relative_to(ROOT))})
                    if ed=='jp':scan_rows.extend(scan_strings(member,location))
            if ed=='jp' and ext in ['.hmb','.bin','.dat','.txt']:
                scan_rows.extend(scan_strings(data,name))
            if ext=='.ncgr':
                stem=str(Path(name).with_suffix(''));palname=stem+'.NCLR';cellname=stem+'.NCER';scrname=stem+'.NSCR'
                try:
                    raw,bpp,dims=characters(data);pal=palette(read(palname))
                    refs=[name,palname]
                    if cellname in inventory:
                        frames=cells(read(cellname),raw,bpp,pal)
                        for im,info in frames:emit(ed,f'{stem}/cell/{info["cell"]}','sprite_cell',im,refs+[cellname],**info)
                    elif scrname in inventory:
                        emit(ed,f'{stem}/screen','tile_background',background(read(scrname),raw,bpp,pal),refs+[scrname])
                    else:
                        emit(ed,f'{stem}/tiles','unassembled_tiles',tile_sheet(raw,bpp,pal),refs,issues=['no_cell_or_screen_map'])
                except Exception as e:
                    failures.append({'edition':ed,'file':name,'stage':'2D_decode','error':str(e) or type(e).__name__})
                    try:
                        raw,bpp,dims=characters(data);pal=palette(read(palname))
                        emit(ed,f'{stem}/fallback_tiles','unassembled_tiles',tile_sheet(raw,bpp,pal),[name,palname],issues=['screen_or_cell_decode_failed'])
                    except Exception:
                        pass  # original explicit decode failure remains in manifest
            if ext in ['.nsbmd','.nsbtx']:
                try:
                    found=False
                    for block in texture_blocks(data):
                        found=True
                        for texname,tex in block['textures']:
                            texture_counts[ed]=texture_counts.get(ed,0)+1
                            pals=dict(block['palettes'])
                            matches=[n for n in pals if n in [texname,(texname+'_pl')[:15],(texname+'_pl')[:16]]]
                            if tex.format.name=='A1BGR5':candidates=[(None,None)];method='direct_color'
                            elif len(matches)==1:candidates=[(matches[0],pals[matches[0]])];method='name_match_not_material_binding'
                            elif len(pals)==1:candidates=list(pals.items());method='single_palette'
                            else:candidates=list(pals.items());method='all_palette_candidates_binding_unresolved'
                            if not candidates:
                                failures.append({'edition':ed,'file':name,'texture':texname,'stage':'texture_palette','error':'No local palette'});continue
                            rendered=0
                            for palname,pal in candidates:
                                try:
                                    # ndspy 4.2 Palette stores ColorTuple while its texture
                                    # renderer expects packed BGR555 LUT indices.
                                    packed=None if pal is None else [ndspy.color.pack(*c) for c in pal.colors]
                                    im=ndspy.texture.renderTextureDataAsImage(tex.data1,tex.data2,tex.format,tex.width,tex.height,packed,tex.isColor0Transparent)
                                    emit(ed,f'{name}/texture/{texname}/palette/{palname}','model_texture',im,[name],texture=texname,palette=palname,format=tex.format.name,palette_method=method,parser_notes=block['parser_notes'])
                                    rendered+=1
                                except Exception as e:
                                    if method!='all_palette_candidates_binding_unresolved':raise
                            if not rendered:raise ValueError(f'No usable palette for {texname}')
                    if not found:
                        failures.append({'edition':ed,'file':name,'stage':'model_texture_binding','error':'No embedded TEX0; material/external texture binding not resolved','not_decode_failure':True})
                except Exception as e:failures.append({'edition':ed,'file':name,'stage':'texture_decode','error':str(e) or type(e).__name__})
            if ext=='.ntft':
                palname=str(Path(name).with_suffix('.ntfp'))
                try:
                    pal=colors(read(palname));assert len(data)==32768 and len(pal)==256
                    # Unheadered resources: save both plausible layouts, never call either proven.
                    emit(ed,f'{name}/candidate/tiled256x128','raw_texture_candidate',tile_sheet(data,8,pal,32),[name,palname],issues=['dimensions_and_layout_unverified'])
                    im=Image.new('RGBA',(256,128));im.putdata([pal[v] for v in data])
                    emit(ed,f'{name}/candidate/linear256x128','raw_texture_candidate',im,[name,palname],issues=['dimensions_and_layout_unverified'])
                except Exception as e:failures.append({'edition':ed,'file':name,'stage':'raw_texture','error':str(e)})
        for part in ['arm9','arm7']:
            data=(ROOT/f'work/extracted/{ed}/{part}.bin').read_bytes()
            if ed=='jp':scan_rows.extend(scan_strings(data,part))
        banner_at=struct.unpack_from('<I',rom,0x68)[0];banner=rom[banner_at:banner_at+0x840]
        im=tile_sheet(banner[0x20:0x220],4,colors(banner[0x220:0x240]),4)
        emit(ed,'banner/icon','banner_icon',im,['NDS banner'])
        for i,lang in enumerate(['Japanese','English','French','German','Italian','Spanish']):
            text=banner[0x240+i*256:0x340+i*256].decode('utf-16le').split('\0')[0]
            banner_rows.append({'edition':ed,'language':lang,'source_text':text,'translation':None,'status':'external_system_font_policy_pending'})
        assert sha((ROOT/INPUTS[ed]).read_bytes())==next(r['sha256'] for r in originals if r['edition']==ed)

    # Stable source inventory is tracked; edits never silently overwrite translation work.
    for ed in ['jp','us']:
        dest=ROOT/'translations'/f'{ed}-source.json';records=[r for r in text_rows if r['edition']==ed]
        if dest.exists():
            assert json.loads(dest.read_text(encoding='utf-8'))==records,'Existing source inventory differs; review before replacement'
        else:save(dest,records)
    us={r['key']:r for r in assets if r['edition']=='us'}
    for r in assets:
        if r['edition']=='jp':
            other=us.get(r['key']);r['regional_pixel_difference']=None if other is None else r['pixel_sha256']!=other['pixel_sha256']
    # Supplemental audits must be refreshed with review_stage4.py after extraction.
    save(ROOT/'metadata/extraction_manifest.json',{'schema':1,'graphics':assets,'archives':archive_rows,'failures_and_unresolved':failures,'banner_text':banner_rows,'supplemental_audit_needs_refresh':True})
    save(OUT/'extra-string-candidates.json',scan_rows)
    save(ROOT/'metadata/text_extraction_checks.json',text_checks)
    report={'graphics_by_edition':{ed:dict(Counter(r['kind'] for r in assets if r['edition']==ed)) for ed in ['jp','us']},
            'texture_records_before_palette_variants':texture_counts,'unique_pixel_images':len({r['pixel_sha256'] for r in assets}),
            'jp_regional_differences':sum(r.get('regional_pixel_difference') is True for r in assets),
            'extra_string_candidates':len(scan_rows),'extra_strings_by_location':dict(Counter(r['location'] for r in scan_rows)),
            'narc_members':len(archive_rows),'issues':dict(Counter(r['stage'] for r in failures)),
            'bmg_json_roundtrip_all_passed':True,'original_rom_hashes_unchanged':True}
    save(ROOT/'metadata/stage4_extraction.json',report)
    make_review(assets,report)
    print(json.dumps(report,ensure_ascii=False,indent=2))


def make_review(assets,report):
    jp=[r for r in assets if r['edition']=='jp'];us={r['key']:r for r in assets if r['edition']=='us'}
    for category,subset in [('ui',[r for r in jp if r['kind'] in ['sprite_cell','tile_background','unassembled_tiles','banner_icon']]),('models',[r for r in jp if r['kind']=='model_texture']),('raw',[r for r in jp if r['kind']=='raw_texture_candidate'])]:
        seen=set();unique=[]
        for r in subset:
            if r['pixel_sha256'] not in seen:seen.add(r['pixel_sha256']);unique.append(r)
        # Review every unique source image, with lookup IDs for classifications.
        cards=[]
        for i,r in enumerate(unique):
            img='png/'+Path(r['path']).name
            other=us.get(r['key']);compare='' if not other else f'<img loading="lazy" src="png/{Path(other["path"]).name}">'
            cards.append(f'<article data-diff="{r.get("regional_pixel_difference")}"><b>{category}-{i:04}</b> {html.escape(r["key"])}<br>{r["width"]}×{r["height"]} · JP / US<br><img loading="lazy" src="{img}">{compare}</article>')
        (OUT/f'{category}.html').write_text('<!doctype html><meta charset="utf-8"><title>치비로보 원본 그래픽</title><style>body{font:15px sans-serif;background:#e7e9ee}article{border:1px solid #aaa;background:white;padding:14px;margin:12px;overflow-wrap:anywhere}img{image-rendering:pixelated;max-width:100%;vertical-align:top;background:repeating-conic-gradient(#bbb 0% 25%,#ddd 0% 50%) 0/16px 16px;margin:8px}article[data-diff="True"]{border:3px solid #cd6500}</style><h1>원본 그래픽 · '+category+'</h1><p>주황 테두리는 두 지역의 픽셀 차이입니다. 번역 대상 확정 표시가 아닙니다.</p>'+''.join(cards),encoding='utf-8')
        font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',13)
        for page in range((len(unique)+59)//60):
            sheet=Image.new('RGB',(1200,1200),'#c8ccd2');d=ImageDraw.Draw(sheet)
            for n,r in enumerate(unique[page*60:(page+1)*60]):
                x=(n%6)*200;y=(n//6)*120
                im=Image.open(ROOT/r['path']).convert('RGBA');im.thumbnail((190,94),Image.Resampling.NEAREST)
                sheet.paste(im,(x+(190-im.width)//2,y+22),im)
                d.text((x+4,y+2),f'{category}-{page*60+n:04}',font=font,fill='black')
            sheet.save(OUT/f'{category}-contact-{page:02}.png')
        save(OUT/f'{category}-review-index.json',[{'review_id':f'{category}-{i:04}',**r} for i,r in enumerate(unique)])
    (OUT/'index.html').write_text('''<!doctype html><meta charset="utf-8"><title>치비로보 전수 추출</title><style>body{font:18px sans-serif;margin:40px;line-height:1.8;max-width:1000px}pre{white-space:pre-wrap;font-size:14px}</style><h1>4단계 전수 추출</h1><p><a href="ui.html">UI·타일·배너 원본 대조</a> / <a href="models.html">모델 텍스처 원본 대조</a> / <a href="raw.html">헤더 없는 텍스처 후보</a></p><p>일본어 본문은 translations/jp-source.json, 북미 대조는 us-source.json에 추출했습니다. 태그·속성을 포함한 JSON에서 BMG로의 무변경 왕복을 확인했습니다. 화자와 미연결 창, 팔레트 일부·모델 바인딩은 미확정입니다. 미해석 효과를 포함한 화면 재현이나 원문 후보의 실제 표시 여부까지 검증한 것은 아닙니다.</p><pre>'''+html.escape(json.dumps(report,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')


if __name__=='__main__':main()
