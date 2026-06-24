# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
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
    if t == "multi_select":
        return [x.get("name", "") for x in p.get("multi_select", [])]
    if t == "number":
        return p.get("number")
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    if t == "select":
        return (p.get("select") or {}).get("name", "")
    return ""


# PHさんの詳細
print("=== P.H の詳細 ===")
cursor = None
while True:
    res = npost(f"databases/{ENG_DB}/query", {"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
    for page in res.get("results", []):
        props = page["properties"]
        name = gtxt(props.get("名前", {}))
        if "P.H" in name or name == "PH":
            print(f"名前: {name}")
            print(f"単価: {gtxt(props.get('単価（万円）', {}))}万")
            print(f"スキル: {gtxt(props.get('スキル', {}))}")
            print(f"情報取得日: {gtxt(props.get('情報取得日', {}))}")
            print(f"提案対象: {props.get('提案対象フラグ', {}).get('checkbox')}")
            print(f"担当者: {gtxt(props.get('担当者', {}))}")
            print(f"居住地: {gtxt(props.get('居住地', {}))}")
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

# 今日の案件のうち必須スキルにPMOを含むもの
print("\n=== PMO関連案件（今日） ===")
res2 = npost(
    f"databases/{CASE_DB}/query", {"sorts": [{"timestamp": "created_time", "direction": "descending"}], "page_size": 50}
)
pmo_cases = []
for page in res2.get("results", []):
    props = page["properties"]
    skills = gtxt(props.get("必要スキル", {}))
    name = gtxt(props.get("案件名", {}))
    price = gtxt(props.get("単価（万円）", {}))
    date_val = gtxt(props.get("情報取得日", {}))
    created = page.get("created_time", "")[:10]
    if "PMO" in str(skills) or "PMO" in name:
        print(f"  {name[:40]} | 単価:{price}万 | 必須:{skills} | {date_val or created}")
        pmo_cases.append(page)

if not pmo_cases:
    print("  PMO案件なし")

# 全案件の必須スキル一覧（上位20件）
print("\n=== 今日の案件 必須スキル一覧 ===")
for page in res2.get("results", [])[:20]:
    props = page["properties"]
    name = gtxt(props.get("案件名", {}))
    skills = gtxt(props.get("必要スキル", {}))
    price = gtxt(props.get("単価（万円）", {}))
    print(f"  {name[:35]:<35} | 単価:{str(price or '?'):>4}万 | 必須:{skills}")
