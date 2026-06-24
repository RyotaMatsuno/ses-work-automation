import sys
from datetime import datetime, timezone

import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# created_time で確認
res = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 20, "sorts": [{"timestamp": "created_time", "direction": "descending"}]},
)
results = res.json().get("results", [])

now = datetime.now(timezone.utc)
from collections import Counter

day_dist = Counter()
for p in results:
    ct = p.get("created_time", "")
    if ct:
        dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
        days = (now - dt).days
        day_dist[days] += 1
    name = ""
    for v in p.get("properties", {}).get("\u6848\u4ef6\u540d", {}).get("title", []):
        name += v.get("plain_text", "")
    sys.stdout.buffer.write(f"  created {days}d ago: {name[:30]}\n".encode("utf-8"))

sys.stdout.buffer.write(b"\nDistribution:\n")
for d in sorted(day_dist):
    sys.stdout.buffer.write(f"  {d}d: {day_dist[d]}件\n".encode("utf-8"))
