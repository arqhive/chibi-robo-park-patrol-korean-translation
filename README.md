# 피워라! 치비로보! (NDS) 한글 패치

*Chibi-Robo! Park Patrol* (닌텐도 DS, 일본판 `AJBJ`) 비공식 한국어 팬 패치입니다.
일본판(『咲かせて！ちびロボ！』) 원문을 기준으로 번역했습니다.

**제작: arqhive** · **최신 버전: [v1.0f](../../releases/tag/v1.0f) (완성판)**

**소개 페이지: [arqhive 한글 패치 아카이브](https://arqhive.vercel.app/korean-translation/chibi-robo-park-patrol)**

- 대사, 메뉴, 아이템·놀이기구 설명, 치비컴 화면, 도움말을 한글화했습니다.
- 그림 글씨 520여 장을 한글화했습니다(타이틀, 저장 화면, 치비컴·공원만들기 화면, 일시정지 창, 지도, 하루 결과, 아이콘 이름표).
- 대사와 그림 글씨 글꼴은 닌텐도 DS 도트 글꼴에 맞춘 **갈무리**를 씁니다.
- 「%s」에 들어가는 이름의 받침에 따라 을/를, 이/가, 은/는, 과/와, (으)로 같은 조사를 게임이 알아서 고릅니다.
- 메뉴(DSi, TWiLight Menu++ 등)에 보이는 게임 이름을 "피워라! 치비로보!"로 바꿨습니다.

> 이 저장소에는 **게임 데이터(롬, 추출한 원문 대사, 원본 그래픽, 스크린샷)가 들어 있지 않습니다.**
> 패치를 적용하려면 본인이 소유한 게임에서 직접 덤프한 원본이 필요합니다.

## 사용자용: 패치 적용

### 준비물

- 일본판 롬(`AJBJ`). 북미판·유럽판에는 적용할 수 없습니다.
- BPS 패치 도구. [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)나 Floating IPS, 또는 이 저장소의 `tools/bps.py`를 쓰면 됩니다.

### 적용 방법

1. [배포 페이지](../../releases/tag/v1.0f)에서 `AJBJ_KPatch_v1.0f.zip`을 받아 압축을 풉니다.
2. 원본 일본판 롬에 `AJBJ_KPatch_v1.0f.bps`를 적용합니다.
3. 결과 롬의 확인값을 아래 표와 비교합니다.

자세한 방법은 [`README_KO.txt`](release/README_KO.txt)를 참고하세요.

### 파일 확인값

| 항목 | 원본 일본판 | 패치 적용 결과 (v1.0f) |
|---|---|---|
| 크기 | 67,108,864 바이트 | 67,108,864 바이트 |
| CRC32 | `B77D7EA5` | `114D8C97` |
| MD5 | `855bfa33d378bd5b42a2299f8f952bb6` | `a9c1571f4b8eb6a76d6a416295f0d6fd` |
| SHA-1 | `b67dfdea892bb8f149ebe051d3be242a41f0ac54` | `609147555c1eb1234123f9e3f0681b27aea3bbd3` |

원본 파일명 예: `Sakasete! Chibi-Robo! (Japan).nds`

### 실행 환경

- **확인함**: melonDS, 3DS + TWiLight Menu++.

이상한 화면이나 어색한 문장을 발견하면 이슈로 알려 주세요.

## 개발자용

- [`translation/ko.json`](translation/ko.json): 번역문입니다. 메시지 파일 이름과 번호, 번역 조각(색·대기 같은 제어 코드 포함)만 들어 있습니다.
- [`tools/`](tools/): 추출·그림 글씨·빌드 도구입니다. 원본 롬에서 뽑은 자료가 있어야 빌드할 수 있습니다.
- [`docs/particle-patch.md`](docs/particle-patch.md): 조사 자동 선택 패치 설명입니다.
- [`docs/test-cheats-melonds.md`](docs/test-cheats-melonds.md): 검수할 때 쓴 melonDS 치트입니다.

## 라이선스

- 도구와 문서: [MIT](LICENSE).
- 글꼴 갈무리: [SIL Open Font License 1.1](licenses/Galmuri-OFL.md).
- 게임과 원본 데이터의 권리는 Nintendo와 skip Ltd.에 있습니다. 이 패치는 비공식 팬 번역입니다.
