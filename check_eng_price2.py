import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(BASE_DIR, "config", ".env"))
for k, v in config.items():
    if k not in os.environ and v:
        os.environ[k] = v

API_KEY = os.environ["NOTION_API_KEY"]
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
H = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

payload = {
    "page_size": 10,
    "filter": {
        "and": [
            {"property": "稼働状況", "select": {"equals": "稼働可能"}},
        ]
    },
}
r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=H, json=payload, timeout=30)
r.raise_for_status()

for p in r.json()["results"]:
    props = p["properties"]
    price = props.get("単価（万円）", {}).get("number")
    if price:
        continue
    body = "".join(i.get("plain_text", "") for i in props.get("備考（LINEメモ）", {}).get("rich_text", []))
    name_parts = props.get("名前", {}).get("title", [])
    name = name_parts[0]["plain_text"] if name_parts else "?"
    print(f"--- {name} ---")
    print(body[:300])
    print()
