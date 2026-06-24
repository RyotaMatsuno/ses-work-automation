# -*- coding: utf-8 -*-
"""PH(京成小岩)さんの情報取得 + 案件DBから単価マッチ抽出"""

import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
DB_ENG = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
DB_PROJ = "343450ff-37c0-81e4-934e-f25f90284a3c"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 1. PHさん検索 - 名前にPHを含む人員
print("=== 1. PH search in engineer DB ===")
url = f"https://api.notion.com/v1/databases/{DB_ENG}/query"
# まず全件取得して名前にPHを含むものを抽出（プロパティ名不明のため）
all_eng = []
cursor = None
while True:
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    if r.status_code != 200:
        print(f"  ERR: {r.status_code} {r.text[:200]}")
        break
    data = r.json()
    all_eng.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")

print(f"  Total engineers: {len(all_eng)}")

# Find PH
ph_records = []
for rec in all_eng:
    props = rec.get("properties", {})
    # title プロパティ探す
    for k, v in props.items():
        if "title" in v:
            arr = v.get("title", [])
            name = "".join([t.get("plain_text", "") for t in arr])
            if "PH" in name and ("京成" in name or "小岩" in name or len(ph_records) == 0):
                # PHを含む候補
                if "PH" in name:
                    ph_records.append((rec, name, k))
                    break

print(f"\n  Found {len(ph_records)} PH candidates:")
for rec, name, title_key in ph_records[:10]:
    props = rec.get("properties", {})
    addr = ""
    addr_key = None
    for k, v in props.items():
        if any(s in k for s in ["住所", "勤務地", "最寄", "エリア", "場所"]):
            if "rich_text" in v:
                addr = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
                addr_key = k
                break
            if "select" in v and v.get("select"):
                addr = v["select"].get("name", "")
                addr_key = k
                break
    status = ""
    for k, v in props.items():
        if "ステータス" in k or "状態" in k or "Status" in k:
            sel = v.get("select") or v.get("status")
            if sel:
                status = sel.get("name", "")
                break
    price = ""
    for k, v in props.items():
        if any(s in k for s in ["単価", "希望", "price", "金額"]):
            if "number" in v and v.get("number") is not None:
                price = str(v["number"])
                break
            if "rich_text" in v:
                price = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
                if price:
                    break
    print(f"    name='{name}' | status='{status}' | addr='{addr}' | price='{price}'")

# 2. scheduler status
print("\n=== 2. scheduler status (17:00 check) ===")
try:
    s = requests.get(
        "http://127.0.0.1:8765/jobs/mail_pipeline/status", headers={"X-Auth-Token": "jobz-terra-2026"}, timeout=5
    )
    print(s.json())
except Exception as e:
    print(f"ERR: {e}")
