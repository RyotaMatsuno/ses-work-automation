
"""
1. テストページ削除
2. 案件DBの(no title)ページ実態調査
3. エンジニアDBの(no title)ページ実態調査
"""
import requests
import os
import json
from dotenv import dotenv_values
from pathlib import Path

ENV_PATH = Path(r'C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env')
config = dotenv_values(ENV_PATH)
NOTION_KEY = config.get("NOTION_API_KEY", "")
PROJECT_DB = config.get("NOTION_PROJECT_DB_ID", "")
ENGINEER_DB = config.get("NOTION_ENGINEER_DB_ID", "")

HEADERS = {
    "Authorization": f"Bearer {NOTION_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}

# 1. テストページ削除
test_page_id = "35b450ff-37c0-8103-9539-efcc749cd77e"
r = requests.patch(
    f"https://api.notion.com/v1/pages/{test_page_id}",
    headers=HEADERS, json={"in_trash": True}
)
print(f"テストページ削除: {r.status_code}")

# 2. 案件DB の最近ページを確認（タイトルなし問題の調査）
r2 = requests.post(
    f"https://api.notion.com/v1/databases/{PROJECT_DB}/query",
    headers=HEADERS,
    json={"page_size": 10, "sorts": [{"property": "案件名", "direction": "descending"}]}
)
pages = r2.json().get("results", [])
print(f"\n=== 案件DB 最新10件 ===")
for p in pages:
    title_list = p["properties"].get("案件名", {}).get("title", [])
    name = title_list[0]["plain_text"] if title_list else "(no title)"
    detail_list = p["properties"].get("案件詳細", {}).get("rich_text", [])
    detail = detail_list[0]["plain_text"][:80] if detail_list else "(詳細なし)"
    created = p["created_time"][:10]
    print(f"  [{created}] 「{name}」 | 詳細: {detail[:60]}")

# 3. エンジニアDB 最新10件
r3 = requests.post(
    f"https://api.notion.com/v1/databases/{ENGINEER_DB}/query",
    headers=HEADERS,
    json={"page_size": 10, "sorts": [{"property": "名前", "direction": "descending"}]}
)
eng_pages = r3.json().get("results", [])
print(f"\n=== エンジニアDB 最新10件 ===")
for p in eng_pages:
    title_list = p["properties"].get("名前", {}).get("title", [])
    name = title_list[0]["plain_text"] if title_list else "(no title)"
    note_list = p["properties"].get("備考（LINEメモ）", {}).get("rich_text", [])
    note = note_list[0]["plain_text"][:60] if note_list else "(メモなし)"
    created = p["created_time"][:10]
    print(f"  [{created}] 「{name}」 | {note[:50]}")
