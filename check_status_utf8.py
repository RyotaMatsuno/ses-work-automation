import io
import sys

import requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

cfg = dotenv_values("config/.env")
NOTION_TOKEN = cfg["NOTION_API_KEY"]
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

db_id = "343450ff-37c0-81e4-934e-f25f90284a3c"
r = requests.get(f"https://api.notion.com/v1/databases/{db_id}", headers=headers, timeout=10)
db = r.json()
status_prop = db.get("properties", {}).get("ステータス", {})
options = status_prop.get("select", {}).get("options", [])
print("ステータス選択肢:")
for o in options:
    print(repr(o["name"]))

# 全プロパティも確認
print("\n全プロパティ:")
for k in db.get("properties", {}).keys():
    print(repr(k))
