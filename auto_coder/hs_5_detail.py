# -*- coding: utf-8 -*-
"""HS年齢OK+商流OK 5件の詳細取得"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"}

TARGETS = [
    ("383450ff-37c0-81f7-afdb-d51fdea7885d", "★新着 購買管理システム 65万 score=6"),
    ("37f450ff-37c0-81e0-9fe3-ec56edd00ffb", "証拠金取引 75万"),
    ("380450ff-37c0-816a-9a0d-d1b55e2590a2", "Hベンダ Java基本設計 75万"),
    ("380450ff-37c0-81bb-b3e1-c372f76e2693", "PL/SQL技術者 63万"),
    ("380450ff-37c0-81d7-b23e-fb696f36c9a2", "SRE統合監視 70万"),
]

for pid, label in TARGETS:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"  page_id: {pid}")
    print(f"{'=' * 60}")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  ERR {r.status_code}")
        continue
    detail = "".join(
        [t.get("plain_text", "") for t in r.json().get("properties", {}).get("案件詳細", {}).get("rich_text", [])]
    )
    print(detail[:2000])
    print(f"\n--- (total {len(detail)} chars) ---")
