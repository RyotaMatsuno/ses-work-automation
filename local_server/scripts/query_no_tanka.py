import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os

# Find NOTION_TOKEN
NOTION_TOKEN = None
env_candidates = ['config/.env', '.env']
for p in env_candidates:
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line.startswith('NOTION_TOKEN=') or line.startswith('NOTION_API_KEY='):
                    NOTION_TOKEN = line.split('=', 1)[1].strip('"').strip("'")
                    break
    if NOTION_TOKEN:
        break

if not NOTION_TOKEN:
    print("ERROR: NOTION_TOKEN not found in config/.env or .env")
    # Try to list config dir
    if os.path.exists('config'):
        print("config/ contents:", os.listdir('config'))
    sys.exit(1)

DB_ID = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
url = f"https://api.notion.com/v1/databases/{DB_ID}/query"
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

payload = {
    "filter": {
        "property": "\u5358\u4fa1\uff08\u4e07\u5186\uff09",
        "number": {
            "is_empty": True
        }
    },
    "page_size": 100
}

resp = requests.post(url, headers=headers, json=payload)
if resp.status_code != 200:
    print(f"ERROR {resp.status_code}: {resp.text}")
    sys.exit(1)

data = resp.json()
results = data.get("results", [])
print(f"=== \u5358\u4fa1\u672a\u8a2d\u5b9a\u30a8\u30f3\u30b8\u30cb\u30a2: {len(results)}\u540d ===\n")

for r in results:
    props = r.get("properties", {})
    name_prop = props.get("\u540d\u524d", {}).get("title", [])
    name = name_prop[0]["plain_text"] if name_prop else "\u4e0d\u660e"
    
    initial_prop = props.get("\u30a4\u30cb\u30b7\u30e3\u30eb", {}).get("rich_text", [])
    initial = initial_prop[0]["plain_text"] if initial_prop else ""
    
    exp_years = props.get("\u7d4c\u9a13\u5e74\u6570", {}).get("number", None)
    
    skills = props.get("\u30b9\u30ad\u30eb", {}).get("multi_select", [])
    skill_names = [s["name"] for s in skills]
    
    bio = props.get("\u5099\u8003\uff08LINE\u30e1\u30e2\uff09", {}).get("rich_text", [])
    bio_text = bio[0]["plain_text"][:300] if bio else ""
    
    raw_info = props.get("\u4eba\u54e1\u60c5\u5831\u539f\u6587", {}).get("rich_text", [])
    raw_text = raw_info[0]["plain_text"][:400] if raw_info else ""
    
    status = props.get("\u7a3c\u50cd\u72b6\u6cc1", {}).get("select", {})
    status_name = status.get("name", "") if status else ""
    
    flag = props.get("\u63d0\u6848\u5bfe\u8c61\u30d5\u30e9\u30b0", {}).get("checkbox", False)
    
    print(f"--- {name} ({initial}) ---")
    print(f"  \u7d4c\u9a13\u5e74\u6570: {exp_years}")
    print(f"  \u7a3c\u50cd\u72b6\u6cc1: {status_name}")
    print(f"  \u63d0\u6848\u5bfe\u8c61: {flag}")
    print(f"  \u30b9\u30ad\u30eb: {', '.join(skill_names[:10])}")
    print(f"  \u5099\u8003: {bio_text}")
    print(f"  \u539f\u6587(400\u6587\u5b57): {raw_text}")
    print(f"  page_id: {r['id']}")
    print()
