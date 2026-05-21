
# -*- coding: utf-8 -*-
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
PROJECT_DB  = '343450ff-37c0-81e4-934e-f25f90284a3c'
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'

headers = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

def query_db(db_id, filter_obj=None):
    results, payload = [], {"page_size": 100}
    if filter_obj: payload["filter"] = filter_obj
    while True:
        r = requests.post(f"https://api.notion.com/v1/databases/{db_id}/query",
                         headers=headers, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"): break
        payload["start_cursor"] = data["next_cursor"]
    return results

# 案件DB全件のステータス確認
proj_all = query_db(PROJECT_DB)
print("=== 案件DB全件 ===")
for p in proj_all:
    props = p["properties"]
    name = props.get("案件名", {}).get("title", [{}])[0].get("plain_text", "?")
    status = props.get("ステータス", {}).get("select", {})
    status_name = status.get("name", "未設定") if status else "未設定"
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    print(f"  [{status_name}] {name} / {price}万")

# 単価バグのあるエンジニア（1000以上）を特定
print("\n=== 単価バグ（円入力）のエンジニア ===")
eng_all = query_db(ENGINEER_DB)
bug_list = []
for p in eng_all:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    if price >= 1000:
        corrected = round(price / 10000)
        bug_list.append({"id": p["id"], "name": name, "raw_price": price, "corrected": corrected})
        print(f"  {name}: {price} -> 修正値: {corrected}万")

print(f"\n合計 {len(bug_list)}件の単価バグ")

# JSONで保存
with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\price_bugs.json', 'w', encoding='utf-8') as f:
    json.dump(bug_list, f, ensure_ascii=False, indent=2)
