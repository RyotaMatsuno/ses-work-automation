import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# line_webhook の line_query.py を直接インポート（line_query/ではなくline_webhook/）
import importlib.util

spec = importlib.util.spec_from_file_location(
    "line_query_webhook", r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\line_query.py"
)
lq = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lq)

sys.stdout.buffer.write(f"PROP_STATUS: {lq.PROP_STATUS!r}\n".encode("utf-8"))
sys.stdout.buffer.write(f"VAL_RECRUITING: {lq.VAL_RECRUITING!r}\n".encode("utf-8"))

# 案件DBから1件取得してステータスを確認
import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

res = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5},
)
projects = res.json().get("results", [])
for p in projects[:3]:
    status = lq._select_prop(p, lq.PROP_STATUS)
    name = lq._text_prop(p, lq.PROP_PJNAME)
    match = status == lq.VAL_RECRUITING
    sys.stdout.buffer.write(f"  {name[:20]!r}: status={status!r} match={match}\n".encode("utf-8"))
