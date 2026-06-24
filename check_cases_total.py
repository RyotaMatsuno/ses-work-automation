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


# 案件DB全件カウント
print("=== 案件DB 全件カウント ===")
total = 0
today_count = 0
today = datetime.now(JST).strftime("%Y-%m-%d")
pmo_count = 0
pmo_cases = []
cursor = None

while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{CASE_DB}/query", payload)
    for page in res.get("results", []):
        total += 1
        props = page["properties"]
        date_val = gtxt(props.get("情報取得日", {}))
        created = page.get("created_time", "")[:10]
        effective_date = date_val or created
        name = gtxt(props.get("案件名", {}))
        skills = gtxt(props.get("必要スキル", {}))
        price = gtxt(props.get("単価（万円）", {}))

        if effective_date == today:
            today_count += 1

        # PMO関連（案件名・必須スキル・案件詳細）
        detail = gtxt(props.get("案件詳細", {}))
        raw = gtxt(props.get("案件情報原文", {}))
        if "PMO" in name or "PMO" in str(skills) or "PMO" in detail[:100] or "PMO" in raw[:200]:
            pmo_count += 1
            pmo_cases.append(
                {
                    "name": name,
                    "price": price,
                    "skills": skills,
                    "date": effective_date,
                }
            )

    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

print(f"総案件数: {total}件")
print(f"本日登録: {today_count}件")
print(f"PMO関連: {pmo_count}件")
if pmo_cases:
    print("\nPMO案件一覧:")
    for c in pmo_cases[:10]:
        print(f"  {c['name'][:40]} | 単価:{c['price']}万 | 必須:{c['skills']} | {c['date']}")
