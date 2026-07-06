# -*- coding: utf-8 -*-
"""Safety scan for rate/remote anomalies in active Notion cases."""

from __future__ import annotations

import csv
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))

from extractors.rate_extractor import extract_rate
from extractors.remote_extractor import extract_remote

CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
OUTPUT = SES_WORK / "research_results" / "anomaly_report.csv"

_MAN_PATTERN = re.compile(r"(\d{2,3})\s*万")
_PERIODIC_ONSITE = re.compile(r"週\d+出社|月\d+回出社|必要時出社|月1出社")


def _load_token() -> str:
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    token = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN", "")
    if not token:
        raise SystemExit("NOTION_API_KEY not set")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query_active(token: str) -> list[dict]:
    results: list[dict] = []
    cursor: str | None = None
    while True:
        body: dict = {
            "page_size": 100,
            "filter": {"property": "ステータス", "select": {"equals": "募集中"}},
        }
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            f"{NOTION_BASE}databases/{CASE_DB_ID}/query",
            headers=_headers(token),
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
        time.sleep(0.25)
    return results


def _rt(prop: dict | None) -> str:
    if not prop or prop.get("type") != "rich_text":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _title(prop: dict | None) -> str:
    if not prop or prop.get("type") != "title":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def _num(prop: dict | None) -> float | None:
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def _sel(prop: dict | None) -> str:
    if not prop or prop.get("type") != "select":
        return ""
    sel = prop.get("select") or {}
    return sel.get("name", "")


def scan() -> list[dict]:
    token = _load_token()
    pages = _query_active(token)
    anomalies: list[dict] = []

    for page in pages:
        props = page.get("properties", {})
        page_id = page.get("id", "")
        name = _title(props.get("案件名"))
        rate = _num(props.get("単価（万円）"))
        rate_type = _sel(props.get("rate_type"))
        remote_type = _sel(props.get("remote_type"))
        text = _rt(props.get("案件詳細")) or _rt(props.get("案件情報原文"))

        if rate is not None and rate > 1000:
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "rate_gt_1000",
                "detail": f"rate={rate}",
            })
        elif rate is not None and rate > 200:
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "rate_gt_200",
                "detail": f"rate={rate}",
            })
        if rate == 0:
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "rate_zero",
                "detail": "rate=0",
            })

        if text and rate_type == "skill_dependent_no_number" and _MAN_PATTERN.search(text):
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "skill_no_number_but_man_in_text",
                "detail": _MAN_PATTERN.search(text).group(0),
            })

        if text and remote_type == "full_remote" and _PERIODIC_ONSITE.search(text):
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "full_remote_but_periodic_onsite",
                "detail": _PERIODIC_ONSITE.search(text).group(0),
            })

        extracted = extract_rate(text) if text else None
        if extracted and extracted.rate_max_man and extracted.rate_max_man > 200:
            anomalies.append({
                "page_id": page_id,
                "title": name,
                "anomaly": "extractor_rate_gt_200",
                "detail": str(extracted.rate_max_man),
            })

    return anomalies


def main() -> None:
    anomalies = scan()
    OUTPUT.parent.mkdir(exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["page_id", "title", "anomaly", "detail"])
        writer.writeheader()
        writer.writerows(anomalies)
    print(f"Wrote {OUTPUT} ({len(anomalies)} anomalies)")
    if anomalies:
        for row in anomalies[:10]:
            print(f"  [{row['anomaly']}] {row['title'][:40]}")
        raise SystemExit(1)
    print("PASS: no anomalies")
    raise SystemExit(0)


if __name__ == "__main__":
    main()
