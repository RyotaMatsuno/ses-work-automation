# -*- coding: utf-8 -*-
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import sys as _sys

_sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("NOTION_TOKEN") or env.get("NOTION_API_KEY")
db_id = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

results = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"総件数: {len(results)}件\n")
print(f"{'名前':<20} {'スキル'}")
print("-" * 80)
for p in results:
    props = p["properties"]
    name_items = props.get("名前", {}).get("title", [])
    name = name_items[0]["plain_text"] if name_items else "不明"
    skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note_len = len(note_items[0]["plain_text"]) if note_items else 0
    skill_str = ", ".join(skills) if skills else "(なし)"
    print(f"{name:<20} {skill_str}  [備考:{note_len}文字]")
