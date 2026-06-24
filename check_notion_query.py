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

# notion_client.py の get_new_cases ペイロードを確認
print("=== notion_client.py get_new_cases payload確認 ===")
nc = base / "matching_v3" / "notion_client.py"
nc_text = nc.read_text(encoding="utf-8", errors="replace")
in_func = False
for i, l in enumerate(nc_text.splitlines(), 1):
    if "def get_new_cases" in l:
        in_func = True
    if in_func:
        print(f"  {i}: {l}")
        if in_func and i > 10 and l.strip().startswith("def ") and "get_new_cases" not in l:
            break

# 実際にシンプルなクエリを投げてみる（フィルターなし）
print("\n=== 案件DB シンプルクエリテスト ===")
r = requests.post(
    f"https://api.notion.com/v1/databases/{CASE_DB}/query", headers=HEADERS, json={"page_size": 1}, timeout=15
)
print(f"  status: {r.status_code}")
if r.status_code != 200:
    print(f"  error: {r.text[:200]}")
else:
    data = r.json()
    print(f"  OK: {len(data.get('results', []))}件取得")
