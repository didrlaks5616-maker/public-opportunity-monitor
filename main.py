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

KEYWORDS = """마케팅 마케팅대행 마케팅운영 마케팅용역 온라인마케팅 디지털마케팅 통합마케팅 해외마케팅 지역마케팅 관광마케팅 브랜드마케팅 홍보 홍보대행 홍보용역 홍보운영 온라인홍보 정책홍보 사업홍보 언론홍보 홍보전략 PR 광고 광고대행 광고운영 광고용역 온라인광고 디지털광고 검색광고 SNS광고 미디어광고 옥외광고 매체광고 광고캠페인 SNS 소셜미디어 유튜브 인스타그램 블로그 페이스북 숏폼 릴스 틱톡 채널운영 SNS운영 SNS콘텐츠 온라인채널 콘텐츠 콘텐츠제작 홍보콘텐츠 영상콘텐츠 영상제작 홍보영상 브랜드영상 유튜브콘텐츠 숏폼콘텐츠 사진촬영 디자인 그래픽디자인 상세페이지 카탈로그 브로슈어 홍보물 인쇄물 브랜드 브랜딩 브랜드개발 BI CI 네이밍 브랜드전략 브랜드홍보 행사 행사대행 행사운영 행사기획 이벤트 이벤트대행 축제 축제운영 축제대행 페스티벌 포럼 컨퍼런스 세미나 설명회 네트워킹 데모데이 쇼케이스 개막식 기념식 전시 전시회 박람회 페어 엑스포 전시운영 박람회운영 공동관 홍보관 전시관 부스 부스운영 부스설치 전시기획 공간기획 판촉 프로모션 캠페인 기획전 판매전 특판전 판촉전 품평회 팝업 팝업스토어 라이브커머스 체험행사 인플루언서 크리에이터 체험단 서포터즈 기자단 홍보단 앰배서더 관광홍보 관광마케팅 지역홍보 지역브랜딩 지역축제 관광콘텐츠 관광상품 지역활성화 상권활성화 용역 입찰 입찰공고 제안요청서 RFP 제안서 제안서평가 사업자선정 수행기관 수행업체 운영업체 대행사 협력업체 계약 협상에의한계약 일반경쟁 제한경쟁 지명경쟁 전자입찰 나라장터 사전규격 긴급입찰 재공고 입찰참가 입찰참가자격""".split()
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

G2B_OPERATIONS = {
    "용역": "getBidPblancListInfoServc",
    "공사": "getBidPblancListInfoCnstwk",
    "물품": "getBidPblancListInfoThng",
}

@dataclass
class Notice:
    title: str
    organization: str = ""
    notice_type: str = "지원사업"
    fields: list[str] | None = None
    budget: float | None = None
    deadline: str = ""
    published_at: str = ""
    url: str = ""
    source: str = ""
    bid_number: str = ""
    discovered_keywords: list[str] | None = None
    relevance: str = "관련"
    status: str = "신규"
    raw_text: str = ""
    unique_key: str = ""

    def __post_init__(self):
        if self.fields is None:
            self.fields = []
        if self.discovered_keywords is None:
            self.discovered_keywords = []


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
    numeric = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(numeric.group(0)) if numeric else None


def hash_text(value: str) -> str:
    return hashlib.sha256(clean(value).encode("utf-8")).hexdigest()


def classify_fields(text: str) -> list[str]:
    normalized = clean(text).lower()
    return [field for field, terms in CATEGORY_KEYWORDS.items() if any(term.lower() in normalized for term in terms)]


def score_and_keywords(notice: Notice) -> tuple[int, list[str]]:
    text = clean(f"{notice.title} {notice.organization} {notice.raw_text}").lower()
    hits = []
    for keyword in KEYWORDS:
        if keyword.lower() in text and keyword not in hits:
            hits.append(keyword)
    score = min(60, len(hits) * 4)
    if notice.notice_type in {"입찰", "용역"} and any(term.lower() in text for term in BID_TERMS):
        score += 20
    for left, right in [("홍보", "용역"), ("마케팅", "용역"), ("행사", "운영"), ("축제", "대행"), ("영상", "제작"), ("광고", "대행"), ("콘텐츠", "제작"), ("전시", "운영"), ("팝업스토어", "운영")]:
        if left.lower() in text and right.lower() in text:
            score += 10
    return score, hits[:20]


def set_relevance(notice: Notice) -> None:
    score, hits = score_and_keywords(notice)
    notice.discovered_keywords = hits
    title_lower = notice.title.lower()
    hard_excluded = any(word.lower() in title_lower for word in EXCLUDE)
    if hard_excluded and notice.notice_type == "지원사업":
        notice.relevance = "제외"
    elif score >= 30:
        notice.relevance = "직접"
    elif score >= 12:
        notice.relevance = "관련"
    else:
        notice.relevance = "낮음"


def is_relevant(notice: Notice) -> bool:
    set_relevance(notice)
    if notice.relevance == "제외":
        return False
    text = clean(f"{notice.title} {notice.organization} {notice.raw_text}").lower()
    mixed = any(k in text for k in ["홍보", "마케팅", "행사", "축제", "콘텐츠", "광고", "전시", "박람회", "브랜드", "sns", "공간", "인테리어", "디자인", "실내건축", "리모델링"])
    return notice.relevance in {"직접", "관련"} or mixed


def unique_key(notice: Notice) -> str:
    if notice.bid_number:
        return f"{notice.source}|{notice.bid_number}"
    return "|".join([notice.source, clean(notice.organization), clean(notice.title), notice.deadline or ""])


def get_with_retry(url, params=None, attempts=4):
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=(15, 60))
            if response.status_code in {429, 500, 502, 503, 504}:
                raise requests.exceptions.HTTPError(f"temporary HTTP {response.status_code}", response=response)
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status is not None and status not in {429, 500, 502, 503, 504}:
                raise
            if attempt == attempts:
                raise
            wait = 5 * (2 ** (attempt - 1))
            log.warning("request retry %s/%s: %s", attempt, attempts, exc)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def g2b_windows() -> list[tuple[datetime, datetime]]:
    target_year = os.getenv("TARGET_YEAR", "2026").strip()
    now = datetime.now(KST).replace(tzinfo=None)
    if target_year.isdigit() and len(target_year) == 4:
        start = datetime(int(target_year), 1, 1)
    else:
        start = now - timedelta(days=int(os.getenv("LOOKBACK_DAYS", "7")))
    if start > now:
        start = now - timedelta(days=7)
    windows = []
    cursor = start
    while cursor <= now:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        windows.append((cursor, min(now, next_month - timedelta(minutes=1))))
        cursor = next_month
    return windows


def g2b() -> list[Notice]:
    key = os.getenv("G2B_SERVICE_KEY", "").strip()
    if not key:
        log.warning("G2B_SERVICE_KEY is missing")
        return []
    base_url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"
    max_pages = int(os.getenv("MAX_PAGES", "10"))
    kinds = [x.strip() for x in os.getenv("G2B_KINDS", "용역,공사,물품").split(",") if x.strip() in G2B_OPERATIONS]
    out: list[Notice] = []
    for kind in kinds:
        operation = G2B_OPERATIONS[kind]
        for window_start, window_end in g2b_windows():
            for page in range(1, max_pages + 1):
                params = {"type": "json", "inqryDiv": "1", "inqryBgnDt": window_start.strftime("%Y%m%d%H%M"), "inqryEndDt": window_end.strftime("%Y%m%d%H%M"), "numOfRows": 100, "pageNo": page}
                try:
                    payload = get_with_retry(f"{base_url}/{operation}?serviceKey={key}", params=params).json()
                except Exception:
                    log.exception("G2B request failed kind=%s page=%s", kind, page)
                    break
                header = payload.get("response", {}).get("header", {})
                body = payload.get("response", {}).get("body", {})
                if clean(header.get("resultCode")) not in {"", "00", "0"}:
                    log.warning("G2B result error kind=%s code=%s msg=%s", kind, header.get("resultCode"), header.get("resultMsg"))
                    break
                items = body.get("items") or []
                items = items.get("item") if isinstance(items, dict) else items
                if not items:
                    break
                if isinstance(items, dict):
                    items = [items]
                for item in items:
                    title = clean(item.get("bidNtceNm"))
                    if not title:
                        continue
                    raw = " | ".join(f"{k}:{v}" for k, v in item.items() if v not in (None, ""))
                    notice = Notice(
                        title=title,
                        organization=clean(item.get("ntceInsttNm") or item.get("dminsttNm")),
                        notice_type="용역" if kind == "용역" else "입찰",
                        fields=classify_fields(f"{title} {raw}"),
                        budget=parse_budget(item.get("asignBdgtAmt") or item.get("bdgtAmt") or item.get("presmptPrce")),
                        deadline=parse_date(item.get("bidClseDt") or item.get("bidNtceEndDt")),
                        published_at=parse_date(item.get("bidNtceDt") or item.get("ntceDt")),
                        url=clean(item.get("bidNtceDtlUrl") or item.get("bidNtceUrl")),
                        source="나라장터",
                        bid_number=clean(item.get("bidNtceNo")),
                        raw_text=raw,
                    )
                    notice.unique_key = unique_key(notice)
                    out.append(notice)
                total_count = int(body.get("totalCount") or 0)
                if page * 100 >= total_count or len(items) < 100:
                    break
    log.info("G2B collected=%s", len(out))
    return out


def bizinfo() -> list[Notice]:
    key = os.getenv("BIZINFO_API_KEY", "").strip()
    if not key:
        log.warning("BIZINFO_API_KEY is missing")
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
        description = clean(item.get("bsnsSumryCn") or item.get("description"))
        raw = " | ".join(f"{k}:{v}" for k, v in item.items() if v not in (None, ""))
        notice = Notice(
            title=title,
            organization=clean(item.get("jrsdInsttNm") or item.get("organization")),
            notice_type="지원사업",
            fields=classify_fields(f"{title} {description} {raw}"),
            budget=parse_budget(item.get("suptAmt") or item.get("budget")),
            deadline=parse_date(item.get("reqstEndDe") or item.get("requestEndDate")),
            published_at=parse_date(item.get("creatPnttm") or item.get("pblancBeginDe")),
            url=clean(item.get("pblancUrl") or item.get("detailUrl") or item.get("url")),
            source="기업마당",
            raw_text=description,
        )
        notice.unique_key = unique_key(notice)
        out.append(notice)
    log.info("BIZINFO collected=%s", len(out))
    return out


def notion_request(method, path, token, **kwargs):
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": os.getenv("NOTION_VERSION", "2026-03-11"), "Content-Type": "application/json"}
    for attempt in range(4):
        response = requests.request(method, "https://api.notion.com/v1" + path, headers=headers, timeout=30, **kwargs)
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 3:
                response.raise_for_status()
            time.sleep(min(2 * (attempt + 1), 10))
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("Notion request failed")


def rich_text(value: str) -> dict:
    value = clean(value)
    return {"rich_text": [{"type": "text", "text": {"content": value[:2000]}}]} if value else {"rich_text": []}


def title_property(value: str) -> dict:
    return {"title": [{"type": "text", "text": {"content": clean(value)[:2000]}}]}


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
        "공고명": title_property(notice.title),
        "공고 유형": select_property(notice.notice_type),
        "공고번호": rich_text(notice.bid_number),
        "공고일": date_property(notice.published_at),
        "담당자": {"people": []},
        "발주기관": rich_text(notice.organization),
        "분야": multi_select_property(notice.fields),
        "사업예산": number_property(notice.budget),
        "접수 마감일": date_property(notice.deadline),
        "공고 URL": url_property(notice.url),
        "진행상태": select_property(notice.status),
        "발견키워드": rich_text(", ".join(notice.discovered_keywords or [])),
        "관련도": select_property(notice.relevance),
        "최종확인일": date_property(datetime.now(KST).date().isoformat()),
        "수집원": select_property(notice.source),
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
    if not token:
        raise RuntimeError("NOTION_TOKEN is required for live sync")
    data_source_id = notion_data_source_id()
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

    existing_by_bid = {}
    existing_by_fallback = {}
    for page in pages:
        props = page.get("properties", {})
        bid_number = text_from_property(props, "공고번호", "rich_text")
        title = text_from_property(props, "공고명", "title")
        organization = text_from_property(props, "발주기관", "rich_text")
        deadline_data = props.get("접수 마감일", {}).get("date") or {}
        deadline = deadline_data.get("start", "") if deadline_data else ""
        if bid_number:
            existing_by_bid[bid_number] = page["id"]
        if title:
            existing_by_fallback[(clean(organization), clean(title), deadline)] = page["id"]

    for notice in changes:
        properties = build_properties(notice)
        page_id = existing_by_bid.get(notice.bid_number) if notice.bid_number else None
        if page_id is None:
            page_id = existing_by_fallback.get((clean(notice.organization), clean(notice.title), notice.deadline or ""))
        if page_id:
            notion_request("PATCH", f"/pages/{page_id}", token, json={"properties": properties})
        else:
            notion_request("POST", "/pages", token, json={"parent": {"type": "data_source_id", "data_source_id": data_source_id}, "properties": properties})
    log.info("Notion synced=%s", len(changes))


def notify(changes: list[Notice]) -> None:
    if not changes or not os.getenv("NOTIFICATION_TYPE"):
        return
    ranked = sorted(changes, key=lambda n: (0 if n.relevance == "직접" else 1, n.deadline or "9999-99-99"))[:30]
    lines = [f"[{datetime.now(KST):%Y-%m-%d} 공공사업·입찰] 신규/수정 {len(changes)}건"]
    for notice in ranked:
        budget_text = f"{int(notice.budget):,}원" if notice.budget is not None else "-"
        lines.append(f"[{notice.relevance}] {notice.title}\n기관: {notice.organization}\n분야: {', '.join(notice.fields or []) or '-'}\n예산: {budget_text}\n마감: {notice.deadline or '-'}\n{notice.url}")
    body = "\n\n".join(lines)
    kind = os.getenv("NOTIFICATION_TYPE", "").lower()
    if kind == "telegram" and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        requests.post(f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage", json={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": body[:4000]}, timeout=30).raise_for_status()
    elif kind == "slack" and os.getenv("SLACK_WEBHOOK_URL"):
        requests.post(os.environ["SLACK_WEBHOOK_URL"], json={"text": body[:12000]}, timeout=30).raise_for_status()


def main():
    live = os.getenv("DRY_RUN", "true").lower() not in {"1", "true", "yes", "on"}
    all_notices: list[Notice] = []
    for name, collector in [("G2B", g2b), ("BIZINFO", bizinfo)]:
        try:
            all_notices.extend(collector())
        except Exception:
            log.exception("%s failed", name)

    relevant = []
    seen = set()
    for notice in all_notices:
        if not is_relevant(notice):
            continue
        notice.unique_key = unique_key(notice)
        if notice.unique_key in seen:
            continue
        seen.add(notice.unique_key)
        relevant.append(notice)

    if not live:
        print("=== DRY RUN ===")
        for notice in sorted(relevant, key=lambda n: (n.deadline or "9999-99-99", n.relevance, -len(n.discovered_keywords or []))):
            print(json.dumps({"type": notice.notice_type, "title": notice.title, "organization": notice.organization, "fields": notice.fields, "budget": notice.budget, "deadline": notice.deadline, "bid_number": notice.bid_number, "url": notice.url, "discovered_keywords": notice.discovered_keywords, "relevance": notice.relevance, "source": notice.source}, ensure_ascii=False))
        log.info("DRY_RUN relevant=%s", len(relevant))
        return

    notion_sync(relevant)
    notify(relevant)


if __name__ == "__main__":
    main()
