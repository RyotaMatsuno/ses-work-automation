"""Phase 6: 精度KPI最終計測レポート。

計測指標:
- 辞書カバレッジ (target >50%)
- 必要スキル未設定率 (target <15%)
- 尚可スキル未設定率 (target <50%)
- 単価未設定率 (target <20%)
- 高品質率 (target >75%)
- マッチ数分布 (target avg <20)
- 単価異常値 (target 0)

Usage:
    python matching_v3/coverage_report.py
"""
from __future__ import annotations

import json
import logging
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from script_bootstrap import bootstrap

BASE_DIR, SES_WORK = bootstrap()
RESULTS_DIR = SES_WORK / "research_results"
ALIASES_PATH = BASE_DIR / "skill_aliases.json"
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
PRICE_ANOMALY_THRESHOLD = 200
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"

import requests
from dotenv import dotenv_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _load_env() -> dict[str, str]:
    import os
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in os.environ.items() if v})
    return env


def _load_aliases() -> set[str]:
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    canonical = set(data.get("canonical_skills", []))
    alias_values = set(data.get("aliases", {}).values())
    return canonical | alias_values


def _query_all_cases(token: str, *, active_only: bool = False) -> list[dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body: dict[str, Any] = {"page_size": 100}
        if active_only:
            body["filter"] = {
                "property": "ステータス",
                "select": {"equals": "募集中"},
            }
        if cursor:
            body["start_cursor"] = cursor
        resp = requests.post(
            NOTION_BASE + f"databases/{CASE_DB_ID}/query",
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        cursor = data.get("next_cursor")
        if not data.get("has_more") or not cursor:
            break
        time.sleep(0.3)
    return results


def _parse_case(page: dict[str, Any]) -> dict[str, Any]:
    props = page.get("properties", {})

    def _ms(p: dict | None) -> list[str]:
        if not p or p.get("type") != "multi_select":
            return []
        return [i.get("name", "") for i in p.get("multi_select", [])]

    def _num(p: dict | None) -> float | None:
        if not p or p.get("type") != "number":
            return None
        return p.get("number")

    def _sel(p: dict | None) -> str:
        if not p or p.get("type") != "select":
            return ""
        sel = p.get("select") or {}
        return sel.get("name", "")

    required = _ms(props.get("必要スキル"))
    optional = _ms(props.get("尚可スキル"))
    price = _num(props.get("単価（万円）"))
    match_count = _num(props.get("realtime_match_count"))

    return {
        "id": page.get("id", ""),
        "required": required,
        "optional": optional,
        "price": price,
        "match_count": match_count,
        "matching_status": _sel(props.get("matching_status")),
    }


def _build_report(cases: list[dict[str, Any]], alias_lower: set[str], title: str) -> list[str]:
    total = len(cases)
    required_empty = sum(1 for c in cases if not c["required"])
    optional_empty = sum(1 for c in cases if not c["optional"])
    price_unset = sum(1 for c in cases if c["price"] is None)
    price_anomaly = sum(1 for c in cases if c["price"] is not None and c["price"] > PRICE_ANOMALY_THRESHOLD)

    all_skill_vals: list[str] = []
    for c in cases:
        all_skill_vals.extend(c["required"])
        all_skill_vals.extend(c["optional"])
    total_skill_vals = len(all_skill_vals)
    covered = sum(1 for s in all_skill_vals if s.lower() in alias_lower)
    dict_coverage = covered / total_skill_vals if total_skill_vals > 0 else 0.0

    high_quality = sum(
        1 for c in cases
        if c["required"] and c["price"] is not None and c["price"] <= PRICE_ANOMALY_THRESHOLD
    )
    high_quality_rate = high_quality / total if total > 0 else 0.0

    match_counts = [c["match_count"] for c in cases if c["match_count"] is not None]
    avg_match = sum(match_counts) / len(match_counts) if match_counts else 0.0

    required_empty_rate = required_empty / total if total > 0 else 0.0
    optional_empty_rate = optional_empty / total if total > 0 else 0.0
    price_unset_rate = price_unset / total if total > 0 else 0.0

    def _status(val: float, target: float, direction: str) -> str:
        ok = val >= target if direction == "ge" else val <= target
        return "✅" if ok else "❌"

    lines = [
        f"## {title}",
        f"\n総案件数: **{total}件**",
        "\n### KPI一覧\n",
        "| KPI | 現在値 | 目標 | 判定 |",
        "|-----|--------|------|------|",
        f"| 辞書カバレッジ | {dict_coverage:.1%} | >80% | {_status(dict_coverage, 0.80, 'ge')} |",
        f"| 必要スキル未設定率 | {required_empty_rate:.1%} ({required_empty}件) | <5% | {_status(required_empty_rate, 0.05, 'le')} |",
        f"| 尚可スキル未設定率 | {optional_empty_rate:.1%} ({optional_empty}件) | <50% | {_status(optional_empty_rate, 0.50, 'le')} |",
        f"| 単価未設定率 | {price_unset_rate:.1%} ({price_unset}件) | <15% | {_status(price_unset_rate, 0.15, 'le')} |",
        f"| 高品質率 | {high_quality_rate:.1%} ({high_quality}件) | >85% | {_status(high_quality_rate, 0.85, 'ge')} |",
        f"| マッチ数平均 | {avg_match:.1f} ({len(match_counts)}件データあり) | <10 | {_status(avg_match, 10.0, 'le')} |",
        f"| 単価異常値（>200万） | {price_anomaly}件 | 0 | {_status(price_anomaly, 0, 'le')} |",
    ]
    return lines


def run() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="精度KPIレポート")
    parser.add_argument("--active-only", action="store_true", help="募集中のみ")
    args = parser.parse_args()

    env = _load_env()
    token = env.get("NOTION_API_KEY", "")
    if not token:
        logger.error("NOTION_API_KEY not set")
        sys.exit(1)

    logger.info("Notion案件DB全件取得中...")
    raw_pages = _query_all_cases(token, active_only=args.active_only)
    cases = [_parse_case(p) for p in raw_pages]
    logger.info("取得: %d件", len(cases))

    alias_set = _load_aliases()
    alias_lower = {s.lower() for s in alias_set}

    today = date.today().strftime("%Y%m%d")
    RESULTS_DIR.mkdir(exist_ok=True)
    report_path = RESULTS_DIR / f"precision_report_{today}.md"

    lines = [f"# 精度KPIレポート {today}", ""]
    if args.active_only:
        lines.extend(_build_report(cases, alias_lower, "募集中のみ"))
    else:
        lines.extend(_build_report(cases, alias_lower, "全DB"))
        logger.info("募集中のみモードも計測中...")
        active_pages = _query_all_cases(token, active_only=True)
        active_cases = [_parse_case(p) for p in active_pages]
        lines.append("")
        lines.extend(_build_report(active_cases, alias_lower, "募集中のみ"))

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("レポート出力: %s", report_path)


if __name__ == "__main__":
    run()
