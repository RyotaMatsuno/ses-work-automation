import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

print("全件取得開始...", flush=True)
all_pages = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    for attempt in range(3):
        r = requests.post(
            f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=HEADERS, json=payload, timeout=30
        )
        if r.status_code == 200:
            break
        time.sleep(2)
    data = r.json()
    all_pages.extend(data.get("results", []))
    print(f"  取得中... {len(all_pages)}件", flush=True)
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]
    time.sleep(0.3)

# 削除対象: 備考に「メールから自動登録」が含まれるもの
targets = []
keeps = []
for p in all_pages:
    props = p["properties"]
    note_items = props.get("備考（LINEメモ）", {}).get("rich_text", [])
    note = note_items[0]["plain_text"] if note_items else ""
    if "メールから自動登録" in note:
        targets.append(p)
    else:
        keeps.append(p)

print(f"総件数: {len(all_pages)}", flush=True)
print(f"削除対象（メール経由）: {len(targets)}件", flush=True)
print(f"保持（LINE/その他）: {len(keeps)}件", flush=True)

# 保持レコードのサンプル表示
print("\n--- 保持するエンジニア（全件）---", flush=True)
for p in keeps:
    props = p["properties"]
    name_items = props.get("名前", {}).get("title", [])
    name = name_items[0]["plain_text"] if name_items else "?"
    print(f"  {name}", flush=True)

print("\n削除開始...", flush=True)
deleted = 0
errors = 0
for i, p in enumerate(targets):
    for attempt in range(3):
        r = requests.patch(
            f"https://api.notion.com/v1/pages/{p['id']}", headers=HEADERS, json={"in_trash": True}, timeout=15
        )
        if r.status_code == 200:
            deleted += 1
            break
        print(f"  リトライ {attempt + 1}/3 pid={p['id']} status={r.status_code}", flush=True)
        time.sleep(1)
    else:
        errors += 1
    if (i + 1) % 100 == 0:
        print(f"  進捗: {i + 1}/{len(targets)} 削除={deleted} エラー={errors}", flush=True)
    time.sleep(0.35)

print(f"\n完了: {deleted}件削除 / {errors}件エラー", flush=True)
print(f"残存エンジニア数: {len(keeps)}件", flush=True)
