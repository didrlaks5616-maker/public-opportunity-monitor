# 배포 체크리스트

## 1. GitHub Secrets 등록

Repository → Settings → Secrets and variables → Actions → New repository secret

필수 3개:

- `NOTION_TOKEN`: Notion Integration Internal Integration Token
- `G2B_SERVICE_KEY`: data.go.kr 조달청 나라장터 입찰공고정보서비스 인증키
- `BIZINFO_API_KEY`: 기업마당 API 인증키

선택:

- `NOTION_DATA_SOURCE_ID`: `03343ce8-cb69-4a15-bfd1-6b8050b91ed1`
- `NOTION_DATABASE_ID`: 기존 설정값이 있다면 유지 가능
- `G2B_KINDS`: 기본값 `용역,공사,물품`
- `TARGET_YEAR`: 기본값 `2026`
- `MAX_PAGES`: 기본값 `10`
- `NOTIFICATION_TYPE`: `NONE`부터 시작 권장

## 2. Notion 권한

Notion의 `공공기관 지원사업·입찰공고 DB`에서 GitHub Actions용 Integration을 연결(Share / Connections)해야 합니다.

## 3. 첫 실행

Actions → `Public Opportunity Monitor` → `Run workflow`

처음에는 실제 동기화가 수행되므로 API 키와 Notion 연결 상태를 확인합니다.

## 4. 확인할 값

정상 실행 후 Notion에서 다음 속성이 채워지는지 확인합니다.

- `공고명`
- `공고 유형`
- `공고번호`
- `공고일`
- `발주기관`
- `분야`
- `사업예산`
- `접수 마감일`
- `공고 URL`
- `발견키워드`
- `관련도`
- `최종확인일`
- `수집원`

## 5. 알림

Notion 동기화가 정상 확인된 뒤 `NOTIFICATION_TYPE`을 `telegram` 또는 `slack`으로 변경하고 관련 Secret을 추가합니다.

## 6. 운영

GitHub Actions가 매일 18:10 KST에 실행되도록 설정되어 있습니다. PC를 켜둘 필요가 없습니다.

## 주의

API 키/토큰은 이 파일이나 코드에 넣지 않습니다. GitHub Actions Secrets에만 입력합니다.
