import sys

import requests
from dotenv import dotenv_values

cfg = dotenv_values(r"C:\Users\ma_py\OneDrive\デスクトップ\ses_work\config\.env")
token = cfg.get("NOTION_API_KEY") or cfg.get("NOTION_TOKEN")
headers = {"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28", "Content-Type": "application/json"}

# テスト1: ステータス=募集中 のみ
filt1 = {"property": "\u30b9\u30c6\u30fc\u30bf\u30b9", "select": {"equals": "\u52df\u96c6\u4e2d"}}
res1 = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5, "filter": filt1},
)
d1 = res1.json()
sys.stdout.buffer.write(
    f"Filter test1 (status=募集中): total_count_approx={len(d1.get('results', []))}, has_more={d1.get('has_more')}\n".encode(
        "utf-8"
    )
)
if d1.get("results"):
    p = d1["results"][0]
    st = (p.get("properties", {}).get("\u30b9\u30c6\u30fc\u30bf\u30b9", {}).get("select") or {}).get("name")
    sys.stdout.buffer.write(f"  first result status: {st!r}\n".encode("utf-8"))

# テスト2: ステータス=終了 のみ
filt2 = {"property": "\u30b9\u30c6\u30fc\u30bf\u30b9", "select": {"equals": "\u7d42\u4e86"}}
res2 = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5, "filter": filt2},
)
d2 = res2.json()
sys.stdout.buffer.write(
    f"Filter test2 (status=終了): results={len(d2.get('results', []))}, has_more={d2.get('has_more')}\n".encode("utf-8")
)

# テスト3: 単価>=75 のみ
filt3 = {"property": "\u5358\u4fa1\uff08\u4e07\u5186\uff09", "number": {"greater_than_or_equal_to": 75}}
res3 = requests.post(
    "https://api.notion.com/v1/databases/343450ff-37c0-81e4-934e-f25f90284a3c/query",
    headers=headers,
    json={"page_size": 5, "filter": filt3},
)
d3 = res3.json()
sys.stdout.buffer.write(
    f"Filter test3 (rate>=75): results={len(d3.get('results', []))}, has_more={d3.get('has_more')}\n".encode("utf-8")
)
if d3.get("results"):
    p = d3["results"][0]
    rate = (p.get("properties", {}).get("\u5358\u4fa1\uff08\u4e07\u5186\uff09", {}) or {}).get("number")
    sys.stdout.buffer.write(f"  first result rate: {rate}\n".encode("utf-8"))
