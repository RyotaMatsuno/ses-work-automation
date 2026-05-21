
# -*- coding: utf-8 -*-
import requests, os, json, sys
sys.stdout.reconfigure(encoding='utf-8')
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

eng_all = query_db(ENGINEER_DB)
eng_available = query_db(ENGINEER_DB, {"property": "\u7a3c\u50cd\u72b6\u6cc1", "select": {"equals": "\u7a3c\u50cd\u53ef\u80fd"}})
proj_all = query_db(PROJECT_DB)
proj_active = query_db(PROJECT_DB, {"property": "\u30b9\u30c6\u30fc\u30bf\u30b9", "select": {"equals": "\u7a3c\u50cd\u4e2d"}})

# JSONで出力（文字化け回避）
output = {
    "engineer_total": len(eng_all),
    "engineer_available": len(eng_available),
    "project_total": len(proj_all),
    "project_active": len(proj_active),
    "engineers": [],
    "projects": []
}

for p in eng_available:
    props = p["properties"]
    name = props.get("\u540d\u524d", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("\u5358\u4fa1\uff08\u4e07\u5186\uff09", {}).get("number", 0) or 0
    skills = [o["name"] for o in props.get("\u30b9\u30ad\u30eb", {}).get("multi_select", [])]
    status = props.get("\u7a3c\u50cd\u72b6\u6cc1", {}).get("select", {})
    status_name = status.get("name", "") if status else ""
    note_items = props.get("\u5099\u8003\uff08LINE\u30e1\u30e2\uff09", {}).get("rich_text", [])
    note = note_items[0].get("plain_text", "")[:80] if note_items else ""
    output["engineers"].append({"name": name, "price": price, "skills": skills, "status": status_name, "note": note})

for p in proj_active:
    props = p["properties"]
    name = props.get("\u6848\u4ef6\u540d", {}).get("title", [{}])[0].get("plain_text", "?")
    price = props.get("\u5358\u4fa1\uff08\u4e07\u5186\uff09", {}).get("number", 0) or 0
    req = [o["name"] for o in props.get("\u5fc5\u9808\u30b9\u30ad\u30eb", {}).get("multi_select", [])]
    opt = [o["name"] for o in props.get("\u5c1a\u53ef\u30b9\u30ad\u30eb", {}).get("multi_select", [])]
    output["projects"].append({"name": name, "price": price, "required": req, "optional": opt})

with open(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\notion_status.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("DONE")
print(f"engineer_total={output['engineer_total']} available={output['engineer_available']}")
print(f"project_total={output['project_total']} active={output['project_active']}")
