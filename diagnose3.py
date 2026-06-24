import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import re

# =============================================================================
# 問題分析
# =============================================================================
print("=== classify_query の正規表現問題 ===")
# 現在のパターン: r"^([A-Za-z]{1,4})[\s\u3000/](.+)$"
# H.S 北小金 → "H.S" は [A-Za-z]{1,4} にマッチしない（.が含まれる）

test_cases = ["HS 北小金", "H.S 北小金", "H.S　北小金", "HS/北小金", "TK 渋谷"]
pattern_old = re.compile(r"^([A-Za-z]{1,4})[\s\u3000/](.+)$")
pattern_new = re.compile(r"^([A-Za-z]{1,4}(?:\.[A-Za-z])?)[.\s\u3000/]+(.+)$")

for tc in test_cases:
    old = pattern_old.match(tc)
    new = pattern_new.match(tc)
    print(f"  [{tc}] 旧={old.group(1, 2) if old else '×'} 新={new.group(1, 2) if new else '×'}")

print()
print("=== 116件問題の分析 ===")
print("原因: 案件DBの「必要スキル」が空の案件が多い")
print("  skill_match(required=[], engineer_skills=[...]) → True")
print("  つまりスキル未入力案件が全部マッチしてしまう")
print()
print("解決策: engineer_queryで必須スキル空案件をスキップ（すでに実装済みだが確認）")
print("  line_webhook/line_query.py の engineer_query内:")
print('  "if not required and gross < 10: continue" ← これが効いているはず')
print()
print("=== 実際の案件数確認 ===")

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
PROJECT_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

# 募集中案件を全取得して鮮度と必須スキル状況を確認
from datetime import date, timedelta

import jpholiday


def business_days_since(dt_str):
    from dateutil import parser as dp

    start = dp.isoparse(dt_str).date()
    today = date.today()
    days = 0
    current = start + timedelta(days=1)
    while current <= today:
        if current.weekday() < 5 and not jpholiday.is_holiday(current):
            days += 1
        current += timedelta(days=1)
    return days


payload = {"page_size": 100, "filter": {"property": "ステータス", "select": {"equals": "募集中"}}}
pages = []
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{PROJECT_DB}/query", headers=headers, json=payload)
    d = r.json()
    pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]

print(f"募集中案件数: {len(pages)}件")
fresh = stale = with_skill = without_skill = 0
for p in pages:
    bd = business_days_since(p.get("last_edited_time", "2020-01-01"))
    req = [o["name"] for o in p.get("properties", {}).get("必要スキル", {}).get("multi_select", [])]
    if bd <= 4:
        fresh += 1
    else:
        stale += 1
    if req:
        with_skill += 1
    else:
        without_skill += 1

print(f"  有効(4営業日以内): {fresh}件")
print(f"  期限切れ(4営業日超): {stale}件")
print(f"  必須スキルあり: {with_skill}件")
print(f"  必須スキルなし: {without_skill}件")
print()
print(f"→ 有効 + スキルあり案件の最大数: 有効{fresh}件のうちスキルありのもの")

# 有効案件のうちスキルありのもの
valid_with_skill = 0
for p in pages:
    bd = business_days_since(p.get("last_edited_time", "2020-01-01"))
    req = [o["name"] for o in p.get("properties", {}).get("必要スキル", {}).get("multi_select", [])]
    if bd <= 4 and req:
        valid_with_skill += 1
print(f"  有効 + スキルあり: {valid_with_skill}件 ← これが本来の上限")
print()
print("=== webhook_server.pyのengineeer_queryに鮮度フィルタがないことを確認 ===")
print("line_webhook/line_query.py: engineer_queryには status=募集中 + 4営業日フィルタが実装済み")
print("しかしSTATUSフィルタが適用されていない（デプロイ前チェックが必要）")
