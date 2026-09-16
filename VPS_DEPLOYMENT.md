# 한국 VPS 배포 가이드

이 문서는 GitHub 저장소의 수집기를 한국 VPS에서 매일 오전 9시(KST)에 실행하기 위한 절차입니다.

## 1. Clone

```bash
git clone https://github.com/didrlaks5616-maker/public-opportunity-monitor.git
cd public-opportunity-monitor
```

## 2. 초기 환경 구성

```bash
bash scripts/setup_vps.sh
```

Python 가상환경과 requirements 설치, logs 생성, run.sh 실행 권한 설정을 수행합니다. `python3-venv`가 없으면 스크립트가 설치 명령을 안내합니다.

## 3. `.env` 작성

```bash
cp .env.example .env
nano .env
chmod 600 .env
```

필수 값은 `G2B_SERVICE_KEY`, `BIZINFO_API_KEY`, `NOTION_TOKEN`, `NOTION_DATABASE_ID`, `NOTION_DATA_SOURCE_ID`입니다. Secret은 GitHub 문서나 저장소에 적지 않습니다.

운영 조건은 `G2B_KINDS=용역`입니다.

## 4. 서버 시간 확인

```bash
timedatectl
date
```

운영 기준은 `Asia/Seoul`, 매일 오전 9시입니다. 필요할 때만 다음 명령으로 변경합니다.

```bash
sudo timedatectl set-timezone Asia/Seoul
```

## 5. 네트워크 확인

API Key 없이 실행할 수 있습니다.

```bash
bash scripts/network_check.sh
```

`apis.data.go.kr`, `www.bizinfo.go.kr`의 DNS/IPv4 HTTPS 연결과 HTTP 상태를 확인합니다.

## 6. API Smoke Test

`.env`를 만든 다음 실행합니다. 대량 수집이나 Notion 저장은 하지 않습니다.

```bash
.venv/bin/python scripts/api_smoke_test.py
```

정상 예시는 다음과 같습니다.

```text
G2B_KINDS=용역
G2B OK status=200 items=...
BIZINFO OK status=200 items=...
```

실패하면 `ConnectTimeout`, `ReadTimeout`, 인증 오류 등을 확인합니다. API Key는 출력되지 않습니다.

## 7. 전체 수동 실행

```bash
./run.sh
```

정상 로그의 핵심 기준:

```text
START
G2B_KINDS=용역
G2B attempt...
G2B kind=용역 collected=...
BIZINFO attempt...
BIZINFO collected=...
STAGE1 collected=...
STAGE2 relevant=...
STAGE3 ...
Notion sync complete
DONE synced=...
END exit=0
```

실패할 때는 `G2B FAILED reason=...` 또는 `BIZINFO FAILED reason=...` 형태를 확인합니다.

로그:

```bash
tail -n 100 logs/monitor-$(date +%Y-%m-%d).log
```

## 8. Cron 등록

```bash
crontab -e
```

`deploy/crontab.example`의 항목을 복사하고 `/path/to/repository`를 실제 clone 경로로 바꿉니다.

```cron
0 9 * * * flock -n /tmp/public-opportunity-monitor.lock /실제/저장소/경로/run.sh >> /실제/저장소/경로/logs/cron.log 2>&1
```

설치 후:

```bash
crontab -l
```

## 9. GitHub Actions와의 전환

현재 GitHub Actions의 매일 오전 9시 schedule은 바로 제거하지 않습니다. VPS에서 네트워크 확인 → API smoke test → 전체 수동 실행 → Notion 반영까지 성공한 뒤, 중복 실행을 막기 위해 GitHub Actions의 `schedule`을 비활성화합니다. `workflow_dispatch`는 수동 점검용으로 유지할 수 있습니다.

## 10. 운영 원칙

- 나라장터는 `용역`만 수집합니다.
- API/Notion Secret은 로그에 출력하지 않습니다.
- cron 중복 실행 방지를 위해 `flock`을 사용합니다.
- `run.sh`의 경로는 스크립트 자신의 위치를 기준으로 계산하므로 저장소 위치를 하드코딩하지 않습니다.
