import requests
from dotenv import dotenv_values

cfg = dotenv_values("config/.env")
NOTION_TOKEN = cfg["NOTION_API_KEY"]
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# 案件ページ1つのプロパティ構造を確認
page_id = "364450ff-37c0-81a8-b240-fd79783c92fa"  # Laravel/Next.js
r = requests.get(f"https://api.notion.com/v1/pages/{page_id}", headers=headers)
props = r.json().get("properties", {})
print("=== プロパティ一覧 ===")
for k, v in props.items():
    print(f"{k}: {v.get('type')}")
