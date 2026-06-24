# -*- coding: utf-8 -*-
import os
import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV_PATH = Path(__file__).resolve().parent.parent / "config" / ".env"
config = dotenv_values(ENV_PATH, encoding="utf-8")
for key, value in config.items():
    if value and key not in os.environ:
        os.environ[key] = value

NOTION_TOKEN = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY", "")
DB_ID = os.environ.get("NOTION_ENGINEER_DB_ID", "343450ff-37c0-819d-8769-fb0a8a4ceeb1")

if not NOTION_TOKEN:
    print(f"[ERROR] NOTION_API_KEY / NOTION_TOKEN が未設定です ({ENV_PATH})")
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

res = requests.get(
    f"https://api.notion.com/v1/databases/{DB_ID}",
    headers=HEADERS,
    timeout=30,
)
res.raise_for_status()
existing = res.json().get("properties", {})

if "情報取得日" in existing:
    print("✅ 情報取得日: すでに存在します")
    raise SystemExit(0)

patch = requests.patch(
    f"https://api.notion.com/v1/databases/{DB_ID}",
    headers=HEADERS,
    json={"properties": {"情報取得日": {"date": {}}}},
    timeout=30,
)
if patch.status_code == 200:
    print("✅ 情報取得日: 追加成功")
else:
    print(f"❌ 追加失敗: {patch.status_code} {patch.text}")
    raise SystemExit(1)
