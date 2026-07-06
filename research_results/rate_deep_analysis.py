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
print(f"Total 募集中: {total}\n")

# Corrected analysis - treat 0 as empty
rate_null = 0
rate_zero = 0
rate_low = 0  # 1-34
rate_normal = 0  # 35-100
rate_high = 0  # >100
rate_vals_clean = []

for page in all_pages:
    props = page.get("properties", {})
    rate = props.get("単価（万円）", {}).get("number")
    if rate is None:
        rate_null += 1
    elif rate == 0:
        rate_zero += 1
    elif rate < 35:
        rate_low += 1
        rate_vals_clean.append(rate)
    elif rate <= 100:
        rate_normal += 1
        rate_vals_clean.append(rate)
    else:
        rate_high += 1
        rate_vals_clean.append(rate)

rate_truly_empty = rate_null + rate_zero
print(f"=== 単価分析（修正版）===")
print(f"  NULL (DBに値なし): {rate_null} ({rate_null/total*100:.1f}%)")
print(f"  0万 (抽出失敗): {rate_zero} ({rate_zero/total*100:.1f}%)")
print(f"  1-34万 (異常低): {rate_low} ({rate_low/total*100:.1f}%)")
print(f"  35-100万 (正常帯): {rate_normal} ({rate_normal/total*100:.1f}%)")
print(f"  >100万 (高額): {rate_high} ({rate_high/total*100:.1f}%)")
print(f"")
print(f"  【真の単価空率】: {rate_truly_empty}/{total} = {rate_truly_empty/total*100:.1f}%")
print(f"  【真の高品質(スキル+正常単価)】:")

# Recalculate high quality
hq_corrected = 0
ultra_corrected = 0
for page in all_pages:
    props = page.get("properties", {})
    skills = props.get("必要スキル", {}).get("multi_select", [])
    rate = props.get("単価（万円）", {}).get("number")
    loc_texts = props.get("勤務地", {}).get("rich_text", [])
    loc = "".join([t.get("plain_text", "") for t in loc_texts]).strip()
    pref = props.get("尚可スキル", {}).get("multi_select", [])
    
    has_skills = len(skills) > 0
    has_real_rate = rate is not None and rate >= 35
    has_loc = bool(loc)
    has_pref = len(pref) > 0
    
    if has_skills and has_real_rate:
        hq_corrected += 1
    if has_skills and has_real_rate and has_loc and has_pref:
        ultra_corrected += 1

print(f"    旧定義(0万含む): 355/436 = 81.4%")
print(f"    修正定義(35万以上): {hq_corrected}/{total} = {hq_corrected/total*100:.1f}%")
print(f"    最高品質(修正): {ultra_corrected}/{total} = {ultra_corrected/total*100:.1f}%")

# Rate distribution (clean)
if rate_vals_clean:
    print(f"\n=== 正常単価の分布 ({len(rate_vals_clean)}件) ===")
    print(f"  平均: {sum(rate_vals_clean)/len(rate_vals_clean):.0f}万")
    print(f"  35-50万: {sum(1 for v in rate_vals_clean if 35 <= v <= 50)}")
    print(f"  51-60万: {sum(1 for v in rate_vals_clean if 51 <= v <= 60)}")
    print(f"  61-70万: {sum(1 for v in rate_vals_clean if 61 <= v <= 70)}")
    print(f"  71-80万: {sum(1 for v in rate_vals_clean if 71 <= v <= 80)}")
    print(f"  81-90万: {sum(1 for v in rate_vals_clean if 81 <= v <= 90)}")
    print(f"  >90万: {sum(1 for v in rate_vals_clean if v > 90)}")

# Sample some 0万 cases with rate text in detail
print(f"\n=== 0万案件の原文単価パターン (サンプル5件) ===")
count = 0
for page in all_pages:
    if count >= 5:
        break
    props = page.get("properties", {})
    rate = props.get("単価（万円）", {}).get("number")
    if rate == 0:
        detail_texts = props.get("案件詳細", {}).get("rich_text", [])
        detail = "".join([t.get("plain_text", "") for t in detail_texts])
        # Find rate context
        for kw in ["単価", "金額", "予算", "MAX", "max", "Max"]:
            idx = detail.find(kw)
            if idx >= 0:
                start = max(0, idx - 10)
                end = min(len(detail), idx + 60)
                count += 1
                print(f"  [{count}] ...{detail[start:end]}...")
                break

print("\n=== DONE ===")
