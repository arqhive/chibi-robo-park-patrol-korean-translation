"""Read-only follow-up: material bindings, extra text refs, maps and tiny labels."""
from collections import Counter, defaultdict
import json
import html
import re
import struct
from pathlib import Path
from PIL import Image
from inspect_roms import ROOT, save, sha
from extract_graphics import blocks, characters, palette, background, colors, texture_blocks

OUT=ROOT/'work/stage4-followup'


def load(path):
    return json.loads((ROOT/path).read_text(encoding='utf-8'))


def u32(b,p):return struct.unpack_from('<I',b,p)[0]


def dictionary(b,p,unit):
    count=b[p+1];size=struct.unpack_from('<H',b,p+2)[0]
    e=p+struct.unpack_from('<H',b,p+6)[0]
    size_of_entry,names=struct.unpack_from('<HH',b,e)
    assert size_of_entry==unit and p+size<=len(b)
    assert e+names+count*16<=p+size
    return [(b[e+names+i*16:e+names+(i+1)*16].rstrip(b'\0').decode('ascii'),b[e+4+i*unit:e+4+(i+1)*unit]) for i in range(count)]


def subfiles(b):
    for i in range(struct.unpack_from('<H',b,14)[0]):
        p=u32(b,16+4*i);size=u32(b,p+4)
        assert p+size<=len(b)
        yield b[p:p+4],b[p:p+size]


def materials(b):
    result=[]
    for magic,section in subfiles(b):
        if magic!=b'MDL0':continue
        for model,value in dictionary(section,8,4):
            start=u32(value,0);end=start+u32(section,start)
            assert end<=len(section)
            m=section[start:end];at=u32(m,8);count=m[24]
            entries=dictionary(m,at+4,4);assert len(entries)==count
            rows=[{'model':model,'material':n,'texture':None,'palette':None} for n,v in entries]
            for kind,off in zip(['texture','palette'],struct.unpack_from('<HH',m,at)):
                for name,v in dictionary(m,at+off,4):
                    offset,n,_=struct.unpack('<HBB',v)
                    # Verified against all material indices: this offset is relative
                    # to the material list, not the dictionary entry as some notes say.
                    assert at+offset+n<=len(m)
                    for index in m[at+offset:at+offset+n]:
                        assert index<count and rows[index][kind] is None
                        rows[index][kind]=name
            result.extend(rows)
    return result


def thumb_literal_refs(code,targets):
    found=defaultdict(list)
    for p in range(0,min(0x117000,len(code)-1),2):
        w=struct.unpack_from('<H',code,p)[0]
        if w&0xf800==0x4800:
            literal=((p+4)&~3)+(w&255)*4
            if literal in targets:found[literal].append(p)
    return found


def tagged_string(b,p):
    start=p;parts=[];chunk=bytearray()
    while b[p]:
        if b[p]==0x1a:
            if chunk:parts.append(chunk.decode('cp932'));chunk.clear()
            length=b[p+1];assert 3<=length<=64
            parts.append({'escape_hex':b[p:p+length].hex()});p+=length
        else:chunk.append(b[p]);p+=1
        assert p-start<512
    if chunk:parts.append(chunk.decode('cp932'))
    return parts,b[start:p+1]


def main():
    OUT.mkdir(exist_ok=True)
    master=load('metadata/extraction_manifest.json');findings={}
    a=(ROOT/'work/extracted/jp/arm9.bin').read_bytes()
    # Keep extension investigations separate from already-reviewed PNG ordering.
    extra_assets=[];material_rows=[];pattern_rows=[]
    for ed in ['jp','us']:
        inv={r['path']:r for r in load(f'metadata/inventory_{ed}.json')['files']}
        def read(name):
            r=inv[name];data=(ROOT/f'work/extracted/{ed}'/r['disk_file']).read_bytes()
            assert sha(data)==r['sha256'];return data
        textures=defaultdict(list);palettes=defaultdict(list);local={}
        for name in inv:
            if not name.endswith(('.nsbmd','.nsbtx')):continue
            tex={};pal={}
            for section in texture_blocks(read(name)):
                for n,t in section['textures']:
                    sig=sha(str((t.width,t.height,t.format.name,t.isColor0Transparent)).encode()+t.data1+t.data2)
                    textures[n].append({'file':name,'sha256':sig});tex[n]=sig
                for n,p in section['palettes']:
                    sig=sha(bytes(c for rgba in p.colors for c in rgba));palettes[n].append({'file':name,'sha256':sig});pal[n]=sig
            local[name]=(tex,pal)
        for name in inv:
            if name.endswith('.nsbmd'):
                rows=materials(read(name));pairs=[]
                for row in rows:
                    row.update(edition=ed,file=name)
                    for kind,catalog,own in [('texture',textures,local[name][0]),('palette',palettes,local[name][1])]:
                        n=row[kind]
                        if n is None:state='not_declared';candidates=[]
                        elif n in own:state='local_name_binding';candidates=[{'file':name,'sha256':own[n]}]
                        else:
                            candidates=catalog.get(n,[])
                            state='missing' if not candidates else 'external_unique_content_name_match' if len({v['sha256'] for v in candidates})==1 else 'external_multiple_content_candidates'
                        row[kind+'_binding']={'status':state,'candidates':candidates}
                    pairs.append(row)
                material_rows.extend(pairs)
            elif name.endswith('.nsbtp'):
                for magic,b in subfiles(read(name)):
                    assert magic==b'PAT0'
                    for anim,v in dictionary(b,8,4):
                        start=u32(v,0);frames,nt,np,to,po=struct.unpack_from('<HBBHH',b,start+4)
                        tex=[b[start+to+i*16:start+to+(i+1)*16].rstrip(b'\0').decode() for i in range(nt)]
                        pal=[b[start+po+i*16:start+po+(i+1)*16].rstrip(b'\0').decode() for i in range(np)]
                        tracks=[]
                        for mat,v in dictionary(b,start+12,8):
                            n,unknown,off=struct.unpack('<IHH',v);keys=[]
                            for i in range(n):
                                frame,t,p=struct.unpack_from('<HBB',b,start+off+i*4)
                                assert t<nt and p<np and frame<=frames
                                keys.append({'frame':frame,'texture':tex[t],'palette':pal[p]})
                            tracks.append({'material':mat,'keys':keys})
                        pattern_rows.append({'edition':ed,'file':name,'animation':anim,'frames':frames,'textures':tex,'palettes':pal,'tracks':tracks})
        # Same-base associations are structural candidates, not runtime claims.
        pairs={'EditBGB':'EditBGA','NewBGGrid':'NewBG','NewPCBGGrid':'NewPCBG','BGDesktop':'PCBG','BGMPWindow':'PCBG'}
        for scr,source in pairs.items():
            try:
                raw,bpp,_=characters(read(source+'.NCGR'));pal=palette(read(source+'.NCLR'))
                im=background(read(scr+'.NSCR'),raw,bpp,pal)
                path=OUT/f'{ed}-{scr}-using-{source}.png';im.save(path)
                extra_assets.append({'edition':ed,'kind':'screen_pair_candidate','screen':scr+'.NSCR','tiles':source+'.NCGR','palette':source+'.NCLR','path':str(path.relative_to(ROOT)),
                                     'status':'same_loader_call_pair_verified' if ed=='jp' and scr in ['NewBGGrid','NewPCBGGrid'] else 'visually_coherent_structural_pair_runtime_binding_unverified',
                                     'visual_text_review':'No Japanese text identified; grid/window/background pattern. Only upper 192 of 256 rows normally visible on DS.'})
            except (AssertionError,KeyError) as e:
                extra_assets.append({'edition':ed,'kind':'screen_pair_candidate','screen':scr+'.NSCR','tiles':source+'.NCGR','status':'candidate_rejected_bounds','error':str(e)})
        for n in range(3):
            raw=read('MasterSky00.ntft');pal=colors(read(f'MasterSky{n:02}.ntfp'))
            im=Image.new('RGBA',(256,128));im.putdata([pal[v] for v in raw]);path=OUT/f'{ed}-MasterSky{n:02}.png';im.save(path)
            extra_assets.append({'edition':ed,'kind':'sky_palette_variant','texture':'MasterSky00.ntft','palette':f'MasterSky{n:02}.ntfp','path':str(path.relative_to(ROOT)),'status':'shared_resource_table_linked_layout_visually_inferred' if ed=='jp' else 'same_names_comparison_candidate'})

    findings['materials']=material_rows;findings['patterns']=pattern_rows;findings['supplemental_png']=extra_assets
    inventories={ed:{r['path']:r for r in load(f'metadata/inventory_{ed}.json')['files']} for ed in ['jp','us']}
    def resource(ed,name):
        return (ROOT/f'work/extracted/{ed}'/inventories[ed][name]['disk_file']).read_bytes()
    # A bad JP screen pairing is an original-data inconsistency, not an excuse to
    # silently replace a source file. Use the US map for identification only.
    assert resource('jp','Red_White.NSCR')==resource('jp','TitleSaveBG.NSCR')
    raw,bpp,_=characters(resource('jp','Red_White.NCGR'))
    im=background(resource('us','Red_White.NSCR'),raw,bpp,palette(resource('jp','Red_White.NCLR')))
    redpath=OUT/'jp-Red_White-using-us-map.png';im.save(redpath)
    findings['red_white']={'jp_map_identical_to':'TitleSaveBG.NSCR','jp_map_tile_max':767,'jp_tiles_available':len(raw)//(8*bpp),
                          'comparison_map':'us/Red_White.NSCR','path':str(redpath.relative_to(ROOT)),
                          'visual_identification':'Red Nintendo logo; preserve original Latin branding.',
                          'original_jp_mapping_fixed':False,'runtime_usage_verified':False}
    # Test every same-stem NCGR/NCLR with enough tiles for this unresolved map.
    balloon=[]
    for name in inventories['jp']:
        if not name.endswith('.NCGR'):continue
        raw,bpp,_=characters(resource('jp',name))
        if len(raw)//(8*bpp)<312:continue
        pn=name[:-5]+'.NCLR'
        try:im=background(resource('jp','BGBalloon.NSCR'),raw,bpp,palette(resource('jp',pn)))
        except AssertionError:continue
        path=OUT/'balloon-candidates'/(name+'.png');path.parent.mkdir(exist_ok=True);im.save(path)
        balloon.append({'tiles':name,'palette':pn,'path':str(path.relative_to(ROOT))})
    assert len(balloon)==49
    findings['balloon']={'attempts':balloon,'review_result':'All 49 reconstructions contact-reviewed; no coherent intact balloon/window accepted. Dynamic VRAM tile rearrangement or obsolete data remains possible.'}
    text=[dict(r) for r in load('work/stage4/extra-string-candidates.json')[7:26]]
    for r in text:
        r['exact_address_literals_arm9']=[p for p in range(0,len(a)-3,4) if u32(a,p)==0x2000000+r['offset']]
        refs=thumb_literal_refs(a,set(r['exact_address_literals_arm9']))
        r['thumb_literal_load_candidates']=[{'instruction_offset':off,'pool_offset':pool} for pool,offs in refs.items() for off in offs]
        r['status']='referenced_by_output_or_choice_code_runtime_visibility_unverified' if refs else 'data_table_or_pointer_use_pending'
        r['runtime_verified']=False
    full_start=a.find('メッセージウェイト'.encode('cp932'));assert full_start==0x11d57c
    parts,raw=tagged_string(a,full_start)
    text[-1].update(offset=full_start,text=''.join(x for x in parts if isinstance(x,str)),source_parts=parts,source_hex=raw.hex(),
                    original_byte_length=len(raw)-1,previous_fragment_offset=0x11d595,
                    status='tagged_full_message_recovered',note='Old NUL scanner started after an embedded-zero tag. Full tag-aware source recovered.')
    text[-1]['exact_address_literals_arm9']=[p for p in range(0,len(a)-3,4) if u32(a,p)==0x2000000+full_start]
    text[-1]['thumb_literal_load_candidates']=[{'instruction_offset':off,'pool_offset':pool} for pool,offs in thumb_literal_refs(a,set(text[-1]['exact_address_literals_arm9'])).items() for off in offs]
    for r in text:
        if 0x11cbb0<=r['offset']<=0x11cbfc:
            r['status']='six_item_selection_table_referenced';r['selection_table_offset']=0x10b654
            r['table_consumer_offsets']=[0x6c1f6,0x6c21c]
        if 'source_parts' not in r:r['source_parts']=[r['text']]
        source=b''.join(p.encode('cp932') if isinstance(p,str) else bytes.fromhex(p['escape_hex']) for p in r['source_parts'])+b'\0'
        assert a[r['offset']:r['offset']+len(source)]==source
        r['source_hex']=source.hex();r['original_byte_length']=len(source)-1
        us=(ROOT/'work/extracted/us/arm9.bin').read_bytes();match=us.find(source)
        r['same_japanese_bytes_in_us_offset']=match if match>=0 else None
    # Search address-referenced strings with tag-aware termination as a cross-check.
    pointer_strings=[]
    for p in sorted({u32(a,i)-0x2000000 for i in range(0,len(a)-3,4) if 0x2110000<=u32(a,i)<0x2000000+len(a)}):
        try:parts,raw=tagged_string(a,p)
        except (AssertionError,UnicodeDecodeError,IndexError):continue
        t=''.join(v for v in parts if isinstance(v,str))
        if len(re.findall('[ぁ-ヺ一-鿿]',t))>=2 and re.search('[ぁ-ヺ]',t) and all(c.isprintable() or c in '\n\r\t' for c in t):pointer_strings.append(p)
    assert set(pointer_strings)=={r['offset'] for r in text}
    findings['tag_aware_pointer_scan']={'unique_japanese_strings':len(pointer_strings),'range_start':0x110000,'limitation':'Aligned absolute pointers into ARM9 data; indirect/address arithmetic/other encodings are not covered.'}
    findings['localized_us_save_labels']=[{'offset':p,'text':s} for p,s in [(0x11bfd4,'Please save in the house.'),(0x11bff0,'Save (Current %d)'),(0x11c010,'Quit'),(0x11c018,'Load (Current %d)')]]
    for r in findings['localized_us_save_labels']:assert us[r['offset']:r['offset']+len(r['text'])+1]==r['text'].encode()+b'\0'
    findings['extra_strings']=text
    findings['sky_resource_table']={'table_offset':0x131b44,'texture_pointer':u32(a,0x131b44),'palette_pointers':[u32(a,0x131b48+i*4) for i in range(3)],'note':'One texture filename followed by three sky palette filenames; adjacent end_bg record repeats its sole palette three times.'}
    counts={}
    for ed in ['jp','us']:
        rows=[r for r in material_rows if r['edition']==ed]
        no_tex_files={r['file'] for r in master['failures_and_unresolved'] if r['edition']==ed and r['stage']=='model_texture_binding'}
        byfile=defaultdict(list)
        for r in rows:byfile[r['file']].append(r)
        counts[ed]={'model_files_parsed':len(byfile),'materials':len(rows),'texture_binding_states':dict(Counter(r['texture_binding']['status'] for r in rows)),
                    'palette_binding_states':dict(Counter(r['palette_binding']['status'] for r in rows)),
                    'no_tex0_files_without_texture_name':sum(not any(r['texture'] for r in byfile[n]) for n in no_tex_files),
                    'no_tex0_files_with_texture_name':sum(any(r['texture'] for r in byfile[n]) for n in no_tex_files),
                    'pattern_files_parsed':len({r['file'] for r in pattern_rows if r['edition']==ed})}
    findings['summary']=counts
    save(OUT/'technical-findings.json',findings)
    finalize(master,findings)
    print(json.dumps(counts,ensure_ascii=False,indent=2))


def finalize(master,findings):
    from review_stage4 import UNCLEAR_UI,UNCLEAR_MODELS,STYLE
    original=[]
    for cat,numbers in [('ui',UNCLEAR_UI),('models',UNCLEAR_MODELS)]:
        rows=load(f'work/stage4/{cat}-review-index.json')
        original.extend(rows[i] for i in sorted(numbers))
    decisions=[]
    for r in original:
        rid=r['review_id'];i=int(rid.split('-')[1]);status='text_legibility_pending'
        note='확대·원본 대조 후에도 글자 판독 불가. 없는 글자로 간주하거나 임의 번역하지 않음.'
        if rid.startswith('ui-') and 870<=i<=881:
            status='nonlinguistic_fragment_preserve';note='전체 셀과 확대 PNG 재검토: 흰 선·테두리 조각이며 판독 가능한 일본어 글자 없음.'
        elif rid.startswith('ui-') and 1130<=i<=1134:
            status='numeric_symbol_preserve';note='100~500 숫자와 같은 단위 기호. 일본어 문구 아님.'
        elif rid=='ui-1269':
            status='nonlinguistic_color_blocks_preserve';note='PlayIcon 전체 셀과 비교한 분홍·초록 블록 도형. 일본어 글자로 판단하지 않음.'
        elif rid.startswith('ui-') and 178<=i<=181:
            status='original_latin_lettering_preserve';note='음료 캔의 SODA 형태 라틴 글자와 같은 캔의 찌그러진 도안. 일본어 교체 대상에서 제외.'
        elif rid.startswith('models-') and 793<=i<=796:
            status='nonlinguistic_label_marks_preserve';note='32px급 칩 그림의 라벨은 점·선 막대 표시. 판독 가능한 일본어 없음. 전체 칩의 신규 한글 합성 대상은 아님.'
        jp_us=next((v for v in master['graphics'] if v['edition']=='us' and v['key']==r['key']),None)
        decisions.append({'review_id':rid,'key':r['key'],'pixel_sha256':r['pixel_sha256'],'path':r['path'],
                          'width':r['width'],'height':r['height'],'status':status,'reason':note,
                          'same_pixels_as_us':jp_us is not None and jp_us['pixel_sha256']==r['pixel_sha256']})
    byhash={r['pixel_sha256']:r for r in decisions}
    bindings=defaultdict(list)
    for r in findings['materials']:
        if r['texture_binding']['status']=='local_name_binding' and r['palette_binding']['status'] in ['local_name_binding','not_declared']:
            bindings[(r['edition'],r['file'],r['texture'],r['palette'])].append((r['model'],r['material']))
    for r in master['graphics']:
        if r['edition']=='jp' and r['pixel_sha256'] in byhash:
            d=byhash[r['pixel_sha256']];r['status']=d['status'];r['review']={'classification':d['status'],'review_id':d['review_id'],'method':'native_and_enlarged_review_with_regional_comparison','note':d['reason']}
        if r['kind']=='model_texture':
            matches=bindings.get((r['edition'],r['source_files'][0],r['texture'],r['palette']),[])
            r['static_material_bindings']=[{'model':mo,'material':mat} for mo,mat in matches]
    # Keep all detailed parser evidence reproducible in work; compact status in master.
    master['extra_strings']=[r for r in master['extra_strings'] if r['status']=='rejected_binary_or_encoding_false_positive']+findings['extra_strings']
    pending=[r for r in decisions if r['status']=='text_legibility_pending']
    compact={'small_graphic_review':decisions,'materials_summary':findings['summary'],
             'extra_text_count':len(findings['extra_strings']),'tag_aware_scan':findings['tag_aware_pointer_scan'],
             'localized_us_save_labels':findings['localized_us_save_labels'],
             'sky_resource_table':findings['sky_resource_table'],
             'red_white':findings['red_white'],
             'balloon_pairing_attempts':49,
             'supplemental_png':findings['supplemental_png'],
             'remaining_small_graphic_count':len(pending),'cleared_small_graphic_count':len(decisions)-len(pending),
             'remaining_screen_maps':['BGBalloon.NSCR'],
             'original_map_inconsistency_preserved':['Red_White.NSCR'],
             'visually_coherent_but_code_unlinked_maps':['BGDesktop.NSCR','BGMPWindow.NSCR','EditBGB.NSCR'],
             'code_linked_maps':[{'screen':'NewBGGrid.NSCR','instruction_offset':0xa1026,'pool_offsets':[0xa1070,0xa1074]},
                                 {'screen':'NewPCBGGrid.NSCR','instruction_offset':0xed34,'pool_offsets':[0xed5c,0xed60]}],
             'technical_evidence':'work/stage4-followup/technical-findings.json',
             'full_runtime_verified':False}
    master['followup']=compact
    master['review_summary']['small_or_unclear_label_unique_png']=len(pending)
    for issue in master['failures_and_unresolved']:
        if issue['stage']=='model_texture_binding':
            rows=[r for r in findings['materials'] if r['edition']==issue['edition'] and r['file']==issue['file']]
            issue['followup_status']='external_texture_names_resolved_to_candidates' if any(r['texture'] for r in rows) else 'no_texture_binding_declared_in_materials'
    save(ROOT/'metadata/extraction_manifest.json',master)
    save(ROOT/'metadata/stage4_followup.json',{k:v for k,v in compact.items() if k!='small_graphic_review'})
    translated=[]
    for r in findings['extra_strings']:
        translated.append({'file':'arm9.bin','offset':r['offset'],'source_text':r['text'],'source_parts':r['source_parts'],'source_hex':r['source_hex'],'translation_parts':None,
                           'status':'scope_candidate_runtime_use_unverified','notes':'Reference and source bytes checked; do not inject without separate relocation/width validation.'})
    dest=ROOT/'translations/extra-source.json'
    if dest.exists():assert load('translations/extra-source.json')==translated,'Do not overwrite edited translation work'
    else:save(dest,translated)
    rows=''.join(f'<tr><td>{html.escape(r["review_id"])}</td><td>{html.escape(r["key"])}</td><td>{html.escape(r["reason"])}</td><td>{"같음" if r["same_pixels_as_us"] else "다름"}</td></tr>' for r in decisions)
    pictures=''.join(f'<article><b>{html.escape(r["review_id"])}</b> {html.escape(r["key"])}<br><img src="../stage4/png/{Path(r["path"]).name}"><img style="width:{r["width"]*4}px" src="../stage4/png/{Path(r["path"]).name}"></article>' for r in pending)
    maps=''.join(f'<article>{html.escape(r.get("screen",r.get("palette","")))} · {html.escape(r["status"])}<br><img src="{Path(r["path"]).name}"></article>' for r in findings['supplemental_png'] if r['edition']=='jp' and 'path' in r)
    texts=''.join(f'<tr><td>0x{r["offset"]:x}</td><td><pre>{html.escape(r["text"])}</pre></td><td>{"6항목 선택 테이블" if r["status"]=="six_item_selection_table_referenced" else "출력·선택 코드 참조"}</td><td>{"동일 원문 있음" if r["same_japanese_bytes_in_us_offset"] is not None else "동일 원문 미발견"}</td></tr>' for r in findings['extra_strings'])
    body=f'''<h1>피워라 치비로보! · 미확인 항목 추가 조사</h1><p>4단계 범위 승인 전, 사용자가 요청한 추가 조사 결과입니다. 정적 분석이며 게임 플레이 확인과 구분합니다.</p>
<table><tr><th>항목</th><th>추가로 확인한 것</th><th>남은 것</th></tr>
<tr><td>작은 그림 48개</td><td>숫자·기호·도형·라틴 글자 26개를 일본어 교체 대상에서 분리</td><td><a href="#small">22개는 확대해도 판독 불가</a></td></tr>
<tr><td>ARM9 문자열 19개</td><td>13개는 출력·선택 코드 참조, 6개는 선택 목록 테이블 소비 코드 확인. “30프레임”의 앞 문장과 태그 복원</td><td>일반 플레이·개발 메뉴 중 어느 쪽에서 노출되는지 미확인</td></tr>
<tr><td>배경 맵 7개</td><td>2개는 같은 로더 호출로 타일·팔레트 연결 확인. 3개는 자연스러운 창·배경 조합 발견. Red_White는 북미 배치표 대조로 Nintendo 로고 확인</td><td>BGBalloon은 49조합을 확인했으나 연결 미해결. 구조 후보 3개도 호출 연결 미확인. 일본판 Red_White 배치 불일치는 원본 그대로 보존</td></tr>
<tr><td>하늘 팔레트 2개</td><td>MasterSky00 타일과 함께 읽는 코드 확인. 저녁·밤색 PNG 추출</td><td>게임 중 시간대 전환은 미실행</td></tr>
<tr><td>모델</td><td>양 지역 각각 604파일 / 4,165재질 읽음. 기존 미연결 187파일 중 29개는 텍스처 이름 자체를 사용하지 않음</td><td>나머지 158파일은 외부 이름 후보 확인. 같은 이름의 일반·편집용 뱅크 등 실제 선택은 미확인</td></tr>
<tr><td>패턴 애니메이션</td><td>지역별 NSBTP 16파일의 텍스처·팔레트 전환 목록 해석</td><td>장면별 재생·외부 연결은 미확인</td></tr></table>
<p><a href="../../docs/stage4-code-connections.md">후속 코드 연결 조사 기록</a> — 일반·편집용 뱅크와 이벤트 테이블의 정적 연결을 추가 확인했습니다. 상위 진입 조건은 조사 중입니다.</p><h2>추가 문자열 원문</h2><p>북미판에는 저장 안내·저장·불러오기·종료가 영어로 존재합니다. 일본어가 그대로 남은 목록도 있어, 19개를 모두 개발용으로 제외하지 않습니다. 형식 태그와 %d 변수는 별도 원문 JSON에 보존했습니다.</p><table><tr><th>위치</th><th>원문</th><th>참조 근거</th><th>북미판 비교</th></tr>{texts}</table>
<h2>배경·하늘 후보</h2>{maps}<article>일본판 Red_White 타일 + 북미판 배치표 (식별용 재구성)<br><img src="jp-Red_White-using-us-map.png"><p>일본판 원래 배치표는 TitleSaveBG와 동일하여 단독 타일 수를 초과합니다. 이 비교는 원본 수정이나 실행 확인이 아닙니다.</p></article><h2 id="small">아직 판독하지 못한 22개</h2><p>작은 글자 픽셀 자체가 부족해 확대만으로 원문을 확정할 수 없습니다. 임의로 문구를 만들어 넣지 않습니다.</p>{pictures}
<details><summary>기존 48개 전체 재검토 사유</summary><table><tr><th>ID</th><th>자원</th><th>판정 근거</th><th>북미판 픽셀</th></tr>{rows}</table></details>
<h2>범위 결정용 제안</h2><p>본문 2,349항목·일본어 그림 후보 108묶음에, ARM9의 19개를 별도 번역 후보로 포함하는 안입니다. 작은 그림 22개와 호출 미확인 자원은 판정 보류로 유지하고 실행 중 연결될 때 확인합니다. 이번 조사에서 새로 확정한 일본어 그림은 없습니다.</p>
<p><a href="../stage4/index.html">최초 추출 결과</a> · <a href="../stage4/japanese-graphics.html">일본어 그림 후보</a></p>'''
    (OUT/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>피워라 치비로보! · 추가 조사</title>'+STYLE+body+'</html>',encoding='utf-8')
    initial=ROOT/'work/stage4/index.html'
    content=initial.read_text(encoding='utf-8')
    marker='<!-- followup-link -->'
    if marker not in content:
        content=content.replace('<h1>',marker+'<p class="note"><a href="../stage4-followup/index.html">추가 조사 결과 보기</a> — 아래는 최초 추출 요약입니다. 보류 48개 중 26개가 재분류되었으며 최신 근거는 추가 조사 화면을 보세요.</p><h1>',1)
        initial.write_text(content,encoding='utf-8')

    # Reapply the deeper JP code audit after this earlier survey refreshes the
    # master manifest. Keep all asset decisions in that same manifest.
    if (ROOT/'metadata/stage4_deep_connections.json').exists():
        from investigate_stage4_connections import main as trace_connections
        trace_connections()


if __name__=='__main__':main()
