import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import requests
from dotenv import dotenv_values

cfg = dotenv_values("../config/.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
eng_db = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 1件だけ取得してプロパティ構造を確認
res = requests.post(f"https://api.notion.com/v1/databases/{eng_db}/query", headers=headers, json={"page_size": 1})
data = res.json()
if data.get("results"):
    page = data["results"][0]
    props = page.get("properties", {})
    print("Property names:", list(props.keys()))
    print()
    # イニシャル、名前、最寄り駅、備考のプロパティ構造を表示
    for key in list(props.keys())[:8]:
        p = props[key]
        print(f"{key!r}: type={p.get('type')!r}")
else:
    print("No results:", data)
