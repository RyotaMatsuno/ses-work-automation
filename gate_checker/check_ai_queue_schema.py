#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Notion 追加更新: AI作業キューDB登録 + SES Wiki修正"""

import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv("C:/Users/ma_py/OneDrive/デスクトップ/ses_work/config/.env")

NOTION_TOKEN = os.environ["NOTION_API_KEY"]
WIKI_BLOCK_ID = "353450ff-37c0-8145-9e3e-d80c8c8ed594"
AI_QUEUE_DB_ID = "37a450ff-37c0-819a-981b-c2e06ed282bb"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# === 1. AI作業キューDBにタスク登録 ===
# まずスキーマ確認のためDBを取得
db_resp = requests.get(
    f"https://api.notion.com/v1/databases/{AI_QUEUE_DB_ID}",
    headers=headers,
    timeout=20,
)
print(f"AI Queue DB schema status: {db_resp.status_code}")
if db_resp.status_code == 200:
    schema = db_resp.json().get("properties", {})
    print(f"Properties: {list(schema.keys())}")
    for k, v in schema.items():
        print(f"  - {k}: {v.get('type')}")
else:
    print(db_resp.text[:500])
