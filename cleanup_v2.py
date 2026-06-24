"""
エンジニアDB旧データ一括削除 - エラーハンドリング強化版
"""

import sys
import time
from pathlib import Path

import requests
from dotenv import dotenv_values

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

CUTOFF = "2026-05-09"


# --- 全件取得（リトライ付き） ---
def query_all():
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
            if r.status_code == 200 and r.text.strip():
                break
            print(f"  クエリリトライ {attempt + 1}/3 status={r.status_code}", flush=True)
            time.sleep(2)
        else:
            print("クエリ失敗。終了。", flush=True)
            sys.exit(1)
        data = r.json()
        all_pages.extend(data.get("results", []))
        print(f"  取得中... {len(all_pages)}件", flush=True)
        if not data.get("has_more"):
            break
        cursor = data["next_cursor"]
        time.sleep(0.3)
    return all_pages


print("全件取得開始...", flush=True)
all_pages = query_all()
targets = [p for p in all_pages if p["created_time"][:10] < CUTOFF]
keeps = [p for p in all_pages if p["created_time"][:10] >= CUTOFF]

print(f"総件数: {len(all_pages)}", flush=True)
print(f"削除対象: {len(targets)}件 / 保持: {len(keeps)}件", flush=True)

# --- 削除実行 ---
print("削除開始...", flush=True)
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

print(f"完了: {deleted}件削除 / {errors}件エラー", flush=True)
