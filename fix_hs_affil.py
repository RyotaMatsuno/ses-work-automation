import sys

sys.stdout.reconfigure(encoding="utf-8")
import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

PAGE_ID = "36c450ff-37c0-813b-8f31-d38228e3cf2e"

props = {
    "\u6240\u5c5e\u4f1a\u793e\u540d": {"rich_text": [{"type": "text", "text": {"content": "\u677e\u91ccLINE"}}]},
}

r = requests.patch(f"https://api.notion.com/v1/pages/{PAGE_ID}", headers=headers, json={"properties": props})
print(f"status: {r.status_code}")
if r.status_code == 200:
    print("OK: H.S 所属会社名 -> 松野LINE")
else:
    print(r.text[:300])
