# -*- coding: utf-8 -*-
"""PH候補4件の原文取得"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
HEADERS = {
    "Authorization": "Bearer " + (env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")),
    "Notion-Version": "2022-06-28",
}

TARGETS = [
    ("380450ff-37c0-8139-9e26-ea226ab6b7d7", "生保システム開発支援 50万"),
    ("380450ff-37c0-8176-88ab-f20d34c7f23f", "Linux運用保守 50万"),
    ("37f450ff-37c0-81a8-97d5-e5e3a8ceff00", "光アクセス施工管理 38万"),
    ("380450ff-37c0-811f-9f0e-f963936d9490", "パッチ対応支援 50万"),
]

for pid, label in TARGETS:
    print(f"\n{'=' * 50}")
    print(f"  {label} | page_id: {pid[:36]}")
    print(f"{'=' * 50}")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print(f"  ERR {r.status_code}")
        continue
    props = r.json().get("properties", {})
    detail = "".join([t.get("plain_text", "") for t in props.get("案件詳細", {}).get("rich_text", [])])
    if not detail:
        for k, v in props.items():
            if "原文" in k and v.get("type") == "rich_text":
                detail = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
                break
    print(detail[:1500])
