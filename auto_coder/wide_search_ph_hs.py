# -*- coding: utf-8 -*-
"""PH + HS 拡大検索（鮮度14日・単価レンジ拡大）"""

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

# 募集中 14日以内
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
print(f"募集中案件(14日以内): {len(all_proj)}件")


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
        r"単[価金][^0-9]{0,5}(\d{2,3})\s*[~〜\-−]\s*(\d{2,3})",
        r"(\d{2,3})\s*万[\s〜~−\-]+(\d{2,3})\s*万",
        r"〜\s*(\d{2,3})\s*万",
        r"(\d{2,3})\s*万[円前]",
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            g = m.groups()
            if len(g) >= 2 and g[1]:
                return int(g[0]), int(g[1])
            return int(g[0]), int(g[0])
    return None, None


# ========== PH検索 ==========
# PHスキル: PHP/Laravel/JS/MySQL/HTML/CSS/Web開発/PMO/テスト
# 単価: 35-55万（PHは40万なので案件側45-55万で粗利5万取れる）
# 外国籍: 不問（松野指示）
PH_WANT = [
    "PHP",
    "Laravel",
    "JavaScript",
    "MySQL",
    "HTML",
    "CSS",
    "Web",
    "WEB",
    "PMO",
    "テスト",
    "結合テスト",
    "詳細設計",
    "開発支援",
    "支援",
    "PG",
    "フロント",
    "バック",
    "ウェブ",
]
PH_NG = [
    "COBOL",
    "C\\+\\+",
    "組込",
    "車載",
    "ECU",
    "SAP",
    "ABAP",
    "Salesforce",
    "ネットワーク",
    "インフラ",
    "サーバ構築",
    "機械学習",
    "AI開発",
]

print("\n========== PH候補（35-55万・14日・外国籍不問） ==========")
ph_cands = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    low, high = extract_price(detail)
    if not high or not (35 <= high <= 55):
        continue
    skip = False
    for ng in PH_NG:
        if re.search(ng, full):
            skip = True
            break
    if skip:
        continue
    score, matches = 0, []
    for sk in PH_WANT:
        if re.search(sk, full, re.IGNORECASE):
            score += 1
            matches.append(sk)
    if score == 0:
        continue
    ph_cands.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches[:8],
            "created": rec.get("created_time", "")[:10],
            "snippet": detail[:200],
        }
    )

ph_cands.sort(key=lambda x: (-x["score"], -x["high"]))
print(f"候補: {len(ph_cands)}件 (TOP15)")
for c in ph_cands[:15]:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")

# ========== HS検索 ==========
# HSスキル: Java, Spring, Web系, 基本設計〜保守, 26年経験
# 単価: 60-85万
# 年齢: 50代OKの案件 → 「40代まで」をNG
HS_MUST = ["Java"]
HS_WANT = [
    "Spring",
    "SpringBoot",
    "Web",
    "WEB",
    "基本設計",
    "詳細設計",
    "製造",
    "運用保守",
    "保守",
    "業務システム",
    "エンハンス",
    "改修",
    "JSP",
    "Servlet",
    "Tomcat",
    "PostgreSQL",
    "Oracle",
]
HS_NG_TECH = [
    "Python必須",
    "PHP必須",
    "Ruby",
    "Go言語",
    "Scala",
    "Kotlin",
    "組込",
    "車載",
    "ECU",
    "COBOL",
    "C\\+\\+",
    "React必須",
    "Vue.js必須",
]
HS_ALREADY = ["383450ff-37c0-81c6", "380450ff-37c0-81cd"]  # 既出の勤怠・証券代行

print("\n\n========== HS候補（Java必須・60-85万・14日・年齢50代OK） ==========")
hs_cands = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    if not re.search(r"Java", full):
        continue
    low, high = extract_price(detail)
    if not high or not (60 <= high <= 85):
        continue
    # 既出除外
    if any(rec["id"].startswith(a) for a in HS_ALREADY):
        continue
    # 技術NG
    skip = False
    for ng in HS_NG_TECH:
        if re.search(ng, full):
            skip = True
            break
    if skip:
        continue
    # 年齢チェック（40代までNG）
    age_ng = bool(re.search(r"(40代まで|〜40歳|40歳まで|～40代|30代まで|〜39歳|20代〜30代)", full))
    score, matches = 0, []
    for sk in HS_WANT:
        if re.search(sk, full):
            score += 1
            matches.append(sk)
    hs_cands.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches[:8],
            "age_ng": age_ng,
            "created": rec.get("created_time", "")[:10],
            "snippet": detail[:200],
        }
    )

hs_cands.sort(key=lambda x: (-x["score"], -x["high"]))
print(f"候補: {len(hs_cands)}件")
print("\n--- 年齢制限なし（50代OK） ---")
ok = [c for c in hs_cands if not c["age_ng"]]
print(f"  {len(ok)}件")
for c in ok[:10]:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")

print("\n--- 40代まで（チャレンジ枠） ---")
ng = [c for c in hs_cands if c["age_ng"]]
print(f"  {len(ng)}件")
for c in ng[:5]:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")
