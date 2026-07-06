import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get ALL pages (no filter) with pagination
all_pages = []
has_more = True
start_cursor = None
while has_more:
    body = {"page_size": 100}
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=30)
    data = resp.json()
    all_pages.extend(data.get("results", []))
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

total = len(all_pages)

# Status breakdown
status_dist = {}
for p in all_pages:
    st = (p["properties"].get("ステータス", {}).get("select") or {}).get("name", "(なし)")
    status_dist[st] = status_dist.get(st, 0) + 1

print(f"案件DB 全{total}件\n")
for k, v in sorted(status_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
