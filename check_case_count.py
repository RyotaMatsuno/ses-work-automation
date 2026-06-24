# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
JST = timezone(timedelta(hours=9))


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# 募集中の全件数を確認
print("=== 案件DB ステータス別件数 ===")
for status in ["募集中", "稼働中", "選考中", "クローズ", "営業終了"]:
    res = npost(
        f"databases/{CASE_DB}/query",
        {"filter": {"property": "ステータス", "select": {"equals": status}}, "page_size": 1},
    )
    # has_moreがあるので全件カウント
    count = 0
    cursor = None
    while True:
        payload = {"filter": {"property": "ステータス", "select": {"equals": status}}, "page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r2 = npost(f"databases/{CASE_DB}/query", payload)
        count += len(r2.get("results", []))
        if not r2.get("has_more"):
            break
        cursor = r2.get("next_cursor")
    print(f"  {status}: {count}件")

# webhook_server.pyが取得している件数（募集中+稼働中+選考中）
print("\n=== webhook_server.pyのget_active_projects()が取得する件数 ===")
total = 0
for status in ["募集中", "稼働中", "選考中"]:
    cursor = None
    cnt = 0
    while True:
        payload = {"filter": {"property": "ステータス", "select": {"equals": status}}, "page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r2 = npost(f"databases/{CASE_DB}/query", payload)
        cnt += len(r2.get("results", []))
        if not r2.get("has_more"):
            break
        cursor = r2.get("next_cursor")
    total += cnt
    print(f"  {status}: {cnt}件")
print(f"  合計: {total}件")

# 今日の案件（情報取得日=今日）
today = datetime.now(JST).strftime("%Y-%m-%d")
cnt = 0
cursor = None
while True:
    payload = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "情報取得日", "date": {"on_or_after": today}},
            ]
        },
        "page_size": 100,
    }
    if cursor:
        payload["start_cursor"] = cursor
    r2 = npost(f"databases/{CASE_DB}/query", payload)
    cnt += len(r2.get("results", []))
    if not r2.get("has_more"):
        break
    cursor = r2.get("next_cursor")
print(f"\n  本日({today})登録の募集中案件: {cnt}件")

# 単価37〜50万の募集中案件
cnt2 = 0
cursor = None
while True:
    payload = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "単価（万円）", "number": {"greater_than_or_equal_to": 37}},
                {"property": "単価（万円）", "number": {"less_than_or_equal_to": 50}},
            ]
        },
        "page_size": 100,
    }
    if cursor:
        payload["start_cursor"] = cursor
    r2 = npost(f"databases/{CASE_DB}/query", payload)
    cnt2 += len(r2.get("results", []))
    if not r2.get("has_more"):
        break
    cursor = r2.get("next_cursor")
print(f"  単価37〜50万の募集中案件: {cnt2}件")
