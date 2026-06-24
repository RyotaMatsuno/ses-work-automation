import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
NOTION_API_KEY = config["NOTION_API_KEY"]
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# 所属会社（rich_text）と担当者名（所属側）（rich_text）を追加
payload = {
    "properties": {"所属会社": {"rich_text": {}}, "所属担当者名": {"rich_text": {}}, "所属メール": {"email": {}}}
}

res = requests.patch(f"https://api.notion.com/v1/databases/{ENGINEER_DB_ID}", headers=headers, json=payload)
print(f"status: {res.status_code}")
if res.status_code == 200:
    print("フィールド追加OK: 所属会社 / 所属担当者名 / 所属メール")
else:
    print(res.text[:300])
