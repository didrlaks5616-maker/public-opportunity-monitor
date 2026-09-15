# 공공사업·입찰 영업기회 자동 모니터

마케팅·홍보·브랜딩·광고·SNS·콘텐츠·행사·축제·전시·박람회 관련 **지원사업과 공공 입찰/용역 공고**를 수집해 Notion DB에 동기화하는 Python 자동화 프로젝트입니다.

## 현재 구성

- 조달청 나라장터 입찰공고정보서비스: 용역 공고
- 기업마당(BizInfo): 지원사업/사업공고
- 제목·설명·API 원문 필드 기반 키워드 필터
- BID / SUPPORT 분류
- 공고 식별키 기반 중복 제거
- Notion Data Source 생성/업데이트
- GitHub Actions 매일 09:00 KST 실행
- DRY_RUN 지원
- Telegram / Slack 알림 선택 가능

## GitHub Secrets

Repository → Settings → Secrets and variables → Actions → New repository secret

필수:

- `NOTION_TOKEN`
- `NOTION_DATA_SOURCE_ID`
- `G2B_SERVICE_KEY`
- `BIZINFO_API_KEY`

권장:

- `NOTION_DATABASE_ID`
- `NOTIFICATION_TYPE` (`NONE`, `telegram`, `slack` 중 하나)
- 알림 사용 시 해당 토큰/웹훅

API 키는 코드나 `.env` 파일에 커밋하지 마세요.

## Notion

기존에 만든 DB:

- Database ID: `fca9bf93-daf7-4ae9-9579-cc38b2824e4e`
- Data Source ID: `99b9dd7c-d1da-4429-8caa-f13ff86c77d6`

Notion Integration이 해당 데이터베이스에 연결되어 있어야 합니다.

## 수동 테스트

GitHub Actions → Public Opportunity Monitor → Run workflow

현재 workflow는 Secrets가 설정되면 실제 Notion 동기화를 수행합니다.

로컬 테스트:

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`DRY_RUN=true`이면 Notion을 수정하지 않고 수집/필터 결과만 출력합니다.

## 운영상 주의

현재 버전은 전국 모든 기관의 개별 홈페이지를 완전하게 커버하는 단계가 아닙니다. 나라장터와 기업마당을 우선 연결하고, 이후 기관별 HTML/HWP/HWPX/RFP 파서를 추가해 커버리지를 확장합니다.
