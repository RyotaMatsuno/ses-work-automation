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

# Get ALL 募集中
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

# Metrics
skills_empty = 0
pref_empty = 0
rate_null = 0
rate_zero = 0
rate_normal = 0
loc_empty = 0
rate_type_dist = {}
remote_type_dist = {}
pipeline_v2 = 0
has_confidence = 0

for page in all_pages:
    props = page.get("properties", {})
    
    # Skills
    if not props.get("必要スキル", {}).get("multi_select", []):
        skills_empty += 1
    
    # Preferred
    if not props.get("尚可スキル", {}).get("multi_select", []):
        pref_empty += 1
    
    # Rate
    rate = props.get("単価（万円）", {}).get("number")
    if rate is None:
        rate_null += 1
    elif rate == 0:
        rate_zero += 1
    else:
        rate_normal += 1
    
    # Location
    loc = "".join([t.get("plain_text", "") for t in props.get("勤務地", {}).get("rich_text", [])]).strip()
    if not loc:
        loc_empty += 1
    
    # Rate type
    rt = (props.get("rate_type", {}).get("select") or {}).get("name", "(empty)")
    rate_type_dist[rt] = rate_type_dist.get(rt, 0) + 1
    
    # Remote type
    rmt = (props.get("remote_type", {}).get("select") or {}).get("name", "(empty)")
    remote_type_dist[rmt] = remote_type_dist.get(rmt, 0) + 1
    
    # Pipeline version
    pv = (props.get("pipeline_version", {}).get("select") or {}).get("name")
    if pv == "v2":
        pipeline_v2 += 1
    
    # Confidence
    conf = props.get("extraction_confidence", {}).get("number")
    if conf is not None:
        has_confidence += 1

rate_truly_empty = rate_null + rate_zero
hq = sum(1 for p in all_pages if
    len(p["properties"].get("必要スキル", {}).get("multi_select", [])) > 0 and
    (p["properties"].get("単価（万円）", {}).get("number") or 0) > 0)

uhq = sum(1 for p in all_pages if
    len(p["properties"].get("必要スキル", {}).get("multi_select", [])) > 0 and
    (p["properties"].get("単価（万円）", {}).get("number") or 0) > 0 and
    "".join([t.get("plain_text", "") for t in p["properties"].get("勤務地", {}).get("rich_text", [])]).strip() and
    (p["properties"].get("remote_type", {}).get("select") or {}).get("name", "") not in ["", "(empty)"])

print(f"=== R5 POST-BACKFILL METRICS ({total}件) ===\n")

print("--- BEFORE → AFTER 比較 ---")
print(f"  必要スキル空:     6.0% → {skills_empty/total*100:.1f}%")
print(f"  単価空(修正版):  49.5% → {rate_truly_empty/total*100:.1f}%  (null:{rate_null} + 0万:{rate_zero})")
print(f"  勤務地空:        29.1% → {loc_empty/total*100:.1f}%")
print(f"  リモート空:     100.0% → {remote_type_dist.get('(empty)',0)/total*100:.1f}%")
print(f"  高品質(スキル+単価): 46.1% → {hq/total*100:.1f}%")
print(f"  最高品質(4項目):  24.9% → {uhq/total*100:.1f}%")
print(f"  v2適用率:         4.3% → {pipeline_v2/total*100:.1f}%")

print(f"\n--- rate_type 分布 ---")
for k, v in sorted(rate_type_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({v/total*100:.1f}%)")

print(f"\n--- remote_type 分布 ---")
for k, v in sorted(remote_type_dist.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({v/total*100:.1f}%)")
