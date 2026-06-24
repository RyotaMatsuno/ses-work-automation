# -*- coding: utf-8 -*-
"""
1. PHさんサマリー書き換え＋Notion更新
2. PHさん再マッチ(外国籍不問、スキル拡張版)
3. HS北小金検索
"""

import re
import sys

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from datetime import datetime, timedelta

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}
DB_ENG = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
DB_PROJ = "343450ff-37c0-81e4-934e-f25f90284a3c"

PH_PAGE_ID = "37c450ff-37c0-81ed-afa7-cbf210c027af"

# ========== 1. PHさんサマリー書き換え ==========
NEW_SUMMARY = """【LINE auto-register: matsuno】
【氏　名】P.H（27歳女性）
【所　属】弊社社員（TERRA）
【稼　動】2026年7月～
【最寄駅】京成小岩（京成線・東京都葛飾区）
【経　歴】
　・PMO支援＋テスト（25/6-26/6, 1年）
　　WBS・議事録・タスク管理／テスト計画・移行計画／エビデンス整理／リリース資料／インシデント対応／新人教育資料
　・在庫管理システム開発（24/6-25/5, 1年）★開発実績
　　設計（テーブル定義／詳細設計読み込み）＋コーディング バック・フロント約20画面
　　メール送信機能、CSV取込、PDF出力、勤怠管理画面、フォーム作成、軽微改修
　　単体テスト＋結合テスト
　・化学業界 研究用試薬の製造・品質試験（23/2-24/5, 1.3年）※前職、薬学部卒
【技　術】PHP / JavaScript / HTML/CSS / MySQL / Laravel / Git / GitHub / Linux / Excel / Word / Teams / Outlook
【経験工程】設計支援、Web系バック&フロント開発（PHP/Laravel/JS）、単体・結合テスト、PMO支援
【単　価】40万円（相談可）
【面　談】並行営業中（面談設定無し）
【備　考】韓国籍ですが、日本育ちのため日本語はネイティブです。
#skill_skip
"""

# PHさんの「人員情報原文」プロパティを更新
print("=== Step 1: PHさんサマリー更新 ===")
chunks = []
for i in range(0, len(NEW_SUMMARY), 2000):
    chunks.append({"type": "text", "text": {"content": NEW_SUMMARY[i : i + 2000]}})

body = {"properties": {"人員情報原文": {"rich_text": chunks}}}
# スキルも更新(multi_select)
body["properties"]["スキル"] = {
    "multi_select": [
        {"name": "PMO"},
        {"name": "PHP"},
        {"name": "JavaScript"},
        {"name": "MySQL"},
        {"name": "Laravel"},
        {"name": "HTML/CSS"},
        {"name": "Git"},
        {"name": "Linux"},
    ]
}
r = requests.patch(f"https://api.notion.com/v1/pages/{PH_PAGE_ID}", headers=HEADERS, json=body, timeout=30)
print(f"  PATCH status: {r.status_code}")
if r.status_code != 200:
    print(f"  Error: {r.text[:500]}")

# ========== 2. 案件DBから再マッチ(外国籍不問・スキル拡張) ==========
print("\n=== Step 2: 募集中案件(5日以内) 取得 ===")
url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
since = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00.000Z")
all_proj = []
cursor = None
while True:
    qbody = {
        "filter": {
            "and": [
                {"property": "ステータス", "select": {"equals": "募集中"}},
                {"timestamp": "created_time", "created_time": {"on_or_after": since}},
            ]
        },
        "page_size": 100,
    }
    if cursor:
        qbody["start_cursor"] = cursor
    rr = requests.post(url, headers=HEADERS, json=qbody, timeout=30)
    data = rr.json()
    all_proj.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  募集中案件: {len(all_proj)}件")

# スキル拡張版マッチ
PH_SKILLS = [
    "PHP",
    "Laravel",
    "JavaScript",
    "JS",
    "MySQL",
    "HTML",
    "CSS",
    "Linux",
    "PMO",
    "テスト",
    "結合テスト",
    "単体テスト",
    "Web",
    "WEB",
    "ウェブ",
    "詳細設計",
    "テーブル設計",
    "支援",
    "アシスタント",
]
PH_NG = [
    "COBOL",
    "C++",
    "C\\+\\+",
    "組込",
    "組み込み",
    "ECU",
    "車載",
    "Java\\s*(5|6|7|8|10)年以上",
    "Java\\s*(５|６|７|８)年以上",
]


def extract_price(text):
    m = re.search(r"(\d{2,3})\s*[万円]+[\s〜~−\-]*(\d{2,3})?", text)
    if m:
        return int(m.group(1)), int(m.group(2)) if m.group(2) else int(m.group(1))
    return None, None


candidates = []
for rec in all_proj:
    props = rec.get("properties", {})
    title = ""
    for k, v in props.items():
        if v.get("type") == "title":
            title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
    detail = ""
    for k, v in props.items():
        if "詳細" in k and v.get("type") == "rich_text":
            detail = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
    low, high = extract_price(detail)
    if not high or not (35 <= high <= 65):
        continue
    # NGワード除外
    skip = False
    for ng in PH_NG:
        if re.search(ng, detail) or re.search(ng, title):
            skip = True
            break
    if skip:
        continue
    # スキルマッチスコア
    score = 0
    matches = []
    for sk in PH_SKILLS:
        if re.search(sk, detail) or re.search(sk, title):
            score += 1
            matches.append(sk)
    if score == 0:
        continue
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches[:8],
            "detail_snippet": detail[:300],
        }
    )

candidates.sort(key=lambda x: (-x["score"], -x["high"]))
print("\n=== PH再マッチ候補(外国籍不問、スキル拡張): TOP10 ===")
for c in candidates[:10]:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")

# ========== 3. HS北小金 検索 ==========
print("\n=== Step 3: HS北小金検索 ===")
url2 = f"https://api.notion.com/v1/databases/{DB_ENG}/query"
all_eng = []
cursor = None
while True:
    qbody = {"page_size": 100}
    if cursor:
        qbody["start_cursor"] = cursor
    rr = requests.post(url2, headers=HEADERS, json=qbody, timeout=30)
    data = rr.json()
    all_eng.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  Total engineers: {len(all_eng)}")

# HS北小金 を検索
hs_matched = []
for rec in all_eng:
    props = rec.get("properties", {})
    text = ""
    for k, v in props.items():
        t = v.get("type")
        if t == "title":
            text += "".join([x.get("plain_text", "") for x in v.get("title", [])]) + " | "
        elif t == "rich_text":
            text += "".join([x.get("plain_text", "") for x in v.get("rich_text", [])]) + " | "
    if "北小金" in text or re.search(r"\bHS\b", text):
        hs_matched.append((rec, text))

print(f"  Matched: {len(hs_matched)}")
for rec, txt in hs_matched[:3]:
    print(f"\n  --- page_id={rec['id'][:36]} ---")
    print(f"  text: {txt[:800]}")
