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
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


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


def fetch_all(db_id, filter_obj=None):
    results, cursor = [], None
    while True:
        payload = {"page_size": 100}
        if filter_obj:
            payload["filter"] = filter_obj
        if cursor:
            payload["start_cursor"] = cursor
        res = npost(f"databases/{db_id}/query", payload)
        results.extend(res.get("results", []))
        if not res.get("has_more"):
            break
        cursor = res.get("next_cursor")
    return results


# 1. PHさんのNotionレコードに #skill_skip を追記
print("=== PHさんに #skill_skip タグを追記 ===")
eng_pages = fetch_all(ENG_DB)
for page in eng_pages:
    props = page["properties"]
    name = "".join(x.get("plain_text", "") for x in props.get("名前", {}).get("title", []))
    if name == "P.H":
        note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
        current_note = note_items[0].get("plain_text", "") if note_items else ""
        if "#skill_skip" not in current_note:
            new_note = current_note + "\n#skill_skip" if current_note else "#skill_skip"
            npatch(
                f"pages/{page['id']}",
                {"properties": {"備考（LINEメモ）": {"rich_text": [{"text": {"content": new_note[:2000]}}]}}},
            )
            print("✅ #skill_skip 追記完了")
        else:
            print("✅ 既に #skill_skip あり")
        break

# 2. PHさん（37万、単価37〜50万）で全件マッチングトレース
print("\n=== PHさん(37万) 全案件マッチングトレース ===")
all_cases = fetch_all(
    CASE_DB,
    {
        "or": [
            {"property": "ステータス", "select": {"equals": "募集中"}},
            {"property": "ステータス", "select": {"equals": "稼働中"}},
            {"property": "ステータス", "select": {"equals": "選考中"}},
        ]
    },
)
print(f"取得案件数: {len(all_cases)}件")

eng_price = 37
matched = []
skip_price_low = 0  # 単価37万未満（粗利0以下）
skip_price_high = 0  # 単価50万超
skip_no_price = 0  # 単価未入力
passed = 0

for page in all_cases:
    props = page["properties"]
    name = "".join(x.get("plain_text", "") for x in props.get("案件名", {}).get("title", []))
    proj_price = props.get("単価（万円）", {}).get("number") or 0
    skills = [o["name"] for o in props.get("必要スキル", {}).get("multi_select", [])]

    # 単価フィルタ（37〜50万）
    if proj_price == 0:
        skip_no_price += 1
        continue
    if proj_price < 37:
        skip_price_low += 1
        continue
    if proj_price > 50:
        skip_price_high += 1
        continue

    # ここまで来たら粗利OK（スキルフィルタは #skill_skip で除外）
    gross = proj_price - eng_price
    passed += 1
    matched.append({"name": name, "price": proj_price, "gross": gross, "skills": skills})

print(f"\n単価未入力: {skip_no_price}件（スキップ）")
print(f"単価37万未満: {skip_price_low}件（粗利不足でスキップ）")
print(f"単価50万超: {skip_price_high}件（上限超でスキップ）")
print(f"\nマッチ: {passed}件")
print("\nマッチ案件一覧（上位10件）:")
for m in sorted(matched, key=lambda x: x["gross"], reverse=True)[:10]:
    print(f"  {m['name'][:40]:<40} | {m['price']}万 | 粗利{m['gross']}万 | 必須:{m['skills']}")
