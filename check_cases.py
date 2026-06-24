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
    if t == "multi_select":
        return ", ".join(x.get("name", "") for x in p.get("multi_select", []))
    if t == "number":
        return p.get("number")
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    return ""


# 案件DBの全プロパティ確認
print("=== 案件DB 全プロパティ ===")
schema = nget(f"databases/{CASE_DB}")
for k, v in schema["properties"].items():
    print(f"  '{k}': {v['type']}")

# フィルターなしで直近案件を取得
print("\n=== 案件DB 直近10件 ===")
res = npost(
    f"databases/{CASE_DB}/query", {"sorts": [{"timestamp": "created_time", "direction": "descending"}], "page_size": 10}
)
for page in res.get("results", []):
    props = page["properties"]
    name = gtxt(props.get("案件名", {}))
    price = gtxt(props.get("単価（万円）", {}))
    skills = gtxt(props.get("必要スキル", {}))
    date = gtxt(props.get("情報取得日", {}))
    created = page.get("created_time", "")[:10]
    status = gtxt(props.get("ステータス", {}))
    print(f"  {name[:35]:<35} | {str(price or '?'):>4}万 | 取得:{date or created} | {status}")
    if skills:
        print(f"    必須スキル: {skills[:60]}")
