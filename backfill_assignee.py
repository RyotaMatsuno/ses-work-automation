"""
既存Notionレコードのバックフィル
備考（LINEメモ）に "[LINE auto-register: okamoto]" が含まれるレコードの
担当者カラムを「岡本」にセット。それ以外は「松野」にセット。
"""

import os

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

API_KEY = os.environ.get("NOTION_API_KEY", "")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}


def query_all(db_id):
    results, payload = [], {"page_size": 100}
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload)
        d = r.json()
        results.extend(d.get("results", []))
        if not d.get("has_more"):
            break
        payload["start_cursor"] = d["next_cursor"]
    return results


def get_note(props, key):
    items = props.get(key, {}).get("rich_text", [])
    return items[0].get("plain_text", "") if items else ""


def get_assignee(props):
    s = props.get("担当者", {}).get("select")
    return s["name"] if s else None


def set_assignee(page_id, name):
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{page_id}",
        headers=HEADERS,
        json={"properties": {"担当者": {"select": {"name": name}}}},
    )
    return r.status_code


# エンジニアDB
pages = query_all(ENGINEER_DB)
eng_ok = eng_ng = 0
for p in pages:
    props = p["properties"]
    if get_assignee(props):  # 既にセット済みはスキップ
        continue
    note = get_note(props, "備考（LINEメモ）")
    name = "岡本" if "auto-register: okamoto" in note.lower() else "松野"
    sc = set_assignee(p["id"], name)
    if sc == 200:
        eng_ok += 1
    else:
        eng_ng += 1

print(f"エンジニアDB: {eng_ok}件更新, {eng_ng}件失敗")

# 案件DB
pages = query_all(PROJECT_DB)
prj_ok = prj_ng = 0
for p in pages:
    props = p["properties"]
    if get_assignee(props):
        continue
    note = get_note(props, "案件詳細")
    name = "岡本" if "auto-register: okamoto" in note.lower() else "松野"
    sc = set_assignee(p["id"], name)
    if sc == 200:
        prj_ok += 1
    else:
        prj_ng += 1

print(f"案件DB: {prj_ok}件更新, {prj_ng}件失敗")
print("バックフィル完了")
