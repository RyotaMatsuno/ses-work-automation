# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def notion_post(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


# PHさんを名前で検索
print("=== PHさんのエンジニア情報 ===")
res = notion_post(
    f"databases/{ENG_DB}/query", {"filter": {"property": "名前", "title": {"contains": "PH"}}, "page_size": 5}
)
for page in res.get("results", []):
    props = page["properties"]

    def gtxt(p):
        t = p.get("type", "")
        if t == "title":
            return "".join(x["plain_text"] for x in p.get("title", []))
        if t == "rich_text":
            return "".join(x["plain_text"] for x in p.get("rich_text", []))
        if t == "select":
            return (p.get("select") or {}).get("name", "")
        if t == "number":
            return str(p.get("number", ""))
        if t == "checkbox":
            return str(p.get("checkbox", ""))
        return ""

    print(f"名前: {gtxt(props.get('名前', {}))}")
    print(f"単価: {gtxt(props.get('単価（万円）', {}))}")
    print(f"スキル: {gtxt(props.get('スキル', {}))[:200]}")
    print(f"提案対象: {gtxt(props.get('提案対象フラグ', {}))}")
    print(f"稼働状況: {gtxt(props.get('稼働状況', {}))}")
    print()

# 本日の有効案件数確認
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
today = datetime.now(JST).strftime("%Y-%m-%d")
print(f"=== 本日({today})の有効案件 ===")
res2 = notion_post(
    f"databases/{CASE_DB}/query",
    {
        "filter": {
            "and": [
                {"property": "情報取得日", "date": {"on_or_after": today}},
            ]
        },
        "sorts": [{"property": "情報取得日", "direction": "descending"}],
        "page_size": 10,
    },
)
cases = res2.get("results", [])
print(f"件数: {len(cases)}件")
for page in cases[:5]:
    props = page["properties"]

    def gtxt(p):
        t = p.get("type", "")
        if t == "title":
            return "".join(x["plain_text"] for x in p.get("title", []))
        if t == "rich_text":
            return "".join(x["plain_text"] for x in p.get("rich_text", []))
        if t == "number":
            return str(p.get("number", ""))
        if t == "select":
            return (p.get("select") or {}).get("name", "")
        return ""

    name = gtxt(props.get("案件名", {})) or gtxt(props.get("Name", {}))
    price_min = gtxt(props.get("単価下限", {}))
    price_max = gtxt(props.get("単価上限", {}))
    date = gtxt(props.get("情報取得日", {}))
    print(f"  {name[:40]} | {price_min}〜{price_max}万 | {date}")
