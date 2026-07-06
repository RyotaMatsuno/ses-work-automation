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

all_pages = []
has_more = True
start_cursor = None
page_num = 0
while has_more:
    body = {"filter": {"property": "ステータス", "select": {"equals": "募集中"}}, "page_size": 100}
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body, timeout=30)
    data = resp.json()
    batch = data.get("results", [])
    all_pages.extend(batch)
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")
    page_num += 1
    print(f"Page {page_num}: +{len(batch)} (total: {len(all_pages)})")

total = len(all_pages)
sk_e = rt_n = rt_z = rt_ok = loc_e = 0
rt_dist = {}
rm_dist = {}
v2 = 0

for p in all_pages:
    pr = p.get("properties", {})
    if not pr.get("必要スキル", {}).get("multi_select", []):
        sk_e += 1
    r = pr.get("単価（万円）", {}).get("number")
    if r is None: rt_n += 1
    elif r == 0: rt_z += 1
    else: rt_ok += 1
    loc = "".join([t.get("plain_text","") for t in pr.get("勤務地",{}).get("rich_text",[])]).strip()
    if not loc: loc_e += 1
    rtype = (pr.get("rate_type",{}).get("select") or {}).get("name","(empty)")
    rt_dist[rtype] = rt_dist.get(rtype,0)+1
    rmtype = (pr.get("remote_type",{}).get("select") or {}).get("name","(empty)")
    rm_dist[rmtype] = rm_dist.get(rmtype,0)+1
    if (pr.get("pipeline_version",{}).get("select") or {}).get("name") == "v2":
        v2 += 1

hq = sum(1 for p in all_pages if len(p["properties"].get("必要スキル",{}).get("multi_select",[]))>0 and (p["properties"].get("単価（万円）",{}).get("number") or 0)>0)
uhq = sum(1 for p in all_pages if len(p["properties"].get("必要スキル",{}).get("multi_select",[]))>0 and (p["properties"].get("単価（万円）",{}).get("number") or 0)>0 and "".join([t.get("plain_text","") for t in p["properties"].get("勤務地",{}).get("rich_text",[])]).strip() and (p["properties"].get("remote_type",{}).get("select") or {}).get("name","") not in [""," ","(empty)"])

print(f"\n{'='*50}")
print(f"R5 BEFORE vs AFTER ({total}件)")
print(f"{'='*50}")
print(f"必要スキル空:     6.0% -> {sk_e/total*100:.1f}%")
print(f"単価空(修正版):  49.5% -> {(rt_n+rt_z)/total*100:.1f}%  (null:{rt_n}, 0万:{rt_z})")
print(f"勤務地空:        29.1% -> {loc_e/total*100:.1f}%")
rm_empty = rm_dist.get("(empty)",0)
print(f"リモート空:     100.0% -> {rm_empty/total*100:.1f}%")
print(f"高品質:          46.1% -> {hq/total*100:.1f}%")
print(f"最高品質(4項目): 24.9% -> {uhq/total*100:.1f}%")
print(f"v2適用:           4.3% -> {v2/total*100:.1f}%")
print(f"\nrate_type:")
for k,v in sorted(rt_dist.items(), key=lambda x:-x[1]):
    print(f"  {k}: {v} ({v/total*100:.1f}%)")
print(f"\nremote_type:")
for k,v in sorted(rm_dist.items(), key=lambda x:-x[1]):
    print(f"  {k}: {v} ({v/total*100:.1f}%)")
