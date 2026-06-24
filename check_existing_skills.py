import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")

import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = env.get("NOTION_TOKEN") or env.get("NOTION_API_KEY")
db_id = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# 全件取得
results = []
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json=payload)
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

print(f"総件数: {len(results)}")

# スキルが1件以上あるレコードを確認
with_skills = [
    (
        p["id"],
        "".join([t["plain_text"] for t in p["properties"].get("名前", {}).get("title", [])]),
        [o["name"] for o in p["properties"].get("スキル", {}).get("multi_select", [])],
    )
    for p in results
    if p["properties"].get("スキル", {}).get("multi_select")
]

print(f"スキル登録済み: {len(with_skills)}件")
print(f"スキルなし: {len(results) - len(with_skills)}件")

# サンプル表示
for pid, name, skills in with_skills[:10]:
    print(f"  {name}: {skills}")
