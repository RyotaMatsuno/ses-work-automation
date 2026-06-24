import sys

sys.stdout.reconfigure(encoding="utf-8")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_API_KEY") or config.get("NOTION_TOKEN", "")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 稼働状況ごとの件数
statuses = {}
total = 0
payload = {"page_size": 100}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json=payload)
    d = r.json()
    for p in d.get("results", []):
        st = p.get("properties", {}).get("稼働状況", {}).get("select", {})
        name = st.get("name", "（未設定）") if st else "（未設定）"
        statuses[name] = statuses.get(name, 0) + 1
        total += 1
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]

print(f"エンジニアDB 合計: {total}件")
for k, v in sorted(statuses.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}件")
