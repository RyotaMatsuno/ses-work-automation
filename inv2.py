import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
import re

import requests
from dotenv import dotenv_values

config = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = config.get("NOTION_TOKEN") or config.get("NOTION_API_KEY")
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

# 備考フィールドの実際のフォーマットを全件確認
payload = {"page_size": 100}
pages = []
while True:
    r = requests.post(f"https://api.notion.com/v1/databases/{ENG_DB}/query", headers=headers, json=payload, timeout=15)
    d = r.json()
    pages.extend(d.get("results", []))
    if not d.get("has_more"):
        break
    payload["start_cursor"] = d["next_cursor"]


def gtext(p, key):
    prop = p.get("properties", {}).get(key, {})
    pt = prop.get("type")
    if pt == "title":
        return "".join(t.get("plain_text", "") for t in prop.get("title", []))
    if pt == "rich_text":
        return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
    if pt == "email":
        return prop.get("email", "") or ""
    if pt == "select":
        return (prop.get("select") or {}).get("name", "")
    return ""


print("=== 備考フィールドのフォーマット調査（全件） ===")
print()

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
SENDER_RE = re.compile(r"(?:送信者|送信元|From)[:\s：]+(.+)")

for p in pages:
    name = gtext(p, "名前")
    ini = gtext(p, "イニシャル") or "?"
    memo = gtext(p, "備考（LINEメモ）")
    affil = gtext(p, "所属会社")

    # 備考から送信者情報を抽出
    sender_match = SENDER_RE.search(memo) if memo else None
    email_match = EMAIL_RE.search(memo) if memo else None

    print(f"[{ini} / {name[:15]}]")
    print(f"  所属会社: [{affil[:30] if affil else '空'}]")

    if sender_match:
        print(f"  備考-送信者: {sender_match.group(1)[:60]}")
    if email_match:
        print(f"  備考-メール: {email_match.group(0)}")

    # 備考の先頭200文字
    if memo:
        print(f"  備考先頭: {memo[:120].replace(chr(10), ' / ')}")
    print()
