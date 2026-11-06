"""Apply the user-requested semantic wordplay revision to the draft glossary."""
import json
from inspect_roms import ROOT, save

# ID, proposed Korean, source meaning, translation rationale, source-description indexes.
REVISIONS = [
    ('T063','고쳐요','고쳐진다·고친다는 뜻을 살린 수리 상품명.','동사의 의미와 공손한 말끝을 유지. ルン의 소리는 한국어 공통 말끝 ~요로 정리.',[107]),
    ('T064','다듬어요','손보다·만지다. 지형을 손보는 메뉴.','지형 편집을 뜻하는 동사로 옮기고 ~요 계열로 통일.',[108]),
    ('T065','놓아요','놓을 수 있다. 물건 배치.','물건을 놓는 의미를 그대로 표시. 가능형의 세부 형태는 간결한 메뉴명으로 압축.',[109]),
    ('T066','놀아요','놀 수 있다. 놀이기구 배치.','원문의 놀다를 보존. 원문 이름에 없는 놀이공원·새 기능을 추가하지 않음.',[110]),
    ('T067','꾸며요','장식하다. 장식물 배치.','꾸민다는 뜻과 ~요 말끝을 보존.',[111]),
    ('T068','세워요','세우다. 동상 배치.','건설 전체로 확대하지 않고 세우다를 유지.',[112]),
    ('T069','봉긋제로','솟아오른 부분을 0으로. 평탄화.','모ッコリ의 솟음은 봉긋, 제로는 제로로 살려 관련 상품과 연결.',[113]),
    ('T070','올리고내리고','올리다 + 내리다. 지면 높이 조절.','상반되는 두 동사의 짝을 한국어에서도 유지.',[114,115]),
    ('T071','강내기','강을 끌어오다·내다. 강 만들기.','강을 낸다는 기능을 짧게 표현. 원문 장음 말장난은 재현하지 않음.',[116,117]),
    ('T072','길내기','길을 내다. 길 만들기.','강내기와 짝을 이루도록 같은 형식을 사용.',[118,119]),
    ('T073','풀무성무성','풀 + 무성하게 자라는 모양.','풀과 ボーボ의 무성함을 반복 형태로 옮김.',[122]),
    ('T074','잎무성무성','잎 + 무성하게 자라는 모양.','같은 계열의 풀·잎·수염 차이를 보존.',[123]),
    ('T075','수염무성무성','수염 + 무성하게 자라는 모양. 설명에는 선인장 효과가 나옴.','기능만 보고 원문 수염을 가시로 바꾸지 않음. 선인장이라는 풀이를 이름에 추가하지 않음.',[124]),
    ('T076','작은 봉긋','작게 솟아오른 것. 작은 언덕.','이 계열의 ちび는 중간·큰 크기와 대조되므로 작은으로 명시.',[125]),
    ('T077','봉긋','솟아오른 모양. 보통 크기의 언덕.','기본 이름에는 원문에 없는 보통·중간을 추가하지 않음.',[126]),
    ('T078','큰 봉긋','크게 솟아오른 것. 큰 언덕.','작은 봉긋·봉긋·큰 봉긋의 세 단계를 보존.',[127]),
    ('T079','졸졸졸졸','물 흐르는 소리를 연상시키는 반복 조어로 해석.','기능 설명의 마이너스 이온만으로 분수·폭포라고 확정하지 않고 소리의 반복을 살린 잠정안.',[128]),
    ('T080','벽돌벽돌','벽돌이라는 말의 반복.','원문 반복을 그대로 번역. 화단 기능 설명을 이름에 추가하지 않음.',[129]),
    ('T081','피어나세요','꽃이 피라는 권유·명령.','권유의 뜻을 살림. 한국 사투리를 새로 부여하지 않음.',[130]),
    ('T082','물아고여라','물이 고이라는 뜻.','원문의 명령형 말장난을 한국어 호명·명령으로 표현.',[131]),
    ('T083','지워요','사라지다. 물건·길·강 삭제.','실제 메뉴 동작이 드러나는 지우다로 옮겨 ~요 계열로 통일.',[146]),
    ('T033','공원만들기','공원을 만든다는 이름.','파크·츠쿠루의 의미를 한국어로 전달. 원문 소리의 결합은 간결한 기능명으로 정리.',[]),
    ('T034','도구사요','도구를 살 수 있다는 이름.','도구와 구매라는 의미를 짧고 공손하게 표시. 도구를 바꾼다는 다른 뜻으로 오인하지 않도록 함.',[]),
]


def main():
    path=ROOT/'translations/glossary.json'
    glossary=json.loads(path.read_text(encoding='utf-8'))
    assert glossary['status']=='draft_awaiting_user_approval'
    entries={r['id']:r for r in glossary['entries']}
    source=json.loads((ROOT/'translations/jp-source.json').read_text(encoding='utf-8'))
    static={r['index']:r for r in source if r['file']=='MsgStatic.bmg'}
    for id_,korean,meaning,reason,indexes in REVISIONS:
        entry=entries[id_]
        if 'wordplay_revision' in entry:
            assert entry['korean_proposal']==korean,'Do not overwrite later review edits'
            continue
        old=entry['korean_proposal']
        refs=[dict(file='MsgStatic.bmg',index=i,source_text=static[i]['source_text']) for i in indexes]
        if id_ in ['T033','T034']:
            indexes=[201,203,246,247] if id_=='T033' else [224,225]
            refs=[dict(file=r['file'],index=r['index'],source_text=r['source_text']) for r in source if r['file']=='MsgResFull.bmg' and r['index'] in indexes]
        entry.update(korean_proposal=korean,note=meaning+' '+reason,approval='proposed')
        entry['wordplay_revision']=dict(previous_proposal=old,meaning=meaning,reason=reason,function_evidence=refs,
                                       evidence_limit='Description/context comparison, not a new code-level item-description mapping.',
                                       user_request='말장난 상품명은 한국어 의미가 드러나도록 재검토')
    glossary['wordplay_policy']='한국어 의미를 우선하되 원문의 반복·대비·말끝을 가능한 범위에서 보존. 기능 설명이나 새로운 능력을 이름·대사에 임의 추가하지 않음.'
    save(path,glossary)
    print('Revised 21 coined item names and 2 related shop/menu names; approval remains pending.')


if __name__=='__main__':main()
