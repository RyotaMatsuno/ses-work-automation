# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

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


def npatch(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def gtxt(p):
    if not p:
        return ""
    t = p.get("type", "")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
    if t == "select":
        return (p.get("select") or {}).get("name", "")
    if t == "number":
        return p.get("number")
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    return ""


# 1. 選考中 305件を全部「募集中」に一括更新
print("=== 選考中 → 募集中 一括更新 ===")
updated = 0
cursor = None
while True:
    payload = {"filter": {"property": "ステータス", "select": {"equals": "選考中"}}, "page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{CASE_DB}/query", payload)
    for page in res.get("results", []):
        try:
            npatch(f"pages/{page['id']}", {"properties": {"ステータス": {"select": {"name": "募集中"}}}})
            updated += 1
        except Exception as e:
            print(f"  エラー: {e}")
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")
    print(f"  更新中... {updated}件")
print(f"完了: {updated}件を募集中に変更")

# 2. 稼働中 10件の詳細を出力
print("\n=== 稼働中 10件 詳細 ===")
res2 = npost(
    f"databases/{CASE_DB}/query",
    {
        "filter": {"property": "ステータス", "select": {"equals": "稼働中"}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 20,
    },
)
for page in res2.get("results", []):
    props = page["properties"]
    name = gtxt(props.get("案件名", {}))
    price = gtxt(props.get("単価（万円）", {}))
    assignee = gtxt(props.get("担当者", {}))
    created = page.get("created_time", "")[:10]
    info_date = gtxt(props.get("情報取得日", {}))
    client = gtxt(props.get("クライアント", {}))
    location = gtxt(props.get("勤務地", {}))
    req_skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]
    print(f"案件名: {name}")
    print(f"  単価:{price}万 | 担当:{assignee} | 登録:{info_date or created} | クライアント:{client}")
    print(f"  勤務地:{location} | 必須スキル:{req_skills}")
    print()
