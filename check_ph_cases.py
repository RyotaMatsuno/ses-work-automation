# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from datetime import date, datetime, timedelta

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# 募集中で単価37〜47万の案件を全件確認
print("=== 募集中・単価37〜47万の案件 全件（4営業日以内） ===")
results, cursor = [], None
while True:
    payload = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "単価（万円）", "number": {"greater_than_or_equal_to": 37}},
                {"property": "単価（万円）", "number": {"less_than_or_equal_to": 47}},
            ]
        },
        "sorts": [{"property": "単価（万円）", "direction": "descending"}],
        "page_size": 100,
    }
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{CASE_DB}/query", payload)
    results.extend(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

print(f"総件数: {len(results)}件")
print()

# 4営業日チェック（line_query.pyと同じロジック）
import jpholiday


def business_days_since(created_time_str):
    if not created_time_str:
        return 999
    start_date = datetime.fromisoformat(created_time_str.replace("Z", "+00:00")).date()
    today = date.today()
    if start_date >= today:
        return 0
    days = 0
    current = start_date + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and not jpholiday.is_holiday(current):
            days += 1
        current += timedelta(days=1)
    return days


within_4 = []
over_4 = []
for page in results:
    props = page["properties"]
    name_items = props.get("案件名", {}).get("title", [])
    name = "".join(x.get("plain_text", "") for x in name_items)
    price = props.get("単価（万円）", {}).get("number") or 0
    created = page.get("created_time", "")
    age = business_days_since(created)
    created_date = created[:10]
    if age <= 4:
        within_4.append({"name": name, "price": price, "age": age, "created": created_date})
    else:
        over_4.append({"name": name, "price": price, "age": age, "created": created_date})

print(f"4営業日以内: {len(within_4)}件")
for c in within_4:
    print(f"  {c['name'][:40]:<40} | {c['price']}万 | {c['age']}日前 ({c['created']})")

print(f"\n4営業日超（除外中）: {len(over_4)}件")
for c in over_4[:10]:
    print(f"  {c['name'][:40]:<40} | {c['price']}万 | {c['age']}日前 ({c['created']})")
if len(over_4) > 10:
    print(f"  ...他{len(over_4) - 10}件")
