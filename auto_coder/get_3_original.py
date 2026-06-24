# -*- coding: utf-8 -*-
"""原文取得: HS用2件 + PH用1件"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"}

TARGETS = [
    ("383450ff-37c0-81c6-8bff-ff3f3ebd4d73", "【既送信】勤怠・給与システム 田町 78万"),
    ("380450ff-37c0-81cd-8a23-c0ffcc9ba437", "【追加】証券代行業務システム 調布 70-75万"),
    ("380450ff-37c0-81ca-be38-e56b2882442e", "【PH向け】某業界向けシステム開発 50万"),
]

for pid, label in TARGETS:
    print("\n========================================")
    print(f"  {label}")
    print(f"  page_id: {pid}")
    print("========================================")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  ERR {r.status_code}: {r.text[:300]}")
        continue
    p = r.json().get("properties", {})
    title = ""
    for k, v in p.items():
        if v.get("type") == "title":
            title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
    print(f"  Title: {title}")
    detail = "".join([t.get("plain_text", "") for t in p.get("案件詳細", {}).get("rich_text", [])])
    print("\n--- 案件詳細 原文 ---")
    print(detail)
    print(f"\n--- (total {len(detail)} chars) ---\n")
