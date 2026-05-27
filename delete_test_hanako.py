
import os, sys, requests

base = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work"
from dotenv import dotenv_values
env = dotenv_values(os.path.join(base, "config", ".env"))
token = env["NOTION_API_KEY"]
db_id = env.get("NOTION_ENGINEER_DB_ID", "343450ff-37c0-819d-8769-fb0a8a4ceeb1")

headers = {
    "Authorization": f"Bearer {token}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# テスト花子を検索して削除
res = requests.post(
    f"https://api.notion.com/v1/databases/{db_id}/query",
    headers=headers,
    json={"filter": {"property": "名前", "title": {"contains": "テスト花子"}}}
)
pages = res.json().get("results", [])
print(f"Found: {len(pages)}件")
for p in pages:
    pid = p["id"]
    r = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=headers, json={"archived": True})
    print(f"Deleted: {pid[:8]} -> {r.status_code}")
