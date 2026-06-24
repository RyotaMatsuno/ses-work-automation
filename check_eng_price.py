import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import requests
from dotenv import dotenv_values

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
config = dotenv_values(os.path.join(BASE_DIR, "config", ".env"))
for k, v in config.items():
    if k not in os.environ and v:
        os.environ[k] = v

API_KEY = os.environ["NOTION_API_KEY"]
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
H = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# Get engineers without price
results = []
payload = {
    "page_size": 100,
    "filter": {
        "and": [
            {"property": "稼働状況", "select": {"equals": "稼働可能"}},
        ]
    },
}
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=H, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    results.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    payload["start_cursor"] = data["next_cursor"]

no_price_with_body = []
for p in results:
    props = p["properties"]
    price = props.get("単価（万円）", {}).get("number")
    if price:
        continue
    body = "".join(i.get("plain_text", "") for i in props.get("備考（LINEメモ）", {}).get("rich_text", []))
    name_parts = props.get("名前", {}).get("title", [])
    name = name_parts[0]["plain_text"] if name_parts else "?"

    # Try to extract price from body text
    # Common patterns: "45万", "50万円", "単価:50", "希望単価：50万"
    price_match = re.search(r"(\d{2,3})\s*万", body)
    if price_match:
        extracted_price = int(price_match.group(1))
        if 25 <= extracted_price <= 120:  # 妥当な範囲
            no_price_with_body.append({"name": name, "body_head": body[:200], "extracted": extracted_price})

print(f"単価なしエンジニア総数: {sum(1 for p in results if not p['properties'].get('単価（万円）', {}).get('number'))}")
print(f"テキストから単価抽出可能: {len(no_price_with_body)}")
print()
for s in no_price_with_body[:10]:
    print(f"  {s['name']}: {s['extracted']}万円 ← {s['body_head'][:100]}")
