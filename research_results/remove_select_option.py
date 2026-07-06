import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get current schema to see ステータス options
resp = requests.get(f"https://api.notion.com/v1/databases/{ANKEN_DB}", headers=headers, timeout=15)
db = resp.json()
status_prop = db["properties"].get("ステータス", {})
current_options = status_prop.get("select", {}).get("options", [])
print("Current options:")
for o in current_options:
    print(f"  {o['name']} ({o.get('color','')})")

# Remove 選考中, keep the rest
new_options = [o for o in current_options if o["name"] != "選考中"]
print(f"\nAfter removal: {[o['name'] for o in new_options]}")

# Update DB
resp2 = requests.patch(
    f"https://api.notion.com/v1/databases/{ANKEN_DB}",
    headers=headers,
    json={
        "properties": {
            "ステータス": {
                "select": {
                    "options": new_options
                }
            }
        }
    },
    timeout=15
)
if resp2.status_code == 200:
    print("OK - 選考中 removed from select options")
else:
    print(f"Error: {resp2.status_code} {resp2.text[:200]}")
