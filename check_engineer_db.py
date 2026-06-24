"""
エンジニアDB の重複・ゴミデータ調査
- 「注力人材」タイトルのデータが何件あるか
- 今日登録されたデータ（正常分）は何件か
"""

from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 全件取得して集計
all_pages = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=HEADERS, json=payload)
    data = r.json()
    all_pages.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]

print(f"エンジニアDB 総ページ数: {len(all_pages)}")

# タイトル別集計
from collections import Counter

names = []
no_skill = 0
today_data = []
legacy_data = []

for p in all_pages:
    title_list = p["properties"].get("名前", {}).get("title", [])
    name = title_list[0]["plain_text"] if title_list else "(no title)"
    created = p["created_time"][:10]
    skills = [o["name"] for o in p["properties"].get("スキル", {}).get("multi_select", [])]

    names.append(name)
    if not skills:
        no_skill += 1
    if created >= "2026-05-09":
        today_data.append({"name": name, "skills": skills, "created": created, "id": p["id"]})
    if created <= "2026-04-17":
        legacy_data.append(name)

name_counts = Counter(names)
print("\n重複名上位10件:")
for name, cnt in name_counts.most_common(10):
    print(f"  {cnt}件: 「{name}」")

print(f"\nスキルなしページ数: {no_skill}")
print(f"2026-05-09以降の登録: {len(today_data)}件")
for d in today_data:
    print(f"  [{d['created']}] {d['name']} / スキル:{d['skills']}")

print(f"\n2026-04-17以前（旧バージョン由来）: {len(legacy_data)}件")
legacy_counts = Counter(legacy_data)
for name, cnt in legacy_counts.most_common(5):
    print(f"  {cnt}件: 「{name}」")
