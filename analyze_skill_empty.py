# -*- coding: utf-8 -*-
"""
案件DBのスキル要件空レコードを分析。
raw_body（案件詳細）テキストがあるのにスキルが空のケースがどれだけあるか確認。
"""

import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, "config", ".env")
config = dotenv_values(env_path)
for k, v in config.items():
    if k not in os.environ and v:
        os.environ[k] = v

API_KEY = os.environ["NOTION_API_KEY"]
PROJECT_DB_ID = "343450ff-37c0-81e4-934e-f25f90284a3c"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}


def query_all(db_id, filter_obj=None):
    results = []
    payload = {"page_size": 100}
    if filter_obj:
        payload["filter"] = filter_obj
    while True:
        r = requests.post(
            f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload, timeout=30
        )
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


pages = query_all(PROJECT_DB_ID, {"property": "ステータス", "select": {"equals": "募集中"}})
print(f"募集中案件: {len(pages)}")

skill_empty = 0
has_body_no_skill = 0
no_body_no_skill = 0
has_skill = 0
sample_bodies = []

for p in pages:
    props = p["properties"]
    skills = [i["name"] for i in props.get("必要スキル", {}).get("multi_select", [])]

    # raw body from 案件詳細 or 備考
    body_parts = []
    for key in ["案件詳細", "備考（LINEメモ）"]:
        rt = props.get(key, {}).get("rich_text", [])
        body_parts.append("".join(i.get("plain_text", "") for i in rt))
    body = " ".join(body_parts).strip()

    if skills:
        has_skill += 1
    else:
        skill_empty += 1
        if len(body) > 50:
            has_body_no_skill += 1
            if len(sample_bodies) < 3:
                name_parts = props.get("案件名", {}).get("title", [])
                name = name_parts[0]["plain_text"] if name_parts else "?"
                sample_bodies.append({"name": name, "body_len": len(body), "body_head": body[:300]})
        else:
            no_body_no_skill += 1

print(f"スキルあり: {has_skill}")
print(f"スキル空: {skill_empty}")
print(f"  うち案件詳細あり(50文字超): {has_body_no_skill} ← これが改善対象")
print(f"  うち案件詳細もなし: {no_body_no_skill}")

for i, s in enumerate(sample_bodies):
    print(f"\n--- Sample {i + 1}: {s['name']} (body:{s['body_len']}文字) ---")
    print(s["body_head"])
