import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

config = dotenv_values("config/.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# エンジニアDB追加フィールド
engineer_db = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
engineer_add = {
    "properties": {
        "添付ファイルパス": {"rich_text": {}},
        "DriveリンクURL": {"url": {}},
        "人員情報原文": {"rich_text": {}},
        "最寄り駅": {"rich_text": {}},
        "イニシャル": {"rich_text": {}},
    }
}
r1 = requests.patch(f"https://api.notion.com/v1/databases/{engineer_db}", headers=headers, json=engineer_add)
print("エンジニアDB追加:", r1.status_code, flush=True)
if r1.status_code != 200:
    print(r1.text[:300], flush=True)

# 案件DB追加フィールド
project_db = "343450ff-37c0-81e4-934e-f25f90284a3c"
project_add = {
    "properties": {
        "元MessageID": {"rich_text": {}},
        "案件情報原文": {"rich_text": {}},
        "仕入単価（万円）": {"number": {"format": "number"}},
    }
}
r2 = requests.patch(f"https://api.notion.com/v1/databases/{project_db}", headers=headers, json=project_add)
print("案件DB追加:", r2.status_code, flush=True)
if r2.status_code != 200:
    print(r2.text[:300], flush=True)

print("完了", flush=True)
