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

# Get 募集中 with rate < 30
body = {
    "filter": {
        "and": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "単価（万円）", "number": {"is_not_empty": True}},
            {"property": "単価（万円）", "number": {"less_than": 30}}
        ]
    },
    "page_size": 30
}

resp = requests.post(f"https://api.notion.com/v1/databases/{ANKEN_DB}/query", headers=headers, json=body)
data = resp.json()
results = data.get("results", [])

print(f"=== 単価<30万 サンプル（{len(results)} / 159件）===\n")

for i, page in enumerate(results[:20]):
    props = page.get("properties", {})
    title = "".join([t.get("plain_text", "") for t in props.get("案件名", {}).get("title", [])])
    rate = props.get("単価（万円）", {}).get("number")
    detail_texts = props.get("案件詳細", {}).get("rich_text", [])
    detail = "".join([t.get("plain_text", "") for t in detail_texts])
    skills = [s.get("name", "") for s in props.get("必要スキル", {}).get("multi_select", [])]
    
    # Extract rate-related text from detail
    rate_context = ""
    for keyword in ["単価", "金額", "予算", "万", "スキル見", "MAX", "max"]:
        idx = detail.find(keyword)
        if idx >= 0:
            start = max(0, idx - 20)
            end = min(len(detail), idx + 50)
            rate_context += f" | ...{detail[start:end]}..."
    
    print(f"[{i+1}] {title[:50]}")
    print(f"    DB単価: {rate}万")
    print(f"    スキル: {', '.join(skills[:5])}")
    if rate_context:
        print(f"    原文単価文脈: {rate_context[:200]}")
    else:
        # Show first 200 chars of detail for reference
        print(f"    詳細冒頭: {detail[:150]}")
    print()
