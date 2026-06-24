# -*- coding: utf-8 -*-
import json
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

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


def npatch_status(page_id):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/pages/{page_id}",
        data=json.dumps({"properties": {"ステータス": {"select": {"name": "募集中"}}}}, ensure_ascii=False).encode(),
        headers=HEADERS,
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.status


def gtxt(p):
    if not p:
        return ""
    t = p.get("type", "")
    if t == "title":
        return "".join(x.get("plain_text", "") for x in p.get("title", []))
    if t == "rich_text":
        return "".join(x.get("plain_text", "") for x in p.get("rich_text", []))
    if t == "select":
        return (p.get("select") or {}).get("name", "")
    if t == "number":
        return p.get("number")
    if t == "date":
        return (p.get("date") or {}).get("start", "")
    return ""


# 選考中の全page_idを収集
print("=== 選考中ページID収集 ===")
page_ids = []
cursor = None
while True:
    payload = {"filter": {"property": "ステータス", "select": {"equals": "選考中"}}, "page_size": 100}
    if cursor:
        payload["start_cursor"] = cursor
    res = npost(f"databases/{CASE_DB}/query", payload)
    page_ids.extend(p["id"] for p in res.get("results", []))
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")
print(f"対象: {len(page_ids)}件")

# 並列更新
print("並列更新中...")
ok = err = 0
with ThreadPoolExecutor(max_workers=10) as ex:
    futures = {ex.submit(npatch_status, pid): pid for pid in page_ids}
    for f in futures:
        try:
            f.result()
            ok += 1
        except Exception:
            err += 1
print(f"完了: 成功{ok}件 / エラー{err}件")

# 稼働中 詳細
print("\n=== 稼働中 詳細 ===")
res2 = npost(
    f"databases/{CASE_DB}/query",
    {
        "filter": {"property": "ステータス", "select": {"equals": "稼働中"}},
        "sorts": [{"timestamp": "created_time", "direction": "descending"}],
        "page_size": 20,
    },
)
for page in res2.get("results", []):
    p = page["properties"]
    print(f"案件名: {gtxt(p.get('案件名', {}))}")
    price = gtxt(p.get("単価（万円）", {}))
    print(
        f"  単価:{price}万 | 担当:{gtxt(p.get('担当者', {}))} | 登録:{gtxt(p.get('情報取得日', {})) or page.get('created_time', '')[:10]}"
    )
    print(f"  クライアント:{gtxt(p.get('クライアント', {}))} | 勤務地:{gtxt(p.get('勤務地', {}))}")
    req = [o["name"] for o in p.get("必要スキル", {}).get("multi_select", [])]
    print(f"  必須スキル:{req}")
    print()
