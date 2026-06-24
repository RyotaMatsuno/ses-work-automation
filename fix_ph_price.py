# -*- coding: utf-8 -*-
import json
import sys
import urllib.request

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

env = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
TOKEN = env.get("NOTION_API_KEY", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}
ENG_DB = "343450ff-37c0-819d-8769-fb0a8a4ceeb1"


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


# PHさんのページIDを取得
cursor = None
while True:
    payload = {"page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{ENG_DB}/query", payload)
    for page in res.get("results", []):
        props = page["properties"]
        name_p = props.get("名前", {})
        name = "".join(x.get("plain_text", "") for x in name_p.get("title", []))
        if name == "P.H":
            page_id = page["id"]
            current_price = props.get("単価（万円）", {}).get("number")
            print(f"P.H 発見: page_id={page_id} 現在単価={current_price}万")
            # 37万に更新
            npatch(f"pages/{page_id}", {"properties": {"単価（万円）": {"number": 37}}})
            print("✅ 単価を37万に更新しました")
            break
    else:
        if res.get("has_more"):
            cursor = res.get("next_cursor")
            continue
        print("P.H が見つかりません")
    break
