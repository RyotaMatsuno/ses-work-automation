# -*- coding: utf-8 -*-
"""Build 60-case golden set from Notion case DB (read-only)."""

from __future__ import annotations

import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES_WORK = Path(__file__).resolve().parents[1]
GOLDEN_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SES_WORK))

from mail_pipeline.project_notion_save import prepare_notion_project_fields
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
RANDOM_SEED = 20260625


def _load_token() -> str:
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    token = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN", "")
    if not token:
        raise SystemExit(f"NOTION_API_KEY not set ({env_path})")
    return token


def _headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query_all(token: str, *, active_only: bool = True) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if active_only:
            body["filter"] = {"property": "ステータス", "select": {"equals": "募集中"}}
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


def _ms(prop: dict | None) -> list[str]:
    if not prop or prop.get("type") != "multi_select":
        return []
    return [i.get("name", "") for i in prop.get("multi_select", [])]


def _num(prop: dict | None) -> float | None:
    if not prop or prop.get("type") != "number":
        return None
    return prop.get("number")


def _sel(prop: dict | None) -> str:
    if not prop or prop.get("type") != "select":
        return ""
    return (prop.get("select") or {}).get("name", "")


def _parse_page(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})
    detail = _rt(props.get("案件詳細"))
    raw = _rt(props.get("案件情報原文"))
    source = detail or raw
    price = _num(props.get("単価（万円）"))
    return {
        "case_id": page.get("id", ""),
        "title": _title(props.get("案件名")),
        "source_text": source,
        "required_skills": _ms(props.get("必要スキル")),
        "preferred_skills": _ms(props.get("尚可スキル")),
        "rate_man": price,
        "location": _rt(props.get("勤務地")) or None,
        "remote_type": None,
        "matching_status": _sel(props.get("matching_status")),
        "match_count": _num(props.get("realtime_match_count")),
        "text_len": len(source),
    }


def _classify_rate(text: str, rate: float | None) -> str:
    if rate is not None and rate > 0:
        if re.search(r"\d{2,3}\s*万?\s*[〜～\-~]\s*\d{2,3}\s*万", text):
            return "explicit_range"
        if re.search(r"(?:MAX|上限|まで)\s*\d{2,3}\s*万", text, re.I):
            return "max_type"
        return "has_number"
    if re.search(r"スキル見合.*?(?:MAX|上限|〜|~|～)\s*\d{2,3}\s*万", text, re.I | re.S):
        return "skill_cap"
    if re.search(r"スキル見合", text):
        return "skill_no_number"
    if re.search(r"(?:単価|予算|金額|月額)", text):
        return "ambiguous"
    return "no_rate_text"


def _classify_remote(text: str) -> str:
    if re.search(r"フルリモート|完全リモート|フル在宅|出社なし", text):
        return "full_remote"
    if re.search(r"リモート併用|ハイブリッド|週\d.*出社|一部出社", text):
        return "hybrid"
    if re.search(r"常駐|オンサイト|出社前提|出社必須", text):
        return "onsite"
    if re.search(r"リモート|テレワーク|在宅", text):
        return "ambiguous_remote"
    return "no_remote"


def _classify_skill(case: dict[str, Any]) -> str:
    skills = " ".join(case["required_skills"]).lower()
    title = case["title"].lower()
    blob = f"{skills} {title}"
    if any(k in blob for k in ("react", "vue", "angular", "フロント")):
        return "frontend"
    if any(k in blob for k in ("aws", "infra", "インフラ", "linux", "ネットワーク")):
        return "infra"
    if any(k in blob for k in ("pmo", "pm", "マネジメント", "プロジェクト")):
        return "pm"
    if any(k in blob for k in ("java", "python", "go", "c#", "backend", "バック")):
        return "backend"
    return "other"


def _pick(pool: list[dict], n: int, used: set[str], *, key=None) -> list[dict]:
    candidates = [c for c in pool if c["case_id"] not in used]
    if key:
        random.shuffle(candidates)
        candidates.sort(key=key)
    random.shuffle(candidates)
    picked: list[dict] = []
    for case in candidates:
        if len(picked) >= n:
            break
        if case["case_id"] in used:
            continue
        picked.append(case)
        used.add(case["case_id"])
    return picked


def _capture_baseline_extraction(case: dict[str, Any]) -> dict[str, Any]:
    subject = case["source_text"][:120]
    body = case["source_text"]
    req, opt, price, location = prepare_notion_project_fields({}, subject, body)
    return {
        "required_skills": req,
        "preferred_skills": opt,
        "rate_man": price,
        "location": location,
    }


def _extraction_matches_notion(case: dict[str, Any]) -> bool:
    subject = case["source_text"][:120]
    body = case["source_text"]
    req, _, price, location = prepare_notion_project_fields({}, subject, body)
    if not req or price is None or price <= 0 or not location:
        return False
    notion_req = {s.lower() for s in case["required_skills"]}
    extracted_req = {s.lower() for s in req}
    return bool(notion_req & extracted_req)


def _to_golden(case: dict[str, Any], group: str, *, with_gold: bool = False) -> dict[str, Any]:
    entry = {
        "case_id": case["case_id"],
        "source_text": case["source_text"],
        "group": group,
        "current_values": {
            "required_skills": case["required_skills"],
            "preferred_skills": case["preferred_skills"],
            "rate_man": case["rate_man"],
            "location": case["location"],
            "remote_type": case["remote_type"],
        },
        "gold_labels": {
            "rate_min_man": None,
            "rate_max_man": None,
            "rate_type": None,
            "remote_type": None,
            "location": None,
            "required_skills_normalized": [],
            "preferred_skills_normalized": [],
        },
    }
    if not with_gold:
        entry["baseline_extraction"] = _capture_baseline_extraction(case)
        return entry
    return entry


def build_cases(active: list[dict[str, Any]]) -> list[dict[str, Any]]:
    random.seed(RANDOM_SEED)
    used: set[str] = set()
    cases: list[dict[str, Any]] = []

    a_pool = active
    rate_buckets: dict[str, list[dict]] = {}
    remote_buckets: dict[str, list[dict]] = {}
    skill_buckets: dict[str, list[dict]] = {}
    for c in a_pool:
        text = c["source_text"]
        rate_buckets.setdefault(_classify_rate(text, c["rate_man"]), []).append(c)
        remote_buckets.setdefault(_classify_remote(text), []).append(c)
        skill_buckets.setdefault(_classify_skill(c), []).append(c)

    a_targets = [
        ("rate", "explicit_range", 6),
        ("rate", "max_type", 4),
        ("rate", "skill_no_number", 4),
        ("rate", "skill_cap", 4),
        ("rate", "no_rate_text", 4),
        ("rate", "ambiguous", 2),
        ("remote", "full_remote", 5),
        ("remote", "hybrid", 5),
        ("remote", "onsite", 5),
        ("remote", "ambiguous_remote", 5),
        ("remote", "no_remote", 5),
        ("skill", "backend", 10),
        ("skill", "frontend", 5),
        ("skill", "infra", 5),
        ("skill", "pm", 5),
        ("skill", "other", 5),
    ]
    bucket_map = {"rate": rate_buckets, "remote": remote_buckets, "skill": skill_buckets}
    for kind, bucket, count in a_targets:
        pool = bucket_map[kind].get(bucket, [])
        for case in _pick(pool, count, used):
            if len([c for c in cases if c["group"] == "A"]) >= 30:
                break
            cases.append(_to_golden(case, "A", with_gold=True))
        if len([c for c in cases if c["group"] == "A"]) >= 30:
            break

    while len([c for c in cases if c["group"] == "A"]) < 30:
        extra = _pick(a_pool, 1, used)
        if not extra:
            break
        cases.append(_to_golden(extra[0], "A", with_gold=True))

    # Group B: 20 normal cases (extraction-verified)
    b_pool = [
        c for c in active
        if c["required_skills"]
        and c["rate_man"] is not None
        and c["rate_man"] > 0
        and c["rate_man"] <= 200
        and c["location"]
        and _extraction_matches_notion(c)
    ]
    for case in _pick(b_pool, 20, used):
        cases.append(_to_golden(case, "B"))

    # Group C: 10 edge cases
    c_specs = [
        ([c for c in active if c["rate_man"] == 0], 3),
        ([c for c in active if c["matching_status"] == "ERROR"], 3),
        ([c for c in active if not c["required_skills"]], 2),
        ([c for c in active if c["text_len"] < 80], 2),
    ]
    for pool, n in c_specs:
        for case in _pick(pool, n, used):
            cases.append(_to_golden(case, "C"))

    while len([c for c in cases if c["group"] == "C"]) < 10:
        extra = _pick([c for c in active if c["case_id"] not in used], 1, used)
        if not extra:
            break
        cases.append(_to_golden(extra[0], "C"))

    return cases


def compute_baseline(active: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(active)
    req_empty = sum(1 for c in active if not c["required_skills"])
    price_empty = sum(
        1 for c in active if c["rate_man"] is None or c["rate_man"] == 0
    )
    loc_empty = sum(1 for c in active if not c["location"])
    remote_empty = total  # remote_type not populated yet in DB

    match_counts = [c["match_count"] for c in active if c["match_count"] is not None]
    zero_match = sum(1 for m in match_counts if m == 0)
    over_50 = sum(1 for m in match_counts if m >= 50)
    avg_match = sum(match_counts) / len(match_counts) if match_counts else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "active_only",
        "total_cases": total,
        "required_skill_empty_rate": round(req_empty / total, 4) if total else 0,
        "price_empty_rate": round(price_empty / total, 4) if total else 0,
        "location_empty_rate": round(loc_empty / total, 4) if total else 0,
        "remote_empty_rate": round(remote_empty / total, 4) if total else 0,
        "avg_match_count": round(avg_match, 2),
        "zero_match_rate": round(zero_match / len(match_counts), 4) if match_counts else 0,
        "match_50plus_rate": round(over_50 / len(match_counts), 4) if match_counts else 0,
        "note": "price_empty treats 0万 as empty per R5 spec",
    }


def main() -> None:
    token = _load_token()
    print("Fetching active cases from Notion...")
    pages = _query_all(token, active_only=True)
    active = [_parse_page(p) for p in pages if _parse_page(p)["source_text"]]
    print(f"Parsed {len(active)} active cases with source text")

    golden = build_cases(active)
    if len(golden) < 60:
        print(f"[WARN] Only {len(golden)} cases sampled (target 60)")

    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / "golden_cases.json"
    golden_path.write_text(
        json.dumps({"cases": golden, "count": len(golden)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {golden_path} ({len(golden)} cases)")

    baseline = compute_baseline(active)
    baseline_path = GOLDEN_DIR / "baseline_metrics.json"
    baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {baseline_path}")


if __name__ == "__main__":
    main()
