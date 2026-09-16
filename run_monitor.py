import logging
import os
import time
from urllib.parse import quote, unquote

import requests

import main

log = logging.getLogger("monitor.wrapper")
stats = {"g2b_raw": 0, "bizinfo_raw": 0, "sources_ok": 0, "relevant_pass": 0, "duplicates": 0}
_seen_relevant = set()


def normalize_g2b_service_key() -> None:
    raw = os.getenv("G2B_SERVICE_KEY", "").strip()
    if not raw:
        return
    decoded = unquote(raw) if "%" in raw else raw
    # main.py currently appends serviceKey to the URL. Keep the env value
    # percent-encoded exactly once so requests does not double-encode it.
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
        result = collector()
        stats[f"{name}_raw"] = len(result)
        stats["sources_ok"] += 1
        return result
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


main.notion_request = notion_request_with_backoff
main.g2b = wrap_collector("g2b", main.g2b)
main.bizinfo = wrap_collector("bizinfo", main.bizinfo)
main.is_relevant = wrapped_is_relevant

normalize_g2b_service_key()
os.environ.setdefault("ALLOW_G2B_OFF_HOURS", "true")
main.main()

filtered = stats["g2b_raw"] + stats["bizinfo_raw"] - stats["relevant_pass"]
log.info(
    "PIPELINE SUMMARY g2b_raw=%s bizinfo_raw=%s filtered_out=%s relevant=%s duplicates_removed=%s sources_ok=%s/2",
    stats["g2b_raw"], stats["bizinfo_raw"], filtered, stats["relevant_pass"], stats["duplicates"], stats["sources_ok"],
)
