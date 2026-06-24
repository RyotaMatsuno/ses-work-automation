# -*- coding: utf-8 -*-
import io
import sys

import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {"Authorization": f"Bearer {NOTION_KEY}", "Notion-Version": "2022-06-28"}
r = requests.get(f"https://api.notion.com/v1/databases/{PROJECT_DB}", headers=headers)
props = r.json().get("properties", {})
if "入力元" in props:
    options = props["入力元"].get("select", {}).get("options", [])
    print("入力元の選択肢:")
    for opt in options:
        print(f'  - "{opt["name"]}"')
else:
    print("入力元フィールドなし")
