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
LOG = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\research_results\close_senkou.log"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def log(msg):
    with open(LOG, 'a', encoding='utf-8') as f:
        f.write(msg + "\n")
        f.flush()

# Clear log
with open(LOG, 'w', encoding='utf-8') as f:
    f.write("")

# Get all 選考中
all_ids = []
has_more = True
start_cursor = None
while has_more:
    body = {"filter": {"property": "ステータス", "select": {"equals": "選考中"}}, "page_size": 100}
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=30)
    data = resp.json()
    for p in data.get("results", []):
        all_ids.append(p["id"])
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

log(f"Total: {len(all_ids)}")

success = 0
errors = 0
for i, pid in enumerate(all_ids):
    resp = requests.patch(
        f"https://api.notion.com/v1/pages/{pid}",
        headers=headers,
        json={"properties": {"ステータス": {"select": {"name": "終了"}}}},
        timeout=15
    )
    if resp.status_code == 200:
        success += 1
    else:
        errors += 1
    if (i+1) % 3 == 0:
        time.sleep(1.1)
    if (i+1) % 50 == 0:
        log(f"  {i+1}/{len(all_ids)} ok={success} err={errors}")

log(f"DONE: {success} ok, {errors} err")
print(f"Launched. Total={len(all_ids)}")
