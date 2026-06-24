import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import dotenv_values

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
config = dotenv_values(ENV_PATH)
h = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 全件取得して作成日別に集計
pages, payload = [], {"page_size": 100}
while True:
    r = requests.post(
        "https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1/query", headers=h, json=payload
    )
    data = r.json()
    pages.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"総件数: {len(pages)}")
from collections import Counter

dates = Counter()
for p in pages:
    ct = p.get("created_time", "")[:10]
    dates[ct] += 1
for d, cnt in sorted(dates.items()):
    print(f"  {d}: {cnt}件")
