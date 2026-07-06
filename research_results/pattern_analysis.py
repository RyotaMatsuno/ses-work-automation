import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests
import json
import os
import re
from dotenv import load_dotenv

load_dotenv(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = os.getenv("NOTION_API_KEY")
ANKEN_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# Get 0万 cases
all_zero = []
has_more = True
start_cursor = None
while has_more:
    body = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"property": "単価（万円）", "number": {"equals": 0}}
            ]
        },
        "page_size": 100
    }
    if start_cursor:
        body["start_cursor"] = start_cursor
    resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body)
    data = resp.json()
    all_zero.extend(data.get("results", []))
    has_more = data.get("has_more", False)
    start_cursor = data.get("next_cursor")

print(f"Total 0万 cases: {len(all_zero)}\n")

# Categorize rate patterns in raw text
patterns = {
    "skill_miawase": 0,      # スキル見合い
    "tilde_number": 0,       # 〜70万, ~65万
    "max_number": 0,          # MAX75万, max 70
    "number_man": 0,          # 70万, 65万 (plain)
    "budget_word": 0,         # 予算:, 金額:
    "no_rate_text": 0,        # No rate-related text at all
    "other": 0,
}

remote_patterns = {
    "full_remote": 0,
    "hybrid": 0,
    "onsite": 0,
    "partial": 0,
    "no_remote_text": 0,
}

examples = {k: [] for k in patterns}
remote_examples = {k: [] for k in remote_patterns}

for page in all_zero:
    props = page.get("properties", {})
    detail_texts = props.get("案件詳細", {}).get("rich_text", [])
    detail = "".join([t.get("plain_text", "") for t in detail_texts])
    title = "".join([t.get("plain_text", "") for t in props.get("案件名", {}).get("title", [])])
    
    # Rate pattern classification
    found_rate = False
    if re.search(r'スキル見合', detail):
        patterns["skill_miawase"] += 1
        if len(examples["skill_miawase"]) < 3:
            # Extract context
            m = re.search(r'.{0,20}スキル見合.{0,40}', detail)
            examples["skill_miawase"].append(m.group() if m else "")
        
        # Check if there's also a MAX value
        m2 = re.search(r'[Mm][Aa][Xx]\s*[:：]?\s*(\d+)', detail)
        if m2:
            patterns["max_number"] += 1
            found_rate = True
        found_rate = True
    
    if re.search(r'[〜~～]\s*\d+\s*万', detail):
        patterns["tilde_number"] += 1
        m = re.search(r'.{0,10}[〜~～]\s*\d+\s*万.{0,20}', detail)
        if len(examples["tilde_number"]) < 3:
            examples["tilde_number"].append(m.group() if m else "")
        found_rate = True
    
    if re.search(r'[Mm][Aa][Xx]\s*[:：]?\s*\d+', detail, re.IGNORECASE):
        patterns["max_number"] += 1
        m = re.search(r'.{0,10}[Mm][Aa][Xx]\s*[:：]?\s*\d+.{0,20}', detail, re.IGNORECASE)
        if len(examples["max_number"]) < 3:
            examples["max_number"].append(m.group() if m else "")
        found_rate = True
    
    if re.search(r'\d{2,3}\s*万', detail) and not found_rate:
        patterns["number_man"] += 1
        m = re.search(r'.{0,15}\d{2,3}\s*万.{0,20}', detail)
        if len(examples["number_man"]) < 3:
            examples["number_man"].append(m.group() if m else "")
        found_rate = True
    
    if re.search(r'(予算|金額|単価)', detail) and not found_rate:
        patterns["budget_word"] += 1
        found_rate = True
    
    if not found_rate:
        patterns["no_rate_text"] += 1
        if len(examples["no_rate_text"]) < 3:
            examples["no_rate_text"].append(title[:60])
    
    # Remote pattern classification
    found_remote = False
    if re.search(r'フルリモート|完全リモート|フル在宅', detail):
        remote_patterns["full_remote"] += 1
        found_remote = True
    elif re.search(r'リモート併用|ハイブリッド|週\d出社|週\d.*出社', detail):
        remote_patterns["hybrid"] += 1
        found_remote = True
    elif re.search(r'常駐|オンサイト|出社必須', detail):
        remote_patterns["onsite"] += 1
        found_remote = True
    elif re.search(r'リモート|テレワーク|在宅', detail):
        remote_patterns["partial"] += 1
        found_remote = True
    
    if not found_remote:
        remote_patterns["no_remote_text"] += 1

print("=== RATE PATTERN CLASSIFICATION (0万 cases) ===")
for k, v in patterns.items():
    pct = v / len(all_zero) * 100 if all_zero else 0
    print(f"  {k}: {v} ({pct:.1f}%)")
    if examples.get(k):
        for ex in examples[k]:
            print(f"    ex: {ex}")

print(f"\n  RULE-RECOVERABLE (スキル見合い+MAX+〜N万+N万): {patterns['skill_miawase'] + patterns['tilde_number'] + patterns['max_number'] + patterns['number_man']}")
print(f"  NEEDS LLM (budget_word): {patterns['budget_word']}")
print(f"  TRULY NO DATA: {patterns['no_rate_text']}")

print(f"\n=== REMOTE PATTERNS (in 0万 subset, n={len(all_zero)}) ===")
for k, v in remote_patterns.items():
    pct = v / len(all_zero) * 100 if all_zero else 0
    print(f"  {k}: {v} ({pct:.1f}%)")

# Now check remote patterns in ALL 募集中 cases
print(f"\n=== Checking remote patterns in ALL 募集中 ===")
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
r_full = r_hybrid = r_onsite = r_partial = r_none = 0
for page in all_pages:
    props = page.get("properties", {})
    detail_texts = props.get("案件詳細", {}).get("rich_text", [])
    detail = "".join([t.get("plain_text", "") for t in detail_texts])
    if re.search(r'フルリモート|完全リモート|フル在宅', detail):
        r_full += 1
    elif re.search(r'リモート併用|ハイブリッド|週\d出社|週\d.*出社', detail):
        r_hybrid += 1
    elif re.search(r'常駐|オンサイト|出社必須', detail):
        r_onsite += 1
    elif re.search(r'リモート|テレワーク|在宅', detail):
        r_partial += 1
    else:
        r_none += 1

print(f"  Total: {total}")
print(f"  フルリモート: {r_full} ({r_full/total*100:.1f}%)")
print(f"  ハイブリッド: {r_hybrid} ({r_hybrid/total*100:.1f}%)")
print(f"  常駐: {r_onsite} ({r_onsite/total*100:.1f}%)")
print(f"  リモート(曖昧): {r_partial} ({r_partial/total*100:.1f}%)")
print(f"  言及なし: {r_none} ({r_none/total*100:.1f}%)")
print(f"  抽出可能合計: {r_full+r_hybrid+r_onsite+r_partial} ({(r_full+r_hybrid+r_onsite+r_partial)/total*100:.1f}%)")
