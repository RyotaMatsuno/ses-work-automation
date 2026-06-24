import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
config = dotenv_values(base / "config" / ".env")
NOTION_KEY = config["NOTION_API_KEY"]
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 案件DBの実際のプロパティ名を確認
r = requests.get(f"https://api.notion.com/v1/databases/{CASE_DB}", headers=HEADERS, timeout=15)
props = r.json().get("properties", {})
# 日付系プロパティを列挙
print("=== 案件DB プロパティ一覧（日付・作成日時系） ===")
for name, prop in props.items():
    if prop.get("type") in ["date", "created_time", "last_edited_time"]:
        print(f"  '{name}': type={prop['type']}")

# notion_client.py の _business_days_ago も確認
print("\n=== _business_days_ago 関数 ===")
nc_text = (base / "matching_v3" / "notion_client.py").read_text(encoding="utf-8", errors="replace")
in_func = False
for i, l in enumerate(nc_text.splitlines(), 1):
    if "_business_days_ago" in l and "def " in l:
        in_func = True
    if in_func:
        print(f"  {i}: {l}")
        if in_func and i > 10 and l.strip().startswith("def ") and "_business_days_ago" not in l:
            break

# 実際の値を確認
print("\n=== _business_days_ago(4) の返り値 ===")
sys.path.insert(0, str(base / "matching_v3"))
sys.path.insert(0, str(base))
try:
    from notion_client import _business_days_ago

    result = _business_days_ago(4)
    print(f"  result: {result} (type={type(result).__name__})")
    print(f"  isoformat: {result.isoformat()}")
except Exception as e:
    print(f"  error: {e}")

# フィルター付きクエリをテスト
print("\n=== 登録日時フィルター付きクエリテスト ===")
from datetime import date, timedelta

since = (date.today() - timedelta(days=7)).isoformat()
payload = {"filter": {"and": [{"property": "登録日時", "date": {"on_or_after": since}}]}}
r2 = requests.post(f"https://api.notion.com/v1/databases/{CASE_DB}/query", headers=HEADERS, json=payload, timeout=15)
print(f"  status: {r2.status_code}")
if r2.status_code != 200:
    print(f"  error: {r2.text[:300]}")
else:
    print(f"  OK: {len(r2.json().get('results', []))}件")
