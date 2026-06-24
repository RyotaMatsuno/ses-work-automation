# -*- coding: utf-8 -*-
"""IMAP候補2件がDBに入ってるか確認 + 未登録なら本文取得"""

import email
import imaplib
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

# 1. DB検索: 件名キーワードで確認
KEYWORDS = ["サーバサイド開発5年", "損保PMO", "八丁堀"]
print("=== DB keyword search ===")
for kw in KEYWORDS:
    url = f"https://api.notion.com/v1/databases/{DB_PROJ}/query"
    body = {
        "filter": {
            "or": [
                {"property": "案件名", "title": {"contains": kw}},
                {"property": "案件詳細", "rich_text": {"contains": kw}},
            ]
        },
        "page_size": 5,
    }
    r = requests.post(url, headers=HEADERS, json=body, timeout=30)
    results = r.json().get("results", [])
    print(f"  '{kw}': {len(results)}件")
    for rec in results:
        props = rec.get("properties", {})
        title = ""
        for k, v in props.items():
            if v.get("type") == "title":
                title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
        status = ""
        for k, v in props.items():
            if "ステータス" in k:
                sel = v.get("select") or v.get("status")
                if sel:
                    status = sel.get("name", "")
        print(f"    [{status}] {title[:60]} | page_id={rec['id'][:36]}")

# 2. IMAP: 2件の本文を直接取得
print("\n=== IMAP: 候補メール本文取得 ===")
IMAP_HOST = "mail65.onamae.ne.jp"
addr = "sessales@terra-ltd.co.jp"
pw = env.get("SESSALES_PASSWORD")
since_imap = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")

SEARCH_SUBJECTS = [
    "Javaでのサーバサイド開発5年以上",
    "損保PMO案件",
]

try:
    M = imaplib.IMAP4_SSL(IMAP_HOST, 993, timeout=30)
    M.login(addr, pw)
    M.select("INBOX", readonly=True)
    typ, data = M.search(None, f"(SINCE {since_imap})")
    ids = data[0].split()
    check_ids = ids[-200:]

    for search_subj in SEARCH_SUBJECTS:
        print(f"\n--- Searching: '{search_subj}' ---")
        for mid in reversed(check_ids):
            typ2, msg_data = M.fetch(mid, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
            if typ2 != "OK":
                continue
            raw_h = msg_data[0][1]
            msg_h = email.message_from_bytes(raw_h)
            subj_parts = decode_header(msg_h.get("Subject", ""))
            subj = ""
            for part, enc in subj_parts:
                if isinstance(part, bytes):
                    subj += part.decode(enc or "utf-8", errors="replace")
                else:
                    subj += part
            if search_subj not in subj:
                continue

            # 本文取得
            print(f"  Found! Subject: {subj[:100]}")
            typ3, full_data = M.fetch(mid, "(RFC822)")
            if typ3 != "OK":
                continue
            full_msg = email.message_from_bytes(full_data[0][1])
            body_text = ""
            if full_msg.is_multipart():
                for part in full_msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain":
                        payload = part.get_payload(decode=True)
                        charset = part.get_content_charset() or "utf-8"
                        body_text = payload.decode(charset, errors="replace")
                        break
            else:
                payload = full_msg.get_payload(decode=True)
                charset = full_msg.get_content_charset() or "utf-8"
                body_text = payload.decode(charset, errors="replace")
            print("  Body (first 2000 chars):")
            print(body_text[:2000])
            break
        else:
            print("  Not found in last 200 mails")

    M.logout()
except Exception as e:
    print(f"IMAP ERROR: {e}")
