# -*- coding: utf-8 -*-
"""HS: フィルタ最小で全候補出し（Java+70万+14日のみ）"""

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


HS_ALREADY = ["383450ff-37c0-81c6"]

# Java+70万以上 フィルタのみ。NG_TECHなし
print(f"募集中(14日): {len(all_proj)}件")
print("\n=== Java + 70万以上 全件（フィルタ最小）===\n")
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
    # 年齢検出
    age = "記載なし"
    am = re.search(r"(\d{2})代(まで|迄)", full)
    if am:
        age = f"{am.group(1)}代まで"
    am2 = re.search(r"(\d{2})歳(まで|迄)", full)
    if am2:
        age = f"{am2.group(1)}歳まで"
    am3 = re.search(r"[〜～](\d{2})(歳|代)", full)
    if am3:
        age = f"〜{am3.group(1)}{am3.group(2)}"
    am4 = re.search(r"(\d{2})\s*[〜～−\-]\s*(\d{2})歳", full)
    if am4:
        age = f"{am4.group(1)}〜{am4.group(2)}歳"
    am5 = re.search(r"年齢不問", full)
    if am5:
        age = "年齢不問"
    am6 = re.search(r"50代", full)
    if am6 and "まで" not in age:
        age = "50代記載あり"
    # 商流
    sh_ng = "NG" if re.search(r"弊社.{0,5}(抜け|外れ)", full) else "OK"
    # 55歳判定
    ok55 = "✅"
    if re.search(r"(40代(まで|迄)|〜40|44歳|45歳(まで|迄))", full):
        ok55 = "❌40代"
    print(f"  {ok55} [{low}-{high}万] 年齢:{age} 商流:{sh_ng} | {title[:60]}")
    print(f"       page_id: {rec['id'][:36]}")
