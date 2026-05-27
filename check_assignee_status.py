from dotenv import dotenv_values
import requests, os
from pathlib import Path

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

NOTION_KEY = os.environ["NOTION_API_KEY"]
ENGINEER_DB = os.environ["NOTION_ENGINEER_DB_ID"]
PROJECT_DB = os.environ["NOTION_PROJECT_DB_ID"]
HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# エンジニアDBを数件確認
r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
                  headers=HEADERS, json={"page_size": 3})
data = r.json()
pages = data.get("results", [])
print(f"取得件数: {len(pages)}")
for p in pages:
    props = p["properties"]
    name_prop = props.get("名前", {}).get("title", [])
    name = name_prop[0]["plain_text"] if name_prop else "未記載"
    assignee_prop = props.get("担当者", {})
    current = assignee_prop.get("select")
    print(f"  {name} / 担当者: {current}")
