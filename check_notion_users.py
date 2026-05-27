
import requests, sys, io
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

cfg = dotenv_values("config/.env")
NOTION_TOKEN = cfg["NOTION_API_KEY"]
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# ワークスペースのメンバー・招待一覧を確認
r = requests.get("https://api.notion.com/v1/users", headers=headers, timeout=10)
data = r.json()
print("=== ユーザー一覧 ===")
for u in data.get("results", []):
    print(f"name={u.get('name')} type={u.get('type')} email={u.get('person', {}).get('email', '')}")
