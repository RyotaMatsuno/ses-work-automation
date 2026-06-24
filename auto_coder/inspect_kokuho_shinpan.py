# -*- coding: utf-8 -*-
"""国保/信販 4件の案件詳細を取得して比較材料を整理"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

TARGETS = [
    ("37f450ff-37c0-8119-b12c-c0ac83cc2908", "国保向け健康保険組合向けシステム改修・保守（8月）"),
    ("37f450ff-37c0-8103-b1ee-ccb390fd49e6", "国保向け健康保険組合向けシステム改修・保守"),
    ("37f450ff-37c0-81ad-858f-d836a8e6dbf9", "某大手信販会の運用保守(半年短期予定)"),
    ("37f450ff-37c0-8117-8e54-f58e839cce08", "某大手信販会の運用保守"),
]

for pid, title in TARGETS:
    print(f"\n========== {title[:60]} ==========")
    print(f"page_id: {pid}")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  GET FAIL: {r.status_code}")
        continue
    data = r.json()
    print(f"  created: {data.get('created_time')}")
    props = data.get("properties", {})
    # 案件詳細
    detail = props.get("案件詳細", {}).get("rich_text", [])
    text = "".join([t.get("plain_text", "") for t in detail])
    # First 2000 chars
    print("  --- 案件詳細 (first 2000 chars) ---")
    print(text[:2000])
    print(f"  --- (truncated, total {len(text)} chars) ---")
