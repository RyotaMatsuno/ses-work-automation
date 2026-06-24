import sys

import requests

sys.stdout.reconfigure(encoding="utf-8")
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
h = {
    "Authorization": f"Bearer {config['NOTION_API_KEY']}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# エンジニアDBのプロパティ確認
r1 = requests.get("https://api.notion.com/v1/databases/343450ff-37c0-819d-8769-fb0a8a4ceeb1", headers=h)
print("=== エンジニアDB ===")
for name, p in r1.json().get("properties", {}).items():
    print(f"  {name}: {p['type']}")

# 案件DBのプロパティ確認
r2 = requests.get("https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c", headers=h)
print("\n=== 案件DB ===")
for name, p in r2.json().get("properties", {}).items():
    print(f"  {name}: {p['type']}")
    if p["type"] == "select":
        opts = p.get("select", {}).get("options", [])
        for o in opts:
            print(f"    - {o['name']}")
