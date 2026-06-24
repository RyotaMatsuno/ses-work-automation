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


for status in ["選考中", "稼働中"]:
    print(f"\n=== {status} サンプル5件 ===")
    res = npost(
        f"databases/{CASE_DB}/query",
        {
            "filter": {"property": "ステータス", "select": {"equals": status}},
            "sorts": [{"timestamp": "created_time", "direction": "descending"}],
            "page_size": 5,
        },
    )
    for page in res.get("results", []):
        props = page["properties"]
        name = gtxt(props.get("案件名", {}))
        price = gtxt(props.get("単価（万円）", {}))
        created = page.get("created_time", "")[:10]
        info_date = gtxt(props.get("情報取得日", {}))
        assignee = gtxt(props.get("担当者", {}))
        print(f"  {name[:40]:<40} | {str(price) if price else '?'}万 | {info_date or created} | {assignee}")
