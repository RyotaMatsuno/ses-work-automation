# -*- coding: utf-8 -*-
"""上位4件の詳細取得"""

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
    ("380450ff-37c0-81ca-be38-e56b2882442e", "某業界向けシステム開発（SE＆PG募集）", 50, "score=5 トップ候補"),
    ("380450ff-37c0-8158-92d7-c31249e3ec0b", "公共系WEBシステム刷新 交代枠", 53, "score=1 単価優位"),
    ("37f450ff-37c0-8104-a9f8-cf3bdb9170d4", "後期高齢者医療標準システムの保守開発（COBOL）", 60, "外国籍OK確定"),
    ("380450ff-37c0-8130-a2e4-d35c2912b9b9", "RPA（UiPath）でのツール開発・改修業務", 47, "ツール開発系"),
]

for pid, title, price, tag in TARGETS:
    print(f"\n========== [{tag}] {title} ({price}万) ==========")
    print(f"page_id: {pid}")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  GET FAIL: {r.status_code}")
        continue
    p = r.json().get("properties", {})
    detail = "".join([t.get("plain_text", "") for t in p.get("案件詳細", {}).get("rich_text", [])])
    print("  --- 案件詳細 (first 1500 chars) ---")
    print(detail[:1500])
    print(f"  --- truncated, total {len(detail)} chars ---")
