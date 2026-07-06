"""単価null案件の原文から単価を再抽出してNotionに書き込む。

Usage:
    python matching_v3/recover_prices.py           # dry-run
    python matching_v3/recover_prices.py --execute  # 本番書き込み
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import requests
from config import CASE_DB_ID, Config

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1/"

PRICE_PATTERNS = [
    r'(?:単価|月額|精算|想定単価|予算)[：:\s]*(\d{2,3})(?:\s*[~〜～]\s*\d{2,3})?\s*万',
    r'(\d{2,3})\s*[~〜～\-]\s*\d{2,3}\s*万',
    r'(\d{3,7})\s*円',
]


def extract_price(text: str) -> int | None:
    """原文から月額単価（万円）を抽出。範囲は下限採用、円建ては万円換算。"""
    if not text:
        return None
    if re.search(r'年収', text):
        return None
    text_clean = re.sub(r'(\d),(\d)', r'\1\2', text)
    for pat in PRICE_PATTERNS:
        m = re.search(pat, text_clean)
        if m:
            raw = int(re.sub(r'[^\d]', '', m.group(1)))
            value = round(raw / 10000) if raw >= 1000 else raw
            if 20 <= value <= 200:
                return value
    return None


def _notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _query_null_price_cases(api_key: str) -> list[dict]:
    """ステータス=募集中 AND 単価（万円）=null AND 案件情報原文≠空 を全件取得。"""
    headers = _notion_headers(api_key)
    payload: dict = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "単価（万円）", "number": {"is_empty": True}},
                {"property": "案件情報原文", "rich_text": {"is_not_empty": True}},
            ]
        }
    }
    results: list[dict] = []
    next_cursor: str | None = None
    while True:
        body = dict(payload)
        if next_cursor:
            body["start_cursor"] = next_cursor
        resp = requests.post(
            f"{NOTION_BASE}databases/{CASE_DB_ID}/query",
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        next_cursor = data.get("next_cursor")
        if not data.get("has_more") or not next_cursor:
            break
    return results


def _get_rich_text(prop: dict | None) -> str:
    if not prop:
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))


def _get_title(prop: dict | None) -> str:
    if not prop:
        return ""
    return "".join(t.get("plain_text", "") for t in prop.get("title", []))


def _patch_price(api_key: str, page_id: str, price: int) -> bool:
    headers = _notion_headers(api_key)
    resp = requests.patch(
        f"{NOTION_BASE}pages/{page_id}",
        headers=headers,
        json={"properties": {"単価（万円）": {"number": price}}},
        timeout=30,
    )
    if resp.status_code in (400, 403, 404):
        logger.warning("PATCH %s failed: %s", page_id, resp.text[:200])
        return False
    resp.raise_for_status()
    return True


def run(execute: bool = False) -> None:
    cfg = Config()
    api_key = cfg.notion_api_key
    if not api_key:
        logger.error("NOTION_API_KEY not set")
        sys.exit(1)

    logger.info("Querying null-price active cases...")
    pages = _query_null_price_cases(api_key)
    logger.info("Found %d candidates", len(pages))

    recovered = 0
    skipped = 0
    for page in pages:
        props = page.get("properties", {})
        name = _get_title(props.get("案件名"))
        raw_text = _get_rich_text(props.get("案件情報原文"))
        price = extract_price(raw_text)
        if price is None:
            skipped += 1
            continue
        excerpt = raw_text[:80].replace("\n", " ")
        if execute:
            ok = _patch_price(api_key, page["id"], price)
            status = "UPDATED" if ok else "FAILED"
        else:
            status = "DRY-RUN"
        print(f"[{status}] {name!r:30s} | {price}万 | {excerpt}")
        recovered += 1

    print(f"\n=== 完了 ===")
    print(f"対象: {len(pages)}件 / 抽出成功: {recovered}件 / スキップ: {skipped}件")
    if not execute:
        print("（--execute を付けて本番書き込み）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="Notionへの書き込みを実行")
    args = parser.parse_args()
    run(execute=args.execute)
