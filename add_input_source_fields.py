import os
import sys

import requests
from dotenv import dotenv_values


sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = os.path.dirname(__file__)
ENV_PATH = os.path.join(BASE_DIR, "config", ".env")
config = dotenv_values(ENV_PATH)

NOTION_API_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB_ID = config.get("NOTION_ENGINEER_DB_ID", "")
PROJECT_DB_ID = config.get("NOTION_PROJECT_DB_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

INPUT_SOURCE_OPTIONS = [
    {"name": "松野メール", "color": "blue"},
    {"name": "岡本メール", "color": "green"},
    {"name": "共通メール", "color": "gray"},
    {"name": "松野LINE", "color": "yellow"},
    {"name": "岡本LINE", "color": "orange"},
]


def get_database_properties(db_id):
    res = requests.get(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=HEADERS,
        timeout=30,
    )
    if res.status_code != 200:
        print(f"[NG] DB取得失敗 db={db_id}: {res.status_code} {res.text[:300]}")
        return None
    return res.json().get("properties", {})


def add_fields(db_id, label):
    if not db_id:
        print(f"[SKIP] {label}: DB ID未設定")
        return False

    existing = get_database_properties(db_id)
    if existing is None:
        return False

    properties = {}
    if "入力元" not in existing:
        properties["入力元"] = {"select": {"options": INPUT_SOURCE_OPTIONS}}
    if "所属会社名" not in existing:
        properties["所属会社名"] = {"rich_text": {}}

    if not properties:
        print(f"[OK] {label}: 追加不要（既存）")
        return True

    res = requests.patch(
        f"https://api.notion.com/v1/databases/{db_id}",
        headers=HEADERS,
        json={"properties": properties},
        timeout=30,
    )
    if res.status_code == 200:
        print(f"[OK] {label}: 追加 {', '.join(properties.keys())}")
        return True

    print(f"[NG] {label}: {res.status_code} {res.text[:300]}")
    return False


def main():
    if not NOTION_API_KEY:
        print("[NG] NOTION_API_KEY未設定")
        return 1

    ok_engineer = add_fields(ENGINEER_DB_ID, "エンジニアDB")
    ok_project = add_fields(PROJECT_DB_ID, "案件DB")
    return 0 if ok_engineer and ok_project else 1


if __name__ == "__main__":
    raise SystemExit(main())
