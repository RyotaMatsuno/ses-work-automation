import sys
from pathlib import Path

import requests
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

base = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work")
config = dotenv_values(base / "config" / ".env")
NOTION_KEY = config["NOTION_API_KEY"]
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# get_active_engineers の内容確認
print("=== get_active_engineers payload ===")
nc_text = (base / "matching_v3" / "notion_client.py").read_text(encoding="utf-8", errors="replace")
in_func = False
for i, l in enumerate(nc_text.splitlines(), 1):
    if "def get_active_engineers" in l:
        in_func = True
    if in_func:
        print(f"  {i}: {l}")
        if in_func and i > 47 and l.strip().startswith("def ") and "get_active_engineers" not in l:
            break

# エンジニアDBの実際のプロパティ確認
print("\n=== エンジニアDB プロパティ（checkbox/select系） ===")
r = requests.get(f"https://api.notion.com/v1/databases/{ENG_DB}", headers=HEADERS, timeout=15)
props = r.json().get("properties", {})
for name, prop in props.items():
    if prop.get("type") in ["checkbox", "select", "date", "created_time"]:
        print(f"  '{name}': type={prop['type']}")
