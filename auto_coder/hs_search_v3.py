# -*- coding: utf-8 -*-
"""HS再検索: Java + 50代OK + 商流OK（上位抜け案件除外）"""

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
print(f"募集中案件(14日): {len(all_proj)}件")


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


def is_age_ng_55(text):
    """55歳NGの年齢制限を検出"""
    if re.search(r"(40代まで|〜40歳|40歳まで|～40代|30代まで|〜39歳|20代〜30代)", text):
        return True
    if re.search(r"(〜45歳|45歳まで)", text):
        return True
    return False


def is_shohryu_ng(text):
    """商流NG: 上位が抜ける案件 = 1社先提案不可"""
    # 「弊社は商流から抜けます」「弊社は抜けます」「弊社抜け」
    if re.search(r"弊社.{0,5}(抜け|外れ)", text):
        return True
    # 「貴社まで」は基本OK（TERRA直提案可）
    # 「貴社プロパー様まで」もTERRA社員ならOK
    return False


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
    "SQL",
]
HS_NG_TECH = ["Python必須", "PHP必須", "Ruby", "Go言語", "Scala", "Kotlin", "組込", "車載", "ECU", "COBOL", "C\\+\\+"]
HS_ALREADY = ["383450ff-37c0-81c6"]  # 既送信の勤怠・給与のみ

print("\n========== HS全候補（Java必須・55-90万・14日） ==========")
hs_all = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    if not re.search(r"Java", full):
        continue
    low, high = extract_price(detail)
    if not high or not (55 <= high <= 90):
        continue
    if any(rec["id"].startswith(a) for a in HS_ALREADY):
        continue
    skip = False
    for ng in HS_NG_TECH:
        if re.search(ng, full):
            skip = True
            break
    if skip:
        continue
    age_ng = is_age_ng_55(full)
    shohryu_ng = is_shohryu_ng(full)
    score = sum(1 for s in HS_WANT if re.search(s, full))
    matches = [s for s in HS_WANT if re.search(s, full)][:6]
    # 50代記載チェック
    age_ok_explicit = bool(re.search(r"(50代|〜50歳|50歳まで|〜55歳|55歳まで|年齢不問|年齢制限.{0,3}(なし|無))", full))
    hs_all.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches,
            "age_ng": age_ng,
            "age_ok_explicit": age_ok_explicit,
            "shohryu_ng": shohryu_ng,
            "created": rec.get("created_time", "")[:10],
        }
    )

hs_all.sort(key=lambda x: (-x["score"], -x["high"]))

# 分類出力
ok = [c for c in hs_all if not c["age_ng"] and not c["shohryu_ng"]]
age_ng_list = [c for c in hs_all if c["age_ng"] and not c["shohryu_ng"]]
sh_ng = [c for c in hs_all if c["shohryu_ng"]]

print(f"\n=== ✅ 年齢OK＋商流OK: {len(ok)}件 ===")
for c in ok:
    age_tag = "★50代明記OK" if c["age_ok_explicit"] else "年齢記載なし"
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]} | {age_tag}")
    print(f"    matches: {c['matches']}")

print(f"\n=== ⚠️ 40代まで（チャレンジ枠）: {len(age_ng_list)}件 ===")
for c in age_ng_list[:5]:
    print(f"\n  [{c['low']}-{c['high']}万 score={c['score']} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")

print(f"\n=== ❌ 商流NG（上位抜け）: {len(sh_ng)}件 ===")
for c in sh_ng[:3]:
    print(f"\n  [{c['low']}-{c['high']}万] {c['title']}")
