# -*- coding: utf-8 -*-
"""Benchmark hard filters: measure avg match count before/after applying all 4 filters.

Uses:
- Notion エンジニアDB for engineer data
- Notion 案件DB (募集中) for case properties (rate_type, remote_type, etc.)
- matching_v3/logs/structured.jsonl for required_skills

No LLM calls. Run time: ~2-3 minutes.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SES_WORK))
sys.path.insert(0, str(SES_WORK / "matching_v3"))

from hard_filters import (
    FilterDropStats,
    apply_hard_filters,
    build_case_view,
    build_engineer_view,
    rate_compatible,
    location_compatible,
    skill_compatible,
    start_timing_compatible,
)
from matcher import SkillNormalizer, prepare_engineer_skills, build_skill_index, filter_engineers_by_required_skills
from config import HARD_FILTERS

CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
STRUCTURED_JSONL = SES_WORK / "matching_v3" / "logs" / "structured.jsonl"
SKILL_ALIASES = SES_WORK / "matching_v3" / "skill_aliases.json"
SAMPLE_CASES = 50  # limit Notion API calls


def _load_token() -> str:
    env = dict(dotenv_values(SES_WORK / "config" / ".env", encoding="utf-8"))
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


def _sel(prop: dict | None) -> str | None:
    if not prop or prop.get("type") != "select":
        return None
    sel = prop.get("select")
    return sel.get("name") if sel else None


def _rt(prop: dict | None) -> str:
    if not prop or prop.get("type") != "rich_text":
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _num(prop: dict | None) -> float | None:
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def _multi_select(prop: dict | None) -> list[str]:
    if not prop or prop.get("type") != "multi_select":
        return []
    return [o.get("name", "") for o in prop.get("multi_select", []) if o.get("name")]


def _query_db(token: str, db_id: str, body: dict) -> list[dict]:
    results: list[dict] = []
    cursor: str | None = None
    while True:
        b = {**body, "page_size": 100}
        if cursor:
            b["start_cursor"] = cursor
        r = requests.post(f"{NOTION_BASE}databases/{db_id}/query", headers=_headers(token), json=b, timeout=30)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
        time.sleep(0.25)
    return results


def _fetch_engineers(token: str) -> list[dict[str, Any]]:
    pages = _query_db(token, ENGINEER_DB_ID, {})
    engineers: list[dict[str, Any]] = []
    for page in pages:
        props = page.get("properties", {})
        title_prop = props.get("氏名") or props.get("名前") or {}
        name_list = title_prop.get("title", [])
        name = "".join(t.get("plain_text", "") for t in name_list).strip()
        eng: dict[str, Any] = {
            "id": page.get("id", ""),
            "氏名": name,
            "単価（万円）": _num(props.get("単価（万円）")) or _num(props.get("単価")),
            "居住地": _sel(props.get("居住地")) or _rt(props.get("居住地")),
            "スキル": _multi_select(props.get("スキル")) or _multi_select(props.get("必須スキル")),
            "正規化スキル": _multi_select(props.get("正規化スキル")),
            "稼働可能日": _rt(props.get("稼働可能日")) or _rt(props.get("稼働開始")),
        }
        engineers.append(eng)
    return engineers


def _fetch_cases(token: str, limit: int) -> list[dict[str, Any]]:
    body = {"filter": {"property": "ステータス", "select": {"equals": "募集中"}}}
    pages = _query_db(token, CASE_DB_ID, body)[:limit]
    cases: list[dict[str, Any]] = []
    for page in pages:
        props = page.get("properties", {})
        c: dict[str, Any] = {
            "id": page.get("id", ""),
            "rate_type": _sel(props.get("rate_type")),
            "remote_type": _sel(props.get("remote_type")),
            "勤務地": _rt(props.get("勤務地")),
            "単価（万円）": _num(props.get("単価（万円）")),
            "必要スキル": _multi_select(props.get("必要スキル")),
            "尚可スキル": _multi_select(props.get("尚可スキル")),
        }
        cases.append(c)
    return cases


def _load_structured() -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not STRUCTURED_JSONL.exists():
        return out
    with STRUCTURED_JSONL.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                row = json.loads(line)
                out[row["case_id"]] = row
            except (json.JSONDecodeError, KeyError):
                pass
    return out


def run() -> None:
    token = _load_token()
    normalizer = SkillNormalizer(SKILL_ALIASES)

    print("Fetching engineers from Notion...")
    raw_engineers = _fetch_engineers(token)
    engineers = [prepare_engineer_skills(e, normalizer) for e in raw_engineers]
    skill_index = build_skill_index(engineers, normalizer)
    print(f"Engineers: {len(engineers)}")

    print(f"Fetching {SAMPLE_CASES} 募集中 cases from Notion...")
    cases = _fetch_cases(token, SAMPLE_CASES)
    print(f"Cases fetched: {len(cases)}")

    structured = _load_structured()
    print(f"structured.jsonl entries: {len(structured)}")

    before_list: list[int] = []
    after_list: list[int] = []
    agg_stats = FilterDropStats()

    for case in cases:
        case_id = case["id"]
        case_json = structured.get(case_id, {})

        # Use Notion backfilled properties if structured.jsonl doesn't have them
        if not case_json.get("rate_type"):
            case_json["rate_type"] = case.get("rate_type")
        if not case_json.get("remote_type"):
            case_json["remote_type"] = case.get("remote_type")
        if not case_json.get("price_max"):
            case_json["price_max"] = case.get("単価（万円）")

        required_skills = (
            case_json.get("required_skills")
            or case.get("必要スキル")
            or []
        )
        case_json["required_skills"] = required_skills

        # Initial skill filter (same as matching_v3)
        candidates = filter_engineers_by_required_skills(engineers, normalizer, skill_index, required_skills)
        before_count = len(candidates)
        before_list.append(before_count)

        # Apply hard filters
        remaining, stats = apply_hard_filters(case, case_json, candidates, normalizer)
        after_count = len(remaining)
        after_list.append(after_count)

        agg_stats.total_in += stats.total_in
        agg_stats.dropped_rate += stats.dropped_rate
        agg_stats.dropped_remote_location += stats.dropped_remote_location
        agg_stats.dropped_skill_threshold += stats.dropped_skill_threshold
        agg_stats.dropped_start_timing += stats.dropped_start_timing
        agg_stats.total_out += stats.total_out

    n = len(cases)
    avg_before = sum(before_list) / n if n else 0
    avg_after = sum(after_list) / n if n else 0
    reduction_pct = (1 - avg_after / avg_before) * 100 if avg_before > 0 else 0

    print("\n=== Hard Filter Benchmark ===")
    print(f"Sample cases:      {n}")
    print(f"Engineers:         {len(engineers)}")
    print(f"Avg candidates before hard filter: {avg_before:.1f}")
    print(f"Avg candidates after  hard filter: {avg_after:.1f}")
    print(f"Reduction:         {reduction_pct:.1f}%")
    print()
    print("--- Per-filter drop-off (aggregate) ---")
    total_in = agg_stats.total_in or 1
    print(f"  rate:            {agg_stats.dropped_rate} ({agg_stats.dropped_rate/total_in*100:.1f}%)")
    print(f"  remote_location: {agg_stats.dropped_remote_location} ({agg_stats.dropped_remote_location/total_in*100:.1f}%)")
    print(f"  skill_threshold: {agg_stats.dropped_skill_threshold} ({agg_stats.dropped_skill_threshold/total_in*100:.1f}%)")
    print(f"  start_timing:    {agg_stats.dropped_start_timing} ({agg_stats.dropped_start_timing/total_in*100:.1f}%)")
    print(f"  total survived:  {agg_stats.total_out}")
    print()
    target_hit = "YES" if avg_after <= 15 else "NO"
    print(f"Target 5-15/case: {target_hit} (avg={avg_after:.1f})")
    print()
    print("HARD_FILTERS config:", HARD_FILTERS)


if __name__ == "__main__":
    run()
