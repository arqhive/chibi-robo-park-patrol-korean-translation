"""Curated visual groups, reviewed against all 509 source/result thumbnails.

This only classifies the review board; it never modifies artwork or captions.
Unknown future assets fail explicitly instead of silently inheriting a filename group.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = [
    ('cassette', '카세트', '컬렉션·상점·로그인·스티커의 카세트 그림을 함께 비교합니다.'),
    ('park', '공원 시설·지형 아이콘', '노란 바탕의 시설·지형 그림과 회색 비활성 상태입니다.'),
    ('toys', '장난감 캐릭터 아이콘', '캐릭터 선택 아이콘의 일반·회색 상태를 모았습니다.'),
    ('tools', '탈것·도구·칩 아이콘', '상점의 탈것, 도구, 칩과 품절 표시입니다.'),
    ('stickers', '스티커', '흰 테두리가 있는 수집 스티커 그림입니다. 카세트 모양은 카세트에서 비교합니다.'),
    ('weather-icons', '시간·날씨·쿠로 아이콘', '같은 해·달·쿠로 그림을 사용하는 화면들을 함께 비교합니다.'),
    ('launchers', '메뉴 선택 아이콘', '공원·상점·스티커 메뉴와 치비컴의 선택 타일입니다.'),
    ('buttons', '버튼·결정·취소·뒤로', '창 모양, 긴 사각형, 둥근 버튼을 같은 문구끼리 나란히 비교합니다.'),
    ('construction', '공사 중 표시', '공사 중 표지와 캐릭터 위에 겹쳐 표시되는 글씨입니다.'),
    ('pointers', '위치·방향·조작 안내', '여기·이것 화살표와 시점 이동·스크롤 안내입니다.'),
    ('map', '지도 장소 이름', '지도와 플레이 화면에 반복되는 장소·체크포인트 이름입니다.'),
    ('abilities', '기술·댄스 이름', '플레이 화면과 상태 화면의 같은 기술·댄스 이름을 비교합니다.'),
    ('names', '캐릭터 이름 글씨', '캐릭터마다 색이 다른 큰 이름 글씨입니다.'),
    ('headings', '제목·로고·장식 글씨', '제목 로고, 오늘의 결과 제목, 터치 안내와 단위 글씨입니다.'),
    ('mood', '오늘 기분은?·질문 간판', '오늘 기분은? 문구와 전광판·질문창 변형을 비교합니다.'),
    ('forecast', '예보 문장·수량', '예보의 조사·문장과 많이·꽤·조금·안 나옴을 같은 문구끼리 비교합니다.'),
    ('menu-text', '메뉴 항목·정보 글씨', '설치·상태·소모 와츠 등 항목 이름과 짧은 안내 문구입니다.'),
    ('window-title', '창 제목', '왼쪽 창 아이콘이 붙은 작은 제목 글씨입니다.'),
    ('dialogue', '검은 안내창', '치비컴의 검은 바탕 질문창을 같은 문구끼리 비교합니다.'),
    ('warnings', '빨간 경고창', '부족·없음 경고창의 글씨와 테두리를 비교합니다.'),
    ('panels', '정보 패널·화면 배경', '예보창, 상태 패널, 저장 화면처럼 큰 바탕을 포함하는 그림입니다.'),
]


def classify(key):
    family, number = key.split('/')[0], key.split('/')[-1]
    n = int(number) if number.isdigit() else -1
    if family == 'NewPCCassette': return 'cassette', '컬렉션 · 흰 바탕'
    if family == 'NewPCShopIcon':
        if n in {0,1,2,8,9,10,11,12,13,14,42,47}: return 'tools', '상점 아이콘'
        return 'cassette', '상점 · 노란 바탕'
    if family == 'NewPCLogIn':
        if n in {8,9}: return 'cassette', '메뉴 · 컬렉션'
        if n in {2,5,6,7}: return 'weather-icons', '메뉴 · 예보'
        return 'launchers', '작은 메뉴 아이콘'
    if family.startswith('NewPCSealScr'):
        if family == 'NewPCSealScrB1' and n == 4: return 'cassette', '수집 스티커'
        return 'stickers', '수집 스티커'
    if family.startswith('NEIcon'):
        if family == 'NEIconFeelMSG': return 'mood', '흰 글씨 · 검정 외곽선'
        if family.startswith('NEIconToy'): return 'toys', '일반·비활성'
        return 'park', '일반·비활성'
    if family in {'PCDesktop','PCMPCharSelect','PCMPGameSelect','PCMPGeoSelect','PCMPPurpSelect','PCMPYesNoSelect'}:
        if n == 10: return 'window-title', '치비컴'
        if n in {11,14}: return 'buttons', '치비컴 · 창형 버튼'
        if 21 <= n <= 26: return 'launchers', '큰 창형 메뉴 아이콘'
        if 27 <= n <= 31: return 'dialogue', '검정 바탕 질문창'
        if 32 <= n <= 34: return 'warnings', '빨강 바탕 경고창'
    if family == 'NewPCStaticA':
        if n in {19,20,30,31,32,33,34,35,89,90,91,92,93,94}: return 'buttons', '작은 창 그림 + 글씨'
        if n in {11,12,25,26}: return 'pointers', '표시 화살표·십자'
        if n == 27: return 'construction', '마름모 표지'
        return 'menu-text', '짧은 항목 이름'
    if family == 'NewPCStaticB': return ('buttons','둥근 입체 버튼') if n < 50 else ('construction','캐릭터 위 글씨')
    if family == 'NewPCStaticB2': return 'menu-text', '빨강 창형 항목' if n in {23,24} else '짧은 항목 이름'
    if family == 'NewPCStaticB3': return ('menu-text','문장·설명') if n <= 34 else ('panels','파랑 정보창')
    if family == 'NewPCSelectToy':
        if n in {0,1,2,3,4,5,14}: return 'names', '색상별 이름'
        if n in {6,7,11,12,13}: return 'mood', '질문창' if n == 6 else '전광판'
        return 'menu-text', '소모량 항목'
    if family in {'NewPCShopMInfo','NewPCSeal'}: return 'window-title', '작은 창 아이콘 + 제목'
    if family in {'EditPointA','EditIconStaticA'}: return 'pointers', '위치·조작 안내'
    if family == 'MiniMap': return 'map', '지도 표시'
    if family == 'PlayIcon':
        return ('map','플레이 화면 표시') if n in {115,116,117,135,136,144,145} else ('abilities','작은 흰 외곽선 글씨')
    if family == 'StatusMenuA': return ('abilities','검정 칩 + 글씨') if n < 54 else ('panels','노랑 상태 패널')
    if family == 'StatusMenuA2': return ('weather-icons','시간 그림 + 글씨') if n >= 70 else ('abilities','캐릭터·색상 칩 + 글씨')
    if family == 'NewPCKForecast': return ('headings','예보 제목') if n == 0 else ('forecast','파랑 줄무늬 바탕')
    if family == 'NewPCKForecast2':
        if n == 0: return 'panels','파랑 예보창'
        if n in {7,8,9,10,11,19}: return 'weather-icons','작은 예보 아이콘'
        if n in {16,17}: return 'window-title','작은 창 아이콘 + 제목'
        return 'forecast','투명 바탕 · 남색 외곽선'
    if family.startswith('DayResult'): return 'headings', '결과 제목·단위'
    if family == 'TitleLogo': return 'headings','타이틀·시작 안내'
    if family == 'TitleSave':
        if n == 26: return 'menu-text','저장 슬롯'
        if n in {50,51}: return 'headings','터치 안내'
        return 'buttons','긴 사각형 버튼'
    if family == 'TitleSaveBG': return 'panels','저장 화면'
    if family == 'NPCSB3Pen': return 'panels','캐릭터 상태 패널'
    raise ValueError(f'Visual review required: {key}')


def main():
    manifest=json.loads((ROOT/'metadata/extraction_manifest.json').read_text(encoding='utf-8'))
    assets={}
    for r in manifest['graphics']:
        if r['edition']!='jp' or r.get('localization',{}).get('action')!='translate_proposed': continue
        category,variant=classify(r['key'])
        entry=assets.setdefault(r['pixel_sha256'],{'category':category,'variant':variant,'references':[]})
        assert entry['category']==category, (r['key'],entry)
        entry['references'].append(r['key'])
    output={'schema_version':1,'reviewed_at':'2026-10-15','basis':'All 509 unique source/result thumbnails reviewed; grouping by visible motif and layout, across resource files.','categories':[{'id':a,'name':b,'description':c} for a,b,c in CATEGORIES],'assets':assets}
    (ROOT/'metadata/graphics_visual_categories.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(assets)} visuals classified into {len(CATEGORIES)} categories')

if __name__=='__main__': main()
