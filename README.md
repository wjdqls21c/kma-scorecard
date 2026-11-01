# 기상청 성적표 v0.2.1

2026-11-01 개발. 독립 예보 검증 프로젝트. 개발자의 API 활용신청은 승인되었습니다. 인증키 Secret 등록 후 2026-11-01 06:16 KST 첫 실수집이 성공했습니다(예보 222행, 관측 18행, 수집 오류 0). **24시간 리드 평가 표본은 대상 시각이 지나야 생기며, 시간 구간 정합성 등 평가 방법 검증은 아직 남아 있습니다.**

## 전국 지역 확장 (v0.2.1)

공식 2026-09-30 격자 워크북을 내려받아 161개 시·군·광역도시를 생성했습니다. 서울·부산 등 광역도시는 구·동을 선택지에 넣지 않습니다. 도 지역은 시·군으로 묶고, 구가 있는 일반시는 공식 목록의 첫 번째 구 지점을 대표로 사용합니다. 전체 도시의 면적 평균이 아니며 화면에 대표 행정지점과 격자를 표시합니다. 전남광주통합특별시 등 공식 최신 명칭을 원자료 그대로 보존하고, 광주 도시 선택지는 별도 대표 격자로 둡니다.

- 원문: https://data.kma.go.kr/community/board/detailBoard.do?bbrdTypeNo=4&bbrdNo=70342&pgmNo=92
- 원본: archive/metadata/kma-grids-2026-09-30.xlsx, SHA-256은 dist/regions.json에 기록.
- 지역 목록: dist/regions.json 및 동일 내용의 regions.mjs. 재생성 스크립트: scripts/build_regions.py (개발 시 openpyxl 필요).
- 도시별 자료 유무와 대표 지점 표시, 시·군 이름 검색. 신규 지역의 과거 월 자료가 없으면 빈 값으로 표시.
- 일반 단기예보 API로 직전 24시간 전 발표본을 소급 조회하고 발표시각·격자·정확히 24시간 리드를 검증. 실시간 수집과 취득방식을 구분하고, 관측으로 예보를 재구성하지 않음.
- 현재 및 과거 API 호출은 동일 격자·요청에서 캐시 재사용. 회당 최대 1,200 HTTP 시도·14분 예산, 연속 대량 오류 시 중단하고 부분 성공 보존. 정상 실행은 지역별 이미 확보한 발표본을 다시 조회하지 않음.
- 평가 시각인 02/05/08/11/14/17/20/23시 관측만 수집. 보통 하루 약 3,840회(160격자 × 8시각 × 예보 2페이지와 관측 1회)의 예상치이며 응답 페이지 수·재시도에 따라 달라집니다. 실제 승인 트래픽을 넘기면 중단하며 유료 API는 사용하지 않음.
- archive/daily/YYYY-MM-DD.json에 24시간 리드 예보와 관측을 보존. 기존 발표별 원본 파일은 유지. 과거 예보는 덮어쓰지 않고 관측 결측만 보충.
- 웹에는 최근 30일 평가 표본과 최신 2개 발표본만 공개. 모든 리드의 장기 변경 이력은 아직 제공하지 않음. 과거 원본 ZIP은 별도 보존.
- 긴 과거 파일셋 다운로드에는 기상자료개방포털 로그인이 필요. 계정 세션 만료 시 다시 로그인해야 하며 API 키가 웹 로그인을 대체하지 않음. 기온은 2021-06-29의 시간 해상도 변경 이전 자료를 동일한 24시간 리드 지표에 섞지 않음.

## 과거 자료 확보 결과 (2026-11-01)

기상자료개방포털에 로그인해 단기예보 TMP/POP와 초단기실황 기온/강수 CSV를 실제로 내려받았습니다. 2026-09-01 09:00~2026-10-01 08:00 KST의 720시간 고정 구간에서 여주(여흥동 71,121), 서울(청운효자동 60,127), 부산(연산제5동 98,76) 각각 240개 기온 및 강수 비교쌍을 확보했습니다. 이는 최근 30일이 아닙니다. 앱의 평가 기간 선택에서 조회합니다. 기온 MAE는 여주 1.4708°C, 서울 1.1371°C, 부산 1.2475°C입니다. 강수는 누적 구간 정합성 교차 검증 전의 실험 지표입니다.

서울의 2026년 10월 실황 다운로드는 CSV 헤더만 반환했습니다. 파일 존재를 데이터 확보로 처리하지 않으며, 최근 30일 전체를 확보했다고 주장하지 않습니다. 이 사실만으로 10월 자료가 영구적으로 없다고 단정하지 않습니다. 기존 단기예보 API의 1/2/7/30일 전 실호출도 별도 읽기 전용 워크플로로 확인했습니다. 최근 API만으로 한 달을 복원할 수 없어 파일셋을 보충합니다.

- 예보: https://data.kma.go.kr/data/rmt/rmtList.do?code=420&pgmNo=572
- 실황: https://data.kma.go.kr/data/rmt/rmtList.do?code=400&pgmNo=570
- 형식 안내: https://data.kma.go.kr/community/nuriLovePopup.do
- `archive/history/2026-09/forecasts.zip`: 내려받은 예보 원본 ZIP.
- `archive/history/2026-09/observations.zip`: 다운로드한 실황 CSV 중 정확히 일치하는 3개 격자만 묶은 ZIP. 원본 CSV 바이트 보존, 재압축.
- `dist/history-2026-09.json`: 고정 기간 자료, CSV별 SHA-256와 취득 시각 보존. 실시간 data.json과 분리해 자동 수집 시에도 과거 자료가 지워지지 않습니다.
- 실제 내보내기에는 UTC와 KST 보조 열, 날짜별 Start 구분행이 있습니다. 월말 KST 일자가 31/32처럼 이월 전 숫자로 표기된 경우를 확인했습니다. 날짜는 UTC+9로 계산하며 보조 시각도 대조합니다. 역산 예보를 만들지 않습니다.
- 실기상 CSV로 재생성한 값과 배포 JSON의 일치, 월 경계, 빈 파일 거부, 지역·리드타임·평가 구간 분리를 자동 검사합니다. 원자료 관측 QC와 독립 관측소 교차 검증은 남아 있습니다.

## 구현 결과

- 안드로이드 세로 화면에 대응하는 웹앱. 설치용 manifest와 오프라인 앱 셸.
- 전국 161개 시·군·광역도시 대표 격자. 행정구역 전체 대표성은 보장하지 않음.
- 최근 연속 720시간 중 정확히 24시간 앞서 발표한 예보를 평가. 02/05/08/11/14/17/20/23시 최대 240표본.
- 기온 MAE와 편향, 강수 Brier와 50% 분류 기준의 네 가지 건수.
- 표본 수/결측/갱신 지연 표시. 가상 자료는 실제 자료와 분리.
- JSON 로컬 가져오기/내보내기, 발표본별 조회. 가져온 자료는 진위 미확인.
- 표준 라이브러리만 쓰는 Python 수집기와 GitHub Actions 배포 워크플로.

## 조사 결과와 선택

1. 공공데이터포털 단기예보 서비스는 무료, 공공누리 제1유형(출처표시). 개발 신청은 자동승인, 페이지 표시 신청 가능 트래픽은 10,000. 실제 승인 계정의 한도/기간을 확인할 것. 상업 이용은 출처 조건을 지키는 방식으로 검토 가능. 앱명에 기상청을 써도 공식 앱으로 오인시키지 않도록 독립 서비스임을 명시한다.
   - https://www.data.go.kr/data/15084084/openapi.do
   - https://www.kogl.or.kr/info/licenseType1.do
2. 일반 단기예보 조회 페이지의 시간 범위는 ‘현재’. API허브에는 과거 발표시각을 지정하는 별도 예보 경로와 2008년 이후 보유 안내가 있다. 통보문·격자·현재 JSON API는 형식과 시간 해상도가 다르므로 장기간 보유 안내를 현재 JSON API의 조회 보장으로 간주하면 안 된다. 필요한 TMP/POP 시간별 과거 응답 범위와 누락률은 **인증키를 받은 후 실호출 검증 필요**. 이전 30일 데이터를 확보했다고 주장하지 않는다.
   - https://apihub.kma.go.kr/apiList.do?seqApi=10
   - https://www.data.go.kr/data/15058629/openapi.do
3. ASOS는 긴 관측 이력이 있으나 격자와 지점 매칭이 필요하고 겨울철 강수 제공 간격에도 주의해야 한다. 첫 비교는 같은 격자의 초단기실황을 사용하되 독립 ASOS 검증과 동일하지 않다. 인증 후 실황의 RN1 시간 구간을 예보 POP 대상 구간과 대조해야 한다. 검증 전에는 강수 점수를 실험값으로 취급한다.
   - https://data.kma.go.kr/data/grnd/selectAsosRltmList.do
4. 무료 운영 후보는 GitHub Pages + 공개 저장소의 표준 GitHub Actions 실행기. 매시 50분 수집, API 키는 서버 Secret. 현재 Sites 주소는 개발자가 확인하는 비공개 테스트 배포로, 일반 대중 대상 출시 주소가 아니다. GitHub 연결과 공개 저장소 설정을 완료했고 https://wjdqls21c.github.io/kma-scorecard/ 에 테스트 앱을 배포했다. GitHub Pages는 실제 상거래 사이트 운영에 제한이 있으므로 광고·결제 도입 전 약관을 다시 검토하고 Cloudflare Workers 무료 플랜 등으로 이전한다.
   - https://docs.github.com/en/actions/concepts/billing-and-usage
   - https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
   - https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
   - https://developers.cloudflare.com/workers/platform/limits/
5. 예약 실행은 지연·누락 가능하다. 비활동 저장소의 스케줄 중단 조건도 있다. 결측을 성공으로 채우지 않는다. 지역 확대 전 일일 요청량과 저장소 크기를 점검한다. 초기 3개 격자 버전에서는 최초 실행 약 21회 이상, 정상 실행은 이미 저장한 관측을 생략한다. 공개 페이지에는 최근 30일의 24시간 리드 예보와 최신 2개 발표본만 내보내 파일 크기를 제한한다.

## 스마트폰에서 해야 할 다음 단계

### 1. 기상청 키 발급

공공데이터포털에 본인 계정으로 가입/로그인 → 위 단기예보 조회서비스 → 활용신청 → 개발계정 승인 확인. 활용 목적 예시:

> 기상청 단기예보와 동일 격자 초단기실황을 비교해 지역별 기온 오차 및 강수확률 성적을 제공하는 독립 모바일 웹앱 개발. 원자료 출처를 표시하고 발표 당시 예보를 보존합니다.

이 키 하나로 getVilageFcst와 getUltraSrtNcst를 사용한다. API허브 과거 데이터는 별도 인증/활용신청이 필요할 수 있다. **키를 채팅·공개 저장소·웹앱 입력란에 올리지 않는다.**

### 2. GitHub 연결 및 설치 — 완료한 설정 참고

무료 계정을 준비한다. 제공 소스의 `.github/workflows/collect.yml` 경로를 유지해 공개 저장소의 기본 브랜치로 업로드해야 한다. ZIP을 저장소에 하나의 파일로만 올리면 작동하지 않는다. 스마트폰 수동 작업을 줄이기 위해 GitHub 연결 후 저장소 생성/소스 업로드를 진행하는 편이 좋다. 연결 권한과 공개 저장소 생성은 사용자 확인 후 수행한다.

- 저장소 Settings → Secrets and variables → Actions → New repository secret
- 이름: `KMA_SERVICE_KEY`, 값: 발급받은 일반 인증키(인코딩 키도 수집기가 1회 해제)
- Settings → Pages → Build and deployment → Source: GitHub Actions
- Actions → Collect KMA snapshots → Run workflow. Pages 초기 배포는 Actions → Publish Pages → Run workflow
- 실행 로그의 수집 건수/실패 건수 확인. 응답에 키가 포함될 수 있어 원본 URL/예외를 출력하지 않는다.
- 최초 스냅샷 대상 시각이 지난 뒤부터 24시간 리드 비교가 생긴다. 실시간 수집만으로 지난 30일이 즉시 채워지지는 않는다. 위 과거 파일셋 가져오기로 제공 가능한 구간을 별도로 보충한다.

### 3. 실데이터 출시 전 필수 검증

- 공식 활용가이드와 실응답으로 격자, TMP/POP·T1H/RN1 단위, 정시 및 누적 구간을 대조.
- 서울 등 1개 지역에서 발표시각이 다른 원문을 저장하고 소급 덮어쓰기가 없는지 확인.
- 결측·강수 흔적·음수 센티널·QC 정보 처리 정책 확정. 실황에 QC가 없으므로 독립 ASOS/AWS로 표본 교차 검증.
- API 오류/호출 한도/갱신 지연을 실제로 관찰. 사후 예보로 과거 실적을 보충하지 않음.
- 최소 표본 기준과 우천/건조 표본 분포를 검토. 독립성 및 상관이 있는 시간표본으로 부정확한 신뢰구간을 만들지 않음.
- Brier는 ‘낮을수록 좋다’는 오차이며 기상청 전체의 객관적 순위나 미래 신뢰 확률이 아님. 강수 사건 구간 검증 후 공식 점수 노출 여부 결정.

## 로컬 실행과 검사

```
python -m http.server 8080 --directory dist
node --test tests/engine.test.mjs
python -m unittest discover -s tests -p 'test_*.py'
```

수집은 서버 환경변수에 키를 등록한 환경에서 `python collector/collect.py`. 네트워크 없는 검사에 사용한 데이터는 명시적 합성 fixture다. KMA API 인증 및 예보/실황 파싱과 최초 저장은 실호출로 확인했다. 장기간 가동 안정성과 평가 방법의 검증은 남아 있다.

## 구조와 보존

- `dist/`: 배포용 순수 HTML/CSS/JS, 실시간 data.json 및 고정 과거 자료. API 키 없음.
- `dist/engine.mjs`: 순수 계산 및 파일 검증. 나중에 Android WebView에서도 재사용 가능.
- `collector/collect.py`: 페이지네이션/재시도, 입력 시각·격자 검증, 미래 예보만 수용, 발표본 최초 저장 후 불변.
- `archive/forecasts/YYYY-MM-DD/HHMM-region.json`: 발표별 스냅샷과 수집시각.
- `archive/observations.json`: 관측 보존. 결측 재조회 시 기존 정상값을 지우지 않음. 별도 QC/수정 이력 모델은 이후 추가.
- `.github/workflows/collect.yml`: 예약 수집, 부분 성공 보존. 일부 실패는 명시적으로 실패 표시.
- `.github/workflows/pages.yml`: 수집 실행 종료 후 최신 저장본을 Pages에 배포. Pages 설정이 안 되어도 수집 및 원문 보존은 독립적으로 실행됨.
- `.github/workflows/check.yml`: 코드 변경 시 자동 검사.

## 광고·프리미엄 후속 설계

현재 광고 요청/결제/프리미엄 권한 부여 코드는 없다. 무료 MVP에 결제하는 것처럼 보이는 버튼도 없다. UI 잠정 가격은 4,900원.

1. Android 앱 셸(Capacitor 등) + 검증된 동일 JS 계산 모듈. WebView 임의 JS 브리지에 purchase 성공을 신뢰하지 않는다.
2. Android 광고는 Google Mobile Ads SDK/AdMob 테스트 광고로 시작. 승인, 개인정보처리방침, 동의 처리와 Data safety 검토 후 운영 광고로 전환. 웹 광고는 별도 승인 경로이며 AdMob ID를 HTML에 붙이는 방식이 아니다.
3. Play Billing 비소모성 일회성 상품 `premium_lifetime` 예정. 구매 토큰을 보안 백엔드에서 검증하고 구매 승인/환불·취소·복원 처리. 서버가 결정한 권한으로 연도별 데이터 접근을 제한한다. localStorage 플래그는 유료 권한이 아니다.
4. 연도별 통계는 그 연도의 검증 가능한 원문 보유 기간만 제공. 과거 아카이브 응답 검증 전 연간 수치 판매 금지. 상세·지역 비교의 공개/유료 API 경계를 이후 서버에 구현.
5. Play Console 등록비는 현재 일회성 US$25. 새 개인 계정은 12명/14일 비공개 테스트 조건 등 별도 절차가 있다. 사업자 계정 가능 여부는 실제 등록 자격을 보고 결정. 결제나 계정 생성은 아직 하지 않음.
   - https://support.google.com/googleplay/android-developer/answer/6112435
   - https://support.google.com/googleplay/android-developer/answer/14151465
   - https://developer.android.com/google/play/billing/security
   - https://developers.google.com/admob/android/quick-start

## 알려진 한계

Android 실기기 검사는 사용자 폰에서 수행해야 한다. 현재 브라우저 UI 및 계산/수집기 fixture 검사를 수행했다. PNG 아이콘을 포함했으나 Chrome 실제 설치 검증이 남아 있다. 오프라인에서 앱 셸은 열리지만 기상 자료를 임의로 오래된 캐시에서 제공하지 않는다. 폰트는 시스템 폰트를 사용하며 외부 폰트 서버로 요청하지 않는다. 실제 자동수집은 연결됐다. 연도별 통계·결제·광고는 미연결 상태다.

## 여러 해 과거 자료 게시

수집한 공식 CSV/ZIP을 import_archives.py로 검증한 뒤, `python collector/publish_history.py --input imported.json`으로 월·지역별 작은 JSON과 history-index.json을 생성합니다. 앱은 선택한 지역·기간 파일만 읽습니다. 입력에 고정 period가 있으면 그 기간을 보존하고, 없으면 한국시간 달력 월로 분할합니다. 월 길이에 따라 최대 표본 수도 조정합니다. 여러 해 자료를 단일 거대 JSON에 싣지 않습니다. 현재 실제 확보한 과거 원본은 3개 지역의 기존 30일 구간이며, 전국 장기 과거 자료 전체를 확보했다고 주장하지 않습니다.
