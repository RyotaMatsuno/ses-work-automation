# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"
JST = timezone(timedelta(hours=9))
today = datetime.now(JST).strftime("%Y-%m-%d")


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


def gtxt(p):
    if not p:
        return ""
    t = p.get("type", "")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    if t == "checkbox":
        return p.get("checkbox", False)
    return ""


# 1. 情報取得日が空のエンジニアを全件スキャン
print(f"=== 情報取得日が空のエンジニアを更新（today={today}）===")
cursor = None
updated = []
skipped = []

while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{ENG_DB}/query", payload)

    for page in res.get("results", []):
        props = page["properties"]
        page_id = page["id"]
        name = gtxt(props.get("名前", {}))
        info_date = gtxt(props.get("情報取得日", {}))
        is_target = props.get("提案対象フラグ", {}).get("checkbox", False)

        # 情報取得日が空 かつ 提案対象フラグTrue のエンジニアを更新
        if not info_date and is_target:
            try:
                npatch(f"pages/{page_id}", {"properties": {"情報取得日": {"date": {"start": today}}}})
                updated.append(name or page_id[:8])
                print(f"  更新: {name or page_id[:8]} → 情報取得日={today}")
            except Exception as e:
                print(f"  エラー: {name} → {e}")
        elif not info_date and not is_target:
            skipped.append(name or page_id[:8])

    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

print(f"\n完了: 更新={len(updated)}件 / スキップ(提案対象外)={len(skipped)}件")
print(f"更新済み: {updated}")
