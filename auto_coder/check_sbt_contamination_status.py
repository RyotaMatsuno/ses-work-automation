# -*- coding: utf-8 -*-
"""SBT汚染候補6件+自己重複2組の現状確認
過去チャットの情報をもとに、Notion DBで現在のステータスを確認
"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
DB_PROJECT = "343450ff-37c0-81e4-934e-f25f90284a3c"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 過去チャットで特定済みのpage_id
SBT_CONTAMINATED_IDS = [
    ("37f450ff-37c0-8194", "Prisma Access設計構築"),
    ("37f450ff-37c0-818e", "建設業向けERPパッケージ導入(会計領域)"),
    ("37f450ff-37c0-8163", "テスト、ヘルプデスク、運用保守、データ移行@南行徳"),
    ("37f450ff-37c0-8183", "AWS案件/運用ツール構築/運用自動化@五反田 (b755)"),
    ("37f450ff-37c0-812e", "AWS案件/運用ツール構築/運用自動化"),
    ("37f450ff-37c0-811a", "置局サポート業務"),
]

# 6/15 created の案件を絞り込み取得
url = f"https://api.notion.com/v1/databases/{DB_PROJECT}/query"
body = {
    "filter": {
        "and": [
            {"timestamp": "created_time", "created_time": {"on_or_after": "2026-06-14T00:00:00Z"}},
            {"timestamp": "created_time", "created_time": {"on_or_before": "2026-06-16T00:00:00Z"}},
        ]
    },
    "page_size": 100,
}

print("=== Notion DB query: 6/14-6/15 created records ===")
r = requests.post(url, headers=HEADERS, json=body, timeout=30)
print(f"Status: {r.status_code}")
if r.status_code != 200:
    print(f"Error: {r.text[:500]}")
    sys.exit(1)

data = r.json()
results = data.get("results", [])
print(f"Total records: {len(results)}")

# 各レコードの主要情報を抽出
records = []
for rec in results:
    page_id = rec["id"].replace("-", "")[:16]
    page_id_short = f"{page_id[:8]}-{page_id[8:16]}"
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
            "id_short": page_id_short,
            "title": title[:60],
            "status": status,
            "created": created,
        }
    )

# SBT 6件のステータスを確認
print("\n=== SBT contamination 6 records: current status ===")
for prefix, expected_title in SBT_CONTAMINATED_IDS:
    matched = [r for r in records if r["id"].startswith(prefix)]
    if matched:
        for m in matched:
            print(f"  [{m['status']:10s}] {m['id_short']} | {m['title']} | created={m['created']}")
    else:
        print(f"  [NOT_FOUND] prefix {prefix} ({expected_title})")

# 国保系・信販系の自己重複
print("\n=== 自己重複 2pairs: 国保/信販 ===")
keywords = ["国保", "信販"]
for kw in keywords:
    matched = [r for r in records if kw in r["title"]]
    print(f"  --- {kw} ---")
    for m in matched:
        print(f"    [{m['status']:10s}] {m['id_short']} | {m['title']}")

# 全体サマリ
print("\n=== Status breakdown ===")
from collections import Counter

status_counter = Counter([r["status"] for r in records])
for status, count in status_counter.most_common():
    print(f"  {status or '(empty)'}: {count}")
