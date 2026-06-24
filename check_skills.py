from collections import Counter

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = config.get("NOTION_API_KEY")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 全エンジニアのスキルを収集
all_skills = Counter()
engineers_with_skills = 0
engineers_total = 0
next_cursor = None

while True:
    payload = {"page_size": 100}
    if next_cursor:
        payload["start_cursor"] = next_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload)
    data = resp.json()
    for page in data.get("results", []):
        engineers_total += 1
        props = page.get("properties", {})
        skill_prop = props.get("スキル", {})
        skills = [s.get("name", "") for s in skill_prop.get("multi_select", []) if s.get("name")]
        if skills:
            engineers_with_skills += 1
            for s in skills:
                all_skills[s] += 1

    if not data.get("has_more"):
        break
    next_cursor = data.get("next_cursor")

print(f"エンジニア総数: {engineers_total}")
print(f"スキル登録あり: {engineers_with_skills}")
print(f"ユニークスキル数: {len(all_skills)}")
print("\n=== 頻出スキル TOP40 ===")
for skill, cnt in all_skills.most_common(40):
    print(f"  [{cnt:3d}] {skill!r}")
