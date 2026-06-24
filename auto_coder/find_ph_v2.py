# -*- coding: utf-8 -*-
"""エンジニアDB構造確認 + 京成小岩で住所検索"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
DB_ENG = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 1. DBスキーマ取得
print("=== 1. DB schema ===")
r = requests.get(f"https://api.notion.com/v1/databases/{DB_ENG}", headers=HEADERS, timeout=30)
schema = r.json()
print(f"  Title: {[t.get('plain_text') for t in schema.get('title', [])]}")
print("  Properties:")
for name, prop in schema.get("properties", {}).items():
    print(f"    {name}: {prop.get('type')}")

# 2. 全件取得
print("\n=== 2. fetch all engineers ===")
url = f"https://api.notion.com/v1/databases/{DB_ENG}/query"
all_eng = []
cursor = None
while True:
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    data = r.json()
    all_eng.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  Total: {len(all_eng)}")

# 3. 京成小岩で全プロパティから検索
print("\n=== 3. search '京成小岩' or '小岩' in any property ===")
matched = []
for rec in all_eng:
    props = rec.get("properties", {})
    all_text = ""
    for k, v in props.items():
        t = v.get("type")
        if t == "title":
            all_text += "".join([x.get("plain_text", "") for x in v.get("title", [])]) + " | "
        elif t == "rich_text":
            all_text += "".join([x.get("plain_text", "") for x in v.get("rich_text", [])]) + " | "
        elif t == "select" and v.get("select"):
            all_text += v["select"].get("name", "") + " | "
        elif t == "multi_select":
            all_text += ",".join([x.get("name", "") for x in v.get("multi_select", [])]) + " | "
    if "京成小岩" in all_text or "小岩" in all_text:
        matched.append((rec, all_text))

print(f"  Matched: {len(matched)} records")
for rec, txt in matched[:5]:
    print(f"\n  --- page_id={rec['id'][:36]} ---")
    print(f"  text: {txt[:500]}")

# 4. PH イニシャル検索（プロパティ問わず）
print("\n=== 4. PH initial search (broader) ===")
ph_matched = []
for rec in all_eng:
    props = rec.get("properties", {})
    all_text = ""
    for k, v in props.items():
        t = v.get("type")
        if t == "title":
            all_text += "".join([x.get("plain_text", "") for x in v.get("title", [])]) + " | "
        elif t == "rich_text":
            all_text += "".join([x.get("plain_text", "") for x in v.get("rich_text", [])]) + " | "
    # word boundary: スペース後にPH or 文頭PH or イニシャル形式
    import re

    if re.search(r"\bPH\b|^PH|【PH", all_text):
        ph_matched.append((rec, all_text))
print(f"  Matched PH: {len(ph_matched)}")
for rec, txt in ph_matched[:5]:
    print(f"\n  --- page_id={rec['id'][:36]} ---")
    print(f"  text: {txt[:400]}")
