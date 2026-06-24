# -*- coding: utf-8 -*-
import datetime
import io
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 4営業日 = 約6暦日
cutoff = (datetime.datetime.now() - datetime.timedelta(days=6)).strftime("%Y-%m-%dT00:00:00")

r = requests.post(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
    headers=headers,
    json={
        "filter": {"timestamp": "created_time", "created_time": {"on_or_after": cutoff}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 100,
    },
)
results = r.json().get("results", [])
print(f"直近6日の案件合計: {len(results)}件")
print()

# 日付別集計
by_date = {}
for p in results:
    date_str = p["created_time"][:10]
    props = p.get("properties", {})
    title = "".join([t.get("plain_text", "") for t in props.get("案件名", {}).get("title", [])])
    src_items = props.get("入力元", {}).get("rich_text", [])
    src = "".join([t.get("plain_text", "") for t in src_items]) if src_items else "(空)"
    by_date.setdefault(date_str, []).append((title[:40], src))

for date_str in sorted(by_date.keys(), reverse=True):
    items = by_date[date_str]
    print(f"【{date_str}】{len(items)}件")
    for title, src in items:
        print(f"  - {title} | 入力元:{src}")
