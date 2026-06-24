# -*- coding: utf-8 -*-
"""PH新1位の詳細 + HS北小金見落とし案件チェック"""

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
DB_PROJ = "343450ff-37c0-81e4-934e-f25f90284a3c"

# 1. PH新1位の詳細
print("=== PH新1位: 経費精算SaaS 詳細 ===")
r = requests.get("https://api.notion.com/v1/pages/380450ff-37c0-818e-9403-dde801f332f2", headers=HEADERS, timeout=20)
detail = "".join(
    [t.get("plain_text", "") for t in r.json().get("properties", {}).get("案件詳細", {}).get("rich_text", [])]
)
print(detail[:2000])

# 2. HS北小金 マッチング
# スキル: Web系Java, 基本設計〜製造〜運用保守, 26年経験
# 単価想定: 60-80万くらい(26年経験で高単価可)
print("\n\n=== HS北小金 マッチング ===")
HS_MUST = ["Java"]
HS_NICE = [
    "Spring",
    "SpringBoot",
    "Web",
    "WEB",
    "ウェブ",
    "基本設計",
    "詳細設計",
    "製造",
    "運用保守",
    "保守",
    "JSP",
    "Servlet",
    "Tomcat",
]
HS_NG = ["COBOL", "C\\+\\+", "Python", "PHP", "Ruby", "Go", "Scala", "Kotlin", "組込", "車載", "ECU"]
# 既送信案件のid
SENT = ["勤怠", "給与"]  # タイトル除外用

url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
since = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT00:00:00.000Z")
all_proj, cursor = [], None
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
    rr = requests.post(url, headers=HEADERS, json=body, timeout=30)
    data = rr.json()
    all_proj.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")
print(f"  募集中案件: {len(all_proj)}件")


def extract_price(text):
    # 〜80万 / 80万まで / 75-80万 / 単価:78万 など
    m = re.search(r"単[価金][^0-9]{0,5}(\d{2,3})\s*[~〜\-\−]\s*(\d{2,3})\s*万", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"単[価金][^0-9]{0,5}(\d{2,3})\s*万", text)
    if m:
        return int(m.group(1)), int(m.group(1))
    m = re.search(r"(\d{2,3})\s*万[\s〜~−\-]\s*(\d{2,3})\s*万", text)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.search(r"〜\s*(\d{2,3})\s*万", text)
    if m:
        return int(m.group(1)), int(m.group(1))
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
    full = title + " | " + detail
    # 必須Java
    if not re.search(r"Java", full):
        continue
    # NG除外
    skip = False
    for ng in HS_NG:
        if re.search(ng, full):
            skip = True
            break
    if skip:
        continue
    # 単価チェック
    low, high = extract_price(detail)
    if not high or not (55 <= high <= 90):
        continue
    # 勤怠・給与(=既送信)はマーク
    already_sent = any(s in title for s in SENT)
    # スコア計算
    score = 0
    matches = []
    for n in HS_NICE:
        if re.search(n, full):
            score += 1
            matches.append(n)
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:90],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches[:6],
            "already_sent": already_sent,
        }
    )

candidates.sort(key=lambda x: (-x["score"], -x["high"]))
print(f"\n=== HS北小金 候補(Java必須, 55-90万): {len(candidates)}件 ===")
for c in candidates[:12]:
    flag = "🔵已送信" if c["already_sent"] else ""
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']}] {flag} {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")
