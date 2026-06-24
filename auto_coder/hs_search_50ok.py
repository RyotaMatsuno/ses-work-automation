# -*- coding: utf-8 -*-
"""HS再検索: 50代まで=OK で再フィルタ（14日間全件）"""

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
print(f"募集中(14日): {len(all_proj)}件")


def get_text(rec):
    props = rec.get("properties", {})
    title, detail = "", ""
    for k, v in props.items():
        if v.get("type") == "title":
            title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
        if "詳細" in k and v.get("type") == "rich_text":
            detail = "".join([t.get("plain_text", "") for t in v.get("rich_text", [])])
    return title, detail


def extract_price(text):
    for p in [
        r"(\d{2,3})\s*[万円]+[\s〜~−\-]*(\d{2,3})\s*万",
        r"(\d{2,3})\s*万[\s〜~−\-]+(\d{2,3})\s*万",
        r"〜\s*(\d{2,3})\s*万",
        r"(\d{2,3})\s*万[円前]",
        r"(\d{2,3})万",
    ]:
        m = re.search(p, text)
        if m:
            g = m.groups()
            return (int(g[0]), int(g[1])) if len(g) >= 2 and g[1] else (int(g[0]), int(g[0]))
    return None, None


def age_status_55(text):
    """55歳(50代)が通るかどうか判定"""
    # 明確にNG
    if re.search(r"(40代まで|40代迄|〜40歳|40歳まで|～40代|〜39歳|20代〜30代)", text):
        return "NG_40代"
    if re.search(r"(44歳まで|45歳まで|〜44歳|〜45歳|45歳迄)", text):
        return "NG_45歳"
    # 50代OK
    if re.search(r"(50代まで|50代迄|〜50代|〜59歳|30.{0,3}50歳|50歳まで)", text):
        return "OK_50代"
    # 年齢不問
    if re.search(r"(年齢不問|年齢.{0,3}(なし|無|不問))", text):
        return "OK_不問"
    # 記載なし
    return "OK_記載なし"


HS_ALREADY = ["383450ff-37c0-81c6"]
HS_NG_TECH = [
    "COBOL",
    "C\\+\\+",
    "組込",
    "車載",
    "ECU",
    "Python必須",
    "PHP必須",
    "Ruby",
    "Go言語",
    "Vue.js",
    "React必須",
    "TypeScript.*3年",
    "NewRelic",
    "Zabbix",
    "PL/SQL",
    "PMO.*3年",
]

candidates = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    if not re.search(r"Java", full):
        continue
    low, high = extract_price(detail)
    if not high or high < 70:
        continue
    if any(rec["id"].startswith(a) for a in HS_ALREADY):
        continue
    skip = False
    for ng in HS_NG_TECH:
        if re.search(ng, full, re.IGNORECASE):
            skip = True
            break
    if skip:
        continue
    age = age_status_55(full)
    sh_ng = bool(re.search(r"弊社.{0,5}(抜け|外れ)", full))
    score = sum(
        1
        for s in [
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
            "PostgreSQL",
            "Oracle",
            "SQL",
            "Thymeleaf",
        ]
        if re.search(s, full)
    )
    matches = [
        s
        for s in [
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
            "PostgreSQL",
            "Oracle",
            "SQL",
            "Thymeleaf",
        ]
        if re.search(s, full)
    ][:8]
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches,
            "age": age,
            "sh_ng": sh_ng,
            "created": rec.get("created_time", "")[:10],
        }
    )

candidates.sort(key=lambda x: (-x["score"], -x["high"]))

# 55歳OKの案件だけ
ok = [c for c in candidates if c["age"].startswith("OK") and not c["sh_ng"]]
ng_age = [c for c in candidates if c["age"].startswith("NG") and not c["sh_ng"]]
ng_sh = [c for c in candidates if c["sh_ng"]]

print(f"\n=== ✅ 55歳OK + 商流OK: {len(ok)}件 ===")
for c in ok:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]} | 年齢: {c['age']}")
    print(f"    matches: {c['matches']}")

print(f"\n=== ❌ 40代まで等: {len(ng_age)}件 ===")
for c in ng_age:
    print(f"  [{c['low']}-{c['high']}万 {c['age']}] {c['title']}")

print(f"\n=== ❌ 商流NG: {len(ng_sh)}件 ===")
for c in ng_sh:
    print(f"  [{c['low']}-{c['high']}万] {c['title']}")
