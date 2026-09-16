#!/usr/bin/env python3
from __future__ import annotations

import os
from urllib.parse import quote, unquote

import requests
from dotenv import load_dotenv

load_dotenv()


def normalize_key(raw: str) -> str:
    decoded = unquote(raw.strip()) if "%" in raw else raw.strip()
    return quote(decoded, safe="")


def check_g2b() -> None:
    raw = os.getenv("G2B_SERVICE_KEY", "")
    if not raw:
        print("G2B FAILED missing_secret")
        return
    key = normalize_key(raw)
    url = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"
    params = {
        "serviceKey": key,
        "type": "json",
        "inqryDiv": "1",
        "inqryBgnDt": "202609160000",
        "inqryEndDt": "202609162359",
        "numOfRows": 5,
        "pageNo": 1,
    }
    try:
        r = requests.get(url, params=params, timeout=(20, 60))
        r.raise_for_status()
        payload = r.json()
        body = payload.get("response", {}).get("body", {})
        items = body.get("items") or []
        if isinstance(items, dict):
            items = items.get("item") or [items]
        print(f"G2B OK status={r.status_code} items={len(items)}")
    except Exception as exc:
        print(f"G2B FAILED {type(exc).__name__}")


def check_bizinfo() -> None:
    key = os.getenv("BIZINFO_API_KEY", "").strip()
    if not key:
        print("BIZINFO FAILED missing_secret")
        return
    url = os.getenv("BIZINFO_API_URL", "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do")
    try:
        r = requests.get(url, params={"crtfcKey": key, "dataType": "json", "searchCnt": 5}, timeout=(20, 60))
        r.raise_for_status()
        data = r.json() if "json" in r.headers.get("content-type", "").lower() else {}
        items = data.get("jsonArray") or data.get("items") or data.get("data") or []
        if isinstance(items, dict):
            items = items.get("item") or [items]
        print(f"BIZINFO OK status={r.status_code} items={len(items)}")
    except Exception as exc:
        print(f"BIZINFO FAILED {type(exc).__name__}")


if __name__ == "__main__":
    print(f"G2B_KINDS={os.getenv('G2B_KINDS', '용역')}")
    check_g2b()
    check_bizinfo()
