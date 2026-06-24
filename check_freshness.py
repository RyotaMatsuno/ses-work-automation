import sys
from datetime import datetime, timezone

import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 最近100件の last_edited_time を確認
res = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 20, "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]},
)
results = res.json().get("results", [])

now = datetime.now(timezone.utc)
sys.stdout.buffer.write(b"Recent 20 projects last_edited_time:\n")
for p in results:
    t = p.get("last_edited_time", "")
    if t:
        dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
        delta = now - dt
        days = delta.days
    else:
        days = 999
    props = p.get("properties", {})
    name = ""
    for v in props.get("\u6848\u4ef6\u540d", {}).get("title", []):
        name += v.get("plain_text", "")
    sys.stdout.buffer.write(f"  {days}d: {name[:25]}\n".encode("utf-8"))
