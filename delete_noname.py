import io
import sys

import requests
from dotenv import dotenv_values

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_KEY = cfg["NOTION_API_KEY"]
headers = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28",
}

# (no name) 4件をアーカイブ
ids = [
    "365450ff-37c0-81d0-88a0-fd6c9542c410",
    "365450ff-37c0-81c9-a7fa-c9ce174394ad",
    "365450ff-37c0-817c-a716-e9e152d62f2c",
    "365450ff-37c0-8103-bcd2-ddef336ea570",
]
for pid in ids:
    r = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=headers, json={"archived": True})
    print("✅" if r.status_code == 200 else "❌", pid, r.status_code)
