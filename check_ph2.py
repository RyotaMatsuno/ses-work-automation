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


def nget(path):
    req = urllib.request.Request(f"https://api.notion.com/v1/{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


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
        return str(p.get("number") or "")
    if t == "checkbox":
        return str(p.get("checkbox", ""))
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    return ""


# エンジニアDB: プロパティ名確認
print("=== エンジニアDB プロパティ名 ===")
eng_schema = nget(f"databases/{ENG_DB}")
for k, v in list(eng_schema["properties"].items())[:20]:
    print(f"  '{k}': {v['type']}")

print()

# PH氏をタイトル検索（全件から絞り込み）
print("=== PH氏を検索 ===")
res = npost(f"databases/{ENG_DB}/query", {"page_size": 50})
for page in res.get("results", []):
    props = page["properties"]
    # タイトルプロパティを動的に探す
    name = ""
    for k, v in props.items():
        if v.get("type") == "title":
            name = gtxt(v)
            break
    if "PH" in name or "ph" in name.lower():
        print(f"名前: {name}")
        for k, v in props.items():
            val = gtxt(v)
            if val:
                print(f"  {k}: {val[:80]}")
        print()
