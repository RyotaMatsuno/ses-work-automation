import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
headers = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

res = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5, "filter": {"property": "ステータス", "select": {"equals": "募集中"}}},
)
pages = res.json().get("results", [])
print(f"募集中案件: {len(pages)}件")
for p in pages:
    props = p["properties"]
    name = props.get("案件名", {}).get("title", [{}])[0].get("plain_text", "")
    price = props.get("単価（万円）", {}).get("number")
    print(f"  {name}: {price}")
