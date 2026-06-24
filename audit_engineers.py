import io
import sys

import requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = cfg["NOTION_API_KEY"]
DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

results = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{DB_ID}/query", headers=headers, json=payload)
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"総件数: {len(results)}")
print()

# (no name)、田中太郎、稼働日が古いものを抽出
no_name = []
tanaka = []
old_date = []

for page in results:
    props = page["properties"]
    page_id = page["id"]

    # 名前取得
    title_items = props.get("名前", {}).get("title", [])
    name = title_items[0]["plain_text"] if title_items else ""

    # 稼働可能日
    date_val = props.get("稼働可能日", {}).get("date")
    avail_date = date_val["start"] if date_val else None

    # スキル
    skills = [s["name"] for s in props.get("スキル", {}).get("multi_select", [])]

    print(f"  [{page_id}] 名前='{name}' 稼働日={avail_date} スキル={skills[:3]}")

    if not name or name.strip() == "":
        no_name.append({"id": page_id, "name": name, "avail_date": avail_date, "skills": skills})
    if name == "田中太郎":
        tanaka.append({"id": page_id, "name": name})
    if avail_date and avail_date < "2026-04-01":  # 3週間以上前（本日5/24基準で余裕を持って4月以前）
        old_date.append({"id": page_id, "name": name, "avail_date": avail_date})

print()
print(f"=== (no name): {len(no_name)}件 ===")
for e in no_name:
    print(f"  {e}")
print()
print(f"=== 田中太郎: {len(tanaka)}件 ===")
for e in tanaka:
    print(f"  {e}")
print()
print(f"=== 稼働日古い（4月以前）: {len(old_date)}件 ===")
for e in old_date:
    print(f"  {e}")
