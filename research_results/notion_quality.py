import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get 募集中 cases with pagination
all_pages = []
has_more = True
start_cursor = None

while has_more:
    body = {
        "filter": {
            "property": "ステータス",
            "select": {"equals": "募集中"}
        },
        "page_size": 100
    }
    if start_cursor:
        body["start_cursor"] = start_cursor
    
    resp = requests.post(
        f"https://api.notion.com/v1/databases/{ANKEN_DB}/query",
        headers=headers,
        json=body
    )
    data = resp.json()
    results = data.get("results", [])
    all_pages.extend(results)
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

print(f"=== NOTION 案件DB 募集中: {len(all_pages)} 件 ===\n")

# Analyze field quality
stats = {
    "total": len(all_pages),
    "skills_empty": 0,
    "skills_1only": 0,
    "skills_2plus": 0,
    "preferred_empty": 0,
    "rate_empty": 0,
    "location_empty": 0,
    "role_empty": 0,
    "remote_empty": 0,
    "interview_empty": 0,
    "foreign_empty": 0,
    "high_quality": 0,  # has skills AND rate
}

skill_counts = []

for page in all_pages:
    props = page.get("properties", {})
    
    # Required skills
    skills_prop = props.get("必要スキル", {})
    skills_val = ""
    if skills_prop.get("type") == "rich_text":
        skills_val = "".join([t.get("plain_text", "") for t in skills_prop.get("rich_text", [])])
    elif skills_prop.get("type") == "multi_select":
        skills_val = str([o.get("name", "") for o in skills_prop.get("multi_select", [])])
    
    skills_clean = skills_val.strip() if skills_val else ""
    has_skills = bool(skills_clean and skills_clean not in ['', '[]', 'null', 'None'])
    if not has_skills:
        stats["skills_empty"] += 1
    else:
        try:
            parsed = json.loads(skills_clean) if skills_clean.startswith('[') else [skills_clean]
            cnt = len(parsed) if isinstance(parsed, list) else 1
            skill_counts.append(cnt)
            if cnt == 1:
                stats["skills_1only"] += 1
            else:
                stats["skills_2plus"] += 1
        except:
            skill_counts.append(1)
            stats["skills_1only"] += 1
    
    # Preferred skills
    pref_prop = props.get("尚可スキル", {})
    pref_val = ""
    if pref_prop.get("type") == "rich_text":
        pref_val = "".join([t.get("plain_text", "") for t in pref_prop.get("rich_text", [])])
    if not pref_val or pref_val.strip() in ['', '[]', 'null', 'None']:
        stats["preferred_empty"] += 1
    
    # Rate
    rate_prop = props.get("単価_下限", {}) or props.get("単価下限", {}) or props.get("想定単価", {})
    rate_val = None
    for rate_name in ["単価_下限", "単価下限", "想定単価", "単価"]:
        rp = props.get(rate_name, {})
        if rp.get("type") == "number":
            rate_val = rp.get("number")
        elif rp.get("type") == "rich_text":
            rt = "".join([t.get("plain_text", "") for t in rp.get("rich_text", [])])
            if rt.strip():
                rate_val = rt.strip()
        if rate_val:
            break
    if not rate_val:
        stats["rate_empty"] += 1
    
    # Location
    loc_prop = props.get("勤務地", {})
    loc_val = ""
    if loc_prop.get("type") == "rich_text":
        loc_val = "".join([t.get("plain_text", "") for t in loc_prop.get("rich_text", [])])
    elif loc_prop.get("type") == "select":
        loc_val = (loc_prop.get("select") or {}).get("name", "")
    if not loc_val or loc_val.strip() in ['', 'null', 'None']:
        stats["location_empty"] += 1
    
    # High quality = has skills AND rate
    if has_skills and rate_val:
        stats["high_quality"] += 1

total = stats["total"]
print(f"--- FIELD QUALITY (n={total}) ---")
print(f"  必要スキル空: {stats['skills_empty']} ({stats['skills_empty']/total*100:.1f}%)")
print(f"  必要スキル1個のみ: {stats['skills_1only']} ({stats['skills_1only']/total*100:.1f}%)")
print(f"  必要スキル2個以上: {stats['skills_2plus']} ({stats['skills_2plus']/total*100:.1f}%)")
print(f"  尚可スキル空: {stats['preferred_empty']} ({stats['preferred_empty']/total*100:.1f}%)")
print(f"  単価空: {stats['rate_empty']} ({stats['rate_empty']/total*100:.1f}%)")
print(f"  勤務地空: {stats['location_empty']} ({stats['location_empty']/total*100:.1f}%)")
print(f"  高品質(スキル+単価): {stats['high_quality']} ({stats['high_quality']/total*100:.1f}%)")

if skill_counts:
    print(f"\n--- SKILL COUNT DISTRIBUTION ---")
    print(f"  Avg skills: {sum(skill_counts)/len(skill_counts):.1f}")
    print(f"  1: {sum(1 for s in skill_counts if s == 1)}")
    print(f"  2-3: {sum(1 for s in skill_counts if 2 <= s <= 3)}")
    print(f"  4-5: {sum(1 for s in skill_counts if 4 <= s <= 5)}")
    print(f"  6+: {sum(1 for s in skill_counts if s >= 6)}")

# Show property names for reference
print(f"\n--- ALL PROPERTY NAMES ---")
if all_pages:
    props = all_pages[0].get("properties", {})
    for k in sorted(props.keys()):
        ptype = props[k].get("type", "unknown")
        print(f"  {k} ({ptype})")

print("\n=== DONE ===")
