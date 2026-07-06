import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# First: get schema
resp = requests.get(f"https://api.notion.com/v1/databases/{ENG_DB}", headers=headers, timeout=15)
db = resp.json()
print("=== ENGINEER DB SCHEMA ===")
for k, v in sorted(db.get("properties", {}).items()):
    ptype = v.get("type", "?")
    if ptype == "select":
        opts = [o["name"] for o in v.get("select", {}).get("options", [])]
        print(f"  {k} ({ptype}): {opts}")
    elif ptype == "multi_select":
        opts = [o["name"] for o in v.get("multi_select", {}).get("options", [])]
        print(f"  {k} ({ptype}): [{len(opts)} options]")
    else:
        print(f"  {k} ({ptype})")

# Get all engineers
all_eng = []
has_more = True
start_cursor = None
while has_more:
    body = {"page_size": 100}
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json=body, timeout=30)
    data = resp.json()
    all_eng.extend(data.get("results", []))
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

total = len(all_eng)
print(f"\n=== TOTAL ENGINEERS: {total} ===\n")

# Analyze field quality
skills_empty = 0
skills_counts = []
rate_empty = 0
status_dist = {}
source_dist = {}
has_resume = 0
detail_empty = 0

for eng in all_eng:
    props = eng.get("properties", {})
    
    # Status
    for st_name in ["ステータス", "状態", "稼働状態"]:
        st = (props.get(st_name, {}).get("select") or {}).get("name")
        if st:
            status_dist[st] = status_dist.get(st, 0) + 1
            break
    
    # Skills (multi_select or rich_text)
    skills = props.get("スキル", {}).get("multi_select", [])
    if not skills:
        skills = props.get("保有スキル", {}).get("multi_select", [])
    if not skills:
        # Try rich_text
        sk_text = "".join([t.get("plain_text", "") for t in props.get("スキル", {}).get("rich_text", [])]).strip()
        if not sk_text:
            sk_text = "".join([t.get("plain_text", "") for t in props.get("保有スキル", {}).get("rich_text", [])]).strip()
        if sk_text:
            skills = [sk_text]  # count as having something
    
    if not skills:
        skills_empty += 1
    else:
        skills_counts.append(len(skills))
    
    # Rate (desired)
    for rate_name in ["希望単価", "単価", "希望単価（万円）"]:
        rate = props.get(rate_name, {}).get("number")
        if rate is not None:
            break
    if rate is None:
        rate_empty += 1

print(f"--- FIELD QUALITY ---")
print(f"  スキル空: {skills_empty}/{total} = {skills_empty/total*100:.1f}%")
if skills_counts:
    print(f"  スキル平均個数: {sum(skills_counts)/len(skills_counts):.1f}")
    print(f"    1-3: {sum(1 for s in skills_counts if 1 <= s <= 3)}")
    print(f"    4-10: {sum(1 for s in skills_counts if 4 <= s <= 10)}")
    print(f"    11+: {sum(1 for s in skills_counts if s >= 11)}")
print(f"  希望単価空: {rate_empty}/{total} = {rate_empty/total*100:.1f}%")

print(f"\n--- STATUS ---")
for k, v in sorted(status_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")

# Sample 5 engineers with skills
print(f"\n--- SAMPLE ENGINEERS (with skills) ---")
count = 0
for eng in all_eng:
    if count >= 5:
        break
    props = eng.get("properties", {})
    title_parts = props.get("名前", {}).get("title", [])
    if not title_parts:
        for k, v in props.items():
            if v.get("type") == "title":
                title_parts = v.get("title", [])
                break
    name = "".join([t.get("plain_text", "") for t in title_parts])[:20]
    
    skills = [s.get("name", "") for s in props.get("スキル", {}).get("multi_select", [])]
    if not skills:
        skills = [s.get("name", "") for s in props.get("保有スキル", {}).get("multi_select", [])]
    
    if skills:
        count += 1
        rate = None
        for rn in ["希望単価", "単価", "希望単価（万円）"]:
            rate = props.get(rn, {}).get("number")
            if rate: break
        
        print(f"  [{count}] {name}")
        print(f"    Skills: {', '.join(skills[:10])}")
        print(f"    Rate: {rate}")
        print()

# Sample 3 engineers WITHOUT skills
print(f"--- SAMPLE ENGINEERS (NO skills) ---")
count = 0
for eng in all_eng:
    if count >= 3:
        break
    props = eng.get("properties", {})
    skills = props.get("スキル", {}).get("multi_select", [])
    if not skills:
        skills = props.get("保有スキル", {}).get("multi_select", [])
    if not skills:
        count += 1
        title_parts = []
        for k, v in props.items():
            if v.get("type") == "title":
                title_parts = v.get("title", [])
                break
        name = "".join([t.get("plain_text", "") for t in title_parts])[:20]
        print(f"  [{count}] {name} (skills: EMPTY)")
        # Show what fields DO have data
        for k, v in props.items():
            if v.get("type") == "rich_text":
                text = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])]).strip()
                if text:
                    print(f"    {k}: {text[:80]}")
            elif v.get("type") == "number" and v.get("number") is not None:
                print(f"    {k}: {v['number']}")
            elif v.get("type") == "select" and v.get("select"):
                print(f"    {k}: {v['select']['name']}")
        print()
