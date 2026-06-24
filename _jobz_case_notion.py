import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SES = Path(os.getcwd())
env = {}
with open(SES / "config" / ".env", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN", "")
CASE_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"

# 4営業日前を計算
JST = timezone(timedelta(hours=9))
today = datetime.now(JST).date()
# 4営業日前（土日スキップ）
count = 0
d = today
while count < 4:
    d -= timedelta(days=1)
    if d.weekday() < 5:  # 月-金
        count += 1
since = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=JST)
print(f"■ 4営業日前: {since.isoformat()}")

# 案件DB クエリ（フィルタなし、最新10件）
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# まず全件数確認（created_time フィルタなし）
r = requests.post(
    f"https://api.notion.com/v1/databases/{CASE_DB_ID}/query",
    headers=headers,
    json={"page_size": 10, "sorts": [{"timestamp": "created_time", "direction": "descending"}]},
    timeout=15,
)
data = r.json()
results = data.get("results", [])
print(f"\n■ 案件DB 最新{len(results)}件（created_time 降順）")
for page in results:
    ct = page.get("created_time", "")
    props = page.get("properties", {})
    # タイトル取得
    title = ""
    for pname, pval in props.items():
        if pval.get("type") == "title":
            rich = pval.get("title", [])
            title = "".join(r.get("plain_text", "") for r in rich)
            break
    print(f"  [{ct[:10]}] {title[:50]}")

# created_time フィルタで4営業日以内
r2 = requests.post(
    f"https://api.notion.com/v1/databases/{CASE_DB_ID}/query",
    headers=headers,
    json={"page_size": 20, "filter": {"timestamp": "created_time", "created_time": {"on_or_after": since.isoformat()}}},
    timeout=15,
)
data2 = r2.json()
results2 = data2.get("results", [])
print(f"\n■ 4営業日以内（{since.date()} 以降）の案件: {len(results2)}件")
for page in results2:
    ct = page.get("created_time", "")
    props = page.get("properties", {})
    title = ""
    for pname, pval in props.items():
        if pval.get("type") == "title":
            rich = pval.get("title", [])
            title = "".join(r.get("plain_text", "") for r in rich)
            break
    print(f"  [{ct[:10]}] {title[:60]}")
