"""案件・人材の登録テスト"""
import requests, os
from dotenv import dotenv_values
from pathlib import Path

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    os.environ.setdefault(k, v)

NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")
ENGINEER_DB = os.environ.get("NOTION_ENGINEER_DB_ID", "")
headers = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 案件テスト登録
r1 = requests.post("https://api.notion.com/v1/pages", headers=headers, json={
    "parent": {"database_id": PROJECT_DB},
    "properties": {
        "案件名": {"title": [{"text": {"content": "[テスト]Javaバックエンド案件"}}]},
        "ステータス": {"select": {"name": "募集中"}},
        "案件詳細": {"rich_text": [{"text": {"content": "パイプラインテスト登録"}}]},
        "必要スキル": {"multi_select": [{"name": "Java"}]},
        "単価（万円）": {"number": 65}
    }
})
print(f"案件登録: {r1.status_code} {'OK' if r1.status_code == 200 else r1.json().get('message','')}")

# 人材テスト登録
r2 = requests.post("https://api.notion.com/v1/pages", headers=headers, json={
    "parent": {"database_id": ENGINEER_DB},
    "properties": {
        "名前": {"title": [{"text": {"content": "[テスト]T.T"}}]},
        "稼働状況": {"select": {"name": "稼働可能"}},
        "備考（LINEメモ）": {"rich_text": [{"text": {"content": "パイプラインテスト登録"}}]},
        "スキル": {"multi_select": [{"name": "Java"}]},
        "単価（万円）": {"number": 55}
    }
})
print(f"人材登録: {r2.status_code} {'OK' if r2.status_code == 200 else r2.json().get('message','')}")
