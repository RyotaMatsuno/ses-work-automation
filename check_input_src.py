import datetime
import json
import urllib.request
from collections import Counter

from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

two_days_ago = (
    datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))) - datetime.timedelta(days=2)
).strftime("%Y-%m-%dT%H:%M:%S+09:00")

payload = {"page_size": 100, "filter": {"timestamp": "created_time", "created_time": {"after": two_days_ago}}}
pages = []
cursor = None
while True:
    if cursor:
        payload["start_cursor"] = cursor
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        res = json.loads(r.read())
    pages.extend(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

# 入力元（メールアドレス/担当者）の分布で出回り判定
sender_counter = Counter()
input_src_counter = Counter()
for p in pages:
    props = p["properties"]
    # 担当者
    assignee = props.get("担当者", {}).get("select", {})
    assignee_name = assignee.get("name", "") if assignee else ""
    # 入力元
    src = props.get("入力元", {})
    src_type = src.get("type", "")
    if src_type == "select" and src.get("select"):
        src_val = src["select"].get("name", "")
    elif src_type == "rich_text":
        src_val = "".join(t.get("plain_text", "") for t in src.get("rich_text", []))
    else:
        src_val = src_type
    input_src_counter[src_val] += 1

print(f"2日以内の案件: {len(pages)}件")
print("\n=== 入力元の分布 ===")
for k, v in input_src_counter.most_common(20):
    print(f"  {repr(k)}: {v}件")
