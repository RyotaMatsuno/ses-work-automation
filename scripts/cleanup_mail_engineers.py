#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エンジニアDBのメール経由自動登録エントリをNotionからアーカイブ削除する。

  python scripts/cleanup_mail_engineers.py          # dry-run（デフォルト）
  python scripts/cleanup_mail_engineers.py --exec   # 本番実行
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / "config" / ".env"
NOTION_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
KEEP_CUTOFF_DATE = "2026-05-22"
ARCHIVE_SLEEP_SEC = 0.4
PROGRESS_INTERVAL = 50


def load_config() -> tuple[str, str]:
    config = dotenv_values(ENV_PATH, encoding="utf-8")
    api_key = (config.get("NOTION_API_KEY") or "").strip()
    db_id = (config.get("NOTION_ENGINEER_DB_ID") or "").strip()
    if not api_key or not db_id:
        raise SystemExit(f"ERROR: NOTION_API_KEY / NOTION_ENGINEER_DB_ID が未設定です ({ENV_PATH})")
    return api_key, db_id


def notion_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def rich_text(prop: dict | None) -> str:
    return "".join(item.get("plain_text", "") for item in (prop or {}).get("rich_text", []))


def page_title(page: dict) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            items = prop.get("title", [])
            if items:
                return items[0].get("plain_text", "")
    return "(no title)"


def should_keep(page: dict) -> bool:
    memo = rich_text(page.get("properties", {}).get("備考（LINEメモ）"))
    if "手動登録" in memo:
        return True
    if "LINE auto-register" in memo:
        return True
    created_date = (page.get("created_time") or "")[:10]
    return bool(created_date and created_date <= KEEP_CUTOFF_DATE)


def fetch_all_pages(db_id: str, headers: dict[str, str]) -> list[dict]:
    pages: list[dict] = []
    cursor: str | None = None
    while True:
        payload: dict = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        response = requests.post(
            f"{NOTION_BASE}/databases/{db_id}/query",
            headers=headers,
            json=payload,
            timeout=60,
        )
        if response.status_code != 200:
            raise RuntimeError(f"Notion query failed: status={response.status_code} body={response.text[:300]}")
        data = response.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
        time.sleep(0.3)
    return pages


def archive_page(page_id: str, headers: dict[str, str]) -> str:
    """Returns: success | already_archived | not_found | fail"""
    try:
        response = requests.patch(
            f"{NOTION_BASE}/pages/{page_id}",
            headers=headers,
            json={"archived": True},
            timeout=30,
        )
    except requests.RequestException as exc:
        print(f"ERROR: PATCH failed page_id={page_id}: {exc}", flush=True)
        return "fail"

    if response.status_code == 200:
        return "success"
    if response.status_code == 400:
        return "already_archived"
    if response.status_code == 404:
        print(f"SKIP: 404 not found page_id={page_id}", flush=True)
        return "not_found"

    print(
        f"ERROR: PATCH failed page_id={page_id} status={response.status_code} body={response.text[:200]}",
        flush=True,
    )
    return "fail"


def run(exec_mode: bool) -> int:
    api_key, db_id = load_config()
    headers = notion_headers(api_key)

    print(f"MODE: {'EXEC' if exec_mode else 'DRY-RUN'}", flush=True)
    print("Fetching all engineer pages...", flush=True)
    all_pages = fetch_all_pages(db_id, headers)

    keep_pages = [p for p in all_pages if should_keep(p)]
    delete_pages = [p for p in all_pages if not should_keep(p)]

    print(f"保持 {len(keep_pages)}件 / 削除対象 {len(delete_pages)}件", flush=True)

    if not delete_pages:
        print("DONE success=0 fail=0 already_archived=0 total=0", flush=True)
        return 0

    if not exec_mode:
        print("DRY-RUN: archive skipped. Sample delete targets:", flush=True)
        for page in delete_pages[:10]:
            created = (page.get("created_time") or "")[:10]
            print(
                f"  - {page_title(page)} | created={created} | id={page['id']}",
                flush=True,
            )
        if len(delete_pages) > 10:
            print(f"  ... and {len(delete_pages) - 10} more", flush=True)
        print(
            f"DONE success=0 fail=0 already_archived=0 total={len(delete_pages)}",
            flush=True,
        )
        return 0

    success = fail = already_archived = 0
    total = len(delete_pages)

    for i, page in enumerate(delete_pages, start=1):
        result = archive_page(page["id"], headers)
        if result == "success":
            success += 1
        elif result == "already_archived":
            already_archived += 1
        elif result == "fail":
            fail += 1

        if i % PROGRESS_INTERVAL == 0:
            print(
                f"PROGRESS {i}/{total} success={success} fail={fail} already_archived={already_archived}",
                flush=True,
            )
        time.sleep(ARCHIVE_SLEEP_SEC)

    print(
        f"DONE success={success} fail={fail} already_archived={already_archived} total={total}",
        flush=True,
    )
    return 1 if fail else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive mail-auto-registered engineer DB entries in Notion")
    parser.add_argument(
        "--exec",
        action="store_true",
        help="Actually archive pages (default: dry-run)",
    )
    return run(exec_mode=parser.parse_args().exec)


if __name__ == "__main__":
    raise SystemExit(main())
