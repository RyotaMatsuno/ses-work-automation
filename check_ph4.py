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
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
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
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in p.get("multi_select", []))
    if t == "number":
        return p.get("number")
    if t == "checkbox":
        return p.get("checkbox", False)
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    return ""


# PHさんを全件から探す
print("=== PHさん検索（全件スキャン）===")
cursor = None
ph_engineer = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{ENG_DB}/query", payload)
    for page in res.get("results", []):
        props = page["properties"]
        name = gtxt(props.get("名前", {}))
        initial = gtxt(props.get("イニシャル", {}))
        if "PH" in (name + initial).upper():
            ph_engineer = page
            print(f"発見: 名前={name} / イニシャル={initial}")
            print(f"  単価: {gtxt(props.get('単価（万円）', {}))}")
            print(f"  スキル: {gtxt(props.get('スキル', {}))[:150]}")
            print(f"  提案対象フラグ: {gtxt(props.get('提案対象フラグ', {}))}")
            print(f"  稼働状況: {gtxt(props.get('稼働状況', {}))}")
            print(f"  居住地: {gtxt(props.get('居住地', {}))}")
            print(f"  情報取得日: {gtxt(props.get('情報取得日', {}))}")
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

if not ph_engineer:
    print("PHさんがエンジニアDBに見つかりませんでした")

# 有効案件を確認（情報取得日が4営業日以内）
print("\n=== 有効案件（直近4日）===")
four_days_ago = (datetime.now(JST) - timedelta(days=4)).strftime("%Y-%m-%d")
res2 = npost(
    f"databases/{CASE_DB}/query",
    {
        "filter": {"property": "情報取得日", "date": {"on_or_after": four_days_ago}},
        "sorts": [{"property": "情報取得日", "direction": "descending"}],
        "page_size": 20,
    },
)
cases = res2.get("results", [])
print(f"件数: {len(cases)}件")
for page in cases:
    props = page["properties"]
    name = gtxt(props.get("案件名", {}))
    price = gtxt(props.get("単価（万円）", {}))
    skills = gtxt(props.get("必要スキル", {}))
    date = gtxt(props.get("情報取得日", {}))
    status = gtxt(props.get("ステータス", {}))
    print(f"  {name[:35]:<35} | {str(price):>4}万 | {date} | {status} | スキル: {skills[:40]}")
