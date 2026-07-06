"""Phase 4A: 単価異常値（>200万円）を一括修正するスクリプト。

年収キーワードあり → 月額換算（÷12, 小数点以下四捨五入）
年収キーワードなし → null化

Usage:
    python matching_v3/fix_price_anomalies.py          # dry-run
    python matching_v3/fix_price_anomalies.py --execute # 本番実行
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
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
NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
PRICE_THRESHOLD = 200  # 万円

import requests
from dotenv import dotenv_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ANNUAL_SALARY_KEYWORDS = [
    "年収", "年俸", "年間報酬", "年額", "annual", "yearly", "年間",
]


def _load_env() -> dict[str, str]:
    env_path = SES_WORK / "config" / ".env"
    env = dict(dotenv_values(env_path, encoding="utf-8"))
    env.update({k: v for k, v in __import__("os").environ.items() if v})
    return env


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query_high_price_cases(token: str) -> list[dict[str, Any]]:
    """単価（万円）> PRICE_THRESHOLD の案件を全件取得。"""
    headers = _build_headers(token)
    payload = {
        "filter": {
            "property": "単価（万円）",
            "number": {"greater_than": PRICE_THRESHOLD},
        },
        "page_size": 100,
    }
    results: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        body = dict(payload)
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


def _detect_annual_salary(text: str) -> bool:
    """年収キーワードが含まれているか判定。"""
    text_lower = text.lower()
    return any(kw in text_lower for kw in ANNUAL_SALARY_KEYWORDS)


def _extract_price_from_page(page: dict[str, Any]) -> float | None:
    props = page.get("properties", {})
    num = props.get("単価（万円）", {})
    if num and num.get("type") == "number":
        return num.get("number")
    return None


def _extract_text_from_page(page: dict[str, Any]) -> str:
    props = page.get("properties", {})
    text_parts = []
    for field in ("案件情報原文", "案件詳細", "案件名"):
        prop = props.get(field, {})
        if prop.get("type") == "rich_text":
            for rt in prop.get("rich_text", []):
                text_parts.append(rt.get("plain_text", ""))
        elif prop.get("type") == "title":
            for rt in prop.get("title", []):
                text_parts.append(rt.get("plain_text", ""))
    return " ".join(text_parts)


def _patch_price(page_id: str, new_price: float | None, headers: dict) -> bool:
    url = NOTION_BASE + f"pages/{page_id}"
    body = {
        "properties": {
            "単価（万円）": {"number": new_price},
        }
    }
    for attempt in range(3):
        try:
            resp = requests.patch(url, headers=headers, json=body, timeout=30)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.warning("PATCH failed page_id=%s attempt=%d: %s", page_id, attempt, exc)
            if attempt < 2:
                time.sleep(1)
    return False


def run(execute: bool = False) -> None:
    env = _load_env()
    token = env.get("NOTION_API_KEY", "")
    if not token:
        logger.error("NOTION_API_KEY not set")
        sys.exit(1)

    logger.info("単価 > %d万円 の案件を取得中...", PRICE_THRESHOLD)
    pages = _query_high_price_cases(token)
    logger.info("%d 件の異常値案件を検出", len(pages))

    headers = _build_headers(token)
    fix_records: list[dict[str, Any]] = []

    for page in pages:
        page_id = page.get("id", "")
        current_price = _extract_price_from_page(page)
        text = _extract_text_from_page(page)
        case_name = ""
        for rt in page.get("properties", {}).get("案件名", {}).get("title", []):
            case_name += rt.get("plain_text", "")

        is_annual = _detect_annual_salary(text)
        if is_annual and current_price is not None:
            new_price = round(current_price / 12, 1)
            action = f"年収÷12 ({current_price:.0f}万 → {new_price:.1f}万)"
        else:
            new_price = None
            action = f"null化 ({current_price:.0f}万)"

        fix_records.append({
            "page_id": page_id,
            "case_name": case_name[:50],
            "current_price": current_price,
            "new_price": new_price,
            "is_annual": is_annual,
            "action": action,
        })

        if execute:
            ok = _patch_price(page_id, new_price, headers)
            fix_records[-1]["executed"] = ok
            logger.info("[EXECUTE] %s: %s → %s", case_name[:30], current_price, new_price)
            time.sleep(0.3)
        else:
            logger.info("[DRY-RUN] %s: %s", case_name[:30], action)

    # レポート出力
    today = date.today().strftime("%Y%m%d")
    RESULTS_DIR.mkdir(exist_ok=True)
    report_path = RESULTS_DIR / f"price_fix_dryrun_{today}.md"

    lines = [
        f"# 単価異常値修正レポート {today}",
        f"\n実行モード: {'**本番実行**' if execute else 'dry-run'}",
        f"\n対象件数: {len(fix_records)}件",
        f"\nPRICE_THRESHOLD: {PRICE_THRESHOLD}万円超",
        "\n## 修正内容\n",
        "| 案件名 | 現在価格 | 修正後 | アクション |",
        "|--------|---------|--------|-----------|",
    ]
    for r in fix_records:
        new_p = f"{r['new_price']:.1f}万" if r["new_price"] is not None else "null"
        executed = " ✅" if r.get("executed") else ""
        lines.append(f"| {r['case_name']} | {r['current_price']:.0f}万 | {new_p}{executed} | {r['action']} |")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("レポート出力: %s", report_path)

    null_count = sum(1 for r in fix_records if r["new_price"] is None)
    annual_count = sum(1 for r in fix_records if r["is_annual"])
    logger.info("=== サマリ ===")
    logger.info("年収→月額換算: %d件 / null化: %d件", annual_count, null_count)


def main() -> None:
    parser = argparse.ArgumentParser(description="単価異常値修正スクリプト")
    parser.add_argument("--execute", action="store_true", help="本番実行（デフォルトはdry-run）")
    args = parser.parse_args()
    run(execute=args.execute)


if __name__ == "__main__":
    main()
