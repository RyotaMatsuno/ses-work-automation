# -*- coding: utf-8 -*-
"""SBT 6件を「終了」化"""

import sys
import time

import requests

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

TARGETS = [
    ("37f450ff-37c0-8194-b7b5-e24bcf02b9c7", "Prisma Access設計構築"),
    ("37f450ff-37c0-818e-a95b-f605e9979af2", "建設業向けのERPパッケージ導入(会計領域)"),
    ("37f450ff-37c0-8163-89a4-cfac4b3f4ace", "テスト、ヘルプデスク、運用保守、データ移行@南行徳"),
    ("37f450ff-37c0-8183-b755-cd04a44260e1", "AWS案件/運用ツール構築/運用自動化@五反田"),
    ("37f450ff-37c0-812e-b8a1-c14418fe9aa7", "AWS案件/運用ツール構築/運用自動化"),
    ("37f450ff-37c0-811a-bdc6-fdab1cba2bc5", "置局サポート業務"),
]
MEMO = "\n\n[運用メモ 2026-06-18]\n2026-06-14〜15のmail_pipeline dedup破損で過去終了案件が新着再登録された汚染データと判定。再募集ではないため終了化。"

# Inspect first to know prop types
first_id = TARGETS[0][0]
r = requests.get(f"https://api.notion.com/v1/pages/{first_id}", headers=HEADERS, timeout=20)
print(f"GET first: {r.status_code}")
props = r.json().get("properties", {})

# detect status type
sp = props.get("ステータス", {})
if "status" in sp:
    stype = "status"
elif "select" in sp:
    stype = "select"
else:
    print("ERR: status prop not found")
    sys.exit(1)
print(f"status type: {stype}")

# detail key
DETAIL = None
for k, v in props.items():
    if "rich_text" in v and ("詳細" in k or "本文" in k or "メール" in k):
        DETAIL = k
        break
print(f"detail key: {DETAIL}")

# Update each
results = []
for pid, title in TARGETS:
    print(f"\n--- {title[:40]} ---")
    g = requests.get(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, timeout=20)
    if g.status_code != 200:
        print(f"  GET fail: {g.status_code}")
        results.append((pid, "GET_FAIL"))
        continue
    gp = g.json().get("properties", {})

    body = {"properties": {}}
    if stype == "status":
        body["properties"]["ステータス"] = {"status": {"name": "終了"}}
    else:
        body["properties"]["ステータス"] = {"select": {"name": "終了"}}

    if DETAIL:
        existing = gp.get(DETAIL, {}).get("rich_text", [])
        existing_text = "".join([t.get("plain_text", "") for t in existing])
        new_text = existing_text + MEMO
        chunks = []
        for i in range(0, len(new_text), 2000):
            chunks.append({"type": "text", "text": {"content": new_text[i : i + 2000]}})
        body["properties"][DETAIL] = {"rich_text": chunks}

    pr = requests.patch(f"https://api.notion.com/v1/pages/{pid}", headers=HEADERS, json=body, timeout=20)
    if pr.status_code == 200:
        print("  OK")
        results.append((pid, "OK"))
    else:
        print(f"  FAIL {pr.status_code}: {pr.text[:200]}")
        results.append((pid, f"FAIL_{pr.status_code}"))
    time.sleep(0.4)

print("\n=== DONE ===")
ok = sum(1 for _, s in results if s == "OK")
print(f"OK: {ok}/{len(TARGETS)}")
for pid, status in results:
    print(f"  [{status}] {pid[:18]}")
