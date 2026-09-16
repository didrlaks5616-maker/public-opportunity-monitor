import logging
import os
from urllib.parse import quote, unquote

import main

log = logging.getLogger("monitor.wrapper")
stats = {"g2b_raw": 0, "bizinfo_raw": 0, "sources_ok": 0, "relevant_pass": 0, "duplicates": 0}
_seen_relevant = set()


def normalize_g2b_service_key() -> None:
    raw = os.getenv("G2B_SERVICE_KEY", "").strip()
    if not raw:
        return
    decoded = unquote(raw) if "%" in raw else raw
    os.environ["G2B_SERVICE_KEY"] = quote(decoded, safe="")


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
