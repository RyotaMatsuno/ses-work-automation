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

# Get v2 tagged pages (pipeline_version = v2)
body = {
    "filter": {
        "property": "pipeline_version",
        "select": {"equals": "v2"}
    },
    "page_size": 30
}

resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body)
data = resp.json()
results = data.get("results", [])

print(f"=== v2 tagged pages: {len(results)} ===\n")

for i, page in enumerate(results):
    props = page.get("properties", {})
    
    # Title
    title = "".join([t.get("plain_text", "") for t in props.get("案件名", {}).get("title", [])])
    
    # Rate
    rate = props.get("単価（万円）", {}).get("number")
    rate_type = (props.get("rate_type", {}).get("select") or {}).get("name", "—")
    
    # Remote
    remote_type = (props.get("remote_type", {}).get("select") or {}).get("name", "—")
    
    # Location
    loc_texts = props.get("勤務地", {}).get("rich_text", [])
    location = "".join([t.get("plain_text", "") for t in loc_texts]).strip() or "—"
    
    # Skills
    skills = [s.get("name", "") for s in props.get("必要スキル", {}).get("multi_select", [])]
    skills_str = ", ".join(skills[:5]) if skills else "—"
    
    # Extraction confidence
    confidence = props.get("extraction_confidence", {}).get("number")
    
    # Extraction method
    method = (props.get("extraction_method", {}).get("select") or {}).get("name", "—")
    
    # Needs review
    needs_review = props.get("needs_review", {}).get("checkbox", False)
    
    # Detail (first 150 chars for rate/remote context)
    detail_texts = props.get("案件詳細", {}).get("rich_text", [])
    detail = "".join([t.get("plain_text", "") for t in detail_texts])
    
    # Extract rate context from detail
    rate_ctx = ""
    for kw in ["単価", "金額", "予算", "MAX", "max", "Max"]:
        idx = detail.find(kw)
        if idx >= 0:
            s = max(0, idx - 5)
            e = min(len(detail), idx + 50)
            rate_ctx = detail[s:e].replace('\n', ' ')
            break
    
    # Extract remote context
    remote_ctx = ""
    for kw in ["リモート", "常駐", "出社", "テレワーク", "在宅"]:
        idx = detail.find(kw)
        if idx >= 0:
            s = max(0, idx - 5)
            e = min(len(detail), idx + 40)
            remote_ctx = detail[s:e].replace('\n', ' ')
            break
    
    review_mark = "⚠️" if needs_review else "✅"
    
    print(f"[{i+1}] {review_mark} {title[:50]}")
    print(f"    単価: {rate}万 | rate_type: {rate_type}")
    print(f"    リモート: {remote_type}")
    print(f"    勤務地: {location}")
    print(f"    スキル: {skills_str}")
    print(f"    confidence: {confidence} | method: {method}")
    if rate_ctx:
        print(f"    原文(単価): {rate_ctx}")
    if remote_ctx:
        print(f"    原文(リモート): {remote_ctx}")
    print()
