# 공공기관 지원사업·입찰공고 자동 모니터

마케팅·홍보·브랜딩·디자인·공간·인테리어·행사·전시 관련 **공공기관 지원사업과 나라장터 입찰/용역 공고**를 수집해 Notion DB에 동기화하는 Python 자동화 프로젝트입니다.

## 현재 구성

- 조달청 나라장터 입찰공고정보서비스: 용역 / 공사 / 물품 공고
- 기업마당(BizInfo): 지원사업 / 사업공고
- 제목·기관·API 원문 기반 키워드 필터
- 지원사업 / 입찰 / 용역 분류
- 분야 자동 분류: 인테리어 / 공간 / 브랜딩 / 마케팅 / 디자인 / 행사 / 전시 / 제작 / 홍보
- 공식 공고번호 우선 중복 방지, 번호가 없으면 기관+공고명+마감일로 보조 식별
- Notion Data Source 동기화 및 기존 페이지 업데이트
- GitHub Actions 매일 18:10 KST 실행
- DRY_RUN 지원
- Telegram / Slack 알림 선택 가능

## Notion DB

현재 연결 대상:

- Database: `공공기관 지원사업·입찰공고 DB`
- Data Source ID: `03343ce8-cb69-4a15-bfd1-6b8050b91ed1`

사용 속성:

- `공고명`
- `공고 유형`
- `공고번호`
- `공고일`
- `발주기관`
- `분야`
- `사업예산`
- `접수 마감일`
- `공고 URL`
- `진행상태`
- `담당자`
- `발견키워드`
- `관련도`
- `최종확인일`
- `수집원`

## 나라장터 필드 기본 매핑

- `bidNtceNo` → `공고번호`
- `bidNtceNm` → `공고명`
- `ntceInsttNm` / `dminsttNm` → `발주기관`
- `bidNtceDt` → `공고일`
- `bidClseDt` → `접수 마감일`
- `bidNtceDtlUrl` / `bidNtceUrl` → `공고 URL`
- `asignBdgtAmt` → `bdgtAmt` → `presmptPrce` 순서로 `사업예산` 후보 사용
- 제목 및 원문 필드 분석 → `분야`, `발견키워드`, `관련도`
- 수집 실행일 → `최종확인일`
- 나라장터 수집 → `수집원 = 나라장터`

공사 공고는 Notion의 `공고 유형`에 `입찰`로 저장합니다. 물품도 동일하게 `입찰`로 처리합니다.

## GitHub Secrets

Repository → Settings → Secrets and variables → Actions → New repository secret

필수:

- `NOTION_TOKEN`
- `G2B_SERVICE_KEY`
- `BIZINFO_API_KEY`

선택:

- `NOTION_DATA_SOURCE_ID`
- `NOTION_DATABASE_ID`
- `NOTIFICATION_TYPE` (`NONE`, `telegram`, `slack`)
- 알림 사용 시 해당 토큰/웹훅

API 키와 Notion 토큰은 코드나 `.env` 파일에 커밋하지 마세요.

## 첫 실행

GitHub Actions → `Public Opportunity Monitor` → `Run workflow`

처음에는 `DRY_RUN=false` 상태이므로 Secrets와 Notion 권한이 정상이라면 실제 동기화가 수행됩니다.

로컬 테스트:

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`DRY_RUN=true`이면 Notion을 수정하지 않고 수집·필터 결과만 출력합니다.

## Notion 연결 주의

GitHub Actions의 `NOTION_TOKEN`에 사용하는 Integration이 `공공기관 지원사업·입찰공고 DB`에 연결되어 있어야 합니다.

Notion에서 해당 데이터베이스의 **연결(Connect to / Connections)** 설정에 Integration을 추가해 주세요.

## 운영상 주의

나라장터 API는 업무 구분별 오퍼레이션을 사용해야 하며, API 스키마나 제공 필드는 변경될 수 있습니다. 최종 입찰 판단은 항상 나라장터 원문 공고를 기준으로 확인합니다.
