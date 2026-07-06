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

# Get 募集中 with pagination
all_pages = []
has_more = True
start_cursor = None
while has_more:
    body = {"filter": {"property": "ステータス", "select": {"equals": "募集中"}}, "page_size": 100}
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body)
    data = resp.json()
    all_pages.extend(data.get("results", []))
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

total = len(all_pages)
print(f"=== 案件DB 募集中: {total} 件 ===\n")

# Proper field analysis
skills_empty = 0
skills_counts = []
pref_empty = 0
pref_counts = []
rate_empty = 0
rate_vals = []
cost_rate_empty = 0
location_empty = 0
location_vals = []
remote_vals = {}
detail_empty = 0

for page in all_pages:
    props = page.get("properties", {})
    
    # 必要スキル (multi_select)
    ms = props.get("必要スキル", {}).get("multi_select", [])
    if not ms:
        skills_empty += 1
    else:
        skills_counts.append(len(ms))
    
    # 尚可スキル (multi_select)
    ps = props.get("尚可スキル", {}).get("multi_select", [])
    if not ps:
        pref_empty += 1
    else:
        pref_counts.append(len(ps))
    
    # 単価（万円） (number)
    rate = props.get("単価（万円）", {}).get("number")
    if rate is None:
        rate_empty += 1
    else:
        rate_vals.append(rate)
    
    # 仕入単価（万円） (number)
    cost = props.get("仕入単価（万円）", {}).get("number")
    if cost is None:
        cost_rate_empty += 1
    
    # 勤務地 (rich_text)
    loc_texts = props.get("勤務地", {}).get("rich_text", [])
    loc = "".join([t.get("plain_text", "") for t in loc_texts]).strip()
    if not loc:
        location_empty += 1
    else:
        location_vals.append(loc)
    
    # リモート (select)
    remote = (props.get("リモート", {}).get("select") or {}).get("name", "empty")
    remote_vals[remote] = remote_vals.get(remote, 0) + 1
    
    # 案件詳細 (rich_text)
    detail_texts = props.get("案件詳細", {}).get("rich_text", [])
    detail = "".join([t.get("plain_text", "") for t in detail_texts]).strip()
    if not detail:
        detail_empty += 1

# Results
print(f"--- FIELD QUALITY ---")
print(f"  必要スキル空: {skills_empty}/{total} = {skills_empty/total*100:.1f}%")
has_sk = total - skills_empty
if skills_counts:
    print(f"  必要スキル平均個数: {sum(skills_counts)/len(skills_counts):.1f}")
    print(f"    1個: {sum(1 for s in skills_counts if s == 1)}")
    print(f"    2-3個: {sum(1 for s in skills_counts if 2 <= s <= 3)}")
    print(f"    4-5個: {sum(1 for s in skills_counts if 4 <= s <= 5)}")
    print(f"    6+個: {sum(1 for s in skills_counts if s >= 6)}")

print(f"\n  尚可スキル空: {pref_empty}/{total} = {pref_empty/total*100:.1f}%")
if pref_counts:
    print(f"  尚可スキル平均個数: {sum(pref_counts)/len(pref_counts):.1f}")

print(f"\n  単価（万円）空: {rate_empty}/{total} = {rate_empty/total*100:.1f}%")
if rate_vals:
    print(f"  単価平均: {sum(rate_vals)/len(rate_vals):.0f}万")
    print(f"    <30万: {sum(1 for v in rate_vals if v < 30)}")
    print(f"    30-50万: {sum(1 for v in rate_vals if 30 <= v < 50)}")
    print(f"    50-70万: {sum(1 for v in rate_vals if 50 <= v < 70)}")
    print(f"    70-90万: {sum(1 for v in rate_vals if 70 <= v <= 90)}")
    print(f"    >90万: {sum(1 for v in rate_vals if v > 90)}")

print(f"\n  仕入単価空: {cost_rate_empty}/{total} = {cost_rate_empty/total*100:.1f}%")

print(f"\n  勤務地空: {location_empty}/{total} = {location_empty/total*100:.1f}%")

print(f"\n  案件詳細空: {detail_empty}/{total} = {detail_empty/total*100:.1f}%")

print(f"\n  リモート: {remote_vals}")

# High quality = has skills + rate
hq = sum(1 for p in all_pages if 
    len(p["properties"].get("必要スキル", {}).get("multi_select", [])) > 0 and
    p["properties"].get("単価（万円）", {}).get("number") is not None)
print(f"\n  高品質(スキル+単価): {hq}/{total} = {hq/total*100:.1f}%")

# Ultra high quality = skills + rate + location + preferred
uhq = sum(1 for p in all_pages if
    len(p["properties"].get("必要スキル", {}).get("multi_select", [])) > 0 and
    p["properties"].get("単価（万円）", {}).get("number") is not None and
    "".join([t.get("plain_text", "") for t in p["properties"].get("勤務地", {}).get("rich_text", [])]).strip() and
    len(p["properties"].get("尚可スキル", {}).get("multi_select", [])) > 0)
print(f"  最高品質(スキル+単価+勤務地+尚可): {uhq}/{total} = {uhq/total*100:.1f}%")

print("\n=== DONE ===")
