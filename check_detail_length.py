# -*- coding: utf-8 -*-
# 各案件の案件詳細（生テキスト）の文字数を計測
import sys

sys.path.insert(0, r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook")
from dotenv import dotenv_values

from line_query import _text_prop, business_days_since, fetch_all_pages

ENV_PATH = r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env"
CONFIG = dotenv_values(ENV_PATH)
PROJECT_DB_ID = CONFIG.get("PROJECT_DB_ID") or CONFIG.get("NOTION_PROJECT_DB_ID") or ""

pages = fetch_all_pages(PROJECT_DB_ID, filter_body={"property": "ステータス", "select": {"equals": "募集中"}})

total_chars = 0
lengths = []
for p in pages:
    if business_days_since(p.get("last_edited_time")) > 4:
        continue
    detail = _text_prop(p, "案件詳細")
    lengths.append(len(detail))
    total_chars += len(detail)

lengths.sort(reverse=True)
print(f"有効案件数: {len(lengths)}", flush=True)
print(f"詳細文字数 最大: {lengths[0] if lengths else 0}", flush=True)
print(f"詳細文字数 中央値: {lengths[len(lengths) // 2] if lengths else 0}", flush=True)
print(f"詳細文字数 平均: {total_chars // len(lengths) if lengths else 0}", flush=True)
print(f"全文表示した場合の総文字数（詳細のみ）: {total_chars}", flush=True)
print(f"上位10件の文字数: {lengths[:10]}", flush=True)
