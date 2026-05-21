
import requests, os, json
from dotenv import load_dotenv
load_dotenv(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')

NOTION_API_KEY = os.environ.get('NOTION_API_KEY', '')
ENGINEER_DB = '343450ff-37c0-819d-8769-fb0a8a4ceeb1'
PROJECT_DB  = '343450ff-37c0-81e4-934e-f25f90284a3c'

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

# エンジニアDB全件
eng_all = query_db(ENGINEER_DB)
eng_available = query_db(ENGINEER_DB, {"property": "稼働状況", "select": {"equals": "稼働可能"}})

# 案件DB全件
proj_all = query_db(PROJECT_DB)
proj_active = query_db(PROJECT_DB, {"property": "ステータス", "select": {"equals": "稼働中"}})

print(f"=== エンジニアDB ===")
print(f"全件: {len(eng_all)} / 稼働可能: {len(eng_available)}")
for p in eng_available[:20]:
    props = p["properties"]
    name = props.get("名前", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    skills = [o["name"] for o in props.get("スキル", {}).get("multi_select", [])]
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note = note_items[0].get("plain_text", "")[:50] if note_items else ""
    print(f"  {name} / {price}万 / {','.join(skills[:5])} / {note[:40]}")

print(f"\n=== 案件DB ===")
print(f"全件: {len(proj_all)} / 稼働中: {len(proj_active)}")
for p in proj_active[:20]:
    props = p["properties"]
    name = props.get("案件名", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("単価（万円）", {}).get("number", 0) or 0
    req = [o["name"] for o in props.get("必須スキル", {}).get("multi_select", [])]
    print(f"  {name} / {price}万 / 必須:{','.join(req[:5])}")
