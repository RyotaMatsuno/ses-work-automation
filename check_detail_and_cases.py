# -*- coding: utf-8 -*-
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. 「詳細①」がどこで処理されているか確認
WS = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\line_webhook\webhook_server.py")
content = WS.read_text(encoding="utf-8")

# process_message内で「詳細」が処理される前にline_bridge.route_line_messageに捕まっていないか
idx = content.find("route_line_message")
print("=== route_line_message の呼び出し箇所 ===")
for i, line in enumerate(content.splitlines(), 1):
    if "route_line_message" in line or "handle_line_query" in line or "詳細" in line:
        print(f"L{i}: {line.strip()[:100]}")

print()

# 2. 今日の案件DB登録状況（mail_pipelineからの登録件数）
import urllib.request

from dotenv import dotenv_values

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
CASE_DB = "343450ff-37c0-81e4-934e-f25f90284a3c"


def npost(path, payload):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/{path}",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


today = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")
print(f"=== 本日({today})の案件DB登録状況 ===")

# 今日作成された案件
cursor = None
results = []
while True:
    payload = {
        "filter": {"timestamp": "created_time", "created_time": {"on_or_after": f"{today}T00:00:00+09:00"}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 100,
    }
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{CASE_DB}/query", payload)
    results.extend(res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

print(f"本日登録件数: {len(results)}件")

# 入力元別集計
from collections import Counter

src_count = Counter()
for page in results:
    props = page["properties"]
    src = (props.get("入力元", {}).get("select") or {}).get("name", "不明")
    src_count[src] += 1
for src, cnt in src_count.most_common():
    print(f"  {src}: {cnt}件")

# mail_pipelineのログから今日の案件登録件数も確認
log = Path(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\mail_pipeline\pipeline.log")
if log.exists():
    lines = log.read_text(encoding="utf-8", errors="replace").splitlines()
    today_lines = [l for l in lines if l.startswith(f"[{today}")]
    registered = [l for l in today_lines if "案件登録" in l or "project" in l.lower() or "登録完了" in l]
    print(f"\nmail_pipeline 本日ログ: {len(today_lines)}行")
    print(f"  案件登録関連: {len(registered)}件")
    for l in registered[:5]:
        print(f"  {l[:100]}")
