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

results = []
payload = {"page_size": 100, "filter": {"property": "稼働状況", "select": {"equals": "稼働可能"}}}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=H, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

total = len(results)
skill_empty = 0
has_raw_no_skill = 0
has_price = 0
no_price = 0

for p in results:
    props = p["properties"]
    skills = [i["name"] for i in props.get("スキル", {}).get("multi_select", [])]
    raw = "".join(i.get("plain_text", "") for i in props.get("人員情報原文", {}).get("rich_text", []))
    price = props.get("単価（万円）", {}).get("number")

    if not skills:
        skill_empty += 1
        if len(raw) > 50:
            has_raw_no_skill += 1
    if price:
        has_price += 1
    else:
        no_price += 1

print(f"稼働可能エンジニア: {total}")
print(f"スキルあり: {total - skill_empty}")
print(f"スキル空: {skill_empty}")
print(f"  うち原文あり: {has_raw_no_skill}")
print(f"単価あり: {has_price}")
print(f"単価なし: {no_price}")
