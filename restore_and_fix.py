"""
エンジニアDB ゴミ箱復元 + cleanup条件修正確認
実行: python restore_and_fix.py
"""

import time

import requests

NOTION_KEY = "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"
ENGINEER_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}


# ゴミ箱から全件取得
def query_trash():
    all_pages = []
    cursor = None
    while True:
        payload = {"page_size": 100, "in_trash": True}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=HEADERS, json=payload, timeout=30
        )
        data = r.json()
        pages = data.get("results", [])
        all_pages.extend(pages)
        print(f"  ゴミ箱取得中... {len(all_pages)}件", flush=True)
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return all_pages


# 現在のDB件数確認
def query_active():
    all_pages = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        r = requests.post(
            f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=HEADERS, json=payload, timeout=30
        )
        data = r.json()
        all_pages.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return all_pages


print("=== ゴミ箱復元スクリプト ===", flush=True)
print("現在のアクティブ件数確認中...", flush=True)
active = query_active()
print(f"現在アクティブ: {len(active)}件", flush=True)

print("ゴミ箱内ページ取得中...", flush=True)
trash = query_trash()
print(f"ゴミ箱内: {len(trash)}件", flush=True)

if not trash:
    print("ゴミ箱にページなし。終了。", flush=True)
    exit()

print(f"\n{len(trash)}件を復元します...", flush=True)
restored = 0
errors = 0
for i, p in enumerate(trash):
    name = ""
    try:
        name = p["properties"]["名前"]["title"][0]["plain_text"]
    except:
        name = p["id"]

    r = requests.patch(
        f"https://api.notion.com/v1/pages/{p['id']}", headers=HEADERS, json={"in_trash": False}, timeout=15
    )
    if r.status_code == 200:
        restored += 1
    else:
        errors += 1
        print(f"  エラー: {name} status={r.status_code}", flush=True)

    if (i + 1) % 100 == 0:
        print(f"  進捗: {i + 1}/{len(trash)} 復元={restored} エラー={errors}", flush=True)
    time.sleep(0.35)

print("\n=== 完了 ===", flush=True)
print(f"復元: {restored}件 / エラー: {errors}件", flush=True)
print(f"最終アクティブ件数: {len(active) + restored}件（推定）", flush=True)
