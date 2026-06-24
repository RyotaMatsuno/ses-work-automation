import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 全案件のステータスを集計
cursor = None
status_count = {}
total = 0
while True:
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    res = requests.post(
        "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query", headers=headers, json=body
    )
    data = res.json()
    results = data.get("results", [])
    for p in results:
        st = p.get("properties", {}).get("\u30b9\u30c6\u30fc\u30bf\u30b9", {})
        val = (st.get("select") or {}).get("name", "(empty)")
        status_count[val] = status_count.get(val, 0) + 1
    total += len(results)
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")

sys.stdout.buffer.write(f"Total projects: {total}\n".encode())
sys.stdout.buffer.write(b"Status breakdown:\n")
for k, v in sorted(status_count.items(), key=lambda x: -x[1]):
    sys.stdout.buffer.write(f"  {k!r}: {v}\n".encode("utf-8"))
