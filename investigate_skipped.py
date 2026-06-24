"""
skipped 4件（備考に送信元なし）の実態調査
- 何の情報が入っているか全フィールド確認
- LINE登録パターンの洗い出し
"""

import sys

sys.stdout.reconfigure(encoding="utf-8")


import requests
from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
NOTION_TOKEN = env.get("NOTION_API_KEY") or env.get("NOTION_TOKEN")
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


# 全件取得（備考フィールドを含む全プロパティ）
def get_all_engineers():
    results = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=headers, json=payload)
        data = r.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def get_prop(page, name):
    p = page["properties"].get(name, {})
    t = p.get("type", "")
    if t == "title":
        items = p.get("title", [])
        return "".join(i.get("plain_text", "") for i in items)
    elif t == "rich_text":
        items = p.get("rich_text", [])
        return "".join(i.get("plain_text", "") for i in items)
    elif t == "email":
        return p.get("email") or ""
    elif t == "select":
        sel = p.get("select")
        return sel.get("name", "") if sel else ""
    elif t == "date":
        d = p.get("date")
        return d.get("start", "") if d else ""
    return ""


pages = get_all_engineers()
print(f"総件数: {len(pages)}")
print("=" * 80)

# 備考（送信元）の分布を確認
from collections import Counter

备考_patterns = []

print("\n【全件: 備考フィールドの内容】")
for i, p in enumerate(pages):
    name = get_prop(p, "名前")
    biko = get_prop(p, "備考")
    source = get_prop(p, "input_source") if "input_source" in p["properties"] else ""
    initial = get_prop(p, "イニシャル")
    affil_mail = get_prop(p, "所属メール")
    affil_person = get_prop(p, "所属担当者名")
    page_id = p["id"]

    has_sender = "送信元:" in biko or "送信元：" in biko

    print(f"\n[{i + 1:02d}] 名前={name!r}  initial={initial!r}  source={source!r}")
    print(f"      所属メール={affil_mail!r}  所属担当者={affil_person!r}")
    print(f"      備考={biko[:120]!r}")
    print(f"      page_id={page_id}")

    備考_patterns.append("送信元あり" if has_sender else "送信元なし")

print("\n" + "=" * 80)
c = Counter(備考_patterns)
print("\n【送信元の有無】")
for k, v in c.items():
    print(f"  {k}: {v}件")

# 送信元なしの詳細
print("\n" + "=" * 80)
print("\n【送信元なし の詳細（全フィールド）】")
for i, p in enumerate(pages):
    biko = get_prop(p, "備考")
    has_sender = "送信元:" in biko or "送信元：" in biko
    if not has_sender:
        name = get_prop(p, "名前")
        source = get_prop(p, "input_source") if "input_source" in p["properties"] else ""

        print(f"\n--- 送信元なし [{i + 1}] ---")
        print(f"  page_id: {p['id']}")
        for prop_name, prop_val in p["properties"].items():
            val = get_prop(p, prop_name)
            if val:
                print(f"  {prop_name}: {val!r}")
        print(f"  備考（full）: {biko!r}")
        # created_timeも確認
        print(f"  created_time: {p.get('created_time', '')}")
        print(f"  last_edited_time: {p.get('last_edited_time', '')}")
