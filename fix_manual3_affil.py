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

targets = [
    ("360450ff-37c0-811d-9a67-eef211dc351f", "U.H"),
    ("360450ff-37c0-8137-9dc1-e11b8e6a022c", "R.H"),
    ("360450ff-37c0-81cc-bf28-cc3c8969fd0a", "OA"),
]

for pid, name in targets:
    r = requests.patch(
        f"https://api.notion.com/v1/pages/{pid}",
        headers=headers,
        json={
            "properties": {
                "\u6240\u5c5e\u4f1a\u793e\u540d": {
                    "rich_text": [{"type": "text", "text": {"content": "\u677e\u91ceLINE"}}]
                }
            }
        },
    )
    status = "OK" if r.status_code == 200 else f"ERROR {r.status_code}"
    print(f"{name}: {status}")
