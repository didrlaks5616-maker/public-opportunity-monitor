# 공공기관 지원사업·입찰공고 자동 모니터

마케팅·홍보·브랜딩·디자인·공간·인테리어·행사·전시 관련 **공공기관 지원사업과 입찰/용역 공고**를 수집해 Notion DB에 동기화하는 Python 자동화 프로젝트입니다.

## 현재 구성

- 조달청 나라장터 입찰공고정보서비스: 입찰/용역 공고
- 기업마당(BizInfo): 지원사업/사업공고
- 제목·설명·API 원문 기반 키워드 필터
- 지원사업 / 입찰 / 용역 분류
- 분야 자동 분류: 인테리어 / 공간 / 브랜딩 / 마케팅 / 디자인 / 행사 / 전시 / 제작 / 홍보
- 지역 자동 분류: 전국 및 시·도
- 공고명·기관·마감일 기반 중복 방지
- Notion Data Source 동기화
- GitHub Actions 매일 09:00 KST 실행
- DRY_RUN 지원
- Telegram / Slack 알림 선택 가능

## Notion DB

현재 연결 대상은 새로 만든 다음 DB입니다.

- Database: `공공기관 지원사업·입찰공고 DB`
- Data Source ID: `03343ce8-cb69-4a15-bfd1-6b8050b91ed1`

Notion DB에는 다음 속성을 사용합니다.

- `공고명`
- `공고 유형`
- `분야`
- `발주기관`
- `지역`
- `공고번호`
- `공고일`
- `접수 마감일`
- `사업예산`
- `공고 URL`
- `진행상태`
- `담당자`
- `메모`

## GitHub Secrets

Repository → Settings → Secrets and variables → Actions → New repository secret

필수:

- `NOTION_TOKEN`
- `G2B_SERVICE_KEY`
- `BIZINFO_API_KEY`

선택:

- `NOTION_DATA_SOURCE_ID` (비워두면 새 DB ID를 기본 사용)
- `NOTION_DATABASE_ID`
- `NOTIFICATION_TYPE` (`NONE`, `telegram`, `slack` 중 하나)
- 알림 사용 시 해당 토큰/웹훅

기존 `NOTION_DATA_SOURCE_ID`가 이전 DB ID여도 코드에서 새 DB ID로 자동 전환합니다.

API 키와 Notion 토큰은 코드나 `.env` 파일에 커밋하지 마세요.

## 수동 테스트

GitHub Actions → `Public Opportunity Monitor` → `Run workflow`

`DRY_RUN=false`인 현재 workflow에서는 Secrets가 설정되어 있으면 실제 Notion 동기화를 수행합니다.

로컬 테스트:

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`DRY_RUN=true`이면 Notion을 수정하지 않고 수집·필터 결과만 출력합니다.

## Notion 연결 주의

GitHub Actions에서 사용하는 `NOTION_TOKEN`의 Integration이 새 `공공기관 지원사업·입찰공고 DB`에 접근할 수 있어야 합니다.

Notion에서 해당 데이터베이스의 **연결(Connect to / Connections)** 설정에 GitHub Actions에서 사용하는 Notion Integration을 추가해 주세요.

## 운영상 주의

현재 버전은 전국 모든 기관의 개별 홈페이지를 완전하게 커버하는 단계가 아닙니다. 나라장터와 기업마당을 우선 연결하고, 이후 기관별 HTML/HWP/HWPX/RFP 파서를 추가해 커버리지를 확장합니다.
