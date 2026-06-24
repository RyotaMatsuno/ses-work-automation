import os
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

NOTION_KEY = os.environ["NOTION_API_KEY"]
ENGINEER_DB = os.environ["NOTION_ENGINEER_DB_ID"]
HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# テスト用：岡本担当エンジニアを1件作成
r = requests.post(
    "https://api.notion.com/v1/pages",
    headers=HEADERS,
    json={
        "parent": {"database_id": ENGINEER_DB},
        "properties": {
            "名前": {"title": [{"text": {"content": "TEST_岡本担当エンジニア"}}]},
            "稼働状況": {"select": {"name": "稼働可能"}},
            "担当者": {"select": {"name": "岡本"}},
            "スキル": {"multi_select": [{"name": "Java"}]},
            "単価（万円）": {"number": 60},
        },
    },
)
if r.status_code == 200:
    pid = r.json()["id"]
    print(f"[OK] テストエンジニア作成: {pid}")
else:
    print(f"[NG] {r.status_code}: {r.text[:200]}")
