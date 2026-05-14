
"""
エンジニアDB残件削除 - タイムアウト強化版
"""
import requests, time, sys
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import dotenv_values
from pathlib import Path

ENV_PATH = Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

CUTOFF = "2026-05-09"

def query_all():
    all_pages = []
    cursor = None
    while True:
        payload = {"page_size": 100}
        if cursor:
            payload["start_cursor"] = cursor
        for attempt in range(3):
            r = requests.post(
                f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
                headers=HEADERS, json=payload, timeout=30
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
    return all_pages

print("残件確認中...", flush=True)
all_pages = query_all()
targets = [p for p in all_pages if p["created_time"][:10] < CUTOFF]
print(f"総件数: {len(all_pages)} / 削除対象残り: {len(targets)}件", flush=True)

if len(targets) == 0:
    print("削除対象なし。完了済みです。", flush=True)
    sys.exit(0)

print("削除開始...", flush=True)
deleted = errors = 0
for i, p in enumerate(targets):
    for attempt in range(5):
        try:
            r = requests.patch(
                f"https://api.notion.com/v1/pages/{p['id']}",
                headers=HEADERS, json={"in_trash": True}, timeout=30
            )
            if r.status_code == 200:
                deleted += 1
                break
            time.sleep(2)
        except Exception as e:
            time.sleep(3)
    else:
        errors += 1
    if (i + 1) % 20 == 0:
        print(f"  進捗: {i+1}/{len(targets)} 削除={deleted} エラー={errors}", flush=True)
    time.sleep(0.5)

print(f"完了: {deleted}件削除 / {errors}件エラー", flush=True)
