import os
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v
API_KEY = os.environ.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
r = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1/query",
    headers=HEADERS,
    json={"page_size": 5},
)
pages = r.json().get("results", [])
print(f"取得: {len(pages)}件")
for p in pages:
    props = p["properties"]
    name_items = props.get("名前", {}).get("title", [])
    name_txt = name_items[0].get("plain_text", "?") if name_items else "?"
    assignee = props.get("担当者", {}).get("select")
    assignee_txt = assignee["name"] if assignee else "なし"
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note_txt = note_items[0].get("plain_text", "")[:50] if note_items else ""
    print(f"{name_txt} -> 担当者:{assignee_txt} | 備考:{note_txt}")
