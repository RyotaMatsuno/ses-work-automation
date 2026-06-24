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
    if t == "email":
        return p.get("email", "") or ""
    return ""


# エンジニアDB: 全プロパティ確認（タイトル型を探す）
print("=== エンジニアDB 全プロパティ ===")
eng_schema = nget(f"databases/{ENG_DB}")
title_prop = ""
for k, v in eng_schema["properties"].items():
    print(f"  '{k}': {v['type']}")
    if v["type"] == "title":
        title_prop = k
print(f"\nタイトルプロパティ: '{title_prop}'")

# 直近10件のエンジニアを表示
print("\n=== エンジニアDB 直近10件 ===")
res = npost(
    f"databases/{ENG_DB}/query", {"sorts": [{"property": "情報取得日", "direction": "descending"}], "page_size": 10}
)
for page in res.get("results", []):
    props = page["properties"]
    name = gtxt(props.get(title_prop, {})) if title_prop else ""
    initial = gtxt(props.get("イニシャル", {}))
    price = gtxt(props.get("単価（万円）", props.get("単価", {})))
    flag = gtxt(props.get("提案対象フラグ", {}))
    status = gtxt(props.get("稼働状況", {}))
    date = gtxt(props.get("情報取得日", {}))
    print(f"  {name or initial or '(名前なし)'} | 単価:{price}万 | 対象:{flag} | 状況:{status} | 取得:{date}")

print()

# 案件DBプロパティ確認
print("=== 案件DB プロパティ名 ===")
case_schema = nget(f"databases/{CASE_DB}")
for k, v in list(case_schema["properties"].items())[:25]:
    print(f"  '{k}': {v['type']}")
