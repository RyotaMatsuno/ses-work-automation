"""Notion登録エラーの原因調査"""

import os
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    os.environ.setdefault(k, v)

NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")
ENGINEER_DB = os.environ.get("NOTION_ENGINEER_DB_ID", "")

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 案件DBのプロパティ確認
r = requests.get(f"https://api.notion.com/v1/databases/{PROJECT_DB}", headers=headers)
data = r.json()
print("=== 案件DB プロパティ一覧 ===")
for k in data.get("properties", {}).keys():
    print(f"  - {k}")

# テスト登録
print("\n=== テスト登録 ===")
props = {
    "案件名": {"title": [{"text": {"content": "テスト案件"}}]},
    "ステータス": {"select": {"name": "募集中"}},
    "備考": {"rich_text": [{"text": {"content": "テスト"}}]},
}
r2 = requests.post(
    "https://api.notion.com/v1/pages",
    headers=headers,
    json={"parent": {"database_id": PROJECT_DB}, "properties": props},
)
print(f"ステータス: {r2.status_code}")
if r2.status_code != 200:
    print(r2.json())
