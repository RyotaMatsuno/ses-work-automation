"""
エンジニアDB旧データ一括削除スクリプト（dry-run確認用）
2026-05-08以前に作成されたページをゴミ箱に移す
実行前に必ずdry_run=Trueで確認してから dry_run=Falseに変更すること
"""

import time
from pathlib import Path

import requests
from dotenv import dotenv_values

DRY_RUN = True  # ← 実行時はFalseに変更

ENV_PATH = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {"Authorization": f"Bearer {NOTION_KEY}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

CUTOFF = "2026-05-09"  # これ以前を削除対象

all_pages = []
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    r = requests.post(f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query", headers=HEADERS, json=payload)
    data = r.json()
    all_pages.extend(data.get("results", []))
    if not data.get("has_more"):
        break
    cursor = data["next_cursor"]

targets = [p for p in all_pages if p["created_time"][:10] < CUTOFF]
keeps = [p for p in all_pages if p["created_time"][:10] >= CUTOFF]

print(f"総件数: {len(all_pages)}")
print(f"削除対象 ({CUTOFF}以前): {len(targets)}件")
print(f"保持 ({CUTOFF}以降): {len(keeps)}件")
for p in keeps:
    title_list = p["properties"].get("名前", {}).get("title", [])
    name = title_list[0]["plain_text"] if title_list else "(no title)"
    print(f"  [保持] {p['created_time'][:10]} {name}")

if DRY_RUN:
    print("\n[DRY RUN] 実際の削除は行いません。")
    print("実行するには dry_run=False にしてください。")
else:
    print("\n削除開始...")
    deleted = 0
    errors = 0
    for p in targets:
        r = requests.patch(f"https://api.notion.com/v1/pages/{p['id']}", headers=HEADERS, json={"in_trash": True})
        if r.status_code == 200:
            deleted += 1
        else:
            errors += 1
            print(f"  ERROR {r.status_code}: {p['id']}")
        if deleted % 50 == 0:
            print(f"  {deleted}/{len(targets)} 削除済み...")
        time.sleep(0.35)  # Notion API レート制限対策
    print(f"完了: {deleted}件削除, {errors}件エラー")
