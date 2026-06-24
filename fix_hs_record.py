import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# H.SのPage IDを取得
payload = {"page_size": 100}
pages = []
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload)
    d = r.json()
    pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]

hs_page = None
for p in pages:
    props = p.get("properties", {})
    name_items = props.get("名前", {}).get("title", [])
    name = "".join(t.get("plain_text", "") for t in name_items)
    if name == "H.S":
        hs_page = p
        print(f"H.S Page ID: {p['id']}")
        print(f"現在のイニシャル: [{props.get('イニシャル', {}).get('rich_text', [])}]")
        print(f"現在の最寄り駅: [{props.get('最寄り駅', {}).get('rich_text', [])}]")
        break

if not hs_page:
    print("H.Sが見つかりません")
    sys.exit(1)

# Fix1: イニシャル・最寄り駅を更新
page_id = hs_page["id"]
update_payload = {
    "properties": {
        "イニシャル": {"rich_text": [{"text": {"content": "HS"}}]},
        "最寄り駅": {"rich_text": [{"text": {"content": "北小金"}}]},
        "稼働可能日": {"date": {"start": "2026-07-01"}},
    }
}

r2 = requests.patch(f"https://api.notion.com/v1/pages/{page_id}", headers=headers, json=update_payload)
print(f"\nNotion PATCH status: {r2.status_code}")
if r2.status_code == 200:
    print("✅ H.Sのイニシャル(HS)・最寄り駅(北小金)・稼働可能日(2026-07-01)を更新しました")
else:
    print(f"❌ 更新失敗: {r2.text[:300]}")
