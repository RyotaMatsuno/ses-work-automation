# -*- coding: utf-8 -*-
"""PH: PHP/Laravel/JS特化で再検索(単価35-65万) + HS: 年齢OK3件の詳細"""

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

since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00.000Z")
url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
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
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    data = r.json()
    all_proj.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data.get("next_cursor")


def get_text(rec):
    props = rec.get("properties", {})
    title = ""
    for k, v in props.items():
        if v.get("type") == "title":
            title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
    detail = ""
    for k, v in props.items():
        if "詳細" in k and v.get("type") == "rich_text":
            detail = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
    return title, detail


def extract_price(text):
    patterns = [
        r"(\d{2,3})\s*[万円]+[\s〜~−\-]*(\d{2,3})\s*万",
        r"(\d{2,3})\s*万[\s〜~−\-]+(\d{2,3})\s*万",
        r"〜\s*(\d{2,3})\s*万",
        r"(\d{2,3})\s*万[円前]",
        r"(\d{2,3})万",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            g = m.groups()
            if len(g) >= 2 and g[1]:
                return int(g[0]), int(g[1])
            return int(g[0]), int(g[0])
    return None, None


# ========== PH: PHP/Laravel/JS特化（単価35-65万、NG技術除外） ==========
print("========== PH: PHP/Laravel/JS/MySQL/Web特化 (35-65万) ==========")
PH_CORE = ["PHP", "Laravel", "JavaScript", "MySQL", "HTML", "CSS", "フロントエンド", "バックエンド"]
PH_BONUS = ["PMO", "テスト", "詳細設計", "支援", "PG", "ウェブ", "Web開発"]
PH_NG = [
    "Java.*5年",
    "Java.*3年以上",
    "COBOL",
    "C\\+\\+",
    "Python必須",
    "Django",
    "Ruby",
    "Go言語",
    "SAP",
    "ABAP",
    "Salesforce",
    "ネットワーク",
    "インフラ",
    "組込",
    "車載",
    "AWS.*設計構築",
    "要件定義.*3年",
    "PM.*5年",
    "PL.*3年",
    "リーダー必須",
    "PL/SQL.*必須",
    "Oracle.*必須",
    "RPA",
    "UiPath",
    "JP1",
]

ph_cands = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    low, high = extract_price(detail)
    if not high or not (35 <= high <= 65):
        continue
    # コアスキル1個以上
    core_hit = sum(1 for s in PH_CORE if re.search(s, full, re.IGNORECASE))
    if core_hit == 0:
        continue
    # NG除外
    skip = False
    for ng in PH_NG:
        if re.search(ng, full, re.IGNORECASE):
            skip = True
            break
    if skip:
        continue
    bonus = sum(1 for s in PH_BONUS if re.search(s, full, re.IGNORECASE))
    core_matches = [s for s in PH_CORE if re.search(s, full, re.IGNORECASE)]
    ph_cands.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "core": core_hit,
            "bonus": bonus,
            "total": core_hit + bonus,
            "core_matches": core_matches,
            "created": rec.get("created_time", "")[:10],
        }
    )

ph_cands.sort(key=lambda x: (-x["total"], -x["high"]))
print(f"候補: {len(ph_cands)}件")
for c in ph_cands[:15]:
    print(f"\n  [{c['low']}-{c['high']}万 core={c['core']} bonus={c['bonus']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    core_matches: {c['core_matches']}")

# ========== HS: 年齢OK候補の詳細取得 ==========
print("\n\n========== HS: 年齢OK候補 詳細 ==========")
HS_DETAILS = [
    ("37f450ff-37c0-81e0-9fe3-ec56edd00ffb", "証拠金取引ストレステスト 75万"),
    ("380450ff-37c0-81bb-b3e1-c372f76e2693", "PL/SQL技術者 63万"),
]
for pid, label in HS_DETAILS:
    print(f"\n--- {label} (page_id: {pid[:36]}) ---")
    r = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if r.status_code != 200:
        continue
    detail = "".join(
        [t.get("plain_text", "") for t in r.json().get("properties", {}).get("案件詳細", {}).get("rich_text", [])]
    )
    print(detail[:1500])
