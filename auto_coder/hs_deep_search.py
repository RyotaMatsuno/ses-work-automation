# -*- coding: utf-8 -*-
"""HS: DB検索(3日・Java・70万以上) + メール直接IMAP検索"""

import email
import imaplib
import re
import sys
from email.header import decode_header

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

# ========== 1. DB検索: 3日間・Java・70万以上 ==========
print("========== DB検索: 3日間・Java・70万以上・年齢制限なし・商流OK ==========")
since = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%dT00:00:00.000Z")
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
print(f"  募集中(3日以内): {len(all_proj)}件")


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


HS_ALREADY = ["383450ff-37c0-81c6"]  # 勤怠・給与(既送信)
HS_NG_TECH = ["COBOL", "C\\+\\+", "組込", "車載", "ECU", "Python必須", "PHP必須", "Ruby", "Go言語"]

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
        if re.search(ng, full):
            skip = True
            break
    if skip:
        continue
    # 年齢NG
    age_ng = bool(re.search(r"(40代まで|40代迄|〜40歳|40歳まで|～40代|30代まで|〜45歳|45歳まで)", full))
    # 商流NG
    sh_ng = bool(re.search(r"弊社.{0,5}(抜け|外れ)", full))
    candidates.append(
        {
            "id": rec["id"],
            "title": title[:80],
            "low": low,
            "high": high,
            "age_ng": age_ng,
            "sh_ng": sh_ng,
            "created": rec.get("created_time", "")[:16],
            "snippet": detail[:300],
        }
    )

print(f"\n  Java+70万以上+3日以内: {len(candidates)}件")
print("\n--- ✅ 年齢OK+商流OK ---")
ok = [c for c in candidates if not c["age_ng"] and not c["sh_ng"]]
for c in ok:
    print(f"\n  [{c['low']}-{c['high']}万 {c['created']}] {c['title']}")
    print(f"    page_id: {c['id'][:36]}")
    print(f"    snippet: {c['snippet'][:200]}")

print("\n--- ⚠️ 40代まで(チャレンジ) ---")
age_ng = [c for c in candidates if c["age_ng"] and not c["sh_ng"]]
for c in age_ng:
    print(f"  [{c['low']}-{c['high']}万] {c['title']}")

print("\n--- ❌ 商流NG ---")
sh_ng = [c for c in candidates if c["sh_ng"]]
for c in sh_ng:
    print(f"  [{c['low']}-{c['high']}万] {c['title']}")

# ========== 2. IMAP: 直近3日のJava案件メール件名チェック ==========
print("\n\n========== IMAP: 直近3日のJava+70万メール件名スキャン ==========")
IMAP_HOST = "mail65.onamae.ne.jp"
ACCOUNTS = [
    ("sessales@terra-ltd.co.jp", env.get("SESSALES_PASSWORD")),
    ("r-matsuno@terra-ltd.co.jp", env.get("MATSUNO_PASSWORD")),
]

since_imap = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
found_subjects = []

for addr, pw in ACCOUNTS:
    if not pw:
        print(f"  {addr}: password not found, skip")
        continue
    try:
        M = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=30)
        M.login(addr, pw)
        M.select("INBOX", readonly=True)
        typ, data = M.search(None, f"(SINCE {since_imap})")
        if typ != "OK":
            print(f"  {addr}: search failed")
            M.logout()
            continue
        ids = data[0].split()
        print(f"  {addr}: {len(ids)} mails since {since_imap}")
        # 最新200件のsubjectだけ取得
        check_ids = ids[-200:] if len(ids) > 200 else ids
        java_mails = []
        for mid in check_ids:
            typ2, msg_data = M.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if typ2 != "OK":
                continue
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)
            subj_parts = decode_header(msg.get("Subject", ""))
            subj = ""
            for part, enc in subj_parts:
                if isinstance(part, bytes):
                    subj += part.decode(enc or "utf-8", errors="replace")
                else:
                    subj += part
            # Java + 70万以上のキーワード
            if re.search(r"Java", subj, re.IGNORECASE) and re.search(r"(7[0-9]万|8[0-9]万|75|78|80|85)", subj):
                java_mails.append(subj[:120])
        print(f"    Java+70万候補: {len(java_mails)}件")
        for s in java_mails[-10:]:
            print(f"      {s}")
        M.logout()
    except Exception as e:
        print(f"  {addr}: ERROR {e}")
