import os
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
for k, v in config.items():
    if k not in os.environ:
        os.environ[k] = v

NOTION_KEY = os.environ["NOTION_API_KEY"]
ENGINEER_DB = os.environ["NOTION_ENGINEER_DB_ID"]
PROJECT_DB = os.environ["NOTION_PROJECT_DB_ID"]
HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}


def query_all(db_id):
    results, payload = [], {"page_size": 100}
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=HEADERS, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data["next_cursor"]
    return results


def check_and_fill(db_id, db_name, name_prop_key):
    pages = query_all(db_id)
    unset = []
    for p in pages:
        props = p["properties"]
        current = props.get("担当者", {}).get("select")
        if current is None:
            name_prop = props.get(name_prop_key, {})
            # title型
            title_list = name_prop.get("title", [])
            name = title_list[0]["plain_text"] if title_list else "未記載"
            unset.append((p["id"], name))
    print(f"[{db_name}] 担当者未設定: {len(unset)}件 / 全{len(pages)}件")
    for pid, name in unset[:5]:
        print(f"  - {name} ({pid[:8]}...)")

    # バックフィル実行
    filled = 0
    for pid, name in unset:
        r = requests.patch(
            f"https://api.notion.com/v1/pages/{pid}",
            headers=HEADERS,
            json={"properties": {"担当者": {"select": {"name": "松野"}}}},
        )
        if r.status_code == 200:
            filled += 1
            print(f"  [OK] {name} → 松野")
        else:
            print(f"  [NG] {name}: {r.status_code} {r.text[:100]}")
    print(f"[{db_name}] バックフィル完了: {filled}件")


check_and_fill(ENGINEER_DB, "エンジニアDB", "名前")
print()
check_and_fill(PROJECT_DB, "案件DB", "案件名")
