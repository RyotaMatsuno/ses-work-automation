import sys

sys.stdout.reconfigure(encoding="utf-8")

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY") or config.get("NOTION_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

pages = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json=payload)
    d = r.json()
    pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]

print(f"合計 {len(pages)}件")
print("--- 各エントリの最終更新日 ---")
for p in pages:
    name_items = p["properties"].get("名前", {}).get("title", [])
    name = name_items[0].get("plain_text", "?") if name_items else "?"
    last_edited = p.get("last_edited_time", "")[:10]
    src_items = p["properties"].get("入力元", {}).get("select", {})
    src = src_items.get("name", "?") if src_items else "?"
    print(f"  {last_edited} | {name[:15]} | {src}")
