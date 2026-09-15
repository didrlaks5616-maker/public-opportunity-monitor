from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("monitor")
KST = timezone(timedelta(hours=9))

NEW_NOTION_DATA_SOURCE_ID = "03343ce8-cb69-4a15-bfd1-6b8050b91ed1"
OLD_NOTION_DATA_SOURCE_ID = "99b9dd7c-d1da-4429-8caa-f13ff86c77d6"

KEYWORDS = """마케팅 마케팅대행 마케팅운영 마케팅용역 온라인마케팅 디지털마케팅 통합마케팅 해외마케팅 지역마케팅 관광마케팅 브랜드마케팅 홍보 홍보대행 홍보용역 홍보운영 온라인홍보 정책홍보 사업홍보 언론홍보 홍보전략 PR 광고 광고대행 광고운영 광고용역 온라인광고 디지털광고 검색광고 SNS광고 미디어광고 옥외광고 매체광고 광고캠페인 SNS 소셜미디어 유튜브 인스타그램 블로그 페이스북 숏폼 릴스 틱톡 채널운영 SNS운영 SNS콘텐츠 온라인채널 콘텐츠 콘텐츠제작 홍보콘텐츠 영상콘텐츠 영상제작 홍보영상 브랜드영상 유튜브콘텐츠 숏폼콘텐츠 사진촬영 디자인 그래픽디자인 상세페이지 카탈로그 브로슈어 홍보물 인쇄물 브랜드 브랜딩 브랜드개발 BI CI 네이밍 브랜드전략 브랜드홍보 행사 행사대행 행사운영 행사기획 이벤트 이벤트대행 축제 축제운영 축제대행 페스티벌 포럼 컨퍼런스 세미나 설명회 네트워킹 데모데이 쇼케이스 개막식 기념식 전시 전시회 박람회 페어 엑스포 전시운영 박람회운영 공동관 홍보관 전시관 부스 부스운영 부스설치 전시기획 공간기획 판촉 프로모션 캠페인 기획전 판매전 특판전 판촉전 품평회 팝업 팝업스토어 라이브커머스 체험행사 인플루언서 크리에이터 체험단 서포터즈 기자단 홍보단 앰배서더 관광홍보 관광마케팅 지역홍보 지역브랜딩 지역축제 관광콘텐츠 관광상품 지역활성화 상권활성화 용역 입찰 입찰공고 제안요청서 RFP 제안서 제안서평가 사업자선정 수행기관 수행업체 운영업체 대행사 협력업체 계약 협상에의한계약 일반경쟁 제한경쟁 지명경쟁 전자입찰 전자견적 나라장터 사전규격 긴급입찰 재공고 입찰참가 입찰참가자격""".split()
EXCLUDE = """직원채용 공무원채용 기간제근로자 인사 부동산매각 토목공사 건축공사 전기공사 기계설비 시설보수 단순물품구매 차량구매 사무용품구매 급식 경비 청소 폐기물처리 의료장비 건설자재""".split()
BID_TERMS = "용역 입찰 입찰공고 제안요청서 RFP 제안서 사업자선정 수행업체 운영업체 대행사 협상에의한계약 일반경쟁 제한경쟁 전자입찰".split()

CATEGORY_KEYWORDS = {
    "인테리어": "인테리어 실내건축 리모델링 시설개선 환경개선 공간조성 매장 점포 노후점포 개보수 내부공사".split(),
    "공간": "공간 공간디자인 공간기획 공간조성 홍보관 체험관 전시관 부스 매장환경 상권활성화".split(),
    "브랜딩": "브랜딩 브랜드 브랜드개발 브랜드전략 브랜드디자인 BI CI 네이밍 브랜드홍보 지역브랜딩".split(),
    "마케팅": "마케팅 마케팅대행 온라인마케팅 디지털마케팅 관광마케팅 콘텐츠마케팅 지역마케팅 프로모션 캠페인".split(),
    "디자인": "디자인 그래픽디자인 편집디자인 카탈로그 브로슈어 상세페이지 BI CI 시각디자인".split(),
    "행사": "행사 행사대행 행사운영 행사기획 이벤트 축제 페스티벌 포럼 컨퍼런스 세미나 설명회 기념식".split(),
    "전시": "전시 전시회 박람회 페어 엑스포 전시운영 박람회운영 홍보관 전시관 부스 부스운영 전시기획".split(),
    "제작": "제작 콘텐츠제작 영상제작 홍보물 인쇄물 홍보영상 브랜드영상 사진촬영 제작대행".split(),
    "홍보": "홍보 홍보대행 홍보용역 정책홍보 광고 광고대행 SNS SNS운영 SNS콘텐츠 유튜브 인스타그램 블로그 콘텐츠 홍보콘텐츠".split(),
}
REGION_KEYWORDS = {
    "서울": ["서울", "서울특별시"], "경기": ["경기", "경기도"], "인천": ["인천", "인천광역시"],
    "부산": ["부산", "부산광역시"], "대구": ["대구", "대구광역시"], "광주": ["광주", "광주광역시"],
    "대전": ["대전", "대전광역시"], "울산": ["울산", "울산광역시"], "세종": ["세종", "세종특별자치시"],
    "강원": ["강원", "강원특별자치도"], "충북": ["충북", "충청북도"], "충남": ["충남", "충청남도"],
    "전북": ["전북", "전라북도", "전북특별자치도"], "전남": ["전남", "전라남도"],
    "경북": ["경북", "경상북도"], "경남": ["경남", "경상남도"], "제주": ["제주", "제주특별자치도"],
}

@dataclass
class Notice:
    title: str
    organization: str = ""
    notice_type: str = "지원사업"
    region: str = "전국"
    fields: list[str] | None = None
    budget: float | None = None
    deadline: str = ""
    published_at: str = ""
    url: str = ""
    source: str = ""
    bid_number: str = ""
    memo: str = ""
    content_hash: str = ""
    unique_key: str = ""
    status: str = "신규"

    def __post_init__(self):
        if self.fields is None:
            self.fields = []


def clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_date(value) -> str:
    text = clean(value)
    match = re.search(r"(20\d{2})[-./]?(\d{2})[-./]?(\d{2})", text)
    return f"{match.group(1)}-{match.group(2)}-{match.group(3)}" if match else ""


def parse_budget(value) -> float | None:
    text = clean(value).replace(",", "")
    if not text:
        return None
    unit_map = {"억원": 100_000_000, "억": 100_000_000, "천만원": 10_000_000, "천만": 10_000_000,
                "백만원": 1_000_000, "백만": 1_000_000, "만원": 10_000, "만": 10_000, "원": 1}
    match = re.search(r"(\d+(?:\.\d+)?)\s*(억원|억|천만원|천만|백만원|백만|만원|만|원)", text)
    if match:
        return float(match.group(1)) * unit_map[match.group(2)]
    numeric = re.search(r"\d+(?:\.\d+)?", text)
    return float(numeric.group(0)) if numeric else None


def hash_text(value: str) -> str:
    return hashlib.sha256(clean(value).encode("utf-8")).hexdigest()


def unique_key(notice: Notice) -> str:
    return "|".join([notice.source, notice.bid_number or "", clean(notice.organization), clean(notice.title), notice.deadline or ""])


def classify_region(text: str) -> str:
    normalized = clean(text)
    for region, terms in REGION_KEYWORDS.items():
        if any(term in normalized for term in terms):
            return region
    return "전국"


def classify_fields(text: str) -> list[str]:
    normalized = text.lower()
    matched = []
    for field, terms in CATEGORY_KEYWORDS.items():
        if any(term.lower() in normalized for term in terms):
            matched.append(field)
    return matched


def relevance_score(notice: Notice) -> tuple[int, list[str]]:
    text = (notice.title + " " + notice.organization + " " + notice.memo).lower()
    hits = [k for k in KEYWORDS if k.lower() in text]
    score = min(100, len(hits) * 4)
    if notice.notice_type in {"입찰", "용역"} and any(t.lower() in text for t in BID_TERMS):
        score += 20
    for left, right in [("홍보", "용역"), ("마케팅", "용역"), ("행사", "운영"), ("축제", "대행"),
                        ("SNS", "운영"), ("영상", "제작"), ("광고", "대행"), ("콘텐츠", "제작"),
                        ("박람회", "운영"), ("홍보관", "운영"), ("팝업스토어", "운영")]:
        if left.lower() in text and right.lower() in text:
            score += 10
    return score, hits


def is_relevant(notice: Notice) -> bool:
    text = (notice.title + " " + notice.organization + " " + notice.memo).lower()
    score, _ = relevance_score(notice)
    mixed = any(k in text for k in ["홍보", "마케팅", "행사", "축제", "콘텐츠", "광고", "전시", "박람회", "브랜드", "sns", "공간", "인테리어", "디자인"])
    hard_excluded = any(x.lower() in notice.title.lower() for x in EXCLUDE)
    return (score >= 8 or mixed) and (not hard_excluded or (mixed and notice.notice_type in {"입찰", "용역"}))


def get_with_retry(url, params=None, attempts=4):
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=(15, 60))
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.exceptions.HTTPError(f"temporary HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in {429, 500, 502, 503, 504}:
                raise
            last_error = exc
            if attempt == attempts:
                raise
            wait = 5 * (2 ** (attempt - 1))
            log.warning("temporary network error %s/%s: %s - retry in %ss", attempt, attempts, exc, wait)
            time.sleep(wait)
    raise last_error


def g2b() -> list[Notice]:
    key = os.getenv("G2B_SERVICE_KEY", "").strip()
    if not key:
        return []
    url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    now = datetime.now()
    start = now - timedelta(days=int(os.getenv("LOOKBACK_DAYS", "3")))
    out: list[Notice] = []
    for page in range(1, int(os.getenv("MAX_PAGES", "20")) + 1):
        params = {"type": "json", "inqryDiv": "1", "inqryBgnDt": start.strftime("%Y%m%d%H%M"),
                  "inqryEndDt": now.strftime("%Y%m%d%H%M"), "numOfRows": 100, "pageNo": page}
        response = get_with_retry(f"{url}?serviceKey={key}", params=params)
        body = response.json().get("response", {}).get("body", {})
        items = body.get("items") or []
        items = items.get("item") if isinstance(items, dict) else items
        if not items:
            break
        for item in items:
            title = clean(item.get("bidNtceNm"))
            if not title:
                continue
            raw = " | ".join(f"{k}:{v}" for k, v in item.items() if v not in (None, ""))
            organization = clean(item.get("ntceInsttNm") or item.get("dminsttNm"))
            text = f"{title} {organization} {raw}"
            notice = Notice(
                title=title,
                organization=organization,
                notice_type="용역" if "용역" in title else "입찰",
                region=classify_region(text),
                fields=classify_fields(text),
                budget=parse_budget(item.get("presmptPrce") or item.get("bdgtAmt") or item.get("asignBdgtAmt")),
                deadline=parse_date(item.get("bidClseDt") or item.get("bidNtceEndDt")),
                published_at=parse_date(item.get("bidNtceDt") or item.get("ntceDt")),
                url=clean(item.get("bidNtceDtlUrl") or item.get("bidNtceUrl")),
                source="G2B",
                bid_number=clean(item.get("bidNtceNo")),
                memo=raw,
            )
            notice.content_hash = hash_text(raw)
            notice.unique_key = unique_key(notice)
            out.append(notice)
        if page * 100 >= int(body.get("totalCount") or 0):
            break
    return out


def bizinfo() -> list[Notice]:
    key = os.getenv("BIZINFO_API_KEY", "").strip()
    if not key:
        return []
    url = os.getenv("BIZINFO_API_URL", "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do")
    response = get_with_retry(url, params={"crtfcKey": key, "dataType": "json", "searchCnt": 100})
    data = response.json() if "json" in response.headers.get("content-type", "").lower() else json.loads(response.text)
    items = data.get("jsonArray") or data.get("items") or data.get("data") or []
    if isinstance(items, dict):
        items = items.get("item") or []
    out: list[Notice] = []
    for item in items:
        title = clean(item.get("pblancNm") or item.get("title") or item.get("사업명"))
        if not title:
            continue
        raw = " | ".join(f"{k}:{v}" for k, v in item.items() if v not in (None, ""))
        organization = clean(item.get("jrsdInsttNm") or item.get("organization"))
        description = clean(item.get("bsnsSumryCn") or item.get("description"))
        text = f"{title} {organization} {description} {raw}"
        notice = Notice(
            title=title,
            organization=organization,
            notice_type="지원사업",
            region=classify_region(text),
            fields=classify_fields(text),
            budget=parse_budget(item.get("suptAmt") or item.get("budget")),
            deadline=parse_date(item.get("reqstEndDe") or item.get("requestEndDate")),
            published_at=parse_date(item.get("creatPnttm") or item.get("pblancBeginDe")),
            url=clean(item.get("pblancUrl") or item.get("detailUrl") or item.get("url")),
            source="BIZINFO",
            memo=description,
        )
        notice.content_hash = hash_text(raw)
        notice.unique_key = unique_key(notice)
        out.append(notice)
    return out


def notion_request(method, path, token, **kwargs):
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": os.getenv("NOTION_VERSION", "2026-03-11"), "Content-Type": "application/json"}
    last_response = None
    for attempt in range(4):
        response = requests.request(method, "https://api.notion.com/v1" + path, headers=headers, timeout=30, **kwargs)
        last_response = response
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(min(2 * (attempt + 1), 10))
            continue
        response.raise_for_status()
        return response
    last_response.raise_for_status()
    return last_response


def rich_text(value: str) -> dict:
    value = clean(value)
    return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]} if value else {"rich_text": []}


def date_property(value: str) -> dict:
    return {"date": {"start": value}} if value else {"date": None}


def url_property(value: str) -> dict:
    return {"url": value} if value else {"url": None}


def select_property(value: str) -> dict:
    return {"select": {"name": value}} if value else {"select": None}


def multi_select_property(values: list[str] | None) -> dict:
    return {"multi_select": [{"name": v} for v in (values or []) if v]}


def number_property(value: float | None) -> dict:
    return {"number": value} if value is not None else {"number": None}


def build_properties(notice: Notice) -> dict:
    return {
        "공고명": {"title": [{"type": "text", "text": {"content": notice.title[:2000]}}]},
        "공고 유형": select_property(notice.notice_type),
        "분야": multi_select_property(notice.fields),
        "발주기관": rich_text(notice.organization),
        "지역": select_property(notice.region),
        "공고번호": rich_text(notice.bid_number),
        "공고일": date_property(notice.published_at),
        "접수 마감일": date_property(notice.deadline),
        "사업예산": number_property(notice.budget),
        "공고 URL": url_property(notice.url),
        "진행상태": select_property(notice.status),
        "메모": rich_text(notice.memo),
    }


def notion_data_source_id() -> str:
    configured = os.getenv("NOTION_DATA_SOURCE_ID", "").strip()
    if not configured or configured == OLD_NOTION_DATA_SOURCE_ID:
        return NEW_NOTION_DATA_SOURCE_ID
    return configured


def text_from_property(props: dict, prop_name: str, container: str) -> str:
    parts = props.get(prop_name, {}).get(container, [])
    return "".join(part.get("plain_text", part.get("text", {}).get("content", "")) for part in parts)


def notion_sync(changes: list[Notice]) -> None:
    token = os.getenv("NOTION_TOKEN", "").strip()
    data_source_id = notion_data_source_id()
    if not token:
        raise RuntimeError("NOTION_TOKEN is required for live sync")

    pages = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        data = notion_request("POST", f"/data_sources/{data_source_id}/query", token, json=payload).json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    existing = {}
    for page in pages:
        props = page.get("properties", {})
        title = text_from_property(props, "공고명", "title")
        organization = text_from_property(props, "발주기관", "rich_text")
        date_data = props.get("접수 마감일", {}).get("date") or {}
        deadline = date_data.get("start", "") if date_data else ""
        if title:
            existing["|".join([clean(organization), clean(title), deadline])] = page["id"]

    for notice in changes:
        key = "|".join([clean(notice.organization), clean(notice.title), notice.deadline or ""])
        properties = build_properties(notice)
        if key in existing:
            notion_request("PATCH", f"/pages/{existing[key]}", token, json={"properties": properties})
        else:
            notion_request("POST", "/pages", token, json={
                "parent": {"type": "data_source_id", "data_source_id": data_source_id},
                "properties": properties,
            })


def notify(changes: list[Notice]) -> None:
    if not changes or not os.getenv("NOTIFICATION_TYPE"):
        return
    lines = [f"[{datetime.now(KST):%Y-%m-%d} 공공사업·입찰] 신규/수정 {len(changes)}건"]
    ranked = sorted(changes, key=lambda n: (-relevance_score(n)[0], n.deadline or "9999-99-99"))[:30]
    for notice in ranked:
        budget_text = f"{int(notice.budget):,}원" if notice.budget is not None else "-"
        lines.append(f"[{notice.status}] {notice.title}\n기관: {notice.organization}\n분야: {', '.join(notice.fields or []) or '-'}\n지역: {notice.region}\n예산: {budget_text}\n마감: {notice.deadline or '-'}\n{notice.url}")
    body = "\n\n".join(lines)
    notification_type = os.getenv("NOTIFICATION_TYPE", "").lower()
    if notification_type == "telegram" and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage", json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": body[:4000]}, timeout=30).raise_for_status()
    elif notification_type == "slack" and os.getenv("SLACK_WEBHOOK_URL"):
        requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": body[:12000]}, timeout=30).raise_for_status()


def main():
    live = os.getenv("DRY_RUN", "true").lower() not in {"1", "true", "yes", "on"}
    all_notices: list[Notice] = []
    for name, collector in [("G2B", g2b), ("BIZINFO", bizinfo)]:
        try:
            collected = collector()
            log.info("%s collected=%s", name, len(collected))
            all_notices.extend(collected)
        except Exception as exc:
            log.exception("%s failed: %s", name, exc)

    relevant_notices: list[Notice] = []
    seen = set()
    for notice in all_notices:
        if not is_relevant(notice) or notice.unique_key in seen:
            continue
        seen.add(notice.unique_key)
        relevant_notices.append(notice)

    if not live:
        print("=== DRY RUN ===")
        for notice in sorted(relevant_notices, key=lambda n: (n.deadline or "9999-99-99", -relevance_score(n)[0])):
            print(json.dumps({"status": notice.status, "type": notice.notice_type, "title": notice.title,
                              "organization": notice.organization, "region": notice.region, "fields": notice.fields,
                              "deadline": notice.deadline, "budget": notice.budget, "url": notice.url}, ensure_ascii=False))
        return

    notion_sync(relevant_notices)
    notify(relevant_notices)
    log.info("synced=%s", len(relevant_notices))


if __name__ == "__main__":
    main()
