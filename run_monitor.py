import logging
import os
import time
from urllib.parse import quote, unquote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import main

log = logging.getLogger("monitor.wrapper")
stats = {"g2b_raw": 0, "bizinfo_raw": 0, "sources_ok": 0, "relevant_pass": 0, "duplicates": 0}
_seen_relevant = set()


def build_session() -> requests.Session:
    retry = Retry(
        total=5,
        connect=5,
        read=3,
        status=5,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False,
    )
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


SESSION = build_session()


def robust_get_with_retry(url, params=None, attempts=2):
    safe_url = url.split("?", 1)[0]
    for attempt in range(1, attempts + 1):
        try:
            response = SESSION.get(url, params=params, timeout=(20, 60))
            if response.status_code in {401, 403, 404}:
                response.raise_for_status()
            response.raise_for_status()
            return response
        except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError, requests.exceptions.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in {401, 403, 404}:
                raise
            if attempt == attempts:
                log.error("REQUEST FAILED host=%s attempts=%s reason=%s", safe_url.split("/", 3)[2], attempt, type(exc).__name__)
                raise
            wait = min(2 ** (attempt - 1), 15)
            log.warning("REQUEST RETRY host=%s attempt=%s/%s reason=%s wait=%ss", safe_url.split("/", 3)[2], attempt, attempts, type(exc).__name__, wait)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def normalize_g2b_service_key() -> None:
    raw = os.getenv("G2B_SERVICE_KEY", "").strip()
    if not raw:
        return
    decoded = unquote(raw) if "%" in raw else raw
    os.environ["G2B_SERVICE_KEY"] = quote(decoded, safe="")


def notion_request_with_backoff(method, path, token, **kwargs):
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": os.getenv("NOTION_VERSION", "2026-03-11"),
        "Content-Type": "application/json",
    }
    for attempt in range(1, 9):
        response = requests.request(
            method,
            "https://api.notion.com/v1" + path,
            headers=headers,
            timeout=30,
            **kwargs,
        )
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "")
            try:
                wait = min(max(float(retry_after), 1.0), 15.0)
            except ValueError:
                wait = min(2 ** (attempt - 1), 15.0)
            log.warning("Notion rate limited; retrying in %.1fs attempt=%s/8", wait, attempt)
            if attempt == 8:
                response.raise_for_status()
            time.sleep(wait)
            continue
        if response.status_code >= 500:
            wait = min(2 ** (attempt - 1), 15.0)
            log.warning("Notion server error status=%s; retrying in %.1fs attempt=%s/8", response.status_code, wait, attempt)
            if attempt == 8:
                response.raise_for_status()
            time.sleep(wait)
            continue
        response.raise_for_status()
        return response
    raise RuntimeError("Notion request failed after retries")


def wrap_collector(name, collector):
    def wrapped():
        log.info("%s attempt...", name.upper())
        try:
            result = collector()
            stats[f"{name}_raw"] = len(result)
            stats["sources_ok"] += 1
            log.info("%s collected=%s", name.upper(), len(result))
            return result
        except Exception as exc:
            log.error("%s FAILED reason=%s", name.upper(), type(exc).__name__)
            raise
    return wrapped


_original_is_relevant = main.is_relevant


def wrapped_is_relevant(notice):
    result = _original_is_relevant(notice)
    if not result:
        return False
    stats["relevant_pass"] += 1
    key = main.unique_key(notice)
    if key in _seen_relevant:
        stats["duplicates"] += 1
    else:
        _seen_relevant.add(key)
    return result


main.get_with_retry = robust_get_with_retry
main.notion_request = notion_request_with_backoff
main.g2b = wrap_collector("g2b", main.g2b)
main.bizinfo = wrap_collector("bizinfo", main.bizinfo)
main.is_relevant = wrapped_is_relevant

normalize_g2b_service_key()
os.environ.setdefault("ALLOW_G2B_OFF_HOURS", "true")
log.info("START mode=%s dry_run=%s live=%s", os.getenv("RUN_MODE", "daily"), os.getenv("DRY_RUN", "false"), os.getenv("DRY_RUN", "false").lower() not in {"1", "true", "yes"})
log.info("G2B_KINDS=%s", os.getenv("G2B_KINDS", "용역,공사,물품"))
main.main()

filtered = stats["g2b_raw"] + stats["bizinfo_raw"] - stats["relevant_pass"]
log.info(
    "PIPELINE SUMMARY g2b_raw=%s bizinfo_raw=%s filtered_out=%s relevant=%s duplicates_removed=%s sources_ok=%s/2",
    stats["g2b_raw"], stats["bizinfo_raw"], filtered, stats["relevant_pass"], stats["duplicates"], stats["sources_ok"],
)
log.info("END")
