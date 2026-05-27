import requests
from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
NOTION_API_KEY = config["NOTION_API_KEY"]
ENGINEER_DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 現在のDBスキーマを確認
res = requests.get(f"https://api.notion.com/v1/databases/{ENGINEER_DB_ID}", headers=headers)
db = res.json()
props = db.get("properties", {})
print("現在のフィールド一覧:")
for name, prop in props.items():
    print(f"  {name}: {prop['type']}")
