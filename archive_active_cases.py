# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def npatch(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def gtxt(p):
    if not p:
        return ""
    t = p.get("type", "")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", []))
    return ""


# 稼働中10件を全部アーカイブ（削除）
print("=== 稼働中案件をアーカイブ ===")
res = npost(
    f"databases/{CASE_DB}/query",
    {"filter": {"property": "ステータス", "select": {"equals": "稼働中"}}, "page_size": 20},
)
pages = res.get("results", [])
print(f"対象: {len(pages)}件")

for page in pages:
    name = gtxt(page["properties"].get("案件名", {}))
    try:
        npatch(f"pages/{page['id']}", {"archived": True})
        print(f"  削除: {name[:40]}")
    except Exception as e:
        print(f"  エラー: {name[:30]} → {e}")

print(f"\n完了: {len(pages)}件をアーカイブ")
