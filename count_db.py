
import requests, sys, time
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import dotenv_values
from pathlib import Path

ENV_PATH = Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

CUTOFF = "2026-05-09"

all_pages = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    r = requests.post(
        f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
        headers=HEADERS, json=payload, timeout=30
    )
    data = r.json()
    all_pages.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]
    time.sleep(0.3)

targets = [p for p in all_pages if p["created_time"][:10] < CUTOFF]
keeps   = [p for p in all_pages if p["created_time"][:10] >= CUTOFF]

print(f"現在の総件数: {len(all_pages)}")
print(f"削除対象残り: {len(targets)}件")
print(f"保持対象: {len(keeps)}件")
