# -*- coding: utf-8 -*-
"""HS北小金候補のTop3詳細"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": "2022-06-28"}

TARGETS = [
    ("380450ff-37c0-81af-91ec-eddb308d5b8a", "官庁・自治体Webアプリ開発", 70, "score=7 最有力"),
    ("380450ff-37c0-81cd-8a23-c0ffcc9ba437", "証券代行業務システム", 75, "score=3"),
    ("37f450ff-37c0-81e0-9fe3-ec56edd00ffb", "証拠金取引ストレステスト", 75, "score=3"),
    ("380450ff-37c0-81a2-b56b-f50855ca7eb7", "通信事業者小売販売管理", 75, "score=2"),
    ("380450ff-37c0-816a-9a0d-d1b55e2590a2", "Hベンダ Java基本設計", 75, "score=1"),
]

for pid, name, price, tag in TARGETS:
    print(f"\n========== [{tag}] {name} ({price}万) ==========")
    print(f"page_id: {pid}")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  ERR {r.status_code}")
        continue
    detail = "".join(
        [t.get("plain_text", "") for t in r.json().get("properties", {}).get("案件詳細", {}).get("rich_text", [])]
    )
    print(detail[:1700])
    print(f"--- (total {len(detail)} chars) ---")
