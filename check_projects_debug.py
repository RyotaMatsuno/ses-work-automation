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

# まず最新10件の入力元フィールドを確認
cutoff = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S")
payload = {
    "filter": {"timestamp": "created_time", "created_time": {"on_or_after": cutoff}},
    "sorts": [{"timestamp": "created_time", "direction": "descending"}],
    "page_size": 20,
}
r = requests.post(f"https://api.notion.com/v1/databases/{PROJECT_DB}/query", headers=headers, json=payload)
results = r.json().get("results", [])
print(f"直近7日の全案件: {len(results)}件")
for p in results:
    props = p.get("properties", {})
    title_items = props.get("案件名", {}).get("title", [])
    name = "".join([t.get("plain_text", "") for t in title_items])[:30] if title_items else "(無題)"
    src_items = props.get("入力元", {}).get("rich_text", [])
    src = "".join([t.get("plain_text", "") for t in src_items]) if src_items else "(空)"
    created = p.get("created_time", "")[:10]
    print(f"  [{created}] {name} | 入力元={src}")
