import os
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(__file__).parent.parent / "config" / ".env"
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


def backfill(db_id, db_name):
    pages = query_all(db_id)
    count = 0
    for p in pages:
        assignee_prop = p["properties"].get("担当者", {})
        current = assignee_prop.get("select")
        if current is not None:
            continue
        r = requests.patch(
            f"https://api.notion.com/v1/pages/{p['id']}",
            headers=HEADERS,
            json={"properties": {"担当者": {"select": {"name": "松野"}}}},
        )
        if r.status_code == 200:
            count += 1
        else:
            print(f"  ERROR {p['id']}: {r.status_code}")
    print(f"[{db_name}] バックフィル完了: {count}件")


if __name__ == "__main__":
    backfill(ENGINEER_DB, "エンジニアDB")
    backfill(PROJECT_DB, "案件DB")
