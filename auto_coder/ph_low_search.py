# -*- coding: utf-8 -*-
"""PH: 48万以下全案件検索（内容問わず） + Notionサマリー技術欄更新"""

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
PH_PAGE_ID = "37c450ff-37c0-81ed-afa7-cbf210c027af"

# ========== 1. サマリー技術欄更新 ==========
print("=== 1. PHサマリー更新 ===")
NEW_SUMMARY = """【氏　名】P.H（27歳女性）
【所　属】弊社社員
【稼　動】7月～
【最寄駅】京成小岩
【経　験】設計支援、開発、単体結合テスト、PMO支援
【技　術】PHP / Laravel / JavaScript / HTML / CSS / MySQL / Linux / Git / GitHub / Excel / Word / Outlook / Teams
【単　価】40万円(相談可)
【面　談】並行営業中（面談設定無し）
【備　考】韓国籍ですが、日本育ちのため日本語はネイティブです。"""

chunks = [{"type": "text", "text": {"content": NEW_SUMMARY}}]
body = {
    "properties": {
        "人員情報原文": {"rich_text": chunks},
        "スキル": {
            "multi_select": [
                {"name": "PMO"},
                {"name": "PHP"},
                {"name": "JavaScript"},
                {"name": "MySQL"},
                {"name": "Laravel"},
                {"name": "HTML/CSS"},
                {"name": "Git"},
                {"name": "Linux"},
                {"name": "Excel"},
                {"name": "Word"},
            ]
        },
    }
}
r = requests.patch(f"https://api.notion.com/v1/pages/{PH_PAGE_ID}", headers=HEADERS, json=body, timeout=30)
print(f"  PATCH: {r.status_code}")

# ========== 2. 48万以下全案件検索（14日、内容問わず） ==========
print("\n=== 2. 48万以下 全案件（14日・内容問わず） ===")
since = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT00:00:00.000Z")
url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
all_proj, cursor = [], None
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
print(f"  募集中(14日): {len(all_proj)}件")


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


# 外国籍チェック
def foreign_check(text):
    if re.search(r"外国籍[\s：:]*不可|外国籍\s*NG", text):
        return "不可"
    if re.search(r"外国籍[\s：:]*可|外国籍\s*OK", text):
        return "可"
    return "記載なし"


# 48万以下の全案件
candidates = []
for rec in all_proj:
    title, detail = get_text(rec)
    full = title + " " + detail
    low, high = extract_price(detail)
    if not high:
        continue
    if high > 48:
        continue
    foreign = foreign_check(full)
    # PHスキルマッチスコア
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
    ]
    score = sum(1 for kw in PH_KW if re.search(kw, full, re.IGNORECASE))
    matches = [kw for kw in PH_KW if re.search(kw, full, re.IGNORECASE)][:8]
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "score": score,
            "matches": matches,
            "foreign": foreign,
            "created": rec.get("created_time", "")[:10],
        }
    )

candidates.sort(key=lambda x: (-x["score"], -x["high"]))
print(f"\n  48万以下: {len(candidates)}件\n")
for c in candidates:
    tag = "🔴不可" if c["foreign"] == "不可" else ("🟢可" if c["foreign"] == "可" else "⚪")
    print(f"  [{c['low']}-{c['high']}万 score={c['score']} {tag} {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    matches: {c['matches']}")
