import sys

sys.stdout.reconfigure(encoding="utf-8")
from collections import Counter

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
        return "".join(i.get("plain_text", "") for i in p.get("title", []))
    elif t == "rich_text":
        return "".join(i.get("plain_text", "") for i in p.get("rich_text", []))
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
print(f"Total engineers: {len(pages)}")
print("=" * 80)

# 全件の備考・送信元パターン確認
biko_pattern_list = []

print("\n[ALL RECORDS: biko field]")
for i, p in enumerate(pages):
    name = get_prop(p, "name") or get_prop(p, "\u540d\u524d")
    biko = get_prop(p, "biko") or get_prop(p, "\u5099\u8003")
    initial = get_prop(p, "initial") or get_prop(p, "\u30a4\u30cb\u30b7\u30e3\u30eb")
    affil_mail = get_prop(p, "affil_mail") or get_prop(p, "\u6240\u5c5e\u30e1\u30fc\u30eb")
    affil_person = get_prop(p, "affil_person") or get_prop(p, "\u6240\u5c5e\u62c5\u5f53\u8005\u540d")

    # input_source があれば取得
    source_val = ""
    for key in p["properties"]:
        if "source" in key.lower() or "input" in key.lower():
            source_val = get_prop(p, key)
            break

    has_sender = "\u9001\u4fe1\u5143:" in biko or "\u9001\u4fe1\u5143\uff1a" in biko
    pattern = "has_sender" if has_sender else "no_sender"
    biko_pattern_list.append(pattern)

    print(f"\n[{i + 1:02d}] name={name!r} initial={initial!r} source={source_val!r}")
    print(f"      affil_mail={affil_mail!r} affil_person={affil_person!r}")
    print(f"      biko={biko[:150]!r}")
    print(f"      page_id={p['id']}")
    print(f"      created={p.get('created_time', '')}")

print("\n" + "=" * 80)
cnt = Counter(biko_pattern_list)
print("\n[SENDER PATTERN SUMMARY]")
for k, v in cnt.items():
    print(f"  {k}: {v} records")

print("\n" + "=" * 80)
print("\n[NO SENDER RECORDS - FULL DETAIL]")
for i, p in enumerate(pages):
    biko = get_prop(p, "biko") or get_prop(p, "\u5099\u8003")
    has_sender = "\u9001\u4fe1\u5143:" in biko or "\u9001\u4fe1\u5143\uff1a" in biko
    if not has_sender:
        print(f"\n--- no_sender [{i + 1}] page_id={p['id']} ---")
        # 全プロパティ出力
        for prop_name in p["properties"]:
            val = get_prop(p, prop_name)
            if val:
                print(f"  [{prop_name}] = {val!r}")
        print(f"  biko_full={biko!r}")
        print(f"  created={p.get('created_time', '')}")
        print(f"  last_edited={p.get('last_edited_time', '')}")

# プロパティ名の一覧も出力（最初の1件）
if pages:
    print("\n" + "=" * 80)
    print("\n[PROPERTY NAMES in DB]")
    for k in pages[0]["properties"]:
        print(f"  {k!r} -> type={pages[0]['properties'][k].get('type', '')}")
