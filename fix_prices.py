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

# 案件DB・エンジニアDB両方チェック
DBS = {
    "案件DB": "343450ff-37c0-81e4-934e-f25f90284a3c",
    "エンジニアDB": "343450ff-37c0-819d-8769-fb0a8a4ceeb1",
}

for db_name, db_id in DBS.items():
    res = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query", headers=headers, json={"page_size": 100})
    pages = res.json().get("results", [])
    fixed = 0
    for p in pages:
        props = p["properties"]
        price = props.get("単価（万円）", {}).get("number")
        if price and price >= 1000:
            price_man = round(price / 10000, 1)
            r = requests.patch(
                f"https://api.notion.com/v1/pages/{p['id']}",
                headers=headers,
                json={"properties": {"単価（万円）": {"number": price_man}}},
            )
            name_prop = props.get("案件名") or props.get("名前") or {}
            name = (name_prop.get("title") or [{}])[0].get("plain_text", "?")
            print(f"  [{db_name}] {name}: {price}円 → {price_man}万円 (HTTP {r.status_code})")
            fixed += 1
    print(f"{db_name}: {fixed}件修正")
