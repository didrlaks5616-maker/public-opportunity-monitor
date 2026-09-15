# 배포 체크리스트

## 1. GitHub Secrets 등록

Repository → Settings → Secrets and variables → Actions → New repository secret

필수 4개:

- `NOTION_TOKEN`: Notion Integration Internal Integration Token
- `NOTION_DATA_SOURCE_ID`: `99b9dd7c-d1da-4429-8caa-f13ff86c77d6`
- `G2B_SERVICE_KEY`: data.go.kr 조달청 나라장터 입찰공고정보서비스 인증키
- `BIZINFO_API_KEY`: 기업마당 API 인증키

선택:

- `NOTION_DATABASE_ID`: `fca9bf93-daf7-4ae9-9579-cc38b2824e4e`
- `NOTIFICATION_TYPE`: `NONE`부터 시작 권장

## 2. Notion 권한

Notion DB에서 해당 Integration을 연결(Share)해야 합니다.

## 3. 첫 실행

Actions → Public Opportunity Monitor → Run workflow

첫 실행은 수집 및 Notion 동기화가 정상인지 확인합니다.

## 4. 알림

Notion 동기화가 정상 확인된 뒤 `NOTIFICATION_TYPE`을 `telegram` 또는 `slack`으로 변경하고 관련 Secret을 추가합니다.

## 5. 운영

매일 09:00 KST에 GitHub Actions가 자동 실행됩니다. PC를 켜둘 필요가 없습니다.

## 주의

API 키/토큰은 이 파일이나 코드에 넣지 않습니다. GitHub Actions Secrets에만 입력합니다.
