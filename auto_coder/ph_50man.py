# -*- coding: utf-8 -*-
"""PH: 50万以下全案件（内容問わず・14日）"""

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


def foreign_check(text):
    if re.search(r"外国籍[\s：:]*不可|外国籍\s*NG", text):
        return "不可"
    if re.search(r"外国籍[\s：:]*可|外国籍\s*OK|日本語.{0,20}(ネイティブ|問題).{0,10}可", text):
        return "可"
    return "記載なし"


def sh_check(text):
    if re.search(r"弊社.{0,5}(抜け|外れ)", text):
        return "NG"
    return "OK"


# PH向けスキルマッチ
PH_KW = [
    "PHP",
    "Laravel",
    "JavaScript",
    "JS",
    "MySQL",
    "HTML",
    "CSS",
    "Web",
    "WEB",
    "PMO",
    "テスト",
    "ヘルプデスク",
    "事務",
    "サポート",
    "支援",
    "運用",
    "Excel",
    "データ入力",
    "マニュアル",
    "ドキュメント",
    "フロント",
    "開発",
    "設計",
    "PG",
    "プログラマ",
]

candidates = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    low, high = extract_price(detail)
    if not high or high > 50:
        continue
    foreign = foreign_check(full)
    sh = sh_check(full)
    score = sum(1 for kw in PH_KW if re.search(kw, full, re.IGNORECASE))
    matches = [kw for kw in PH_KW if re.search(kw, full, re.IGNORECASE)][:10]
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches,
            "foreign": foreign,
            "sh": sh,
            "created": rec.get("created_time", "")[:10],
        }
    )

candidates.sort(key=lambda x: (-x["score"], -x["high"]))
print(f"\n50万以下: {len(candidates)}件\n")
for c in candidates:
    ftag = "🔴外NG" if c["foreign"] == "不可" else ("🟢外OK" if c["foreign"] == "可" else "⚪")
    shtag = " 商流NG" if c["sh"] == "NG" else ""
    print(f"  [{c['low']}-{c['high']}万 score={c['score']} {ftag}{shtag} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")
