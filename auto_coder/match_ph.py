# -*- coding: utf-8 -*-
"""PH(P.H)さんに合う案件をDBから抽出"""

import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
DB_PROJ = "343450ff-37c0-81e4-934e-f25f90284a3c"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# 「募集中」案件を直近4営業日分（鮮度ルール）取得
# 単価40万〜55万、PMO/設計支援/開発/テストの経験を活かせる案件
# 外国籍OKフィルタも必要

# まず案件DBスキーマ確認
print("=== schema ===")
r = requests.get(f"https://api.notion.com/v1/databases/{DB_PROJ}", headers=HEADERS, timeout=30)
schema = r.json()
print("  Properties:")
for name, prop in schema.get("properties", {}).items():
    print(f"    {name}: {prop.get('type')}")

# 「募集中」かつ 直近4日以内のcreated案件を取得
since = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00.000Z")
url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"

all_proj = []
cursor = None
while True:
    body = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"timestamp": "created_time", "created_time": {"on_or_after": since}},
            ]
        },
        "page_size": 100,
    }
    if cursor:
        body["start_cursor"] = cursor
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    if r.status_code != 200:
        print(f"ERR: {r.status_code} {r.text[:300]}")
        break
    data = r.json()
    all_proj.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")

print(f"\n=== 募集中 (last 5d UTC): {len(all_proj)} ===")


# 単価抽出関数(案件詳細から正規表現)
def extract_price(text):
    # 「45万」「45-55万」「45万〜55万」「45〜55」など
    m = re.search(r"(\d{2,3})\s*万[円〜~−\-]\s*(\d{2,3})?", text)
    if m:
        low = int(m.group(1))
        high = int(m.group(2)) if m.group(2) else low
        return low, high
    m2 = re.search(r"希望単[価金]\s*[:：]?\s*[\W]*(\d{2,3})", text)
    if m2:
        v = int(m2.group(1))
        return v, v
    m3 = re.search(r"単[価金]\s*[:：]\s*[\W]*(\d{2,3})", text)
    if m3:
        v = int(m3.group(1))
        return v, v
    return None, None


def is_foreign_ok(text):
    # 「外国籍：可」「外国籍OK」「外国籍：日本語問題なければ可」など
    if re.search(r"外国籍[\s：:]*不可|外国籍\s*NG", text):
        return False
    if re.search(r"外国籍[\s：:]*可|外国籍\s*OK|日本語.{0,20}(問題|ネイティブ).{0,10}可", text):
        return True
    # 記載なし → 不明（保守的にFalseとせずTrueとする）
    return None  # 不明


candidates = []
for rec in all_proj:
    props = rec.get("properties", {})
    title = ""
    for k, v in props.items():
        if v.get("type") == "title":
            title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
            break
    detail = ""
    for k, v in props.items():
        if "詳細" in k and v.get("type") == "rich_text":
            detail = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
            break
    low, high = extract_price(detail)
    foreign = is_foreign_ok(detail)
    created = rec.get("created_time", "")
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "price_low": low,
            "price_high": high,
            "foreign": foreign,
            "created": created,
            "detail": detail,
        }
    )

# 単価40-55万に合う & 外国籍可（or 不明）& 簡易スキルマッチ
PH_KEYWORDS = [
    "PMO",
    "設計支援",
    "テスト",
    "開発支援",
    "サポート",
    "PG",
    "プログラマ",
    "詳細設計",
    "基本設計",
    "支援",
    "アシスタント",
]
matched = []
for c in candidates:
    if c["price_high"] is None:
        continue
    # 上限が40-55の間 or 単価範囲がPHに合う
    if not (35 <= c["price_high"] <= 60):
        continue
    # 外国籍 不可なら除外
    if c["foreign"] is False:
        continue
    # 簡易スキルマッチ
    score = 0
    for kw in PH_KEYWORDS:
        if kw in c["title"] or kw in c["detail"][:1000]:
            score += 1
    c["score"] = score
    matched.append(c)

matched.sort(key=lambda x: (-x["score"], x["price_high"] or 999))

print(f"\n=== Candidates for P.H (price 35-60万, foreign-OK or unknown): {len(matched)} ===")
for c in matched[:15]:
    print(f"\n  [{c['price_low']}-{c['price_high']}万 / foreign={c['foreign']} / score={c['score']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    created: {c['created']}")
