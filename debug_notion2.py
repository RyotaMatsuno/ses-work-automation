"""Notion DBプロパティの詳細確認"""
import requests, os, json
from dotenv import dotenv_values
from pathlib import Path

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    os.environ.setdefault(k, v)

NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")
ENGINEER_DB = os.environ.get("NOTION_ENGINEER_DB_ID", "")

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

print("=== 案件DB ===")
r = requests.get(f"https://api.notion.com/v1/databases/{PROJECT_DB}", headers=headers)
props = r.json().get("properties", {})
for k, v in props.items():
    print(f"  [{v['type']}] {k}")

print("\n=== エンジニアDB ===")
r2 = requests.get(f"https://api.notion.com/v1/databases/{ENGINEER_DB}", headers=headers)
props2 = r2.json().get("properties", {})
for k, v in props2.items():
    print(f"  [{v['type']}] {k}")
