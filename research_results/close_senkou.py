import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
import time
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get all 選考中 pages
all_pages = []
has_more = True
start_cursor = None
while has_more:
    body = {
        "filter": {"property": "ステータス", "select": {"equals": "選考中"}},
        "page_size": 100
    }
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=30)
    data = resp.json()
    all_pages.extend(data.get("results", []))
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

print(f"選考中: {len(all_pages)}件 → 全件「終了」に変更\n")

# Batch update
success = 0
errors = 0
for i, page in enumerate(all_pages):
    page_id = page["id"]
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=headers,
        json={
            "properties": {
                "ステータス": {"select": {"name": "終了"}}
            }
        },
        timeout=15
    )
    if resp.status_code == 200:
        success += 1
    else:
        errors += 1
        if errors <= 3:
            print(f"  ERROR [{i}]: {resp.status_code} {resp.text[:100]}")
    
    # Rate limit: Notion API is 3 req/sec
    if (i + 1) % 3 == 0:
        time.sleep(1.1)
    
    if (i + 1) % 50 == 0:
        print(f"  Progress: {i+1}/{len(all_pages)} (success:{success}, error:{errors})")

print(f"\nDone: {success} success, {errors} errors")
