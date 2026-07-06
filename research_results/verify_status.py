import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
headers = {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# Count by status
for st in ["募集中", "選考中", "終了", "営業終了"]:
    body = {"filter": {"property": "ステータス", "select": {"equals": st}}, "page_size": 1}
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=15)
    data = resp.json()
    # Notion doesn't return total count directly, need to paginate for exact count
    # But we can check has_more
    print(f"{st}: {len(data.get('results',[]))}+ (has_more={data.get('has_more')})")

# Get exact count for 選考中 (should be 0)
body = {"filter": {"property": "ステータス", "select": {"equals": "選考中"}}, "page_size": 100}
resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=15)
data = resp.json()
print(f"\n選考中 残り: {len(data.get('results',[]))} 件")
