# -*- coding: utf-8 -*-
"""SBT/国保/信販の現状確認 - pagination対応版"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from collections import Counter

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
DB_PROJECT = "343450ff-37c0-81e4-934e-f25f90284a3c"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Target identifications
SBT_PREFIXES = [
    "37f450ff-37c0-8194",
    "37f450ff-37c0-818e",
    "37f450ff-37c0-8163",
    "37f450ff-37c0-8183",
    "37f450ff-37c0-812e",
    "37f450ff-37c0-811a",
]
# 既に処理済みかもしれない別の2件
SBT_ALREADY_CLOSED = [
    "37f450ff-37c0-8183",  # 既に過去chatで「終了」化
    "37f450ff-37c0-8173",  # 既に過去chatで「終了」化
]

# Pagination で全件取得
url = f"https://api.notion.com/v1/databases/{DB_PROJECT}/query"
body = {
    "filter": {
        "and": [
            {"timestamp": "created_time", "created_time": {"on_or_after": "2026-06-13T00:00:00Z"}},
            {"timestamp": "created_time", "created_time": {"on_or_before": "2026-06-16T00:00:00Z"}},
        ]
    },
    "page_size": 100,
}

all_results = []
cursor = None
page = 0
while True:
    page += 1
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    if r.status_code != 200:
        print(f"Error on page {page}: {r.text[:500]}")
        sys.exit(1)
    data = r.json()
    batch = data.get("results", [])
    all_results.extend(batch)
    print(f"Page {page}: +{len(batch)} (cumulative {len(all_results)})")
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")

print(f"\n=== Total records (6/13-6/15 UTC): {len(all_results)} ===")

# Extract records
records = []
for rec in all_results:
    props = rec.get("properties", {})
    title_prop = props.get("案件名") or props.get("Name") or props.get("title")
    title = ""
    if title_prop:
        title_arr = title_prop.get("title", []) or []
        if title_arr:
            title = title_arr[0].get("plain_text", "")
    status = ""
    status_prop = props.get("ステータス") or props.get("Status")
    if status_prop:
        sel = status_prop.get("select") or status_prop.get("status")
        if sel:
            status = sel.get("name", "")
    created = rec.get("created_time", "")
    records.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "status": status,
            "created": created,
        }
    )

# SBT 6件確認
print("\n=== SBT contamination 6 records: current status ===")
for prefix in SBT_PREFIXES:
    matched = [r for r in records if r["id"].startswith(prefix)]
    if matched:
        for m in matched:
            mark = "★FOUND★"
            print(f"  {mark} [{m['status']:10s}] {m['id'][:36]} | {m['title']} | {m['created']}")
    else:
        print(f"  [NOT_FOUND] {prefix}")

# 過去既処理2件
print("\n=== Already closed (per past chat) ===")
for prefix in SBT_ALREADY_CLOSED:
    matched = [r for r in records if r["id"].startswith(prefix)]
    if matched:
        for m in matched:
            print(f"  [{m['status']:10s}] {m['id'][:36]} | {m['title']}")
    else:
        print(f"  [NOT_FOUND] {prefix}")

# 国保/信販
print("\n=== 国保 keyword ===")
for r in records:
    if "国保" in r["title"]:
        print(f"  [{r['status']:10s}] {r['id'][:36]} | {r['title']}")

print("\n=== 信販 keyword ===")
for r in records:
    if "信販" in r["title"]:
        print(f"  [{r['status']:10s}] {r['id'][:36]} | {r['title']}")

# Status breakdown
print("\n=== Status breakdown (all records 6/13-6/15) ===")
status_counter = Counter([r["status"] for r in records])
for status, count in status_counter.most_common():
    print(f"  {status or '(empty)'}: {count}")
