"""プロパティ名の正確な確認（バイト列で直接表示）"""

import json
import os
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    os.environ.setdefault(k, v)

NOTION_KEY = os.environ.get("NOTION_API_KEY", "")
PROJECT_DB = os.environ.get("NOTION_PROJECT_DB_ID", "")
ENGINEER_DB = os.environ.get("NOTION_ENGINEER_DB_ID", "")

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

r = requests.get(f"https://api.notion.com/v1/databases/{PROJECT_DB}", headers=headers)
props = r.json().get("properties", {})
proj_keys = list(props.keys())

r2 = requests.get(f"https://api.notion.com/v1/databases/{ENGINEER_DB}", headers=headers)
props2 = r2.json().get("properties", {})
eng_keys = list(props2.keys())

output = {
    "project_properties": {k: props[k]["type"] for k in proj_keys},
    "engineer_properties": {k: props2[k]["type"] for k in eng_keys},
}

with open("notion_props.json", "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("saved to notion_props.json")
